"""Content Credentials: binary strings are hints, never signature validation."""
import json
import os
import shutil
import tempfile
from pathlib import Path
from app.services.media_validation import run_media_tool

C2PA_MARKERS = [b"c2pa", b"jumb", b"c2pa.assertions", b"c2pa.actions"]


def _scan_binary_c2pa_markers(file_bytes: bytes) -> dict:
    present = any(marker in file_bytes for marker in C2PA_MARKERS)
    return {"has_c2pa": present, "validation_state": "present_unverified_tool" if present else "none",
            "generative_ai_flag": False, "signer": None, "edit_history": [],
            "unverified_ai_marker": b"trainedAlgorithmicMedia" in file_bytes or b"c2pa.generative-ai" in file_bytes,
            "summary": "Possíveis marcadores C2PA; assinatura não validada." if present else
                       "Nenhuma credencial C2PA identificada. Sua ausência não implica falsificação."}


def parse_c2pa_report(data: dict, trust_configured=False) -> dict:
    active = data.get("active_manifest")
    manifest = data.get("manifests", {}).get(active, {}) if isinstance(active, str) else (active or {})
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("Sem manifesto ativo")
    statuses = data.get("validation_status")
    if not isinstance(statuses, list):
        raise ValueError("Formato de validação desconhecido")
    assertions = manifest.get("assertions", [])
    ai_claim = any("trainedAlgorithmicMedia" in json.dumps(assertion) for assertion in assertions)
    state = "invalid" if statuses else ("valid" if trust_configured else "present_unverified_trust")
    return {"has_c2pa": True, "validation_state": state,
            "generative_ai_flag": ai_claim if state == "valid" else False,
            "unverified_ai_marker": ai_claim if state != "valid" else False,
            "signer": manifest.get("signature_info", {}).get("issuer"),
            "edit_history": [a.get("data", {}) for a in assertions if a.get("label", "").startswith("c2pa.actions")],
            "summary": "Credencial validada com âncoras de confiança." if state == "valid" else
                       "Credencial não validada como confiável; não comprova origem ou autenticidade."}


async def verify_c2pa(file_bytes: bytes, filename="upload.jpg") -> dict:
    binary = shutil.which("c2patool")
    if binary and os.getenv("C2PATOOL_ENABLED", "true").lower() == "true":
        try:
            with tempfile.TemporaryDirectory(prefix="verify-c2pa-") as directory:
                path = Path(directory) / ("asset" + Path(filename).suffix[:10])
                path.write_bytes(file_bytes)
                trusted = bool(os.getenv("C2PATOOL_TRUST_ANCHORS"))
                output = await run_media_tool(binary, str(path), *( ["trust"] if trusted else []))
            return parse_c2pa_report(json.loads(output), trusted)
        except Exception:
            pass
    return _scan_binary_c2pa_markers(file_bytes)
