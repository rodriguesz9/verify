"""Content Credentials: binary strings are hints, never signature validation."""
import json
import os
import shutil
import tempfile
from pathlib import Path
from app.services.media_validation import run_media_tool

C2PA_MARKERS = [b"c2pa", b"jumb", b"c2pa.assertions", b"c2pa.actions"]
AI_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
ACTION_ASSERTIONS = {"c2pa.actions", "c2pa.actions.v2"}


def _scan_binary_c2pa_markers(file_bytes: bytes) -> dict:
    present = any(marker in file_bytes for marker in C2PA_MARKERS)
    return {"has_c2pa": present, "validation_state": "present_unverified_tool" if present else "none",
            "generative_ai_flag": False, "signer": None, "edit_history": [],
            "trust_homologated": False, "voting_eligible": False,
            "unverified_ai_marker": b"trainedAlgorithmicMedia" in file_bytes or b"c2pa.generative-ai" in file_bytes,
            "summary": "Possíveis marcadores C2PA; assinatura não validada." if present else
                       "Nenhuma credencial C2PA identificada. Sua ausência não implica falsificação."}


def parse_c2pa_report(data: dict, trust_configured=False) -> dict:
    """Parse a manifest; callers must establish trust independently of env presence.

    ``trust_configured=True`` is only an explicit trusted-parser input, never the
    application's runtime inference from C2PATOOL_TRUST_ANCHORS. The production
    adapter remains non-voting until tool/config/certificate validation has been
    homologated with real controls. Structure follows C2PA actions assertions:
    https://spec.c2pa.org/specifications/specifications/2.3/specs/C2PA_Specification.html
    """
    if not isinstance(data, dict):
        raise ValueError("Formato de manifesto desconhecido")
    active = data.get("active_manifest")
    manifests = data.get("manifests", {})
    manifest = manifests.get(active, {}) if isinstance(active, str) and isinstance(manifests, dict) else (active if isinstance(active, dict) else {})
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("Sem manifesto ativo")
    statuses = data.get("validation_status")
    if not isinstance(statuses, list):
        raise ValueError("Formato de validação desconhecido")
    assertions = manifest.get("assertions", [])
    if not isinstance(assertions, list):
        raise ValueError("Formato de assertivas desconhecido")
    histories = [assertion["data"] for assertion in assertions if isinstance(assertion, dict)
                 and isinstance(assertion.get("label"), str) and assertion["label"] in ACTION_ASSERTIONS
                 and isinstance(assertion.get("data"), dict)]
    # Only an explicit creation action's exact source type describes AI creation.
    # A mention in description, custom metadata, an ingredient or a software name
    # does not assert that this asset was created by generative AI.
    ai_claim = any(action.get("action") == "c2pa.created" and action.get("digitalSourceType") == AI_SOURCE_TYPE
                   for history in histories
                   for action in (history.get("actions") if isinstance(history.get("actions"), list) else [])
                   if isinstance(action, dict))
    trusted = trust_configured is True
    state = "invalid" if statuses else ("valid" if trusted else "present_unverified_trust")
    signature = manifest.get("signature_info", {})
    return {"has_c2pa": True, "validation_state": state,
            "generative_ai_flag": ai_claim if state == "valid" else False,
            "unverified_ai_marker": ai_claim if state != "valid" else False,
            "signer": signature.get("issuer") if isinstance(signature, dict) else None,
            "edit_history": histories,
            "trust_homologated": trusted and state == "valid", "voting_eligible": trusted and state == "valid",
            "summary": "Credencial validada com âncoras de confiança." if state == "valid" else
                       "Credencial não validada como confiável; não comprova origem ou autenticidade."}


async def verify_c2pa(file_bytes: bytes, filename="upload.jpg") -> dict:
    binary = shutil.which("c2patool")
    if binary and os.getenv("C2PATOOL_ENABLED", "true").lower() == "true":
        try:
            with tempfile.TemporaryDirectory(prefix="verify-c2pa-") as directory:
                path = Path(directory) / ("asset" + Path(filename).suffix[:10])
                path.write_bytes(file_bytes)
                # The CLI can read trust anchors from its environment, but env
                # presence alone does not certify a working trusted setup. Do
                # not run its network-fetching trust subcommand automatically.
                # No production path promotes this unhomologated layer to valid.
                output = await run_media_tool(binary, str(path))
            result = parse_c2pa_report(json.loads(output), trust_configured=False)
            return {**result, "tool_status": "success", "trust_homologated": False, "voting_eligible": False,
                    "reason": "Leitura C2PA disponível, mas ferramenta, âncoras e validação de confiança ainda não foram homologadas. Esta camada não participa do veredito."}
        except Exception:
            pass
    return _scan_binary_c2pa_markers(file_bytes)
