"""Download MEPS HC-243 (2022 Full Year Consolidated, public, about 6 MB) into data/raw."""
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://meps.ahrq.gov/mepsweb/data_files/pufs/h243/h243dta.zip"
OUT = Path(__file__).parents[1] / "data" / "raw"


def main() -> int:
    if (OUT / "h243.dta").exists():
        print("already present")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=120) as r:
        zipfile.ZipFile(io.BytesIO(r.read())).extractall(OUT)
    print("saved", OUT / "h243.dta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
