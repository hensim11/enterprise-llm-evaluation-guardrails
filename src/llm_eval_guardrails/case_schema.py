"""Versioned constants for the serialized evaluation-case contract."""

from enum import StrEnum

EVALUATION_CASE_SCHEMA_VERSION = "1"
SUPPORTED_EVALUATION_CASE_SCHEMA_VERSIONS = frozenset({EVALUATION_CASE_SCHEMA_VERSION})


class RiskCategory(StrEnum):
    """Initial categories from the M0 evaluation dimensions."""

    RELIABILITY = "reliability"
    RELEVANCE = "relevance"
    GROUNDEDNESS = "groundedness"
    INSTRUCTION_FOLLOWING = "instruction_following"
    SAFETY = "safety"
    PRIVACY = "privacy"
    INJECTION_RESISTANCE = "injection_resistance"
    REFUSAL_BEHAVIOR = "refusal_behavior"


class AssertionType(StrEnum):
    """Structured deterministic assertions whose execution belongs to a later milestone."""

    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
