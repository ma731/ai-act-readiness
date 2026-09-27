"""Run the whole assessment: classify the inventory, test the pricing model, render docs.

    python -m scripts.run_assessment            # everything (needs data/raw, see fetch_data)
    python -m scripts.run_assessment --rules    # classification and gaps only, no data
    python -m scripts.run_assessment --check    # fail if committed docs are stale
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import yaml

from src import report
from src.rules import LEGAL_BASIS_DATE, classify_all

ROOT = Path(__file__).parents[1]
RESULTS = ROOT / "results"


def _round(o, nd=4):
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: _round(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v, nd) for v in o]
    if isinstance(o, date):
        return o.isoformat()
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", action="store_true", help="skip the pricing evidence")
    ap.add_argument("--check", action="store_true", help="exit 1 if docs are stale")
    args = ap.parse_args()

    inv = yaml.safe_load((ROOT / "inventory" / "cierzo_systems.yaml").read_text(encoding="utf-8"))
    systems = inv["systems"]
    results = classify_all(systems)
    rows = report.gap_rows(systems, results)

    RESULTS.mkdir(exist_ok=True)
    classification = {"legal_basis_date": LEGAL_BASIS_DATE.isoformat(),
                      "systems": [_round(asdict(c)) for c in results],
                      "gaps": _round(rows)}
    if not args.check:
        (RESULTS / "classification.json").write_text(
            json.dumps(classification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ev_path = RESULTS / "pricing_evidence.json"
    if not args.rules and not args.check:
        from src.evidence import run
        ev = _round(run())
        ev_path.write_text(json.dumps(ev, indent=2) + "\n", encoding="utf-8")
    ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else None

    blocks = {
        "inventory": report.inventory_table(systems, results),
        "flags": report.flags_list(systems, results),
        "gap-summary": report.gap_summary(rows),
        "gaps": report.gap_table(rows),
        "roadmap": report.roadmap(rows),
    }
    tariffs = yaml.safe_load((ROOT / "data" / "tariffs_osakidetza_2024.yaml")
                             .read_text(encoding="utf-8"))
    blocks["cost-build"] = report.cost_build(tariffs, ev)
    if ev:
        blocks |= {
            "evidence-headline": report.evidence_headline(ev),
            "evidence-model": report.evidence_model(ev),
            "evidence-age": report.evidence_age(ev),
            "evidence-born": report.evidence_groups(ev, "born"),
            "evidence-private": report.evidence_private(ev),
            "evidence-unmet": report.evidence_unmet(ev),
            "evidence-class": report.evidence_class(ev),
            "evidence-sex": report.evidence_groups(ev, "sex"),
        }
    stale = report.render_docs(ROOT / "docs", blocks, check=args.check)
    if args.check and stale:
        print("Stale, run python -m scripts.run_assessment:", *map(str, stale), sep="\n  ")
        return 1
    print(f"{len(systems)} systems classified, {len(rows)} obligations; "
          f"{'updated ' + str(len(stale)) + ' docs' if stale else 'docs current'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
