"""The daily EU AI Act watch. Saved excerpts of the official text, no network."""
from pathlib import Path

import pytest

from src import lawwatch as lw

FIX = Path(__file__).parent / "fixtures" / "lawwatch"
PAGE = (FIX / "consolidated_excerpt.html").read_text(encoding="utf-8")
V1, V2 = "02024R1689-20260727", "02024R1689-20271201"
SMALL = {"min_articles": 4, "min_annexes": 1}       # the excerpt holds 4 articles, 1 annex


class Fake:
    def __init__(self, versions=(V1,), acts=None, page=PAGE, fail=None):
        self._v, self._a, self._page, self._fail = list(versions), acts or {}, page, fail
        self.html_calls = 0

    def versions(self):
        if self._fail == "list":
            raise lw.Unavailable("timeout")
        return self._v

    def amending(self):
        return self._a

    def html(self, celex):
        self.html_calls += 1
        if self._fail == "html":
            raise lw.Unavailable("202 bot check, empty body")
        return self._page


def baseline(**kw):
    r = lw.check(None, Fake(**kw), "2026-11-13", **SMALL)
    assert r.status == "baseline" and not r.alarm
    return r.state


# --- reading the page ------------------------------------------------------------ #
def test_excerpt_splits_into_articles_and_annex():
    parts = lw.split_articles(PAGE)
    assert set(parts) == {"Art 4", "Art 5", "Art 6", "Art 50", "Annex III"}
    assert parts["Art 5"].startswith("Article 5 Prohibited AI practices")
    assert "(ba)" in parts["Art 5"]                      # added by the Digital Omnibus
    assert lw.layout_problems(PAGE, parts, **SMALL) == []


def test_amendment_arrows_are_not_part_of_the_text():
    text = " ".join(lw.split_articles(PAGE).values())
    assert "M1" not in text and "▼" not in text and "►" not in text


def test_footnote_numbering_and_spacing_do_not_count_as_changes():
    a = lw.normalise("of the Council ( 57); (b) the ( OJ L 312, 1.2.2024) ( * ) , the")
    b = lw.normalise("of the Council ( 2); (b) the (OJ L 312, 1.2.2024) ( *1 ), the")
    assert a == b


def test_a_real_word_change_does_count():
    assert lw.normalise("SMEs including start-ups") != lw.normalise("SMEs, including start-ups")


@pytest.mark.parametrize("page", ["", "<html><body>Please wait while we check your browser"
                                  "</body></html>",
                                  PAGE.replace('id="art_', 'id="article-')],
                         ids=["empty", "bot-check", "redesigned"])
def test_bot_check_or_redesigned_page_is_flagged_as_unreadable(page):
    assert lw.layout_problems(page, lw.split_articles(page), **SMALL)


def test_real_thresholds_reject_a_truncated_page():
    problems = lw.layout_problems(PAGE, lw.split_articles(PAGE))
    assert any("articles found" in p for p in problems)


# --- the daily decision ------------------------------------------------------------- #
def test_first_run_stores_a_baseline_without_an_alarm():
    state = baseline()
    assert state["consolidated"] == V1 and set(state["articles"]) >= {"Art 5", "Annex III"}


def test_network_failure_is_not_a_change():
    r = lw.check(baseline(), Fake(fail="list"), "d", **SMALL)
    assert r.status == "unavailable" and not r.alarm and r.state is None


def test_same_version_skips_the_download():
    src = Fake()
    r = lw.check(baseline(), src, "d", **SMALL)
    assert r.status == "unchanged" and not r.alarm and src.html_calls == 0


def test_new_amending_act_alarms_before_the_consolidation_catches_up():
    r = lw.check(baseline(), Fake(acts={"32027R0001": "2027-03-01"}), "d", **SMALL)
    assert r.alarm and r.new_acts == {"32027R0001": "2027-03-01"}
    assert r.state["amending_acts"]["32027R0001"] == "2027-03-01"


def test_known_amending_act_is_not_reported_twice():
    state = baseline(acts={"32026R1744": "2026-07-08"})
    r = lw.check(state, Fake(acts={"32026R1744": "2026-07-08"}), "d", **SMALL)
    assert not r.alarm


