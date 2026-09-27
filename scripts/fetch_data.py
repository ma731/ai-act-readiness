"""Download the two public sources into data/raw (about 20 MB in total).

1. INE, Encuesta Europea de Salud en España 2020, adult microdata (the people).
2. Osakidetza, Tarifas 2024 (the prices), so scripts/verify_tariffs.py can check every price.
"""
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

RAW = Path(__file__).parents[1] / "data" / "raw"
EESE = "https://www.ine.es/ftp/microdatos/enceursalud/datos_2020_individual.zip"
TARIFFS = ("https://www.osakidetza.euskadi.eus/contenidos/informacion/osk_servic_para_empresas/"
           "es_def/adjuntos/LIBRO-DE-TARIFAS-2024-CAS_V2.pdf")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-act-readiness"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main() -> int:
    survey = RAW / "eese" / "STATA" / "EESEadulto_2020.dta"
    if not survey.exists():
        (RAW / "eese").mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(io.BytesIO(_get(EESE))).extractall(RAW / "eese")
        print("saved", survey)
    pdf = RAW / "tariffs" / "osakidetza_2024.pdf"
    if not pdf.exists():
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(_get(TARIFFS))
        print("saved", pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
