"""Generate printed controls only, without AI, external APIs or personal media."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    target = Path(args.output_dir)
    target.mkdir(parents=True, exist_ok=True)
    controls = {
        "impresso-base.png": ["CONTROLE DE TESTE", "Nao pague taxa para liberar seu Pix.", "Valor: R$ 123,45", "Data: 03/10/2026"],
        "afirmativo.png": ["CONTROLE DE TESTE", "Pague uma taxa para liberar seu Pix.", "Valor: R$ 123,45", "Data: 03/10/2026"],
        "numeros.png": ["R$ 1.000,00", "R$ 10,00", "Taxa: 10%", "Taxa: 100%"],
        "datas.png": ["Data: 03/10/2026", "Outra data: 30/10/2026"],
        "sem-texto.png": [],
    }
    font = ImageFont.truetype("DejaVuSans.ttf", 42)
    manifest = []
    for name, lines in controls.items():
        destination = target / name
        if destination.exists():
            raise ValueError("Refusing to overwrite an existing fixture.")
        image = Image.new("RGB", (1100, 340), "white" if lines else "blue")
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(lines):
            draw.text((30, 20 + index * 75), line, font=font, fill="black")
        output = io.BytesIO()
        image.save(output, format="PNG")
        data = output.getvalue()
        destination.write_bytes(data)
        manifest.append({"file": name, "reference_lines": lines, "sha256": hashlib.sha256(data).hexdigest(),
                         "origin": "Pillow-rendered test graphic; no generative AI; not a photograph", "group": "F-IMPRESSO" if lines else "F-BLANK"})
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"created": len(manifest), "output_dir": str(target)}))


if __name__ == "__main__":
    main()
