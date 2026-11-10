"""Pull the EU public-sector AI cases (Public Sector Tech Watch) and screen what is new or changed.

    python -m scripts.live_cases                 # download and screen
    python -m scripts.live_cases --csv file.csv  # use a local copy
    python -m scripts.live_cases --limit 200     # cap model calls this run

Writes results/live/eu_cases.json. Uses a model reader when one is configured, otherwise
the English keyword reader. A case is only read again when the Commission edits it.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.screener import pstw
from src.screener.pipeline import screen_one, to_dict
from src.screener.readers import OfflineReader, detect_provider, make_reader

OUT = Path(__file__).resolve().parents[1] / "results" / "live" / "eu_cases.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="local copy of the use-case CSV")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--offline", action="store_true", help="use the English keyword reader only")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    if args.csv:
        url, text = args.csv, Path(args.csv).read_text(encoding="utf-8-sig", errors="replace")
    else:
        url, text = pstw.fetch()
    rows = pstw.to_rows(text)
    reader = OfflineReader("en") if args.offline or not detect_provider() else make_reader()
    out = Path(args.out)
    cache, done = pstw.update(rows, pstw.load_cache(out), reader, screen_one, to_dict, args.limit)
    saved = pstw.save(out, cache, {"file": url, "reader": reader.name, "screened_this_run": done})
    s = saved["summary"]
    print(f"{s['cases']} EU AI cases ({s['in_use']} in use or piloted, "
          f"{s['countries']} jurisdictions); "
          f"{done} screened this run by {reader.name}; "
          f"{s['high_risk_or_prohibited']} in use look high-risk -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
