"""Compute accuracy/coverage from JSONL predictions without API costs.

Usage: PYTHONPATH=backend python backend/scripts/evaluate_predictions.py records.jsonl
Prints aggregate metrics only, not private content or ground-truth URLs.
"""
import argparse
import json
from pathlib import Path
from app.services.benchmark_metrics import evaluate_predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    args = parser.parse_args()
    if args.records.stat().st_size > 10 * 1024 * 1024:
        parser.error("Arquivo excede 10 MiB.")
    try:
        records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(json.dumps(evaluate_predictions(records), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError):
        parser.error("Dados inválidos. Confira o formato/documentação; nenhum resultado de precisão foi produzido.")


if __name__ == "__main__":
    main()
