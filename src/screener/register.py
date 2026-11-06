"""Live proposals: the Dutch public algorithm register (algoritmes.overheid.nl).

Every Dutch public body publishes its algorithms there: what each does, the data, the
human oversight, the supplier, and a publication category it chose itself. One category
is "Hoog-risico AI-systeem", the body's own reading of the AI Act. That gives a real-world
check the sample proposals cannot: does the screener agree with the people who run the
system?

Two caveats travel with every number built from it:
  * The register lists all algorithms, rule-based ones included. The AI Act only covers AI
    systems (Art 3(1)); the screener does not decide that question.
  * A body's own category is a declaration, not a ruling. A disagreement is a case to
    read, not a breach.
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

URL = "https://algoritmes.overheid.nl/api/downloads/NLD?filetype=csv"
PAGE = "https://algoritmes.overheid.nl/nl/algoritme/{id}"
DECLARED = {"Hoog-risico AI-systeem": "high_risk", "Impactvolle algoritmes": "impactful",
            "Overige algoritmes": "other"}
FIELDS = [("description_short", ""), ("goal", "Doel: "), ("methods_and_models", "Werking: "),
          ("human_intervention", "Menselijke tussenkomst: "), ("risks", "Risico's: ")]


def fetch(url: str = URL, timeout: int = 120) -> str:
    """The whole register as CSV text."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "ai-act-readiness screener"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https URL
        return r.read().decode("utf-8-sig")


def _clean(s) -> str:
    s = " ".join(str(s or "").split())
    return s if s.endswith((".", "!", "?")) or not s else s + "."


def to_rows(csv_text: str) -> list[dict]:
    """One proposal row per register entry, in the shape the screener reads."""
    rows = []
    for r in csv.DictReader(io.StringIO(csv_text)):
        parts = [prefix + _clean(r.get(k)) for k, prefix in FIELDS if (r.get(k) or "").strip()]
        supplier = (r.get("provider") or "").strip()
        if supplier:
            parts.append(f"Leverancier: {_clean(supplier)}")
        rows.append({
            "id": r["algorithm_id"], "company": r.get("organization", ""), "title": r.get("name", ""),
            "proposal": " ".join(parts), "lang": "nl",
            "declared": DECLARED.get(r.get("publication_category", ""), "other"),
            "status": r.get("status", ""), "category": r.get("category", ""),
            "published": (r.get("publication_dt") or "")[:10], "url": PAGE.format(id=r["algorithm_id"]),
        })
    return rows


def update(rows: list[dict], cache: dict, reader, screen_one, to_dict, limit: int | None = None) -> tuple[dict, int]:
    """Screen entries that are new, changed, or were read by a different reader. Returns
    (cache, how many were screened). The cache maps id -> stored result."""
    done = 0
    name = getattr(reader, "name", "")
    version = f"{name}@{getattr(reader, 'version', '')}"
    for row in rows:
        old = cache.get(row["id"])
        if old and old.get("published") == row["published"] and old.get("reader_version") == version:
            continue
        if limit is not None and done >= limit:
            break
        d = to_dict(screen_one(row, reader))
        cache[row["id"]] = {
            **{k: row[k] for k in ("id", "company", "title", "declared", "status", "category", "published", "url")},
            "reader": name, "reader_version": version, "tier": d["tier"], "articles": d["articles"], "needs_review": d["needs_review"],
            "review_reasons": d["review_reasons"], "evidence": d["evidence"], "memo": d["memo"],
            "proposal": row["proposal"],
        }
        done += 1
    live = {r["id"] for r in rows}
    for gone in [k for k in cache if k not in live]:
        del cache[gone]
    return cache, done


def compare(results: list[dict]) -> dict:
    """Screener against each body's own category."""
    declared_hr = [r for r in results if r["declared"] == "high_risk"]
    flagged = [r for r in results if r["tier"] in ("high_risk", "prohibited")]
    both = [r for r in declared_hr if r["tier"] in ("high_risk", "prohibited")]
    undeclared = [r for r in flagged if r["declared"] != "high_risk"]
    return {
        "entries": len(results),
        "declared_high_risk": len(declared_hr),
        "screened_high_risk_or_prohibited": len(flagged),
        "agree_on_declared": len(both),
        "recall_on_declared": round(len(both) / len(declared_hr), 3) if declared_hr else None,
        "flagged_not_declared": len(undeclared),
        "tiers": dict(Counter(r["tier"] for r in results)),
        "declared": dict(Counter(r["declared"] for r in results)),
        "by_area": dict(Counter(a for r in flagged for a in r["articles"] if a.startswith("Annex III")).most_common(10)),
        "missed_declared": [r["id"] for r in declared_hr if r["tier"] not in ("high_risk", "prohibited")],
    }


def load_cache(path: Path) -> dict:
    if path.exists():
        return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["results"]}
    return {}


def save(path: Path, cache: dict, meta: dict) -> dict:
    results = sorted(cache.values(), key=lambda r: (r["published"], r["id"]), reverse=True)
    out = {"source": "Algoritmeregister, algoritmes.overheid.nl", "url": URL,
           "synced": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), **meta,
           "comparison": compare(results), "results": results}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out
