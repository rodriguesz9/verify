"""
C2PA Content Credentials Service (Layer 1)
Parses C2PA (Coalition for Content Provenance and Authenticity) manifests.
Uses c2patool binary if available, with binary JUMBF box heuristic fallback.
"""

import os
import json
import shutil
import asyncio
import tempfile
from typing import Dict, Any, List


C2PA_MARKERS = [b"c2pa", b"jumb", b"c2pa.assertions", b"c2pa.actions", b"stCat.created"]
AI_ACTION_MARKERS = [b"c2pa.placed", b"c2pa.filtered", b"c2pa.created", b"c2pa.generative-ai"]


def _scan_binary_c2pa_markers(file_bytes: bytes) -> Dict[str, Any]:
    """Scans file bytes for JUMBF/C2PA standard manifest signatures."""
    has_marker = any(m in file_bytes for m in C2PA_MARKERS)
    if not has_marker:
        return {
            "has_c2pa": False,
            "validation_state": "none",
            "generative_ai_flag": False,
            "signer": None,
            "edit_history": [],
            "summary": "Nenhuma credencial C2PA encontrada (normal para fotos comuns sem Content Credentials)."
        }

    has_ai_marker = (
        b"c2pa.generative-ai" in file_bytes
        or b"trainedAlgorithmicMedia" in file_bytes
        or b"c2pa.actions.created" in file_bytes
    )
    return {
        "has_c2pa": True,
        "validation_state": "present_unverified_tool",
        "generative_ai_flag": has_ai_marker,
        "signer": "Marcador JUMBF C2PA identificado no arquivo",
        "edit_history": ["Histórico C2PA embutido detectado"],
        "summary": "Credenciais C2PA presentes no cabeçalho do arquivo." + (" Sinaliza uso de IA Generativa." if has_ai_marker else "")
    }


async def verify_c2pa(file_bytes: bytes, filename: str = "upload.jpg") -> Dict[str, Any]:
    """
    Validates C2PA Content Credentials from media bytes.
    """
    is_c2pa_enabled = os.getenv("C2PATOOL_ENABLED", "true").lower() == "true"
    c2patool_bin = shutil.which("c2patool")

    if is_c2pa_enabled and c2patool_bin:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            proc = await asyncio.create_subprocess_exec(
                c2patool_bin, tmp_path, "--info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            if proc.returncode == 0 and stdout:
                data = json.loads(stdout.decode("utf-8", errors="ignore"))
                active_manifest = data.get("active_manifest", {})
                assertions = active_manifest.get("assertions", [])
                
                # Check for generative AI assertion
                ai_flag = any(
                    "generative" in str(a).lower() or "ai" in str(a.get("label", "")).lower()
                    for a in assertions
                )
                
                signer = active_manifest.get("signature_info", {}).get("issuer")
                history = [a.get("data", {}) for a in assertions if "action" in str(a.get("label", "")).lower()]

                return {
                    "has_c2pa": True,
                    "validation_state": "valid" if data.get("validation_status") == "success" else "invalid",
                    "generative_ai_flag": ai_flag,
                    "signer": signer,
                    "edit_history": history,
                    "summary": f"Manifesto C2PA verificado: assinado por {signer or 'desconhecido'}." + (" [Contém sinal de IA]" if ai_flag else "")
                }
        except Exception:
            pass

    # Fallback to binary JUMBF scan
    return _scan_binary_c2pa_markers(file_bytes)

