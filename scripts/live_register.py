"""Pull the Dutch public algorithm register and screen what is new or changed.

    python -m scripts.live_register                 # download and screen
    python -m scripts.live_register --csv file.csv  # use a local copy
    python -m scripts.live_register --limit 50      # cap model calls this run

Writes results/live/nl_register.json. A model reader is used when one is configured
(Azure OpenAI, Claude on Foundry, or the Claude API); otherwise the Dutch keyword reader.
Entries already screened by the same reader at the same publication date are skipped,
so a daily run only pays for what changed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.screener import register
from src.screener.pipeline import screen_one, to_dict
from src.screener.readers import OfflineReader, detect_provider, make_reader

OUT = Path(__file__).resolve().parents[1] / "results" / "live" / "nl_register.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="local copy of the register CSV")
    ap.add_argument("--limit", type=int, default=None, help="screen at most this many entries this run")
    ap.add_argument("--offline", action="store_true", help="use the Dutch keyword reader only")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    text = Path(args.csv).read_text(encoding="utf-8-sig") if args.csv else register.fetch()
    rows = register.to_rows(text)
    reader = OfflineReader("nl") if args.offline or not detect_provider() else make_reader()
    if isinstance(reader, OfflineReader) and reader.lang != "nl":
        reader = OfflineReader("nl")
    out = Path(args.out)
    cache = register.load_cache(out)
    cache, done = register.update(rows, cache, reader, screen_one, to_dict, args.limit)
    saved = register.save(out, cache, {"reader": reader.name, "screened_this_run": done})
    c = saved["comparison"]
    print(f"{len(rows)} entries, {done} screened this run by {reader.name}; "
          f"{c['declared_high_risk']} declared high-risk, screener agrees on {c['agree_on_declared']}; "
          f"{c['flagged_not_declared']} flagged but not declared -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
