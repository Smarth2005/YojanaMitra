"""Offline retrieval hit-rate evaluation."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.config import CHROMA_DIR
from src.retriever import Retriever


def run(path: Path, top_k: int, delay: float, output: Path) -> dict[str, object]:
    questions = json.loads(path.read_text(encoding="utf-8"))
    retriever = Retriever(CHROMA_DIR)
    rows = []
    hits = 0
    for item in questions:
        chunks = retriever.search(item["question"], top_k=top_k)
        names = {chunk.metadata.get("scheme_name", "").lower() for chunk in chunks}
        hit = any(expected.lower() in name for expected in item["expected_schemes"] for name in names)
        hits += int(hit)
        rows.append({"question": item["question"], "hit": hit, "schemes": sorted(names)})
        time.sleep(delay)
    result = {"total": len(rows), "hits": hits, "hit_rate": hits / len(rows) if rows else 0, "rows": rows}
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=Path("eval/questions.json"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path("eval/results.json"))
    args = parser.parse_args()
    run(args.questions, args.top_k, args.delay, args.output)
