"""The reader agents: turn a free-text proposal into facts, each backed by a quote.

Every reader shares one output shape:
  * OfflineReader: keyword rules. Free, deterministic, runs in CI and on the static site.
    It is a baseline, tuned on the sample proposals, and says so.
  * Model readers, all with a strict JSON schema: Claude on the Claude API, Claude on
    Azure (Foundry), or an OpenAI model on Azure OpenAI. `make_reader` picks one from
    the environment.

Whatever reads the proposal, `verify_quotes` then drops any fact whose quote is not
actually in the proposal text. A reader cannot add a fact the proposal does not contain.
"""
from __future__ import annotations

import json
import os
import re

from .law import ANNEX_III, ART6_3, FACT_KEYS, PROHIBITED

MODEL = os.getenv("SCREENER_MODEL", "claude-opus-5-5")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def verify_quotes(text: str, evidence: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep only evidence whose quote appears in the text. Returns (kept, rejected)."""
    body = _norm(text)
    kept, rejected = [], []
    for e in evidence:
        q = _norm(e.get("quote", ""))
        (kept if q and q in body else rejected).append(e)
    return kept, rejected


def facts_from_evidence(evidence: list[dict]) -> dict:
    """Build the facts dict only from verified evidence."""
    facts: dict = {}
    for e in evidence:
        key, value = e.get("fact"), e.get("value")
        if key not in FACT_KEYS:
            continue
        if FACT_KEYS[key] is list:
            vals = value if isinstance(value, list) else [value]
            facts.setdefault(key, [])
            facts[key] += [v for v in vals if v not in facts[key]]
        else:
            facts[key] = bool(value)
    return facts


# --------------------------------------------------------------------------------------- #
# Offline reader: keyword rules
# --------------------------------------------------------------------------------------- #
# (fact, value, pattern): a pattern matches inside one sentence; its sentence is the quote.
RULES: list[tuple[str, object, str]] = [
    ("prohibited", "emotion_recognition_work_education",
     r"(emotion|stress|mood|frustrat|sentiment).{0,80}(employee|staff|worker|cashier|agent|student|pupil|class)|"
     r"(employee|staff|worker|cashier|agent|student|pupil|class).{0,80}(emotion|stress|mood|frustrat|sentiment)"),
    ("prohibited", "social_scoring", r"(trust|citizen|social|reliability)\w* score|score (residents|citizens)|rate (residents|citizens)"),
    ("prohibited", "facial_scraping", r"scrap\w+.{0,80}(face|photo|image)|(face|photo|image)\w*.{0,80}scrap"),
    ("prohibited", "crime_prediction_profiling", r"predict\w*.{0,60}(crime|offen|reoffend)"),
    ("prohibited", "exploits_vulnerabilities", r"(child|kids|elderly|minors)\w*.{0,120}(persua|pressure|nudge|urg|purchase)|(persua|nudge|pressure).{0,120}(child|kids|minors)"),
    ("prohibited", "biometric_categorisation_sensitive", r"(infer|deduce|detect)\w*.{0,60}(ethnic|race|religio|political|sexual orientation|union)"),
    ("prohibited", "realtime_rbi_law_enforcement", r"real.time.{0,60}(facial recognition|biometric).{0,80}(police|law enforcement)"),
    ("annex_iii", "4a", r"\b(cvs?|résumé|resume|candidates?|recruit\w*|hiring|shortlist\w*|job applicants?)\b"),
    ("annex_iii", "4b", r"(allocat\w+ (\w+ )?(tasks|shifts)|task allocation|"
                        r"(performance|productivity) (monitor|scor|rank|track)|(monitor|track|rank|scor)\w*.{0,40}(productivity|performance)|"
                        r"promot\w+ (staff|employees|workers)|promotion decisions?|dismiss)"),
    ("annex_iii", "5b", r"(credit\s?worth|credit scor|loan|lending|credit limit)"),
    ("fraud_detection_only", True, r"(fraud|suspicious transaction)"),
    ("annex_iii", "5c", r"(life|health) insurance.{0,80}(pric|premium|underwrit|risk)|(pric|premium|underwrit).{0,80}(life|health) insurance"),
    ("annex_iii", "5d", r"emergency (call|service)|112 call|triage"),
    ("annex_iii", "5a", r"(benefit|subsid|social assistance).{0,80}(eligib|entitle)"),
    ("annex_iii", "3a", r"admission|applicants? to (the )?(university|school|programme)"),
    ("annex_iii", "3b", r"grad(e|ing) (essays|exams|assignments)|evaluat\w+ learning"),
    ("annex_iii", "3d", r"proctor|cheating|exam (monitor|surveil)"),
    ("annex_iii", "2", r"(water|gas|electric|heating|traffic)\w*.{0,100}(valve|pressure|shut.?off|safety)|"
                       r"(valve|pressure|shut.?off)\w*.{0,100}(water|gas|electric|heating) (network|grid|supply)|safety (valve|shut)"),
    ("annex_iii", "1a", r"(facial recognition|face recognition).{0,80}(identif|crowd|public)"),
    ("annex_iii", "1c", r"(emotion|stress|mood|sentiment).{0,60}(voice|face|facial|camera|webcam)|(voice|face|facial|camera|webcam).{0,60}(emotion|stress|mood)"),
    ("annex_iii", "7", r"(asylum|visa|border control|migrant)"),
    ("annex_iii", "8a", r"(\bjudges?\b|\bcourts?\b|sentencing|judicial)"),
    ("annex_iii", "8b", r"(voter|election|electoral)"),
    ("annex_i_safety_component", True, r"(medical device|braking|machinery|lift safety|toy safety|insulin pump)"),
    ("interacts_with_people", True, r"(chatbot|virtual assistant|voice assistant|talks? (to|with) (customers|users|children)|conversational)"),
    ("generates_synthetic_content", True, r"generat\w+ (images|videos|audio|text|copy|visuals|ad creatives)"),
    ("deepfake", True, r"(deepfake|deep fake|synthetic video of|digital twin of (our|the) (ceo|presenter))"),
    ("emotion_or_biometric_categorisation", True, r"(emotion|mood|stress).{0,60}(voice|face|camera|webcam)"),
    ("profiling", True, r"(profil|score each|scores each|shortlist\w*|rank\w* (\w+ )?(candidates|workers|employees|applicants|residents|pickers|drivers)|"
                        r"(each|individual) (worker|employee|picker|driver|candidate|applicant)'?s?'? (pick|performance|productivity|error|history|record)|"
                        r"personal characteristics|behaviour data|behavior data)"),
    ("uses_personal_data", True, r"(customer|employee|patient|applicant|citizen|resident|student|personal) (data|records|history|photos)|(cv|cvs|transaction history|call recordings|exam footage)"),
    ("uses_special_category_data", True, r"(health|medical|biometric|face|facial|religio|ethnic)"),
    ("automated_decision", True, r"automatic\w* (approve|reject|decline|decide|allocat|flag)|without (a )?human (review|check)|no human"),
    ("role", "provider", r"(we will build|we are building|in-house|our own model|we develop|developed by us|we will train)"),
    ("role", "deployer", r"(off-the-shelf|vendor|licen[cs]e[sd]? (a|the)|buy (a|the)|third-party tool|we will use|we use|deploy|in-house)"),
    ("art6_3_claim", "preparatory", r"(only prepares|just prepares|preparatory|recommendation only|final decision (stays|remains) with)"),
]


# Dutch rules, for the Dutch public algorithm register. Same facts, same quote rule.
RULES_NL: list[tuple[str, object, str]] = [
    ("prohibited", "emotion_recognition_work_education",
     r"emoti\w*.{0,80}(medewerker|werknemer|personeel|leerling|student)"),
    ("prohibited", "social_scoring", r"(burgerscore|sociale score|betrouwbaarheidsscore)"),
    # Art 5(1)(d) is about predicting that a person offends; place-based "hotspot" maps are not.
    ("prohibited", "crime_prediction_profiling",
     r"voorspel\w*.{0,80}(of (iemand|een persoon)|personen|individu\w*).{0,60}(crimin|strafba|delict)"),
    ("annex_iii", "1a", r"(gezichtsherkenning|biometrische identificatie)"),
    ("annex_iii", "1c", r"emoti\w*.{0,60}(herken|detect|analy)"),
    ("annex_iii", "2", r"(verkeersregelinstallatie|verkeerslicht|waterkering|stuw\b|sluis|gemaal|drinkwater|stroomnet|energienet)"
                       r".{0,100}(automatisch|aanstu|regel|bedien)"),
    ("annex_iii", "3a", r"toelating\w*.{0,60}(onderwijs|opleiding|school)|(onderwijs|school)\w*.{0,60}toelating"),
    ("annex_iii", "3b", r"(beoordel|nakijk)\w*.{0,40}(toets|examen|tentamen)"),
    ("annex_iii", "4a", r"\b(sollicit\w*|werving\w*|kandidaten|vacature\w*|recruitment\w*)\b"),
    ("annex_iii", "4b", r"(personeelsbeoordeling|prestaties van (medewerkers|werknemers)|taakverdeling.{0,40}medewerkers)"),
    ("annex_iii", "5a", r"(uitkering|bijstand|toeslag|participatiewet|wmo|schuldhulp|minimaregeling)\w*.{0,100}"
                        r"(aanvra|recht|beoordel|toeken|controle|risico|rechtmatig)"
                        r"|(aanvra|beoordel|toeken|controle|risico)\w*.{0,60}(uitkering|bijstand|toeslag|participatiewet|wmo)"),
    ("annex_iii", "5b", r"(kredietwaardig\w*|kredietscore|lening\w*.{0,40}beoordel)"),
    ("fraud_detection_only", True, r"(fraude|misbruik|oneigenlijk gebruik)"),
    ("annex_iii", "5d", r"(\b112\b|meldkamer)"),
    # Law enforcement uses; not municipal enforcement (parking, permits) or the word "politiek".
    ("annex_iii", "6", r"(recidive|opsporingsonderzoek|strafzaak|strafzaken|verdachte\w*|betrouwbaarheid van (het )?bewijs"
                       r"|dna[- ]?profiel\w*|risico op (her)?(crimin|delict|strafba))"),
    ("annex_iii", "7", r"(asiel\w*|vreemdeling\w*|visum|grenscontrole|migratie)"),
    ("annex_iii", "8a", r"(rechter\b|rechtspraak|rechtbank|vonnis)"),
    # 8b is influencing elections, not running them (voting passes, polling stations).
    ("annex_iii", "8b", r"(beïnvloed\w*.{0,40}(verkiezing|stemgedrag|kiezer)|stemadvies|kiezers.{0,40}(bereik|target))"),
    ("interacts_with_people", True, r"(chatbot|chatfunctie|virtuele assistent|digitale assistent|spraakassistent)"),
    ("generates_synthetic_content", True, r"(generatieve ai|taalmodel|chatgpt|copilot|\bgpt)"),
    ("deepfake", True, r"deepfake"),
    ("profiling", True, r"(risicoprofiel\w*|risicoscore\w*|risicoscan\w*|risicoselectie|risicomodel\w*|profilering"
                        r"|selectie.{0,30}(burgers|inwoners|aanvragers)|voorspel\w*.{0,40}kans|kans (is )?dat (iemand|u|een persoon))"),
    ("uses_personal_data", True, r"(persoonsgegevens|\bbsn\b|burgerservicenummer)"),
    ("uses_special_category_data", True, r"(gezondheidsgegevens|medische gegevens|biometrische|etnisch\w*|religie|strafrechtelijke gegevens)"),
    ("automated_decision", True, r"(automatisch\w* (besl|toege|afgewez|afwijz)|zonder menselijke tussenkomst|geautomatiseerde besluit)"),
    ("role", "deployer", r"(leverancier:|ingekocht|aangeschaft|standaardsoftware)"),
    ("role", "provider", r"(zelf ontwikkeld|eigen ontwikkeling|intern ontwikkeld|in eigen beheer)"),
    ("art6_3_claim", "preparatory", r"(medewerker (neemt|beslist|beoordeelt)|besluit wordt (altijd )?genomen door|geen automatische besluit|ondersteun\w* (de|onze) medewerker)"),
]


class OfflineReader:
    name = "offline keyword reader"

    def __init__(self, lang: str = "en"):
        import hashlib
        self.lang = lang
        self.rules = RULES_NL if lang == "nl" else RULES
        if lang != "en":
            self.name = f"offline keyword reader ({lang})"
        # Changes whenever a rule changes, so cached screenings are redone.
        self.version = hashlib.sha1(repr(self.rules).encode()).hexdigest()[:8]

    def read(self, text: str) -> dict:
        evidence = []
        for sent in sentences(text):
            low = sent.lower()
            for fact, value, pattern in self.rules:
                if re.search(pattern, low):
                    evidence.append({"fact": fact, "value": value, "quote": sent})
        # Fraud only counts as a carve-out when the proposal is about fraud and not lending.
        if any(e["fact"] == "fraud_detection_only" for e in evidence) and \
                any(e["value"] == "5b" for e in evidence if e["fact"] == "annex_iii"):
            lending = [s for s in sentences(text) if re.search(r"(approve|decid|grant|limit)\w*.{0,40}(loan|credit)", s.lower())]
            if lending:
                evidence = [e for e in evidence if e["fact"] != "fraud_detection_only"]
        return {"evidence": evidence, "unknowns": [], "reader": self.name}


# --------------------------------------------------------------------------------------- #
# Claude reader: strict JSON schema, quotes required
# --------------------------------------------------------------------------------------- #
FACT_GUIDE = (
    "Facts you may assert (fact -> value):\n"
    f"- prohibited -> one of {sorted(PROHIBITED)}\n"
    f"- annex_iii -> one of {sorted(ANNEX_III)}  ({'; '.join(f'{k}: {v}' for k, v in ANNEX_III.items())})\n"
    "- role -> provider (they build it) or deployer (they use someone else's)\n"
    f"- art6_3_claim -> one of {sorted(ART6_3)} (only if the proposal itself claims it)\n"
    "- annex_i_safety_component, fraud_detection_only, profiling, affects_natural_persons, interacts_with_people, "
    "generates_synthetic_content, deepfake, emotion_or_biometric_categorisation, uses_personal_data, "
    "uses_special_category_data, automated_decision -> true\n"
)

SCHEMA = {
    "type": "object",
    "properties": {
        "evidence": {"type": "array", "items": {
            "type": "object",
            "properties": {"fact": {"type": "string"}, "value": {"type": "string"},
                           "quote": {"type": "string"}},
            "required": ["fact", "value", "quote"], "additionalProperties": False}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["evidence", "unknowns"], "additionalProperties": False,
}

READ_PROMPT = (
    "You read proposals for AI use cases and extract facts that matter under the EU AI Act. "
    "Assert a fact only if a sentence of the proposal supports it, and copy that sentence "
    "(or a contiguous part of it) exactly into `quote`, in the proposal's own language (it may be "
    "Dutch or another language). Do not paraphrase or translate quotes. Do not decide "
    "the risk tier: other code does that. List in `unknowns` the facts that matter but the "
    "proposal does not settle (for example who builds the system, or whether a human reviews "
    "each decision). For boolean facts use the value \"true\".\n\n" + FACT_GUIDE
)

CHALLENGE_PROMPT = (
    "You are a sceptical second reviewer of an AI Act screening. Another reader extracted the "
    "facts below from the proposal. Find facts it MISSED that would change the classification "
    "(a prohibited practice, an Annex III area, an Annex I safety component, a transparency "
    "trigger, profiling). Only add a fact if you can quote the proposal exactly. If nothing "
    "was missed, return an empty evidence list.\n\n" + FACT_GUIDE
)


def _bool_or_str(value: str):
    return True if str(value).lower() == "true" else value


DECLINED = {"evidence": [], "unknowns": ["The model declined to read this proposal; review by hand."]}


class ModelReader:
    """What every model reader shares. A subclass only says how to call its provider:
    `_complete(system, user, schema, effort)` returns the text, or None on a refusal."""

    name = "model reader"

    def _complete(self, system: str, user: str, schema: dict | None, effort: str) -> str | None:
        raise NotImplementedError

    def _ask(self, system: str, user: str, effort: str = "low") -> dict:
        text = self._complete(system, user, SCHEMA, effort)
        if text is None:
            return dict(DECLINED, unknowns=list(DECLINED["unknowns"]))
        out = json.loads(text)
        for e in out["evidence"]:
            e["value"] = _bool_or_str(e["value"])
        return out

    def read(self, text: str) -> dict:
        out = self._ask(READ_PROMPT, f"PROPOSAL:\n{text}")
        out["reader"] = self.name
        return out

    def challenge(self, text: str, evidence: list[dict]) -> dict:
        found = json.dumps([{k: e[k] for k in ("fact", "value")} for e in evidence])
        return self._ask(CHALLENGE_PROMPT, f"PROPOSAL:\n{text}\n\nFACTS ALREADY FOUND:\n{found}", effort="medium")

    def write(self, system: str, user: str) -> str:
        """Free text (the memo). Empty string on a refusal, so the template memo is used."""
        return self._complete(system, user, None, "low") or ""


class ClaudeReader(ModelReader):
    """Claude on the Claude API. Needs ANTHROPIC_API_KEY."""

    def __init__(self, model: str | None = None):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model or MODEL
        self.name = f"Claude ({self.model})"

    def _complete(self, system, user, schema, effort):
        config = {"effort": effort}
        if schema:
            config["format"] = {"type": "json_schema", "schema": schema}
        resp = self.client.beta.messages.create(
            model=self.model, max_tokens=8000, system=system,
            messages=[{"role": "user", "content": user}], output_config=config,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        if resp.stop_reason == "refusal":
            return None
        return next((b.text for b in resp.content if b.type == "text"), "")


class FoundryClaudeReader(ModelReader):
    """Claude on Azure (Microsoft Foundry). Needs ANTHROPIC_FOUNDRY_API_KEY and
    ANTHROPIC_FOUNDRY_RESOURCE. Server-side fallbacks are a Claude API feature, so none here."""

    def __init__(self, model: str | None = None):
        from anthropic import AnthropicFoundry
        self.client = AnthropicFoundry()
        self.model = model or os.getenv("SCREENER_MODEL") or "claude-opus-5-5"
        self.name = f"Claude on Azure Foundry ({self.model})"

    def _complete(self, system, user, schema, effort):
        kwargs = {}
        if schema:
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
        resp = self.client.messages.create(
            model=self.model, max_tokens=8000, system=system,
            messages=[{"role": "user", "content": user}], **kwargs,
        )
        if resp.stop_reason == "refusal":
            return None
        return next((b.text for b in resp.content if b.type == "text"), "")


class AzureOpenAIReader(ModelReader):
    """An OpenAI model deployed on Azure OpenAI. Uses the same variables as Titan:
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION, plus the deployment
    name in AZURE_OPENAI_DEPLOYMENT (or SCREENER_MODEL)."""

    def __init__(self, deployment: str | None = None):
        from openai import AzureOpenAI
        self.client = AzureOpenAI(api_version=os.getenv("OPENAI_API_VERSION", "2024-10-21"))
        self.model = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("SCREENER_MODEL") or "gpt-4o-mini"
        self.name = f"Azure OpenAI ({self.model})"

    def _complete(self, system, user, schema, effort):
        kwargs = {}
        if schema:
            kwargs["response_format"] = {"type": "json_schema",
                                         "json_schema": {"name": "facts", "schema": schema, "strict": True}}
        resp = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **kwargs,
        )
        msg = resp.choices[0].message
        if getattr(msg, "refusal", None):
            return None
        return msg.content or ""


PROVIDERS = {"anthropic": ClaudeReader, "foundry": FoundryClaudeReader, "azure_openai": AzureOpenAIReader}


def detect_provider() -> str | None:
    """SCREENER_PROVIDER wins; otherwise the first provider whose credentials are set."""
    chosen = os.getenv("SCREENER_PROVIDER", "").strip().lower()
    if chosen:
        return chosen if chosen in PROVIDERS else None
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        return "azure_openai"
    if os.getenv("ANTHROPIC_FOUNDRY_API_KEY") and (os.getenv("ANTHROPIC_FOUNDRY_RESOURCE") or os.getenv("ANTHROPIC_FOUNDRY_BASE_URL")):
        return "foundry"
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"):
        return "anthropic"
    return None


def make_reader(prefer_model: bool = True):
    """A model reader when a provider is configured, else the offline reader."""
    provider = detect_provider() if prefer_model else None
    if provider:
        try:
            return PROVIDERS[provider]()
        except Exception:  # noqa: BLE001 - a missing SDK or setting must not stop a screening
            pass
    return OfflineReader()
