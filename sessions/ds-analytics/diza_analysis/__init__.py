"""DIZA's importable, dependency-free analysis API.

Callers inject records explicitly; importing this package never opens a database,
contacts a provider, changes a zone, or assigns a responder.
"""

from .privacy import anonymize_row, public_aggregates
from .triage import Label, allowed_pools, classify, lexicon_hits, match_responder, score_priority
from .zones import cluster_reports, detect_zone_level

__all__ = [
    "Label",
    "allowed_pools",
    "anonymize_row",
    "classify",
    "cluster_reports",
    "detect_zone_level",
    "lexicon_hits",
    "match_responder",
    "public_aggregates",
    "score_priority",
]
