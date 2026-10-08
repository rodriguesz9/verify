"""Derive local OCR/AV controls; no models, network, human-media claims or overwrites."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageEnhance


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(target):
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise ValueError("Refusing to overwrite a nonempty control directory.")
    target.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[2]
    fixtures = repo / "backend/tests/fixtures"
    base = fixtures / "validation/ocr/impresso-base.png"
    reference = json.loads((base.parent / "manifest.json").read_text(encoding="utf-8"))[0]["reference_lines"]
    degraded = target / "impresso-degradado.jpg"
    with Image.open(base) as image:
        rotated = image.convert("RGB").rotate(3.5, resample=Image.Resampling.BICUBIC, expand=True, fillcolor="white")
        ImageEnhance.Contrast(rotated).enhance(0.20).save(degraded, format="JPEG", quality=55, subsampling=2)
    video = fixtures / "synthetic-cafe.mp4"
    audio = repo / "frontend/public/audio/demo-pedido-sintetico.wav"
    av = target / "video-tts-auxiliar.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-n", "-stream_loop", "-1", "-i", str(video),
        "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-threads", "1",
        "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-t", "30", str(av),
    ], check=True, timeout=30, capture_output=True)
    manifest = [
        {"case_id": "OCR05", "file": degraded.name, "sha256": sha256(degraded), "group": "F-IMPRESSO",
         "parent_sha256": sha256(base), "reference_lines": reference,
         "origin": "Conventional transform of printed Pillow control; not a photograph or independent sample",
         "recipe": {"rotation_degrees": 3.5, "resampling": "bicubic", "expand": True, "fill": "white",
                    "contrast_factor": 0.20, "jpeg_quality": 55, "jpeg_subsampling": 2}},
        {"case_id": "VID-AUX01", "file": av.name, "sha256": sha256(av), "group": "F-CAFE+F-ESPEAK",
         "parent_sha256": {"video": sha256(video), "audio": sha256(audio)},
         "origin": "Repeated still AI image with documented eSpeak TTS; conventional mux, NOT human capture, face-swap or lip-sync",
         "reference_text": "Mãe, caí na rua e perdi meu celular. Faz um Pix urgente para o guincho, por favor.",
         "recipe": {"video": "loop original, libx264 CRF26 yuv420p", "audio": "AAC from eSpeak WAV",
                    "duration": "shortest track, at most 30 seconds"}},
    ]
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps({"controls": prepare(args.output_dir)}, ensure_ascii=False))
