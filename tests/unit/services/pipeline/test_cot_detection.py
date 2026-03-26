"""Unit tests for shared CoT detection logic.

Tests cot_detection.should_use_cot() directly, covering edge cases
and the config_metadata override semantics.
"""

import pytest

from rag_solution.services.pipeline.cot_detection import should_use_cot

pytestmark = pytest.mark.unit


class TestCotDetectionOverrides:
    """Test explicit config_metadata overrides."""

    def test_cot_disabled_true_always_skips(self):
        """cot_disabled: True should always skip CoT regardless of question."""
        assert should_use_cot("explain quantum physics", {"cot_disabled": True}) is False

    def test_cot_enabled_true_always_triggers(self):
        """cot_enabled: True should always trigger CoT regardless of question."""
        assert should_use_cot("What is AI?", {"cot_enabled": True}) is True

    def test_cot_enabled_false_forces_off(self):
        """cot_enabled: False should force CoT OFF (not fall through to auto-detect).

        Regression test: sending cot_enabled: false must suppress CoT,
        not silently fall through to auto-detection.
        """
        # This complex question would normally trigger CoT via auto-detection
        assert should_use_cot("How does machine learning compare to deep learning?", {"cot_enabled": False}) is False

    def test_cot_disabled_takes_precedence_over_enabled(self):
        """cot_disabled should take precedence when both flags are set."""
        assert should_use_cot("explain this", {"cot_disabled": True, "cot_enabled": True}) is False

    def test_none_config_metadata(self):
        """None config_metadata should fall through to auto-detection."""
        assert should_use_cot("What is AI?", None) is False
        assert should_use_cot("How does X compare to Y?", None) is True

    def test_empty_config_metadata(self):
        """Empty dict should fall through to auto-detection."""
        assert should_use_cot("What is AI?", {}) is False


class TestCotDetectionAutoDetect:
    """Test automatic complexity detection."""

    def test_empty_question(self):
        """Empty string should not trigger CoT."""
        assert should_use_cot("") is False

    def test_single_word(self):
        """Single word should not trigger CoT."""
        assert should_use_cot("hello") is False

    @pytest.mark.parametrize(
        "question",
        [
            "what were IBM results in 2020",
            "What is the company revenue?",
            "Who is the CEO?",
            "List the key findings",
            "Show me the data",
        ],
    )
    def test_simple_factual_queries_skip_cot(self, question):
        """Simple factual lookups should NOT trigger CoT."""
        assert should_use_cot(question) is False

    @pytest.mark.parametrize(
        "question",
        [
            "How does machine learning compare to deep learning?",
            "Explain the relationship between revenue and costs",
            "Why did the company margins decline?",
            "Walk me through the deployment process",
            "What are the pros and cons of this approach?",
        ],
    )
    def test_complex_questions_trigger_cot(self, question):
        """Complex reasoning questions should trigger CoT."""
        assert should_use_cot(question) is True

    def test_word_count_threshold_at_20(self):
        """Questions with exactly 20 words should NOT trigger, >20 should."""
        twenty_words = " ".join(["word"] * 20)
        twenty_one_words = " ".join(["word"] * 21)
        assert should_use_cot(twenty_words) is False
        assert should_use_cot(twenty_one_words) is True

    def test_whole_word_matching_for_reasoning(self):
        """'reason' should not match inside 'unreasonable'."""
        assert should_use_cot("This is unreasonable behavior") is False
        assert should_use_cot("What is the reason for this?") is True
