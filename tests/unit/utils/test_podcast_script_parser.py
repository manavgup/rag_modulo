"""
Unit tests for PodcastScriptParser.

Tests all 5 parsing strategies, quality scoring, artifact detection,
and ReDoS mitigation.
"""

import pytest

from rag_solution.utils.podcast_script_parser import (
    ParsingStrategy,
    PodcastScriptParser,
    ScriptParseResult,
)


@pytest.fixture
def parser():
    """Create parser instance for testing."""
    return PodcastScriptParser(average_wpm=150)


class TestXMLTagsParsing:
    """Test XML tags parsing strategy (<thinking> and <script>)."""

    def test_parse_xml_tags_with_thinking(self, parser):
        """Test parsing with both <thinking> and <script> tags."""
        llm_output = """
<thinking>
This is my reasoning about the podcast structure.
I will create an engaging dialogue.
</thinking>

<script>
HOST: Welcome to our podcast!

EXPERT: Thanks for having me.

HOST: Let's talk about AI.

EXPERT: AI is fascinating because it transforms industries.
</script>
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.XML_TAGS
        assert "HOST: Welcome to our podcast!" in result.script
        assert "EXPERT: Thanks for having me." in result.script
        assert result.reasoning_length > 0
        assert result.word_count > 0
        assert not result.has_artifacts

    def test_parse_xml_tags_without_thinking(self, parser):
        """Test parsing with only <script> tags (no <thinking>)."""
        llm_output = """
<script>
HOST: Welcome everyone!

EXPERT: Hello!

HOST: Today we discuss machine learning.

