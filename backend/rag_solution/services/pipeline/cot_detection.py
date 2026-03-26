"""Shared Chain of Thought detection logic.

Determines whether a question is complex enough to benefit from
multi-step CoT reasoning. Used by both SearchService and ReasoningStage
to ensure consistent behavior.
"""

from typing import Any

from core.logging_utils import get_logger

logger = get_logger("services.pipeline.cot_detection")


def should_use_cot(question: str, config_metadata: dict[str, Any] | None = None) -> bool:
    """Determine if Chain of Thought reasoning should be used for a question.

    CoT adds ~8s latency per LLM call. Only trigger it for questions that
    genuinely benefit from multi-step reasoning (complex comparisons, causal
    analysis, multi-part questions). Simple factual lookups should skip CoT.

    Args:
        question: The user's search question.
        config_metadata: Optional config dict. Supports explicit overrides
            (cot_disabled takes precedence over cot_enabled):
            - cot_disabled: True -> always skip CoT (highest priority)
            - cot_enabled: True -> force CoT on
            - cot_enabled: False -> force CoT off

    Returns:
        True if CoT should be used, False otherwise.
    """
    # Allow explicit overrides
    if config_metadata:
        if config_metadata.get("cot_disabled"):
            return False
        # Handle both cot_enabled: true (force on) and cot_enabled: false (force off)
        cot_enabled = config_metadata.get("cot_enabled")
        if cot_enabled is not None:
            return bool(cot_enabled)

    question_lower = question.lower()
    words = question_lower.split()
    word_count = len(words)

    # Complex question indicators (multi-word phrases are safe; single words
    # like "explain" may match inside longer words but this is acceptable)
    complex_patterns = [
        "how does",
        "how do",
        "how did",
        "why does",
        "why do",
        "why did",
        "why is",
        "why are",
        "why was",
        "explain",
        "compare",
        "analyze",
        "what are the differences",
        "what is the relationship",
        "how can i",
        "what are the steps",
        "walk me through",
        "break down",
        "elaborate",
        "pros and cons",
        "advantages and disadvantages",
        "benefits and drawbacks",
    ]
    has_complex_pattern = any(pattern in question_lower for pattern in complex_patterns)

    # Multiple questions (multiple ? or " and " conjunction with ?)
    has_multiple_questions = question_lower.count("?") > 1 or (" and " in question_lower and "?" in question_lower)

    # Reasoning-oriented words (whole word match to avoid "unreasonable" matching "reason")
    reasoning_words = {"because", "reason", "rationale", "justify", "evidence", "support"}
    asks_for_reasoning = bool(reasoning_words & set(words))

    # Long questions likely need more reasoning (>20 words)
    is_long = word_count > 20

    return has_complex_pattern or has_multiple_questions or asks_for_reasoning or is_long
