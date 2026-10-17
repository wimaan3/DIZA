"""Conservative EN/ES triage and deterministic responder ranking.

These rules implement the team's TRIAGE.md, not a clinical prediction model.
P0 lexical hits and an existing severity are never downgraded by context.
"""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .config import load_config

SEVERITIES = ("P0", "P1", "P2", "P3")
CATEGORIES = {
    "fire",
    "smoke",
    "gas",
    "flood",
    "power",
    "medical",
    "mental_health",
    "safety_crime",
    "infrastructure",
    "info",
    "logistics",
    "volunteer_offer",
    "other",
}
HAZARDS = {"fire", "smoke", "gas", "flood"}
SKILLS = {
    "fire": "evac_logistics",
    "smoke": "evac_logistics",
    "gas": "evac_logistics",
    "flood": "evac_logistics",
    "power": "facilities",
    "medical": "medical",
    "mental_health": "mental_health",
    "safety_crime": "safety_escort",
    "infrastructure": "facilities",
}


def normalize(text: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text.casefold().replace("’", "'"))
        if not unicodedata.combining(c)
    )


def language_code(language: str) -> str:
    return language.lower().replace("_", "-").split("-")[0]


@dataclass(frozen=True)
class Hit:
    term: str
    tier: str
    lang: str
    category: str = "other"
    vulnerability: str = ""
    skills: tuple[str, ...] = ()
    guards: tuple[str, ...] = ()


@dataclass(frozen=True)
class Label:
    severity: str = "P3"
    category: str = "info"
    vulnerability: tuple[str, ...] = ()
    skills_needed: tuple[str, ...] = ()
    confidence: float = 0.5
    hazard_here_now: bool = False
    language: str = "en"
    keyword_hits: tuple[Hit, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        if self.severity not in SEVERITIES or self.category not in CATEGORIES:
            raise ValueError("Invalid severity or category")


def _guards(text: str, start: int, end: int) -> tuple[str, ...]:
    # Bound negation and test context to this clause, rather than the whole transcript.
    boundaries = list(re.finditer(r"[.!?;,\n]|\b(?:but|however|pero)\b", text))
    left = max((m.end() for m in boundaries if m.end() <= start), default=0)
    right = min((m.start() for m in boundaries if m.start() >= end), default=len(text))
    local, before, after = text[left:right], text[left:start], text[end:right]
    guards = []
    if re.search(r"\b(?:no|not|without|sin|ningun|ninguna)\s+(?:\w+\s+){0,3}$", before):
        guards.append("negation")
    if re.search(
        r"\b(?:fire|smoke|gas|flood|alarm|detector|incendio|alarma)\s+"
        r"(?:(?:alarm|detector)\s+)?(?:test|testing|drill|simulacro|prueba)\b"
        r"|\b(?:test|testing|prueba|simulacro)\s+"
        r"(?:(?:of|the|a|de|la|el|del)\s+){0,4}"
        r"(?:fire|smoke|gas|alarm|detector|fuego|humo|incendio|alarma)\b",
        local,
    ):
        guards.append("test_or_drill")
    if re.search(r"\b(?:on the news|heard that|on tv|en las noticias|me dijeron)\b", before):
        guards.append("hearsay")
    if re.search(r"\b(?:mixtape|fired|on fire at work)\b", local) or re.match(
        r"\s+(?:song|album|outfit|performance)\b", after
    ):
        guards.append("figurative")
    return tuple(guards)


def lexicon_hits(text: str, lang: str = "en") -> list[Hit]:
    """Return hits with context evidence, including guarded hits and code switching."""
    normalized = normalize(text)
    hits = []
    for entry in load_config("lexicon"):
        for hit_lang, terms in entry["terms"].items():
            for term in terms:
                for match in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized):
                    hits.append(
                        Hit(
                            term=term,
                            tier=entry["tier"],
                            lang=hit_lang,
                            category=entry.get("category", "other"),
                            vulnerability=entry.get("vulnerability", ""),
                            skills=tuple(entry.get("skills", [])),
                            guards=()
                            if entry["tier"] == "P0"
                            else _guards(normalized, match.start(), match.end()),
                        )
                    )
    return hits