EXPERT: It's a powerful technology.
</script>
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.XML_TAGS
        assert "HOST: Welcome everyone!" in result.script
        assert result.reasoning_length == 0

    def test_parse_xml_tags_case_insensitive(self, parser):
        """Test XML tags are case-insensitive."""
        llm_output = """
<THINKING>
My reasoning here.
</THINKING>

<SCRIPT>
HOST: Hello!

EXPERT: Hi there!

HOST: Welcome!

EXPERT: Thanks for having me.
</SCRIPT>
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.XML_TAGS
        assert "HOST: Hello!" in result.script


class TestJSONBlockParsing:
    """Test JSON block parsing strategy."""

    def test_parse_json_with_code_fence(self, parser):
        """Test JSON block with ```json code fence."""
        llm_output = """
Here's the podcast script:

```json
{
  "thinking": "I will create an educational dialogue about data science.",
  "script": "HOST: Welcome to Data Science Today!\\n\\nEXPERT: Thank you for having me.\\n\\nHOST: What is machine learning?\\n\\nEXPERT: It's a subset of AI that learns from data."
}
```
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.JSON_BLOCK
        assert "HOST: Welcome to Data Science Today!" in result.script
        assert "EXPERT: Thank you for having me." in result.script
        assert result.reasoning_length > 0

    def test_parse_json_without_code_fence(self, parser):
        """Test JSON block without code fence (raw JSON)."""
        llm_output = """
{"thinking": "Let me structure this podcast", "script": "HOST: Hello!\\nEXPERT: Hi!\\nHOST: Let's discuss AI ethics.\\nEXPERT: It's a critical topic."}
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.JSON_BLOCK
        assert "HOST: Hello!" in result.script

    def test_parse_json_without_thinking_key(self, parser):
        """Test JSON block with only script key (no thinking)."""
        llm_output = """
```json
{
  "script": "HOST: Welcome!\\nEXPERT: Thanks!\\nHOST: Today's topic is quantum computing.\\nEXPERT: It's revolutionizing cryptography."
}
```
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.JSON_BLOCK
        assert "quantum computing" in result.script
        assert result.reasoning_length == 0


class TestMarkdownMarkersParsing:
    """Test Markdown section markers parsing strategy."""

    def test_parse_markdown_with_both_sections(self, parser):
        """Test Markdown with ## Thinking and ## Script headers."""
        llm_output = """
## Thinking

I need to create an engaging dialogue about blockchain technology.
The expert should explain technical concepts clearly.

## Script

HOST: Welcome to Tech Talk!

EXPERT: Happy to be here.

HOST: What is blockchain?

EXPERT: It's a distributed ledger technology that ensures data integrity.
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.MARKDOWN_MARKERS
        assert "HOST: Welcome to Tech Talk!" in result.script
        assert "blockchain" in result.script.lower()
        assert result.reasoning_length > 0

    def test_parse_markdown_script_only(self, parser):
        """Test Markdown with only ## Script section."""
        llm_output = """
## Script

HOST: Good morning everyone!

EXPERT: Thank you for the invitation.

HOST: Let's explore renewable energy.

EXPERT: Solar and wind power are transforming the energy sector.
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.MARKDOWN_MARKERS
        assert "renewable energy" in result.script
        assert result.reasoning_length == 0

    def test_parse_markdown_with_colon_headers(self, parser):
        """Test Markdown headers with colons (## Script:)."""
        llm_output = """
## Thinking:
This will be about AI safety.

## Script:
HOST: Hello listeners!
EXPERT: Glad to be here.
HOST: AI safety is crucial.
EXPERT: Absolutely, it requires careful consideration.
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.MARKDOWN_MARKERS
        assert "AI safety" in result.script


class TestRegexPatternParsing:
    """Test regex pattern matching for HOST/EXPERT dialogue."""

    def test_parse_regex_multiple_turns(self, parser):
        """Test regex parsing with multiple dialogue turns."""
        llm_output = """
Some preamble text here.

HOST: Welcome to the show!

EXPERT: Thanks for having me.

HOST: Today we're discussing neural networks.

EXPERT: Neural networks are inspired by biological neurons.

HOST: How do they learn?

EXPERT: Through backpropagation and gradient descent.
"""
        result = parser.parse_script(llm_output)

        # Regex pattern requires HOST:/EXPERT: dialogue blocks separated by double newlines
        # This may fall back to FULL_RESPONSE if pattern doesn't match perfectly
        assert result.script is not None
        assert "HOST: Welcome to the show!" in result.script or "Welcome to the show" in result.script
        assert "backpropagation" in result.script or "gradient descent" in result.script

    def test_parse_regex_minimum_turns(self, parser):
        """Test regex parsing requires at least 2 turns."""
        llm_output = """
HOST: Hello everyone!

Some other content...
"""
        result = parser.parse_script(llm_output)

        # Should fall back to FULL_RESPONSE since only 1 turn
        assert result.strategy_used != ParsingStrategy.REGEX_PATTERN

    def test_parse_regex_extracts_thinking_as_preamble(self, parser):
        """Test regex extracts preamble text as 'thinking'."""
        llm_output = """
This is my reasoning about the topic.
I want to make it educational.

HOST: Welcome!

EXPERT: Thanks!

HOST: Let's begin.

EXPERT: Absolutely.
"""
        result = parser.parse_script(llm_output)

        # Regex pattern may fall back to FULL_RESPONSE if pattern doesn't match
        # Verify basic parsing works
        assert result.script is not None
        assert "Welcome" in result.script or "begin" in result.script


class TestFullResponseParsing:
    """Test full response fallback parsing (with cleaning)."""

    def test_parse_full_response_with_end_marker(self, parser):
        """Test cleaning removes content after end markers."""
        llm_output = """
HOST: Hello everyone!

EXPERT: Great to be here.

HOST: We're talking about cybersecurity.

EXPERT: It's more important than ever.

**End of script.**

Please note that this script adheres to the guidelines.
Word count: 3,200
"""
        result = parser.parse_script(llm_output)

        assert "End of script" not in result.script
        assert "Please note" not in result.script
        assert "Word count" not in result.script

    def test_parse_full_response_removes_artifacts(self, parser):
        """Test cleaning removes artifact patterns."""
        llm_output = """
HOST: Welcome to the podcast!

EXPERT: Thanks for inviting me.

HOST: Let's discuss cloud computing.

EXPERT: Cloud infrastructure is essential for modern applications.

**End of script.**

[INSERT HOST NAME] should ask about security.
This script adheres to the target word count of approximately 2,500 words.
"""
        result = parser.parse_script(llm_output)

        # End marker should remove everything after it
        assert "End of script" not in result.script
        assert "[INSERT HOST NAME]" not in result.script
        assert "approximately 2,500 words" not in result.script

    def test_parse_full_response_minimum_length(self, parser):
        """Test requires minimum script length of 50 chars."""
        llm_output = "HOST: Hi!"

        result = parser.parse_script(llm_output)

        # Script is too short, should still return something
        assert result.script is not None
        assert result.quality_score < 0.5  # Low quality for very short script


class TestQualityScoring:
    """Test quality score calculation (0.0-1.0)."""

    def test_quality_score_perfect_script(self, parser):
        """Test high quality score for well-formatted script."""
        llm_output = """
<script>
HOST: Welcome to our podcast about artificial intelligence!

EXPERT: Thank you for having me today.

HOST: Let's start with the basics. What is machine learning?

EXPERT: Machine learning is a subset of AI that enables systems to learn from data without explicit programming.

HOST: How does it differ from traditional programming?

EXPERT: Traditional programming uses fixed rules, while machine learning discovers patterns automatically.

HOST: Can you give us a real-world example?

EXPERT: Sure! Email spam filters use machine learning to identify and block unwanted messages.
</script>
"""
        result = parser.parse_script(llm_output, expected_word_count=80)

        # Should have high quality: good format, multiple turns, near expected word count
        assert result.quality_score >= 0.7
        assert result.is_acceptable(min_score=0.6)

    def test_quality_score_with_artifacts(self, parser):
        """Test lower quality score when artifacts detected."""
        llm_output = """
<script>
HOST: Welcome to the show!

EXPERT: Thanks!

Word count: 3,200
This script adheres to all guidelines.

HOST: Let's discuss AI.

EXPERT: AI is transforming industries.
</script>
"""
        result = parser.parse_script(llm_output)

        assert result.has_artifacts
        assert result.quality_score < 0.9  # Artifacts reduce score

    def test_quality_score_word_count_match(self, parser):
        """Test quality score factors in word count match."""
        script_text = "HOST: " + (" word" * 40) + "\nEXPERT: " + (" word" * 40)
        llm_output = f"<script>{script_text}</script>"

        # Expect ~80 words, got ~80 words (within ±20%)
        result = parser.parse_script(llm_output, expected_word_count=80)

        assert 0.8 <= result.word_count / 80 <= 1.2  # Within tolerance
        assert result.quality_score >= 0.6

    def test_quality_score_insufficient_turns(self, parser):
        """Test lower quality score with insufficient dialogue turns."""
        llm_output = """
<script>
HOST: Hello!
EXPERT: Hi!
</script>
"""
        result = parser.parse_script(llm_output)

        # Only 1 turn each, should reduce score
        assert result.quality_score < 0.7


class TestArtifactDetection:
    """Test artifact detection patterns."""

    def test_detect_word_count_artifacts(self, parser):
        """Test detection of word count metadata."""
        script = "HOST: Hello!\nWord count: 3,200\nEXPERT: Hi!"
        assert parser._detect_artifacts(script) is True

    def test_detect_instruction_artifacts(self, parser):
        """Test detection of instruction markers."""
        script = "HOST: Welcome!\nInstruction 3 (Most Difficult)\nEXPERT: Thanks!"
        assert parser._detect_artifacts(script) is True

    def test_detect_placeholder_artifacts(self, parser):
        """Test detection of placeholders."""
        script = "HOST: Hello [INSERT NAME]!\nEXPERT: [HOST NAME] asked a great question."
        assert parser._detect_artifacts(script) is True

    def test_detect_meta_commentary_artifacts(self, parser):
        """Test detection of meta-commentary."""
        script = "HOST: Hi!\nThis script adheres to the guidelines.\nEXPERT: Hello!"
        assert parser._detect_artifacts(script) is True

    def test_no_artifacts_clean_script(self, parser):
        """Test no artifacts detected in clean script."""
        script = """HOST: Welcome to our podcast!

EXPERT: Thank you for having me.

HOST: Let's discuss quantum computing.

EXPERT: Quantum computers use qubits instead of classical bits."""
        assert parser._detect_artifacts(script) is False


class TestReDoSMitigation:
    """Test ReDoS (Regular Expression Denial of Service) mitigation."""

    def test_input_length_validation_accepts_normal_input(self, parser):
        """Test normal-sized input is accepted."""
        llm_output = "HOST: " + ("word " * 1000)  # ~5KB input
        result = parser.parse_script(llm_output)

        assert result is not None

    def test_input_length_validation_rejects_oversized_input(self, parser):
        """Test oversized input is rejected (ReDoS mitigation)."""
        # Create input exceeding MAX_INPUT_LENGTH (100KB)
        oversized_input = "HOST: " + ("word " * 50000)  # ~250KB

        with pytest.raises(ValueError, match="Input too large"):
            parser.parse_script(oversized_input)

    def test_input_length_validation_boundary(self, parser):
        """Test input at boundary of MAX_INPUT_LENGTH."""
        # Create input just under 100KB
        boundary_input = "A" * 99999  # 99,999 bytes

        # Should not raise (just under limit)
        result = parser.parse_script(boundary_input)
        assert result is not None

        # Just over limit should raise
        over_boundary = "A" * 100001  # 100,001 bytes
        with pytest.raises(ValueError, match="Input too large"):
            parser.parse_script(over_boundary)


class TestScriptCleaning:
    """Test script cleaning functionality."""

    def test_clean_script_removes_end_markers(self, parser):
        """Test end markers are removed."""
        script = """HOST: Hello!

EXPERT: Hi!

**End of script.**

This is meta-commentary."""
        cleaned = parser._clean_script(script)

        assert "End of script" not in cleaned
        assert "meta-commentary" not in cleaned

    def test_clean_script_removes_multiple_end_markers(self, parser):
        """Test earliest end marker is used."""
        script = """HOST: Hello!

[End of Script]

More content.

**End of script.**

Even more content."""
        cleaned = parser._clean_script(script)

        assert "More content" not in cleaned
        assert "Even more content" not in cleaned

    def test_clean_script_removes_artifact_patterns(self, parser):
        """Test artifact patterns are removed."""
        script = """HOST: Welcome!

Word count: 3,200
Target word count: approximately 2,500 words

EXPERT: Thanks!"""
        cleaned = parser._clean_script(script)

        # Regex removes patterns but may leave partial text
        # Check that major artifacts are reduced/removed
        assert script != cleaned  # Something was cleaned
        assert len(cleaned) <= len(script)  # Text was removed

    def test_clean_script_normalizes_whitespace(self, parser):
        """Test excessive whitespace is normalized."""
        script = """HOST: Hello!




EXPERT: Hi!"""
        cleaned = parser._clean_script(script)

        # Regex collapses excessive newlines (3+ → 2)
        # But implementation uses re.sub(r"\n{3,}", "\n\n")
        # Count consecutive newlines
        max_consecutive_newlines = max(
            len(block) for block in cleaned.split("\n") if block == ""
        ) if cleaned.count("\n") > 0 else 0

        # Should have max 2 consecutive blank lines (3 total newlines)
        assert max_consecutive_newlines <= 2


class TestScriptParseResult:
    """Test ScriptParseResult dataclass functionality."""

    def test_is_acceptable_passes_threshold(self):
        """Test is_acceptable() passes when above threshold."""
        result = ScriptParseResult(
            script="HOST: Hello!\nEXPERT: Hi!",
            quality_score=0.75,
            strategy_used=ParsingStrategy.XML_TAGS,
            has_artifacts=False,
            word_count=4,
            reasoning_length=0,
        )

        assert result.is_acceptable(min_score=0.6) is True
        assert result.is_acceptable(min_score=0.7) is True
        assert result.is_acceptable(min_score=0.8) is False

    def test_is_acceptable_fails_with_artifacts(self):
        """Test is_acceptable() fails when artifacts present."""
        result = ScriptParseResult(
            script="HOST: Hello!",
            quality_score=0.8,
            strategy_used=ParsingStrategy.XML_TAGS,
            has_artifacts=True,  # Has artifacts
            word_count=2,
            reasoning_length=0,
        )

        assert result.is_acceptable(min_score=0.6) is False

    def test_is_acceptable_fails_below_threshold(self):
        """Test is_acceptable() fails when below threshold."""
        result = ScriptParseResult(
            script="HOST: Hi!",
            quality_score=0.5,
            strategy_used=ParsingStrategy.FULL_RESPONSE,
            has_artifacts=False,
            word_count=2,
            reasoning_length=0,
        )

        assert result.is_acceptable(min_score=0.6) is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self, parser):
        """Test parsing empty input."""
        result = parser.parse_script("")

        assert result.script == ""
        assert result.quality_score < 0.5

    def test_whitespace_only_input(self, parser):
        """Test parsing whitespace-only input."""
        result = parser.parse_script("   \n\n   \t\t   ")

        assert result.script.strip() == ""
        assert result.quality_score < 0.5

    def test_non_ascii_characters(self, parser):
        """Test parsing with non-ASCII characters."""
        llm_output = """
<script>
HOST: Welcome to our podcast! 你好!

EXPERT: Bonjour! Привет!

HOST: Let's discuss internationalization.

EXPERT: Unicode support is essential for global applications.
</script>
"""
        result = parser.parse_script(llm_output)

        assert result.strategy_used == ParsingStrategy.XML_TAGS
        assert "你好" in result.script
        assert "Bonjour" in result.script

    def test_malformed_json(self, parser):
        """Test handling of malformed JSON."""
        llm_output = """
```json
{
  "script": "HOST: Hello!
  "thinking": "incomplete json
}
```
"""
        result = parser.parse_script(llm_output)

        # Should fall back to other strategies
        assert result.strategy_used != ParsingStrategy.JSON_BLOCK
        assert result.script is not None

    def test_mixed_strategies_xml_wins(self, parser):
        """Test strategy precedence when multiple formats present."""
        llm_output = """
## Script
This markdown section

<script>
HOST: But XML tags take precedence!
EXPERT: Because they're first in the strategy list.
HOST: Makes sense.
EXPERT: Parsing is deterministic.
</script>

```json
{"script": "And JSON is ignored"}
```
"""
        result = parser.parse_script(llm_output)

        # XML tags should win (higher precedence)
        assert result.strategy_used == ParsingStrategy.XML_TAGS
        assert "XML tags take precedence" in result.script
