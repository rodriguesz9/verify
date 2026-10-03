"""Bounded local printed-text OCR. Recognition quality is NOT truth confidence."""
import asyncio
import csv
import io
import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


def _prepare_image(data):
    if not data or len(data) > 25 * 1024 * 1024:
        raise ValueError("Image limit")
    with Image.open(io.BytesIO(data)) as image:
        if image.width * image.height > 20_000_000 or image.format not in {"PNG", "JPEG", "WEBP", "GIF"}:
            raise ValueError("Image limit")
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((2400, 2400))
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()


def _parse_tsv(raw):
    if len(raw) > 2_000_000:
        raise ValueError("OCR output limit")
    lines, confidences = {}, []
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t"):
        text = row.get("text", "").strip()
        if not text or row.get("level") != "5":
            continue
        confidence = float(row["conf"])
        if not 0 <= confidence <= 100:
            raise ValueError("Invalid recognition score")
        key = tuple(row[k] for k in ("page_num", "block_num", "par_num", "line_num"))
        lines.setdefault(key, []).append(text)
        confidences.append(confidence)
    text = "\n".join(" ".join(words) for words in lines.values())
    if len(text) > 12000:
        raise ValueError("OCR text limit")
    # Recognition gate only; never expose this average as accuracy/probability.
    usable = bool(confidences) and sum(confidences) / len(confidences) >= 70
    return text, usable


async def extract_local_text(image_bytes):
    base = {"available": False, "provider": "tesseract", "decision_role": "ocr_only", "text": ""}
    if os.getenv("LOCAL_OCR_ENABLED", "true").lower() != "true":
        return {**base, "status": "disabled"}
    binary = shutil.which("tesseract")
    if not binary:
        return {**base, "status": "not_installed"}
    process = None
    try:
        prepared = await asyncio.to_thread(_prepare_image, image_bytes)
        with tempfile.TemporaryDirectory(prefix="verify-ocr-") as directory:
            path = Path(directory) / "input.png"
            path.write_bytes(prepared)
            process = await asyncio.create_subprocess_exec(binary, str(path), "stdout", "-l", "por+eng", "--psm", "3", "tsv",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "OMP_THREAD_LIMIT": "1"})
            raw, _ = await asyncio.wait_for(process.communicate(), timeout=6)
            if process.returncode:
                return {**base, "status": "unavailable", "reason": "OCR local não executou; confira idiomas português/inglês."}
            text, usable = _parse_tsv(raw)
            if not usable:
                return {**base, "status": "low_quality" if text else "no_text"}
            return {**base, "available": True, "status": "success", "text": text, "model_used": "tesseract-lstm-por-eng",
                    "limitations": ["Leitura de texto impresso pode errar números, negações e trechos ilegíveis; compare com a imagem."]}
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        return {**base, "status": "timeout", "reason": "OCR local excedeu o prazo."}
    except Exception:
        return {**base, "status": "invalid_response", "reason": "OCR local não retornou texto utilizável."}
    finally:
        if process is not None and process.returncode is None:
            process.kill()
            await process.communicate()