def classify(transcript: str, fields: Mapping | None = None) -> Label:
    fields = fields or {}
    lang = language_code(fields.get("language", "en"))
    hits = lexicon_hits(transcript, lang)
    active = [
        h
        for h in hits
        if not h.guards or (fields.get("drill_code") and set(h.guards) == {"test_or_drill"})
    ]
    ranked = sorted((h for h in active if h.tier in SEVERITIES), key=lambda h: h.tier)
    severity = ranked[0].tier if ranked else "P3"
    category = ranked[0].category if ranked else fields.get("category", "info")
    hazard = fields.get("hazard", fields.get("category", "info"))
    if hazard not in CATEGORIES:
        hazard = "other"
    if category not in CATEGORIES:
        category = "other"
    reasons = [f"lexicon:{h.term}" for h in ranked if h.tier == severity]
    if fields.get("severity") is not None:
        if fields["severity"] not in SEVERITIES:
            raise ValueError("Invalid existing severity")
        severity = min(severity, fields["severity"])
        reasons.append("existing severity is a floor")
    if fields.get("immediate_danger") is True or fields.get("injured_or_trapped") is True:
        severity = "P0"
        reasons.append("structured immediate danger")
    guarded_hazard = any(h.category == hazard and h.guards for h in hits)
    hazard_here = (
        any(h.tier == "P1" for h in active)
        or (hazard in HAZARDS and not guarded_hazard and fields.get("hazard_here_now") is not False)
        or fields.get("hazard_here_now") is True
    )
    if hazard_here and severity != "P0":
        severity = min(severity, "P1")
        if not ranked:
            category = hazard
    vulnerability = set(fields.get("vulnerability") or [])
    vulnerability.update(h.vulnerability for h in active if h.vulnerability)
    skills = set(fields.get("skills_needed") or [])
    skills.update(s for h in active for s in h.skills)
    if vulnerability or fields.get("needs_assistance") is True:
        severity = min(severity, "P2")
    if "mobility" in vulnerability:
        skills.add("evac_logistics")
    if {"oxygen", "dialysis", "medical_device"} & vulnerability:
        skills.add("medical")
    if category in SKILLS and severity != "P3":
        skills.add(SKILLS[category])
    return Label(
        severity=severity,
        category=category,
        vulnerability=tuple(sorted(vulnerability)),
        skills_needed=tuple(sorted(skills)),
        confidence=0.9 if ranked else 0.5,
        hazard_here_now=hazard_here,
        language=lang,
        keyword_hits=tuple(hits),
        reasons=tuple(reasons),
    )


def score_priority(label: Label | Mapping, acoustic_flags: Sequence[str] = ()) -> int:
    """Rank monotonically; signals only add priority and P0 always ranks first."""

    def get(key, default):
        return (
            label.get(key, default) if isinstance(label, Mapping) else getattr(label, key, default)
        )

    severity = get("severity", "P3")
    if severity not in SEVERITIES:
        raise ValueError("Invalid severity")
    base = {"P0": 100, "P1": 80, "P2": 50, "P3": 10}[severity]
    boost = min(15, 5 * len(set(get("vulnerability", ()))))
    acoustic = min(9, 3 * len(set(acoustic_flags)))
    cap = {"P0": 124, "P1": 99, "P2": 79, "P3": 49}[severity]
    return min(cap, base + boost + acoustic)


def allowed_pools(category: str, severity: str) -> list[str]:
    if severity not in SEVERITIES:
        raise ValueError("Invalid severity")
    if severity == "P0":
        return []
    if severity == "P1" or category == "medical":
        return ["trained_responder"]
    if category == "mental_health":
        return ["trained_listener"]
    return ["general_helper", "bilingual_helper", "trained_responder"]


@dataclass(frozen=True)
class Candidate:
    responder_id: str
    score: float
    matched_skills: tuple[str, ...]
    language_match: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def match_responder(
    skills: Sequence[str],
    language: str,
    severity: str,
    pools_allowed: Sequence[str],
    *,
    responders: Sequence[Mapping],
) -> list[Candidate]:
    """Rank verified available people; reserve/accept atomically in the backend."""
    if severity not in SEVERITIES:
        raise ValueError("Invalid severity")
    if severity == "P0":
        return []
    wanted = set(skills) - {"general"}
    wanted = {s for s in wanted if not s.startswith("lang:")}
    pool_set = set(pools_allowed)
    if severity == "P1":
        pool_set &= {"trained_responder"}
    candidates = []
    for responder in responders:
        if responder.get("verified") is not True or responder.get("status") != "available":
            continue
        if not pool_set.intersection(responder.get("pools", [])):
            continue
        have = set(responder.get("skills", []))
        if not wanted.issubset(have):
            continue
        load = max(0, int(responder.get("active_calls", 0)))
        if load >= load_config("settings")["max_active_calls"]:
            continue
        languages = {language_code(v) for v in responder.get("languages", [])}
        languages.update(s[5:] for s in have if s.startswith("lang:"))
        language_match = language_code(language) in languages
        fatigue = max(0, int(responder.get("calls_this_shift", 0)))
        matched = tuple(sorted(wanted & have))
        score = 20 * len(matched) + 10 * language_match - 8 * load - 0.5 * fatigue
        candidates.append(
            Candidate(
                str(responder["id"]),
                score,
                matched,
                language_match,
                (f"skills:{','.join(matched) or 'general'}", f"load:{load}", f"shift:{fatigue}"),
            )
        )
    return sorted(candidates, key=lambda c: (-c.score, c.responder_id))
