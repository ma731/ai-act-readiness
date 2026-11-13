"""Daily check of the official EU AI Act text. See src/lawwatch.py.

    python -m scripts.law_watch              # check and update results/law/ai_act.json
    python -m scripts.law_watch --issue      # also open a GitHub issue on a change (CI)
    python -m scripts.law_watch --since 32024R1689
        # replay: what the watch would have said when that version was replaced (prints only)

No model calls. Exits 0 when the source is down or unreadable: that is not a change.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from src import lawwatch as lw
from src.rules import LEGAL_BASIS_DATE

STATE = Path(__file__).resolve().parents[1] / "results" / "law" / "ai_act.json"
LABEL = "law-change"


def _summary(text: str) -> None:
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def _gh(*args: str, stdin: str | None = None) -> str:
    return subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True,
                          check=True).stdout


def open_issue(title: str, body: str, key: str) -> str:
    seen = json.loads(_gh("issue", "list", "--label", LABEL, "--state", "all",
                          "--json", "number,body", "--limit", "100") or "[]")
    for i in seen:
        if json.dumps({"key": key}) in (i.get("body") or ""):
            return f"already reported in #{i['number']}"
    _gh("label", "create", LABEL, "--color", "5319e7", "--force",
        "--description", "The official EU AI Act text changed")
    return _gh("issue", "create", "--title", title, "--label", LABEL, "--body-file", "-",
               stdin=body).strip()


def replay_state(src: lw.Cellar, version: str) -> dict:
    """A stored state as it would have looked while `version` was the latest.
    Pass the base act (32024R1689) for the original text: Cellar has no HTML for the
    first consolidation, which is the same text."""
    parts = lw.split_articles(src.html(version))
    acts = {}
    if "-" in version:
        day = version.rsplit("-", 1)[1]
        cutoff = f"{day[:4]}-{day[4:6]}-{day[6:]}"
        acts = {c: d for c, d in src.amending().items() if d and d <= cutoff}
    return {"consolidated": version, "amending_acts": acts, "articles": lw.fingerprint(parts)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--issue", action="store_true", help="open a GitHub issue on a change")
    ap.add_argument("--since", help="replay against an older consolidated version, print only")
    args = ap.parse_args(argv)

    src = lw.Cellar()
    path = Path(args.state)
    if args.since:
        try:
            stored = replay_state(src, args.since)
        except lw.Unavailable as exc:
            print(f"Law watch: source unavailable ({exc})")
            return 0
    else:
        stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    report = lw.check(stored, src, date.today().isoformat())
    _summary(f"Law watch: {report.status}. {report.note}")

    if report.alarm:
        basis = LEGAL_BASIS_DATE.strftime("%d %b %Y")
        title, body = lw.render_issue(report, lw.citation_map(), basis)
        print(f"\n{title}\n\n{body}")
        if args.issue and not args.since:
            print(open_issue(title, body, lw.issue_key(report)))

    if report.state is not None and not args.since:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.state, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
