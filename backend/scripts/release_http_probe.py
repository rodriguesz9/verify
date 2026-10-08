"""Offline HTTP controls for local_release_server.py, never production."""

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8026")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pdf-output", required=True)
    args = parser.parse_args()
    target = urlsplit(args.base_url)
    if target.hostname not in {"127.0.0.1", "localhost"} or target.scheme != "http":
        parser.error("These fixture controls can run only against local HTTP.")
    records = []

    def record(name, response, expected=200, valid=True):
        ok = response.status_code == expected and bool(valid)
        row = {"case": name, "status": response.status_code, "expected": expected, "ok": ok}
        records.append(row)
        print(json.dumps(row), flush=True)
        if not ok:
            raise AssertionError(f"Local control failed: {name}")

    password = "Local-Test-Only-938!"
    async with httpx.AsyncClient(base_url=args.base_url, timeout=20) as client:
        response = await client.post("/api/auth/login", json={"email": "release-a@example.test", "password": password})
        record("login_a", response)
        found = []
        for page, count in ((1, 20), (2, 20), (3, 5)):
            response = await client.get("/api/history", params={"page": page, "limit": 20})
            body = response.json()
            record(f"page_{page}", response, valid=body["total"] == 45 and len(body["items"]) == count)
            found.extend(row["id"] for row in body["items"])
        assert len(set(found)) == 45
        response = await client.get("/api/history", params={"search": "marcador-fora-primeira-pagina"})
        record("global_search", response, valid=response.json()["total"] == 1)
        for kind in ("Text", "Url", "Image", "Audio", "Video"):
            response = await client.get("/api/history", params={"content_type": kind})
            body = response.json()
            record(f"filter_{kind.lower()}", response,
                   valid=body["total"] == 9 and all(row["content_type"] == kind for row in body["items"]))
        response = await client.get("/api/history", params={"content_type": "Image"})
        report_id = response.json()["items"][0]["id"]
        response = await client.get(f"/api/history/{report_id}")
        report = response.json()["raw_result"]
        record("owned_original_report", response, valid=bool(report.get("pdf_snapshot_token")))
        token = report["pdf_snapshot_token"]
        before = (await client.get("/api/history/stats")).json()["daily_used"]
        response = await client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": token})
        record("pdf_original_snapshot", response,
               valid=response.content.startswith(b"%PDF") and response.headers.get("cache-control") == "no-store")
        Path(args.pdf_output).write_bytes(response.content)
        after_response = await client.get("/api/history/stats")
        record("pdf_does_not_add_analysis", after_response, valid=after_response.json()["daily_used"] == before)
        changed = token[:-1] + ("0" if token[-1] != "0" else "1")
        response = await client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": changed})
        record("tampered_pdf_rejected", response, 422)
        response = await client.post("/api/verificar/relatorio-pdf", json={"report": report})
        record("unsigned_pdf_rejected", response, 422)
        response = await client.post("/api/verificar/relatorio-pdf", files={"file": ("control.png", b"not-media", "image/png")})
        record("pdf_reupload_rejected", response, 422)
        response = await client.get("/api/history/not-a-uuid")
        record("malformed_history_id", response, 422)
        response = await client.post("/api/auth/logout")
        record("logout_a", response, 204)
        response = await client.get("/api/history")
        record("history_requires_login", response, 401)
        response = await client.post("/api/auth/login", json={"email": "release-b@example.test", "password": password})
        record("login_b", response)
        response = await client.get("/api/history")
        record("account_b_isolated_history", response,
               valid=response.json()["total"] == 1 and response.json()["items"][0]["query_input"] == "SOMENTE-CONTA-B")
        response = await client.get(f"/api/history/{report_id}")
        record("account_b_cannot_read_a", response, 404)
        response = await client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": token})
        record("account_b_cannot_export_a", response, 403)
        response = await client.post("/api/auth/logout")
        record("logout_b", response, 204)
    Path(args.output).write_text(json.dumps({"scope": "local offline controls, not detector accuracy",
                                            "cases": records}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
