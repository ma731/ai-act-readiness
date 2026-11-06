"""Generated proposals with known answers, to measure the reader rather than trust it.

Each scenario carries a label written by hand (not computed by law.py, which would only
test the code against itself) and is phrased two ways:
  * plain: the words a compliance reviewer would expect ("screens CVs", "trust score")
  * disguised: the same practice in product language ("surfaces the best fits")
Crossed with who builds the system (provider or deployer) and a few neutral context
sentences, that gives a test set whose wording varies while the answer does not.

A model can add a third style, `rewritten`: the model paraphrases a plain proposal and the
label is inherited. That set is only as good as the rewrite, and is reported separately.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

TIERS = ("prohibited", "high_risk", "transparency", "minimal")


@dataclass(frozen=True)
class Scenario:
    key: str
    label: object               # a tier, or {"provider": tier, "deployer": tier}
    area: str
    plain: tuple[str, ...]
    disguised: tuple[str, ...]


S = Scenario
SCENARIOS = [
    S("emotion_at_work", "prohibited", "Art 5(1)(f)",
      ("The system reads employees' facial expressions on webcam to detect stress and frustration during shifts.",
       "It analyses the voices of our call-centre staff to infer their mood and reports it to team leads."),
      ("A camera-based wellbeing layer picks up how our agents are feeling minute by minute so supervisors can step in.",
       "Team leads get a live read on how energised or drained each person on shift seems.")),
    S("social_scoring", "prohibited", "Art 5(1)(c)",
      ("We will give every resident a trust score that decides how quickly their permit requests are handled.",
       "The city will score citizens on their behaviour and use the score to rank access to services."),
      ("Residents get a civic reliability rating, built from their payment and complaint history, that sets their queue priority.",
       "People who have been good neighbours move faster through every council queue.")),
    S("child_nudging", "prohibited", "Art 5(1)(b)",
      ("The app uses persuasive nudges aimed at children to push in-game purchases.",
       "It targets kids with urgent offers designed to pressure them into buying coins."),
      ("Younger players see timed offers tuned to the moment they are most likely to tap buy.",
       "Our engagement engine learns when each young user is most impulsive and shows the shop then.")),
    S("face_scraping", "prohibited", "Art 5(1)(e)",
      ("We will scrape photos from social media to build a face database for identification.",
       "The system scrapes images from public CCTV feeds and the web to grow a facial recognition index."),
      ("We will collect public profile pictures at scale to grow our identity-matching index.",
       "A crawler gathers every portrait it can find online so the matcher knows more people.")),
    S("cv_screening", "high_risk", "Annex III 4a",
      ("The tool screens CVs and shortlists candidates for interviews.",
       "It ranks job applicants and recommends who should go through to the next round."),
      ("It reads incoming applications and surfaces the best fits for each opening.",
       "Hiring managers only see the people the matcher thinks will succeed in the role.")),
    S("worker_monitoring", "high_risk", "Annex III 4b",
      ("It tracks warehouse workers' productivity scores and allocates shifts accordingly.",
       "Performance monitoring of drivers decides who gets promotion and who is let go."),
      ("Each picker's pace feeds tomorrow's rota automatically.",
       "Drivers' on-time records quietly shape who gets the better routes next quarter.")),
    S("credit_scoring", "high_risk", "Annex III 5b",
      ("It assesses the creditworthiness of loan applicants and sets their credit limit.",
       "The model gives every applicant a credit score that decides whether the loan is approved."),
      ("It decides who qualifies for our buy-now-pay-later option and how much they can spend.",
       "Shoppers see an instant spending allowance at checkout, sized to how reliably we think they will repay.")),
    S("life_insurance_pricing", "high_risk", "Annex III 5c",
      ("It sets life insurance premiums from each applicant's health risk.",
       "Health insurance pricing will use the model's risk score for every new customer."),
      ("Cover prices adjust to each customer's medical profile when they sign up for our protection plan.",
       "The quote a member sees for their family cover reflects what their medical history suggests.")),
    S("benefits_eligibility", "high_risk", "Annex III 5a",
      ("The council uses it to check eligibility for social assistance benefits.",
       "It assesses applications for housing benefit and flags who is entitled to payment."),
      ("It flags which households should keep receiving housing support.",
       "Caseworkers get a list of families whose support the system thinks should be reviewed first.")),
    S("exam_proctoring", "high_risk", "Annex III 3d",
      ("It monitors students on webcam during online exams to detect cheating.",
       "The proctoring tool watches pupils during tests and reports suspected cheating to teachers."),
      ("During remote tests it watches for anything that looks like outside help.",
       "If a student's eyes wander off screen during the final, a teacher is told.")),
    S("admissions", "high_risk", "Annex III 3a",
      ("It ranks applicants to the university's master programme for admission.",
       "Admission to the school will be decided with the model's ranking of applicants."),
      ("It decides which applicants get an offer for next year's intake.",
       "The model sorts this year's hopefuls so the committee knows whom to invite.")),
    S("emergency_triage", "high_risk", "Annex III 5d",
      ("It triages emergency calls and sets dispatch priority.",
       "The system evaluates 112 calls and decides which emergency service is sent first."),
      ("When someone dials for help it decides which ambulance goes first.",
       "Incoming distress lines are ordered by how urgent the caller sounds.")),
    S("chatbot", "transparency", "Art 50(1)",
      ("A chatbot answers customers' billing questions on our website.",
       "We will launch a virtual assistant that talks to customers about their orders."),
      ("A conversational helper handles customer questions around the clock.",
       "Customers type their question and get an instant, friendly reply in the app.")),
    S("deepfake_campaign", "transparency", "Art 50(4)",
      ("We will make a deepfake video of our CEO for the annual campaign.",
       "A synthetic video of our presenter will be generated for the product launch."),
      ("Our CEO's likeness will front the campaign without her needing to film anything.",
       "We will clone our spokesperson's face and voice for this year's adverts.")),
    S("ad_generation", {"provider": "transparency", "deployer": "minimal"}, "Art 50(2)",
      ("The tool generates images for ad creatives.",
       "It generates marketing copy and visuals for every campaign."),
      ("The studio model produces campaign visuals on demand.",
       "Every banner and caption in the campaign comes straight out of the model.")),
    S("demand_forecast", "minimal", "none",
      ("It forecasts weekly demand for each store from past sales.",
       "The model predicts how many units of each product we will sell next month."),
      ("Store orders follow a prediction of next week's sales.",
       "Shelves are restocked from the model's view of what will sell.")),
    S("card_fraud", "minimal", "Annex III 5b carve-out",
      ("It flags suspicious card transactions for the fraud team.",
       "The model detects fraud in card payments and holds them for review."),
      ("Unusual payments get held for a second look by the payments team.",
       "Odd-looking card activity is paused until someone checks it.")),
    S("predictive_maintenance", "minimal", "none",
      ("It predicts when factory machines need maintenance from vibration data.",
       "The model estimates the remaining life of each pump so repairs can be planned."),
      ("Engineers get told which machines will need attention next week.",
       "Sensor readings tell us which motors to service before they fail.")),
    S("spam_filter", "minimal", "none",
      ("It filters spam out of the shared customer-service inbox.",
       "The model sorts incoming emails into topics for the right team."),
      ("Junk never reaches the service team's inbox.",
       "Messages land in the right team's queue without anyone sorting them.")),
    S("route_planning", "minimal", "none",
      ("It plans delivery routes for our vans to cut fuel use.",
       "The optimiser assigns parcels to vans and orders the stops."),
      ("Vans leave each morning with the shortest sensible loop.",
       "Stops are ordered overnight so drivers spend less time in traffic.")),
]

COMPANIES = ["Norte Retail", "Ebro Logistics", "Moncayo Health", "Aragon Bank", "Pirineo Insurance",
             "Huesca Council", "Teruel Learning", "Cinca Energy", "Jalon Media", "Gallego Telecom"]
ROLES = {"provider": "We will build it in-house with our own data team.",
         "deployer": "We will license an off-the-shelf vendor tool for this."}
CONTEXT = ["The pilot starts next quarter in one region.",
           "A project lead owns it and reports to the steering committee.",
           "Success is measured against last year's numbers."]


def label(sc: Scenario, role: str) -> str:
    return sc.label[role] if isinstance(sc.label, dict) else sc.label


def generate() -> list[dict]:
    """Deterministic test set: every scenario x style x variant x role."""
    rows, n = [], 0
    for i, sc in enumerate(SCENARIOS):
        for style in ("plain", "disguised"):
            for j, core in enumerate(getattr(sc, style)):
                for role, role_text in ROLES.items():
                    n += 1
                    company = COMPANIES[(i + j) % len(COMPANIES)]
                    ctx = CONTEXT[(i + j + len(role)) % len(CONTEXT)]
                    rows.append({
                        "id": f"G{n:03d}", "company": f"{company} (generated)",
                        "title": sc.key.replace("_", " ").capitalize(),
                        "proposal": f"{company} wants to use AI in its operations. {core} {role_text} {ctx}",
                        "expected_tier": label(sc, role), "scenario": sc.key, "style": style,
                        "role": role, "area": sc.area,
                    })
    return rows


REWRITE_PROMPT = ("Rewrite this business proposal in different words, as a product manager would write it. "
                  "Keep every fact: what the system does, to whom, and who builds it. Do not mention any law, "
                  "risk category or compliance term. Reply with the rewritten proposal only.")


def rewritten(rows: list[dict], reader, limit: int) -> list[dict]:
    """Model paraphrases of plain proposals; the label is inherited."""
    out = []
    for r in [r for r in rows if r["style"] == "plain"][:limit]:
        text = (reader.write(REWRITE_PROMPT, r["proposal"]) or "").strip()
        if text:
            out.append({**r, "id": "R" + r["id"][1:], "proposal": text, "style": "rewritten"})
    return out


def evaluate(rows: list[dict], screenings: list) -> dict:
    """Accuracy overall, by wording style and by tier; confusion matrix; the misses."""
    by_style, by_tier = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    confusion = Counter()
    misses = []
    for r, s in zip(rows, screenings, strict=True):
        got, want = s.assessment.tier, r["expected_tier"]
        ok = got == want
        for d, k in ((by_style, r["style"]), (by_tier, want)):
            d[k][0] += ok
            d[k][1] += 1
        confusion[(want, got)] += 1
        if not ok:
            misses.append({"id": r["id"], "scenario": r["scenario"], "style": r["style"], "role": r["role"],
                           "expected": want, "got": got, "proposal": r["proposal"]})
    pct = lambda a: round(a[0] / a[1], 3) if a[1] else None  # noqa: E731
    total = [sum(v[0] for v in by_style.values()), sum(v[1] for v in by_style.values())]
    # The costly mistake is calling a prohibited or high-risk system something milder.
    severe = sum(1 for m in misses if TIERS.index(m["got"]) > TIERS.index(m["expected"]) and m["expected"] in TIERS[:2])
    return {
        "n": total[1], "accuracy": pct(total),
        "by_style": {k: {"accuracy": pct(v), "n": v[1]} for k, v in by_style.items()},
        "by_tier": {k: {"accuracy": pct(v), "n": v[1]} for k, v in by_tier.items()},
        "confusion": [{"expected": a, "got": b, "n": c} for (a, b), c in sorted(confusion.items())],
        "under_called_severe": severe,
        "misses": misses,
    }
