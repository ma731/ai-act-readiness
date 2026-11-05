"""Screen a spreadsheet of AI use-case proposals against the EU AI Act.

    python -m scripts.screen_proposals                        # the 16 sample proposals
    python -m scripts.screen_proposals my_proposals.xlsx      # your own (.xlsx or .csv)
    python -m scripts.screen_proposals --offline              # never call a model

Input columns: id, company, title, proposal (free text). Optional: expected_tier, which adds
an Evaluation sheet comparing the screener with your labels.

Writes results/proposals/screening.xlsx (Summary, Review queue, Obligations, Evidence, Trace,
Evaluation, About), screening.json and screening.md. With a model configured (Azure OpenAI,
Claude on Azure Foundry, or the Claude API; see the README), the model reads and challenges
each proposal; without one, the offline keyword reader runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.rules import LEGAL_BASIS_DATE
from src.screener.pipeline import screen_all, to_dict
from src.screener.readers import OfflineReader, make_reader

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "proposals_sample.csv"
OUT = ROOT / "results" / "proposals"
TIER_FILL = {"prohibited": "F4C7C3", "high_risk": "FCE8B2", "transparency": "C9DAF8", "minimal": "D9EAD3"}
TIER_LABEL = {"prohibited": "Prohibited", "high_risk": "High-risk", "transparency": "Transparency", "minimal": "Minimal"}


def load(path: Path) -> list[dict]:
    df = pd.read_excel(path) if path.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = {"id", "proposal"} - set(df.columns)
    if missing:
        sys.exit(f"Missing column(s): {', '.join(sorted(missing))}. Need at least: id, proposal.")
    df = df.fillna("")
    return [{k: str(v) for k, v in r.items()} for r in df.to_dict("records")]


def frames(results: list[dict], rows: list[dict]) -> dict[str, pd.DataFrame]:
    expected = {r["id"]: r.get("expected_tier", "") for r in rows}
    summary = pd.DataFrame([{
        "ID": r["id"], "Company": r["company"], "Proposal": r["title"],
        "Verdict": r["verdict"], "AI Act tier": TIER_LABEL[r["tier"]],
        "Key articles": ", ".join(r["articles"]),
        "Obligations": len([o for o in r["obligations"] if o["article"] != "Art 4"]),
        "Next deadline": r["next_deadline"] or "",
        "Human review": "Yes" if r["needs_review"] else "No",
        "Why review": "; ".join(r["review_reasons"]),
        "Memo": r["memo"],
        "Other law": " ".join(r["other_law"]),
    } for r in results])
    obligations = pd.DataFrame([{
        "ID": r["id"], "Proposal": r["title"], "Article": o["article"], "Duty": o["duty"],
        "Who": o["holder"], "Applies from": o["applies_from"], "Already applies": "Yes" if o["in_force"] else "No",
    } for r in results for o in r["obligations"]])
    evidence = pd.DataFrame([{
        "ID": r["id"], "Fact": e["fact"], "Value": str(e["value"]), "Quote from the proposal": e["quote"],
    } for r in results for e in r["evidence"]])
    trace = pd.DataFrame([{"ID": r["id"], "Step": i + 1, "What happened": t}
                          for r in results for i, t in enumerate(r["trace"])])
    out = {"Summary": summary, "Review queue": summary[summary["Human review"] == "Yes"],
           "Obligations": obligations, "Evidence": evidence, "Trace": trace}
    if any(expected.values()):
        ev = pd.DataFrame([{"ID": r["id"], "Proposal": r["title"], "Expected": TIER_LABEL.get(expected[r["id"]], expected[r["id"]]),
                            "Screener": TIER_LABEL[r["tier"]], "Agree": "Yes" if r["tier"] == expected[r["id"]] else "No"}
                           for r in results if expected.get(r["id"])])
        out["Evaluation"] = ev
    return out


def write_excel(path: Path, sheets: dict[str, pd.DataFrame], about: list[tuple[str, str]]) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    widths = {"Proposal": 30, "Verdict": 30, "Key articles": 30, "Why review": 50, "Memo": 80, "Other law": 50,
              "Duty": 60, "Quote from the proposal": 90, "What happened": 90, "Company": 30}
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            ws.freeze_panes = "B2"
            if len(df):
                ws.auto_filter.ref = ws.dimensions
            for i, col in enumerate(df.columns, start=1):
                ws.column_dimensions[get_column_letter(i)].width = widths.get(col, max(12, min(24, len(col) + 4)))
                cell = ws.cell(row=1, column=i)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="2F3A4A")
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
            if "AI Act tier" in df.columns:
                col = list(df.columns).index("AI Act tier") + 1
                inv = {v: k for k, v in TIER_LABEL.items()}
                for r in range(2, len(df) + 2):
                    c = ws.cell(row=r, column=col)
                    fill = TIER_FILL.get(inv.get(c.value, ""))
                    if fill:
                        c.fill = PatternFill("solid", fgColor=fill)
                        c.font = Font(bold=True)
        about_df = pd.DataFrame(about, columns=["", ""])
        about_df.to_excel(xw, sheet_name="About", index=False, header=False)
        ws = xw.sheets["About"]
        ws.column_dimensions["A"].width = 26
        ws.column_dimensions["B"].width = 110
        for row in ws.iter_rows():
            row[0].font = Font(bold=True)
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")


def markdown(results: list[dict], reader_name: str) -> str:
    counts = pd.Series([r["tier"] for r in results]).value_counts()
    lines = ["# AI Act screening of proposals", "",
             f"Legal basis as of {LEGAL_BASIS_DATE:%d %B %Y}. Reader: {reader_name}. Decision support, not legal advice.", "",
             " · ".join(f"**{counts.get(t, 0)}** {TIER_LABEL[t].lower()}" for t in TIER_LABEL)
             + f" · **{sum(r['needs_review'] for r in results)}** for human review", "",
             "| ID | Proposal | Verdict | Key articles | Review |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['id']} | {r['title']} | {r['verdict']} | {', '.join(r['articles'][:3])} | "
                     f"{'yes' if r['needs_review'] else ''} |")
    lines += ["", "## Memos", ""]
    for r in results:
        lines.append(f"**{r['id']} {r['title']}.** {r['memo']}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", default=str(SAMPLE))
    ap.add_argument("--offline", action="store_true", help="use the offline keyword reader only")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    rows = load(Path(args.input))
    reader = OfflineReader() if args.offline else make_reader()
    screenings = screen_all(rows, reader)
    results = [to_dict(s) for s in screenings]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    about = [
        ("What this is", "An EU AI Act screening of AI use-case proposals. Decision support for a compliance review, not legal advice."),
        ("Legal basis", f"Regulation (EU) 2024/1689 as amended by the Digital Omnibus on AI, as of {LEGAL_BASIS_DATE:%d %B %Y}."),
        ("Reader", getattr(reader, "name", "")),
        ("How it decides", "A reader extracts facts, each with a quote from the proposal; facts whose quote is not in the "
                           "proposal are dropped. Code (src/screener/law.py) applies the Act and decides the tier. With a model, "
                           "a second reader looks for missed facts and the memo is checked so it cites only articles the "
                           "classification used. Uncertain or disputed cases go to the Review queue."),
        ("Tiers", "Prohibited (Art 5), High-risk (Annex III or Annex I via Art 6), Transparency (Art 50), Minimal."),
        ("Limits", "The offline reader is a keyword baseline tuned on the sample proposals. Annex I dates are the original "
                   "text. Sector law (medical devices, financial supervision) is not assessed."),
    ]
    write_excel(out / "screening.xlsx", frames(results, rows), about)
    (out / "screening.json").write_text(json.dumps({"legal_basis": LEGAL_BASIS_DATE.isoformat(),
                                                    "reader": getattr(reader, "name", ""), "results": results},
                                                   indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "screening.md").write_text(markdown(results, getattr(reader, "name", "")), encoding="utf-8")

    agree = [r for r in results if any(x["id"] == r["id"] and x.get("expected_tier") for x in rows)]
    msg = f"{len(results)} proposals screened by {getattr(reader, 'name', '')}; {sum(r['needs_review'] for r in results)} for review"
    if agree:
        exp = {x["id"]: x["expected_tier"] for x in rows}
        msg += f"; {sum(r['tier'] == exp[r['id']] for r in agree)}/{len(agree)} agree with the labels"
    print(msg + f" -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
