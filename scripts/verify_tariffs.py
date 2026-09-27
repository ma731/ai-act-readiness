"""Check every price in data/tariffs_osakidetza_2024.yaml against the official PDF.

For each line, the article code must appear on the stated page, on the same text line as the
stated price. Run after scripts/fetch_data.py.
"""
import re
import sys
from pathlib import Path

import yaml
from pypdf import PdfReader

ROOT = Path(__file__).parents[1]
PDF = ROOT / "data" / "raw" / "tariffs" / "osakidetza_2024.pdf"


def main() -> int:
    spec = yaml.safe_load((ROOT / "data" / "tariffs_osakidetza_2024.yaml").read_text("utf-8"))
    reader = PdfReader(PDF)
    bad = 0
    for name, p in spec["prices"].items():
        text = reader.pages[p["page"] - 1].extract_text() or ""
        line = next((ln for ln in text.splitlines() if p["article"] in ln), None)
        price = f"{p['eur']:,}".replace(",", ".")          # Spanish thousands separator
        ok = line is not None and re.search(rf"(^|\s){re.escape(price)}(\s|$)", line)
        print(f"{'ok ' if ok else 'BAD'} {name:24} {p['eur']:>6} EUR  p.{p['page']:<4} {line!r}")
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
