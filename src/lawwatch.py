"""Watch the official text of the EU AI Act and say which parts of our code a change touches.

Source: the EU Publications Office (Cellar), which serves the same consolidated texts as
EUR-Lex. EUR-Lex itself answers scripts with an empty bot-check page, Cellar does not.

    1. ask Cellar which consolidated versions of 32024R1689 exist, and which acts amend it
    2. when a new version appears, download it, split it into articles and annexes,
       hash each one, and compare with the hashes stored on the live-data branch
    3. map every changed article to the functions and constants in src/rules.py and
       src/screener/law.py that cite it

No model is involved. A network failure or an unreadable page never counts as a change.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import tokenize
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELEX = "32024R1689"
CONSOLIDATED = "0" + CELEX[1:]   # consolidated versions: 02024R1689-YYYYMMDD
SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
CELLAR = "https://publications.europa.eu/resource/celex/{}"
EURLEX = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{}"
CODE_FILES = ("src/rules.py", "src/screener/law.py")
UA = "ai-act-readiness law watch (github.com/ma731/ai-act-readiness)"

# Dates of application live in Art 113 (and transitional rules in Art 111), but the code
# stores them as dates, not citations, so the grep cannot find them.
EXTRA_CITES = {
    "Art 113": {"src/rules.py": ["APPLIES", "LEGAL_BASIS_DATE"],
                "src/screener/law.py": ["ANNEX_I_DATE"]},
}

_Q_VERSIONS = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex WHERE {
  ?w cdm:resource_legal_id_celex ?celex .
  FILTER(STRSTARTS(STR(?celex), "%s-"))
}"""
_Q_AMENDING = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?celex ?date WHERE {
  ?base cdm:resource_legal_id_celex "%s"^^xsd:string .
  ?act cdm:resource_legal_amends_resource_legal ?base .
  ?act cdm:resource_legal_id_celex ?celex .
  OPTIONAL { ?act cdm:work_date_document ?date }
}"""


class Unavailable(Exception):
    """The source could not be read today. Never treated as a change."""


# --- fetching ---------------------------------------------------------------- #
def _get(url: str, accept: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
                                               "Accept-Language": "eng"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200:
                raise Unavailable(f"{url} answered {r.status}")
            return r.read()
    except Unavailable:
        raise
    except Exception as exc:  # DNS, TLS, timeouts, HTTP errors: all just "not today"
        raise Unavailable(f"{url}: {exc}") from exc


class Cellar:
    def _sparql(self, query: str) -> list[dict]:
        url = SPARQL + "?" + urllib.parse.urlencode({"query": query})
        return parse_sparql(_get(url, "application/sparql-results+json"))

    def versions(self) -> list[str]:
        return consolidated_ids(self._sparql(_Q_VERSIONS % CONSOLIDATED))

    def amending(self) -> dict[str, str]:
        return {r["celex"]: r.get("date", "") for r in self._sparql(_Q_AMENDING % CELEX)}

    def html(self, celex: str) -> str:
        return _get(CELLAR.format(celex), "application/xhtml+xml, text/html").decode("utf-8")


def parse_sparql(raw: bytes) -> list[dict]:
    try:
        rows = json.loads(raw)["results"]["bindings"]
        return [{k: v["value"] for k, v in row.items()} for row in rows]
    except (ValueError, KeyError, TypeError) as exc:
        raise Unavailable(f"unexpected SPARQL answer: {exc}") from exc


def consolidated_ids(rows: list[dict]) -> list[str]:
    pat = re.compile(rf"^{CONSOLIDATED}-\d{{8}}$")
    return sorted({r["celex"] for r in rows if pat.match(r.get("celex", ""))})


# --- splitting the text ------------------------------------------------------- #
_ART_ID = re.compile(r"^art_(\d+[a-z]?)$")
_ANX_ID = re.compile(r"^anx_([IVXL]+)$")
_MARKERS = re.compile(r"[►▼◄]\s*[A-Z]?\d*")  # amendment arrows like "▼M1"


class _Splitter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: dict[str, list[str]] = {}
        self._key: str | None = None
        self._depth = 0          # div depth inside the current article
        self._skip = 0           # inside an amendment marker paragraph

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "p" and a.get("class") in ("modref", "arrow"):
            self._skip += 1
            return
        if self._skip and tag == "p":
            self._skip += 1
        if tag != "div":
            return
        if self._key is not None:
            self._depth += 1
            return
        el = a.get("id") or ""
        m, n = _ART_ID.match(el), _ANX_ID.match(el)
        if m or n:
            self._key = f"Art {m.group(1)}" if m else f"Annex {n.group(1)}"
            self.parts.setdefault(self._key, [])
            self._depth = 1

    def handle_endtag(self, tag):
        if tag == "p" and self._skip:
            self._skip -= 1
            return
        if tag == "div" and self._key is not None:
            self._depth -= 1
            if self._depth == 0:
                self._key = None

    def handle_data(self, data):
        if self._key is not None and not self._skip:
            self.parts[self._key].append(data)


def normalise(text: str) -> str:
    text = _MARKERS.sub(" ", text).replace(" ", " ")
    text = text.replace("‘", "'").replace("’", "'")
    # footnote calls: "(*)", "(*1)" or "( 57)", numbered differently in each edition
    text = re.sub(r"\(\s*\*\s*\d*\s*\)|\(\s+\d+\s*\)", " ", text)
    text = re.sub(r"\s+", " ", text).replace("( ", "(")
    return re.sub(r" ([,.;:)])", r"\1", text).strip()


def split_articles(html: str) -> dict[str, str]:
    s = _Splitter()
    s.feed(html)
    s.close()
    return {k: normalise(" ".join(v)) for k, v in s.parts.items()}


def layout_problems(html: str, parts: dict[str, str], min_articles: int = 100,
                    min_annexes: int = 10) -> list[str]:
    """Reasons to distrust a page. Any problem means: no verdict today, no alarm."""
    out = []
    if CELEX not in html[:5000]:
        out.append("page does not name the AI Act")
    arts = [k for k in parts if k.startswith("Art ")]
    anx = [k for k in parts if k.startswith("Annex ")]
    if len(arts) < min_articles:
        out.append(f"only {len(arts)} articles found")
    if len(anx) < min_annexes:
        out.append(f"only {len(anx)} annexes found")
    for must in ("Art 5", "Art 6", "Art 50", "Annex III"):
        if len(parts.get(must, "")) < 200:
            out.append(f"{must} missing or nearly empty")
    return out


def fingerprint(parts: dict[str, str]) -> dict[str, str]:
    return {k: hashlib.sha256(v.encode("utf-8")).hexdigest()[:16] for k, v in parts.items()}


_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}


def _roman(s: str) -> int:
    vals = [_ROMAN[c] for c in s]
    return sum(-v if i + 1 < len(vals) and v < vals[i + 1] else v for i, v in enumerate(vals))


def sort_key(key: str) -> tuple:
    kind, ref = key.split(" ", 1)
    if kind == "Art":
        m = re.match(r"(\d+)(.*)", ref)
        return (0, int(m.group(1)), m.group(2))
    return (1, _roman(ref), "")


def diff(old: dict[str, str], new: dict[str, str]) -> dict[str, list[str]]:
    keys = old.keys() | new.keys()
    out = {"changed": [k for k in keys if k in old and k in new and old[k] != new[k]],
           "added": [k for k in keys if k not in old],
           "removed": [k for k in keys if k not in new]}
    return {k: sorted(v, key=sort_key) for k, v in out.items()}


# --- which code cites what ----------------------------------------------------- #
_CITE = re.compile(r"(AI Act )?\b(?:Art(?:icle)?s?\.?\s*(\d+)(?:[a-z](?![a-z]))?(?:\(\w+\))*"
                   r"(?:\s*-\s*(\d+))?|Annex(?:es)?\s+([IVXL]+)\b)")
_OTHER_LAW = ("GDPR", "Directive ")


def citations(text: str) -> set[str]:
    """Articles of the AI Act cited in a piece of text. GDPR and directives are skipped."""
    other = any(w in text for w in _OTHER_LAW)
    out = set()
    for m in _CITE.finditer(text):
        ai_act, a, b, annex = m.groups()
        if other and not ai_act:
            continue
        if annex:
            out.add(f"Annex {annex}")
        elif a:
            lo = int(a)
            hi = int(b) if b and int(b) > lo else lo
            out.update(f"Art {n}" for n in range(lo, hi + 1))
    return out


def _owners(tree: ast.Module) -> list[tuple[int, int, str]]:
    spans = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            spans.append((node.lineno, node.end_lineno, node.name))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    spans.append((node.lineno, node.end_lineno, t.id))
    return sorted(spans)


def _owner_of(line: int, spans) -> str | None:
    for lo, hi, name in spans:
        if lo <= line <= hi:
            return name
    later = [s for s in spans if s[0] > line]   # a comment just above a definition
    return later[0][2] if later else None


def _docstrings(tree: ast.Module) -> set[int]:
    ids = set()
    for node in [tree, *ast.walk(tree)]:
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def citation_map(root: Path = ROOT, files=CODE_FILES) -> dict[str, dict[str, list[str]]]:
    """{"Art 5": {"src/rules.py": ["classify"], "src/screener/law.py": ["PROHIBITED", ...]}}"""
    found: dict[str, dict[str, set[str]]] = {}

    def add(art, f, owner):
        if owner:
            found.setdefault(art, {}).setdefault(f, set()).add(owner)

    for f in files:
        src = (root / f).read_text(encoding="utf-8")
        tree = ast.parse(src)
        spans, docs = _owners(tree), _docstrings(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in docs:
                for art in citations(node.value):
                    add(art, f, _owner_of(node.lineno, spans))
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                for art in citations(tok.string):
                    add(art, f, _owner_of(tok.start[0], spans))
    for art, per_file in EXTRA_CITES.items():
        for f, names in per_file.items():
            if f in files:
                for n in names:
                    add(art, f, n)
    return {a: {f: sorted(n) for f, n in sorted(v.items())} for a, v in found.items()}


# --- the daily check ------------------------------------------------------------- #
@dataclass
class Report:
    # baseline, unchanged, changed, unavailable or unreadable
    status: str
    note: str = ""
    state: dict | None = None                 # what to store, None = keep the old state
    version_before: str = ""
    version_after: str = ""
    new_acts: dict[str, str] = field(default_factory=dict)
    changes: dict[str, list[str]] = field(default_factory=dict)

    @property
    def alarm(self) -> bool:
        return self.status == "changed" and bool(self.new_acts or any(self.changes.values()))


def check(stored: dict | None, source, today: str, min_articles: int = 100,
          min_annexes: int = 10) -> Report:
    try:
        versions = source.versions()
        acts = source.amending()
    except Unavailable as exc:
        return Report("unavailable", str(exc))
    if not versions:
        return Report("unavailable", "no consolidated version listed")

    latest = versions[-1]
    before = (stored or {}).get("consolidated", "")
    if before.startswith(CONSOLIDATED) and latest < before:
        return Report("unavailable", f"listing went backwards ({latest} < {before})")
    known = (stored or {}).get("amending_acts", {})
    new_acts = {c: d for c, d in acts.items() if c not in known} if stored else {}
    state = dict(stored or {})
    state.update({"celex": CELEX, "checked": today, "versions": versions,
                  "amending_acts": {**known, **acts}})

    if stored and latest == before:
        if new_acts:   # amended in the Official Journal, consolidation not out yet
            return Report("changed", "new amending act, consolidated text not updated yet",
                          state, before, latest, new_acts)
        return Report("unchanged", f"still {latest}", state, before, latest)

    try:
        html = source.html(latest)
    except Unavailable as exc:
        return Report("unavailable", str(exc))
    parts = split_articles(html)
    problems = layout_problems(html, parts, min_articles, min_annexes)
    if problems:
        # keep the old state so tomorrow tries again; amending acts still count
        if new_acts:
            return Report("changed", "text unreadable: " + "; ".join(problems), None,
                          before, latest, new_acts)
        return Report("unreadable", "; ".join(problems))

    state.update({"consolidated": latest, "articles": fingerprint(parts)})
    if not stored or not stored.get("articles"):
        return Report("baseline", f"stored {len(parts)} articles and annexes of {latest}",
                      state, before, latest)
    changes = diff(stored["articles"], state["articles"])
    return Report("changed", f"{before} -> {latest}", state, before, latest, new_acts, changes)


# --- the issue ----------------------------------------------------------------------- #
MARKER = "ai-act-law-watch"


def issue_key(r: Report) -> str:
    return r.version_after + "|" + ",".join(sorted(r.new_acts))


def render_issue(r: Report, cites: dict[str, dict[str, list[str]]],
                 legal_basis: str) -> tuple[str, str]:
    touched = [*r.changes.get("changed", []), *r.changes.get("added", []),
               *r.changes.get("removed", [])]
    if touched:
        more = f" and {len(touched) - 5} more" if len(touched) > 5 else ""
        head = ", ".join(touched[:5]) + more
        title = f"EU AI Act text changed: {head}"
    else:
        title = "New act amends the EU AI Act: " + ", ".join(sorted(r.new_acts))

    lines = ["The daily law watch found a change in the official text of the EU AI Act "
             "(Regulation (EU) 2024/1689). The screener's encoding is current to "
             f"{legal_basis}.", ""]
    if r.version_after and r.version_after != r.version_before:
        was = f", was {r.version_before}" if r.version_before else ""
        lines.append(f"- Consolidated version: [{r.version_after}]"
                     f"({EURLEX.format(r.version_after)}){was}")
    for c, d in sorted(r.new_acts.items()):
        dated = f", dated {d}" if d else ""
        lines.append(f"- New amending act: [{c}]({EURLEX.format(c)}){dated}")
    if r.new_acts and not touched:
        lines.append("- The consolidated text has not caught up yet. This watch will report the "
                     "changed articles when it does.")
    if touched:
        lines += ["", "| Article | Change | Re-check in the code |", "|---|---|---|"]
        rows = [(kind, art) for kind in ("changed", "added", "removed")
                for art in r.changes.get(kind, [])]
        rows.sort(key=lambda row: row[1] not in cites)   # the ones our code cites first
        for kind, art in rows:
            where = cites.get(art)
            code = "; ".join(f"`{f}`: " + ", ".join(f"`{n}`" for n in names)
                             for f, names in where.items()) if where else "not cited in the code"
            lines.append(f"| {art} | {kind} | {code} |")
        cited = [a for a in touched if a in cites]
        lines += ["", f"{len(cited)} of {len(touched)} changed parts are cited by the screener."]
    lines += ["", "Once the code is reviewed, update `LEGAL_BASIS_DATE` in `src/rules.py` and "
              "close this issue.", "", f"<!-- {MARKER} {json.dumps({'key': issue_key(r)})} -->"]
    return title, "\n".join(lines) + "\n"
