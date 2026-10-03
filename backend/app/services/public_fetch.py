"""Bounded public HTTP fetches. Validate DNS and connect to the validated IP."""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException


def _is_public_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        # Disallow transition mechanisms that can encode an unvalidated IPv4 peer.
        return ip.is_global and not ip.is_multicast and not (
            isinstance(ip, ipaddress.IPv6Address) and (ip.sixtofour or ip.teredo)
        )
    except ValueError:
        return False


def _resolve_public_host(hostname: str) -> list[str]:
    hostname = hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or "%" in hostname:
        raise HTTPException(400, "Endereço local não pode ser verificado.")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            addresses = list(dict.fromkeys(
                item[4][0] for item in socket.getaddrinfo(
                    hostname, None, type=socket.SOCK_STREAM
                )
            ))
        except (socket.gaierror, UnicodeError) as exc:
            raise HTTPException(400, "Não foi possível localizar o domínio informado.") from exc
    else:
        addresses = [str(literal)]
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise HTTPException(400, "Endereço privado ou reservado não pode ser verificado.")
    return addresses


def _parse_url(value: str) -> httpx.URL:
    if len(value) > 4096 or any(char.isspace() or ord(char) < 32 for char in value):
        raise HTTPException(400, "Informe uma URL pública válida, sem espaços.")
    try:
        url = httpx.URL(value)
        if (url.scheme not in {"http", "https"} or not url.host or url.userinfo
                or url.port not in {None, 80, 443} or "%" in url.host):
            raise ValueError("unsupported URL")
    except (httpx.InvalidURL, ValueError) as exc:
        raise HTTPException(400, "Informe uma URL pública http/https nas portas 80 ou 443, sem credenciais.") from exc
    return url.copy_with(fragment=None)


async def _validate_public_url(value: str) -> None:
    url = _parse_url(value)
    await asyncio.to_thread(_resolve_public_host, url.host)


@dataclass(frozen=True)
class FetchedResource:
    data: bytes
    content_type: str
    final_url: str
    encoding: str


async def fetch_public_resource(
    value: str, *, max_bytes: int, max_redirects: int = 0,
    allowed_types: set[str] | None = None, total_timeout: float = 20.0,
) -> FetchedResource:
    """No environment proxy, cookies, credentials or second hostname lookup.

    TLS verifies the original hostname via SNI. A fresh transport per hop avoids
    reusing a connection for unrelated domains sharing the same public IP.
    Compressed responses are refused to bound decompression as well as download.
    """
    try:
        async with asyncio.timeout(total_timeout):
            current = value
            for hop in range(max_redirects + 1):
                url = _parse_url(current)
                addresses = await asyncio.to_thread(_resolve_public_host, url.host)
                target = url.copy_with(host=addresses[0])
                transport = httpx.AsyncHTTPTransport(verify=True, trust_env=False, retries=0)
                async with httpx.AsyncClient(
                    transport=transport, trust_env=False, timeout=10.0,
                    follow_redirects=False,
                ) as client:
                    async with client.stream(
                        "GET", target,
                        headers={
                            "Host": url.netloc.decode("ascii"),
                            "User-Agent": "Verify/1.0",
                            "Accept-Encoding": "identity",
                        },
                        extensions={"sni_hostname": url.host},
                    ) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location or hop == max_redirects:
                                raise HTTPException(400, "Redirecionamento não permitido ou limite excedido.")
                            current = urljoin(str(url), location)
                            continue
                        if response.status_code >= 400:
                            raise HTTPException(400, f"O site recusou a consulta (HTTP {response.status_code}).")
                        encoding = response.headers.get("content-encoding", "identity").strip().lower()
                        if encoding not in {"", "identity"}:
                            raise HTTPException(415, "O site enviou conteúdo comprimido não suportado pela consulta segura.")
                        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                        if allowed_types is not None and content_type not in allowed_types:
                            raise HTTPException(415, "O link não retornou um documento de texto suportado.")
                        size = response.headers.get("content-length")
                        if size and size.isdigit() and int(size) > max_bytes:
                            raise HTTPException(413, "Conteúdo remoto excede o limite de tamanho.")
                        data = bytearray()
                        async for chunk in response.aiter_raw():
                            if len(data) + len(chunk) > max_bytes:
                                raise HTTPException(413, "Conteúdo remoto excede o limite de tamanho.")
                            data.extend(chunk)
                        return FetchedResource(
                            bytes(data), content_type, str(url), response.encoding or "utf-8"
                        )
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise HTTPException(504, "A consulta ao endereço público excedeu o tempo permitido.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(400, "Não foi possível consultar o endereço público com segurança.") from exc
    raise HTTPException(400, "A URL excedeu o limite de redirecionamentos.")
