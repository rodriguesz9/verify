"""
Metadata Extraction Service (Layer 1)
Extracts EXIF, IPTC, XMP metadata using exiftool with PIL fallback.
Detects generative AI tags and editing software signatures.
"""

import os
import json
import shutil
import asyncio
import tempfile
from typing import Dict, Any, List
from PIL import Image, ExifTags

AI_SOFTWARE_SIGNATURES = [
    "midjourney", "dall-e", "stable diffusion", "stablediffusion",
    "comfyui", "automatic1111", "firefly", "novelai", "invokeai",
    "bing image creator", "leonardo.ai", "photoshop", "gimp"
]


def _scan_for_ai_signatures(metadata_dict: Dict[str, Any]) -> List[str]:
    """Finds mentions of generative AI or heavy manipulation software."""
    found = []
    text_values = " ".join([str(v).lower() for v in metadata_dict.values() if isinstance(v, (str, int, float))])
    for sig in AI_SOFTWARE_SIGNATURES:
        if sig in text_values:
            found.append(sig)
    return list(set(found))


async def extract_metadata(file_bytes: bytes, filename: str = "upload.jpg") -> Dict[str, Any]:
    """
    Extracts metadata from image or document bytes.
    Uses exiftool if available, else PIL.
    """
    metadata: Dict[str, Any] = {}
    is_exiftool_enabled = os.getenv("EXIFTOOL_ENABLED", "true").lower() == "true"
    exiftool_bin = shutil.which("exiftool")

    if is_exiftool_enabled and exiftool_bin:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            proc = await asyncio.create_subprocess_exec(
                exiftool_bin, "-j", "-n", tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            if proc.returncode == 0 and stdout:
                parsed = json.loads(stdout.decode("utf-8", errors="ignore"))
                if parsed and isinstance(parsed, list):
                    metadata = parsed[0]
        except Exception:
            metadata = {}

    # PIL Fallback if exiftool not installed or yielded nothing
    if not metadata:
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            with Image.open(tmp_path) as img:
                metadata["Format"] = img.format
                metadata["ImageSize"] = f"{img.width}x{img.height}"
                metadata["Mode"] = img.mode

                # Read basic EXIF
                raw_exif = getattr(img, "_getexif", lambda: None)()
                if raw_exif:
                    for tag_id, value in raw_exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        try:
                            if isinstance(value, bytes):
                                value = value.decode("utf-8", errors="ignore")
                            metadata[tag_name] = str(value)
                        except Exception:
                            pass

                # Read PNG / WebP / JPEG text info
                if hasattr(img, "info") and img.info:
                    for k, v in img.info.items():
                        if isinstance(v, (str, int, float)):
                            metadata[k] = str(v)

            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

    # Extract target fields
    make = str(metadata.get("Make") or "")
    model = str(metadata.get("Model") or "")
    software = str(metadata.get("Software") or metadata.get("CreatorTool") or "")
    date_original = str(metadata.get("DateTimeOriginal") or metadata.get("CreateDate") or "")
    gps = str(metadata.get("GPSPosition") or metadata.get("GPSLatitude") or "")

    ai_signatures = _scan_for_ai_signatures(metadata)
    is_suspicious = len(ai_signatures) > 0 or ("photoshop" in software.lower() and not make)

    return {
        "source": "exiftool" if (is_exiftool_enabled and exiftool_bin) else "pil",
        "has_exif": len(metadata) > 3,
        "camera_make": make or None,
        "camera_model": model or None,
        "software": software or None,
        "date_original": date_original or None,
        "gps_position": gps or None,
        "ai_signatures_found": ai_signatures,
        "is_suspicious": is_suspicious,
        "summary": (
            f"Assinatura de IA encontrada nos metadados: {', '.join(ai_signatures)}"
            if ai_signatures
            else ("Metadados de câmera válidos identificados" if make else "Sem metadados de câmera original (comum em mídias baixadas da web)")
        ),
        "raw_keys_count": len(metadata),
        "raw_preview": {k: str(v)[:80] for k, v in list(metadata.items())[:12]}
    }
