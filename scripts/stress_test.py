"""Generate proposals with known answers and score the screener on them.

    python -m scripts.stress_test                  # plain + disguised, the configured reader
    python -m scripts.stress_test --offline        # keyword reader only
    python -m scripts.stress_test --rewrite 20     # also 20 model-rewritten proposals (needs a model)

Writes results/generated/stress_test.json and data/generated_proposals.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from src.screener import generate
from src.screener.pipeline import screen_one
from src.screener.readers import OfflineReader, make_reader

ROOT = Path(__file__).resolve().parents[1]


def run(reader, rewrite: int = 0) -> dict:
    rows = generate.generate()
    if rewrite and hasattr(reader, "write"):
        rows += generate.rewritten(rows, reader, rewrite)
    screenings = [screen_one(r, reader) for r in rows]
    ev = generate.evaluate(rows, screenings)
    return {"reader": getattr(reader, "name", ""), "run": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
            "scenarios": len(generate.SCENARIOS), **ev}, rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--rewrite", type=int, default=0, help="add N model-rewritten proposals")
    args = ap.parse_args(argv)
    reader = OfflineReader() if args.offline else make_reader()
    out, rows = run(reader, args.rewrite)
    path = ROOT / "results" / "generated" / "stress_test.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    with (ROOT / "data" / "generated_proposals.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "company", "title", "proposal", "expected_tier", "scenario", "style", "role", "area"])
        w.writeheader()
        w.writerows(rows)
    styles = ", ".join(f"{k} {v['accuracy']:.0%}" for k, v in out["by_style"].items())
    print(f"{out['n']} generated proposals, {out['reader']}: {out['accuracy']:.0%} correct ({styles}); "
          f"{out['under_called_severe']} prohibited or high-risk called milder -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
