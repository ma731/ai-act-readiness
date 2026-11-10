"""One idea in, a reasoned answer out. This is what the site's guide runs in the browser (Pyodide).

check(text, answers) screens a typed idea with the offline reader and the law in code, then
asks only the follow-up questions whose answer could change the result: who builds it, whether
a person makes the final call, whether people talk to it. Each answer is a plain sentence added
to the idea, so it goes through the same reader and quote check as everything else.
"""
from __future__ import annotations

from .law import ANNEX_III
from .pipeline import screen_one, to_dict
from .readers import OfflineReader

# id -> (question, [(label, sentence added to the idea)])
QUESTIONS = {
    "role": ("Will you build it yourselves, or buy it from a vendor?",
             [("We build it", "We develop it ourselves."),
              ("We buy it", "We buy a vendor tool and use it.")]),
    "final_call": ("Does a person make the final decision, with the tool only preparing it?",
                   [("A person decides", "The tool only prepares the case and the final decision remains with a person."),
                    ("The tool decides", "It decides automatically without human review.")]),
    "profiling": ("Does it score or rank individual people?",
                  [("Yes, it scores people", "It scores each person on their personal characteristics."),
                   ("No, it looks at cases", "It looks at documents and cases, not at people.")]),
    "talks": ("Will people talk to it directly, like a chatbot?",
              [("Yes", "Customers talk to it directly as a chatbot."),
               ("No", "Nobody talks to it directly.")]),
}


def _questions(facts: dict, tier: str, asked: set[str]) -> list[dict]:
    todo = []
    if tier in ("high_risk", "transparency") and not facts.get("role"):
        todo.append("role")
    if tier == "high_risk" and facts.get("annex_iii") and not facts.get("art6_3_claim") \
            and not facts.get("automated_decision"):
        todo.append("final_call")
    if facts.get("art6_3_claim") and not facts.get("profiling") and "profiling" not in asked:
        todo.append("profiling")
    if tier == "minimal" and not facts.get("annex_iii") and not facts.get("interacts_with_people"):
        todo.append("talks")
    return [{"id": q, "text": QUESTIONS[q][0], "options": [{"label": lab, "add": s} for lab, s in QUESTIONS[q][1]]}
            for q in todo if q not in asked][:2]


def check(text: str, answers: list[str] | None = None, asked: list[str] | None = None) -> dict:
    """Screen one idea. `answers` are sentences from earlier follow-ups; `asked` their ids."""
    idea = " ".join(text.split())
    if idea and not idea.endswith((".", "!", "?")):
        idea += "."
    full = " ".join([idea, *(answers or [])])
    d = to_dict(screen_one({"id": "idea", "title": "Your idea", "proposal": full}, OfflineReader()))
    steps = [f"Read {len(d['evidence'])} fact(s), each tied to a sentence you wrote." if d["evidence"]
             else "Found nothing the AI Act singles out in the wording."]
    exempt = "Art 6(3)" in d["articles"] and d["tier"] != "high_risk"
    steps += [("So it counts as minimal risk, but the assessment must be written down before use "
               "and the system registered (Art 6(4), Art 49(2)).") if exempt and b.startswith("No prohibited") else b
              for b in d["basis"]]
    steps.append(f"Verdict: {d['verdict']}.")
    obligations = sorted(d["obligations"], key=lambda o: o["applies_from"])
    return {
        "tier": d["tier"], "verdict": d["verdict"], "articles": d["articles"], "steps": steps,
        "quotes": [{"fact": e["fact"], "value": str(e["value"]), "quote": e["quote"],
                    "area": ANNEX_III.get(str(e["value"]), "") if e["fact"] == "annex_iii" else ""}
                   for e in d["evidence"]],
        "obligations": [{"article": o["article"], "duty": o["duty"], "holder": o["holder"],
                         "from": o["applies_from"], "in_force": o["in_force"]} for o in obligations[:5]],
        "more_obligations": max(0, len(obligations) - 5),
        "next_deadline": d["next_deadline"], "review": d["review_reasons"],
        "questions": _questions(d["facts"], d["tier"], set(asked or [])),
        "text": full,
    }
