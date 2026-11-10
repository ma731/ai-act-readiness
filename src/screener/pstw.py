"""Live cases: AI in Europe's public sector, from the European Commission's Public Sector Tech Watch.

The Commission (DIGIT and the JRC) keeps a catalogue of how public bodies across the EU
actually use AI: chatbots, document triage, fraud checks, traffic cameras, benefit
decisions. Each case has an English description, the country, the body and its status.
Screening every case shows a company getting ready for the AI Act which everyday uses
the law treats as high-risk, which only need a transparency notice, and which it barely
touches.

Caveats that travel with every number:
  * A case description is a summary written for the catalogue, not a system's documentation.
  * Public bodies are deployers; the screener's tier is a first pass for a person to check.
  * The Commission updates the file about monthly; the daily run picks up each new release.
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

DATASET = "https://data.europa.eu/api/hub/search/datasets/e8e7bddd-8510-4936-9fa6-7e1b399cbd92"
PAGE = "https://data.europa.eu/data/datasets/e8e7bddd-8510-4936-9fa6-7e1b399cbd92"
EU = {"Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia", "Finland",
      "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
      "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
      "European Union"}
IN_USE = ("Implemented", "Pilot")


def _get(url: str, timeout: int = 120) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "ai-act-readiness screener"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https hosts
        return r.read()


def latest_csv_url() -> str:
    """The catalogue moves its file each release; the data.europa.eu record points at the newest."""
    meta = json.loads(_get(DATASET))["result"]
    urls = [u for d in meta["distributions"] for u in (d.get("download_url") or d.get("access_url") or [])
            if u.endswith(".csv") and "pstw_dataset" in u.lower()]
    if not urls:
        raise RuntimeError("no use-case CSV on the data.europa.eu record")
    return sorted(urls)[-1]


def fetch() -> tuple[str, str]:
    url = latest_csv_url()
    return url, _get(url).decode("utf-8-sig", errors="replace")


def _date(dmy: str) -> str:
    try:
        return datetime.strptime(dmy.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def to_rows(csv_text: str) -> list[dict]:
    """AI cases in the EU, one screener row each."""
    rows = []
    for r in csv.DictReader(io.StringIO(csv_text)):
        r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
        if r.get("Primary Technology") != "Artificial Intelligence" or r.get("Geographical coverage (country)") not in EU:
            continue
        desc = " ".join(r.get("Description", "").split())
        rows.append({
            "id": r["PSTW ID"], "company": r.get("Responsible organisation", ""), "title": r.get("Name", ""),
            "proposal": f"{r.get('Name', '').rstrip('.')}. {desc}", "lang": "en",
            "country": r["Geographical coverage (country)"], "status": r.get("Status", ""),
            "area": r.get("Functions of Government (COFOG level I)", ""),
            "kind": r.get("Responsible organisation category", ""), "start": r.get("Start Year", ""),
            "updated": _date(r.get("Date updated", "")), "url": r.get("Website", "") or r.get("Link to the story", ""),
        })
    return rows


KEEP = ("id", "company", "title", "country", "status", "area", "kind", "start", "updated", "url", "proposal")


def update(rows: list[dict], cache: dict, reader, screen_one, to_dict, limit: int | None = None) -> tuple[dict, int]:
    """Screen cases that are new, edited, or were read by a different reader."""
    done = 0
    version = f"{getattr(reader, 'name', '')}@{getattr(reader, 'version', '')}"
    for row in rows:
        old = cache.get(row["id"])
        if old and old.get("updated") == row["updated"] and old.get("reader_version") == version:
            continue
        if limit is not None and done >= limit:
            break
        d = to_dict(screen_one(row, reader))
        cache[row["id"]] = {**{k: row[k] for k in KEEP}, "reader": getattr(reader, "name", ""),
                            "reader_version": version, "tier": d["tier"], "articles": d["articles"],
                            "needs_review": d["needs_review"], "review_reasons": d["review_reasons"],
                            "evidence": d["evidence"], "memo": d["memo"]}
        done += 1
    live = {r["id"] for r in rows}
    for gone in [k for k in cache if k not in live]:
        del cache[gone]
    return cache, done


def summarise(results: list[dict]) -> dict:
    in_use = [r for r in results if r["status"] in IN_USE]
    flagged = [r for r in in_use if r["tier"] in ("high_risk", "prohibited")]
    by_area = Counter(r["area"] for r in in_use if r["area"])
    hot = Counter(r["area"] for r in flagged if r["area"])
    return {
        "cases": len(results), "in_use": len(in_use), "countries": len({r["country"] for r in results}),
        "bodies": len({r["company"] for r in results}),
        "tiers": dict(Counter(r["tier"] for r in in_use)),
        "high_risk_or_prohibited": len(flagged),
        "needs_review": sum(r["needs_review"] for r in in_use),
        "by_area": [[a, n, hot.get(a, 0)] for a, n in by_area.most_common(8)],
        "by_annex": dict(Counter(a for r in flagged for a in r["articles"] if a.startswith("Annex III")).most_common(8)),
        "by_country": Counter(r["country"] for r in in_use).most_common(6),
        "newest": max((r["updated"] for r in results), default=""),
    }


def load_cache(path: Path) -> dict:
    if path.exists():
        return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["results"]}
    return {}


def save(path: Path, cache: dict, meta: dict) -> dict:
    results = sorted(cache.values(), key=lambda r: (r["updated"], r["id"]), reverse=True)
    out = {"source": "Public Sector Tech Watch, European Commission (DIGIT and JRC)", "page": PAGE,
           "synced": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), **meta,
           "summary": summarise(results), "results": results}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out