def test_new_version_with_changed_article_names_it():
    changed = PAGE.replace("shall be prohibited", "shall be banned", 1)
    assert changed != PAGE
    r = lw.check(baseline(), Fake(versions=(V1, V2), page=changed), "d", **SMALL)
    assert r.alarm and r.changes["changed"] == ["Art 5"]
    assert r.state["consolidated"] == V2


def test_new_version_with_identical_text_is_quiet():
    r = lw.check(baseline(), Fake(versions=(V1, V2)), "d", **SMALL)
    assert r.status == "changed" and not r.alarm
    assert r.state["consolidated"] == V2


def test_new_version_but_unreadable_page_keeps_the_old_state():
    r = lw.check(baseline(), Fake(versions=(V1, V2), page=""), "d", **SMALL)
    assert r.status == "unreadable" and not r.alarm and r.state is None


def test_new_version_but_download_fails_keeps_the_old_state():
    r = lw.check(baseline(), Fake(versions=(V1, V2), fail="html"), "d", **SMALL)
    assert r.status == "unavailable" and not r.alarm and r.state is None


def test_listing_that_goes_backwards_is_ignored():
    state = baseline()
    state["consolidated"] = V2
    r = lw.check(state, Fake(versions=(V1,)), "d", **SMALL)
    assert r.status == "unavailable" and not r.alarm


# --- the Publications Office answers ---------------------------------------------------- #
def test_saved_sparql_answers_parse():
    rows = lw.parse_sparql((FIX / "sparql_versions.json").read_bytes())
    assert lw.consolidated_ids(rows)[-1] == V1
    acts = lw.parse_sparql((FIX / "sparql_amending.json").read_bytes())
    assert {"celex": "32026R1744", "date": "2026-07-08"} in acts


def test_garbage_sparql_answer_is_unavailable_not_empty():
    with pytest.raises(lw.Unavailable):
        lw.parse_sparql(b"<html>maintenance</html>")


# --- which code cites what ------------------------------------------------------------------ #
@pytest.mark.parametrize("text,expected", [
    ("prohibited by Art 5(1)(f) since 2 Feb 2025", {"Art 5"}),
    ("Art 9-15", {f"Art {n}" for n in range(9, 16)}),
    ("Art 47-48 and Annex IV", {"Art 47", "Art 48", "Annex IV"}),
    ("Annex III 5(b) and Annex I", {"Annex III", "Annex I"}),
    ("GDPR Art 9: needs an Art 9(2) basis. Art 35 DPIA (AI Act Art 27(4)).", {"Art 27"}),
    ("Directive 2004/113 Art 5 (Test-Achats)", set()),
])
def test_citations(text, expected):
    assert lw.citations(text) == expected


def test_citation_map_points_at_the_real_code():
    m = lw.citation_map()
    assert "PROHIBITED" in m["Art 5"]["src/screener/law.py"]
    assert "ANNEX_III" in m["Annex III"]["src/screener/law.py"]
    assert "_high_risk_duties" in m["Art 12"]["src/rules.py"]
    assert "APPLIES" in m["Art 113"]["src/rules.py"]
    assert "Art 35" not in m and "Art 22" not in m          # GDPR, not the AI Act


def test_sort_order_is_legal_not_alphabetical():
    keys = ["Annex XIV", "Art 10", "Annex IV", "Art 4a", "Art 5", "Art 4", "Annex I"]
    assert sorted(keys, key=lw.sort_key) == ["Art 4", "Art 4a", "Art 5", "Art 10",
                                             "Annex I", "Annex IV", "Annex XIV"]


def test_issue_names_articles_code_and_link():
    r = lw.check(baseline(), Fake(versions=(V1, V2),
                                  page=PAGE.replace("shall be prohibited", "shall be banned", 1)),
                 "d", **SMALL)
    title, body = lw.render_issue(r, lw.citation_map(), "27 Sep 2026")
    assert title == "EU AI Act text changed: Art 5"
    assert "| Art 5 | changed | " in body and "`PROHIBITED`" in body
    assert f"CELEX:{V2}" in body and f"was {V1}" in body
    assert lw.issue_key(r) in body
    assert "—" not in title + body
