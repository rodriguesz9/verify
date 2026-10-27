"""Bounded local printed-text OCR. Recognition quality is NOT truth confidence."""
import asyncio
import csv
import io
import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


MAX_OCR_OUTPUT_BYTES = 2_000_000
MAX_OCR_ERROR_BYTES = 64_000


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
    if len(raw) > MAX_OCR_OUTPUT_BYTES:
        raise ValueError("OCR output limit")
    lines, confidences = {}, []
    # Tesseract emits raw TSV, not CSV-escaped text. CSV quoting would swallow
    # following rows when a recognized word starts with a literal quote.
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t", quoting=csv.QUOTE_NONE)
    required = {"level", "page_num", "block_num", "par_num", "line_num", "word_num", "conf", "text"}
    if (not rows.fieldnames or len(rows.fieldnames) != len(set(rows.fieldnames))
            or not required.issubset(rows.fieldnames)):
        raise ValueError("Invalid OCR columns")
    for row in rows:
        if None in row or any(row.get(key) is None for key in required):
            raise ValueError("Invalid OCR row")
        if row["level"] not in {"1", "2", "3", "4", "5"}:
            raise ValueError("Invalid OCR level")
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


async def _read_bounded(stream, limit):
    chunks, size = [], 0
    while chunk := await stream.read(65536):
        size += len(chunk)
        if size > limit:
            raise ValueError("OCR output limit")
        chunks.append(chunk)
    return b"".join(chunks)


async def _collect_output(process):
    # Bound both pipes while the child runs; communicate() accumulates them
    # before the parser can enforce its output cap.
    tasks = [asyncio.create_task(_read_bounded(process.stdout, MAX_OCR_OUTPUT_BYTES)),
             asyncio.create_task(_read_bounded(process.stderr, MAX_OCR_ERROR_BYTES)),
             asyncio.create_task(process.wait())]
    try:
        results = await asyncio.gather(*tasks)
        return results[0]
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _stop_process(process):
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass  # Child exited between returncode inspection and kill().

    async def drain(stream):
        while await stream.read(65536):
            pass

    # Drain without retaining output so a full pipe cannot block reaping.
    tasks = [asyncio.create_task(drain(process.stdout)), asyncio.create_task(drain(process.stderr)),
             asyncio.create_task(process.wait())]
    try:
        async with asyncio.timeout(2):
            await asyncio.gather(*tasks)
    except (TimeoutError, OSError):
        pass
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def extract_local_text(image_bytes):
    base = {"available": False, "provider": "tesseract", "decision_role": "ocr_only", "text": ""}
    if os.getenv("LOCAL_OCR_ENABLED", "true").lower() != "true":
        return {**base, "status": "disabled"}
    binary = shutil.which("tesseract")
    if not binary:
        return {**base, "status": "not_installed"}
    try:
        prepared = await asyncio.to_thread(_prepare_image, image_bytes)
        with tempfile.TemporaryDirectory(prefix="verify-ocr-") as directory:
            path = Path(directory) / "input.png"
            path.write_bytes(prepared)
            process = await asyncio.create_subprocess_exec(binary, str(path), "stdout", "-l", "por+eng", "--psm", "3", "tsv",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "OMP_THREAD_LIMIT": "1"})
            try:
                raw = await asyncio.wait_for(_collect_output(process), timeout=6)
            finally:
                # Terminate/reap BEFORE TemporaryDirectory removes the input,
                # including overflow, timeout and caller cancellation.
                await _stop_process(process)
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
