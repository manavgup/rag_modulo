"""
Podcast script parsing utility with multi-layer fallback strategies.

This module provides robust parsing of LLM-generated podcast scripts with:
1. XML tag separation (<thinking> and <script>)
2. Five-layer parsing fallbacks (XML → JSON → markers → regex → full response)
3. Quality scoring (0.0-1.0 confidence with artifact detection)
4. Prompt leakage detection and removal

Based on CoT hardening patterns from Issue #461.
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

logger = logging.getLogger(__name__)


class ParsingStrategy(str, Enum):
    """Enum for different parsing strategies tried."""

    XML_TAGS = "xml_tags"
    JSON_BLOCK = "json_block"
    MARKDOWN_MARKERS = "markdown_markers"
    REGEX_PATTERN = "regex_pattern"
    FULL_RESPONSE = "full_response"


@dataclass
class ScriptParseResult:
    """Result of parsing a podcast script with quality metrics."""

    script: str
    quality_score: float
    strategy_used: ParsingStrategy
    has_artifacts: bool
    word_count: int
    reasoning_length: int  # Length of thinking/reasoning section (if extracted)

    def is_acceptable(self, min_score: float = 0.6) -> bool:
        """Check if script meets minimum quality threshold."""
        return self.quality_score >= min_score and not self.has_artifacts


class PodcastScriptParser:
    """Parser for LLM-generated podcast scripts with quality validation."""

    # Maximum input length to prevent ReDoS attacks (100KB = ~15,000-20,000 words)
    MAX_INPUT_LENGTH: ClassVar[int] = 100_000

    # Artifact patterns that indicate prompt leakage
    ARTIFACT_PATTERNS: ClassVar[list[str]] = [
        r"Word count:\s*\d+",  # "Word count: 3,200"
        r"Instruction\s+\d+",  # "Instruction 3 (Most Difficult)"
        r"This script adheres to",  # Meta-commentary
        r"Please note that this script",
        r"\[INSERT\s+\w+\]",  # Placeholders like [INSERT NAME]
        r"\[HOST\s+NAME\]",  # [HOST NAME]
        r"\[EXPERT\s+NAME\]",  # [EXPERT NAME]
        r"Based on the provided documents",  # Template language
        r"target word count",  # Meta information
        r"approximately\s+\d+\s+words",  # "approximately 2,250 words"
    ]

    # End markers that indicate meta-commentary
    END_MARKERS: ClassVar[list[str]] = [
        "**End of script.**",
        "** End of script **",
        "[End of Response]",
        "[End of Script]",
        "[Instruction's wrapping]",
        "Please note that this script",
        "---\n\n**Podcast Script:**",
        "***End of Script***",
        "This script has been designed",
        "The script above",
    ]

    def __init__(self, average_wpm: int = 150):
        """
        Initialize parser.

        Args:
            average_wpm: Average words per minute for podcast narration
        """
        self.average_wpm = average_wpm

    def parse_script(self, llm_output: str, expected_word_count: int = 0) -> ScriptParseResult:
        """
        Parse LLM output using multi-layer fallback strategy.

        Strategy precedence:
        1. XML tags (<thinking> and <script>)
        2. JSON block with thinking/script keys
        3. Markdown section markers (## Thinking, ## Script)
        4. Regex pattern matching
        5. Full response (with cleaning)

        Args:
            llm_output: Raw LLM response
            expected_word_count: Expected word count for quality validation

        Returns:
            ScriptParseResult with extracted script and quality metrics

        Raises:
            ValueError: If input length exceeds MAX_INPUT_LENGTH (ReDoS mitigation)
        """
        # ReDoS mitigation: Validate input length before regex operations
        if len(llm_output) > self.MAX_INPUT_LENGTH:
            logger.error(
                "Input length %d exceeds maximum %d (ReDoS mitigation)",
                len(llm_output),
                self.MAX_INPUT_LENGTH,
            )
            raise ValueError(
                f"Input too large: {len(llm_output)} bytes "
                f"(max: {self.MAX_INPUT_LENGTH} bytes). "
                "This protects against ReDoS attacks."
            )

        # Try each parsing strategy in order
        strategies = [
            (self._parse_xml_tags, ParsingStrategy.XML_TAGS),
            (self._parse_json_block, ParsingStrategy.JSON_BLOCK),
            (self._parse_markdown_markers, ParsingStrategy.MARKDOWN_MARKERS),
            (self._parse_regex_pattern, ParsingStrategy.REGEX_PATTERN),
            (self._parse_full_response, ParsingStrategy.FULL_RESPONSE),
        ]

        for parse_func, strategy in strategies:
            try:
                script, reasoning = parse_func(llm_output)
                if script and len(script.strip()) > 50:  # Minimum viable script length
                    # Calculate quality metrics
                    quality_score = self._calculate_quality_score(
                        script,
                        reasoning,
                        expected_word_count,
                    )
                    has_artifacts = self._detect_artifacts(script)
                    word_count = len(script.split())

                    logger.info(
                        "Parsed script using %s: %d words, quality=%.2f, artifacts=%s",
                        strategy.value,
                        word_count,
                        quality_score,
                        has_artifacts,
                    )

                    return ScriptParseResult(
                        script=script.strip(),
                        quality_score=quality_score,
                        strategy_used=strategy,
                        has_artifacts=has_artifacts,
                        word_count=word_count,
                        reasoning_length=len(reasoning) if reasoning else 0,
                    )
            except Exception as e:
                logger.debug("Failed to parse with %s: %s", strategy.value, e)
                continue

        # Fallback: return full response with warning
        logger.warning("All parsing strategies failed, returning cleaned full response")
        cleaned = self._clean_script(llm_output)
        return ScriptParseResult(
            script=cleaned,
            quality_score=0.3,  # Low score for fallback
            strategy_used=ParsingStrategy.FULL_RESPONSE,
            has_artifacts=self._detect_artifacts(cleaned),
            word_count=len(cleaned.split()),
            reasoning_length=0,
        )

    def _parse_xml_tags(self, text: str) -> tuple[str, str]:
        """Parse XML tags: <thinking>...</thinking> <script>...</script>."""
        # Match thinking section (optional)
        thinking_pattern = r"<thinking>(.*?)</thinking>"
        script_pattern = r"<script>(.*?)</script>"

        thinking_match = re.search(thinking_pattern, text, re.DOTALL | re.IGNORECASE)
        script_match = re.search(script_pattern, text, re.DOTALL | re.IGNORECASE)

        if not script_match:
            raise ValueError("No <script> tags found")

        thinking = thinking_match.group(1).strip() if thinking_match else ""
        script = script_match.group(1).strip()

        return script, thinking

    def _parse_json_block(self, text: str) -> tuple[str, str]:
        """Parse JSON block with thinking/script keys."""
        # Find JSON block (```json ... ``` or just {...})
        json_pattern = r"```json\s*(.*?)\s*```|(\{.*?\})"
        match = re.search(json_pattern, text, re.DOTALL)

        if not match:
            raise ValueError("No JSON block found")

        json_text = match.group(1) or match.group(2)
        data = json.loads(json_text)

        if "script" not in data:
            raise ValueError("JSON missing 'script' key")

        return data["script"].strip(), data.get("thinking", "").strip()

    def _parse_markdown_markers(self, text: str) -> tuple[str, str]:
        """Parse markdown section markers (## Thinking, ## Script)."""
        # Match sections with ## headings
        thinking_pattern = r"##\s*Thinking[:\s]*(.*?)(?=##|$)"
        script_pattern = r"##\s*Script[:\s]*(.*?)(?=##|$)"

        thinking_match = re.search(thinking_pattern, text, re.DOTALL | re.IGNORECASE)
        script_match = re.search(script_pattern, text, re.DOTALL | re.IGNORECASE)

        if not script_match:
            raise ValueError("No ## Script section found")

        thinking = thinking_match.group(1).strip() if thinking_match else ""
        script = script_match.group(1).strip()

        return script, thinking

    def _parse_regex_pattern(self, text: str) -> tuple[str, str]:
        """Parse using regex to find HOST/EXPERT dialogue blocks."""
        # Find continuous dialogue blocks with HOST: and EXPERT: patterns
        dialogue_pattern = r"((?:HOST:|EXPERT:)(?:.*?\n?)+?)(?:\n\n|\Z)"
        matches = re.findall(dialogue_pattern, text, re.MULTILINE)

        if not matches or len(matches) < 2:  # Need at least 2 turns
            raise ValueError("Insufficient HOST/EXPERT dialogue found")

        script = "\n\n".join(matches)
        # Everything before first dialogue is "thinking"
        first_dialogue_pos = text.find(matches[0])
        thinking = text[:first_dialogue_pos].strip() if first_dialogue_pos > 0 else ""

        return script, thinking

    def _parse_full_response(self, text: str) -> tuple[str, str]:
        """Fallback: clean the full response."""
        cleaned = self._clean_script(text)
        return cleaned, ""

    def _clean_script(self, script: str) -> str:
        """
        Clean script by removing meta-commentary and artifacts.

        Args:
            script: Raw script text

        Returns:
            Cleaned script
        """
        # Remove content after end markers
        first_marker_pos = len(script)
        for marker in self.END_MARKERS:
            pos = script.find(marker)
            if pos != -1 and pos < first_marker_pos:
                first_marker_pos = pos

        if first_marker_pos < len(script):
            script = script[:first_marker_pos]

        # Remove leading/trailing whitespace and separators
        script = script.strip()
        script = script.strip("-")
        script = script.strip()

        # Remove common artifact patterns
        for pattern in self.ARTIFACT_PATTERNS:
            script = re.sub(pattern, "", script, flags=re.IGNORECASE)

        return script

    def _detect_artifacts(self, script: str) -> bool:
        """
        Detect if script contains prompt leakage artifacts.

        Args:
            script: Script text to check

        Returns:
            True if artifacts detected
        """
        for pattern in self.ARTIFACT_PATTERNS:
            if re.search(pattern, script, re.IGNORECASE):
                logger.warning("Artifact detected: %s", pattern)
                return True

        return False

    def _calculate_quality_score(
        self,
        script: str,
        reasoning: str,
        expected_word_count: int = 0,
    ) -> float:
        """
        Calculate quality score (0.0-1.0) based on multiple factors.

        Scoring factors:
        - Word count match (±20% tolerance)
        - Dialogue format (HOST/EXPERT presence)
        - No artifacts detected
        - Reasonable reasoning/script ratio

        Args:
            script: Extracted script
            reasoning: Extracted reasoning/thinking section
            expected_word_count: Expected target word count

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        word_count = len(script.split())

        # Factor 1: Word count match (0.3 weight)
        if expected_word_count > 0:
            ratio = word_count / expected_word_count
            if 0.8 <= ratio <= 1.2:  # Within ±20%
                score += 0.3
            elif 0.6 <= ratio <= 1.4:  # Within ±40%
                score += 0.15
            else:
                score += 0.0
        else:
            score += 0.3  # No target, assume OK

        # Factor 2: Dialogue format (0.3 weight)
        has_host = bool(re.search(r"\bHOST:", script))
        has_expert = bool(re.search(r"\bEXPERT:", script))
        if has_host and has_expert:
            # Count turns
            host_turns = len(re.findall(r"\bHOST:", script))
            expert_turns = len(re.findall(r"\bEXPERT:", script))
            if host_turns >= 3 and expert_turns >= 3:  # At least 3 turns each
                score += 0.3
            else:
                score += 0.15
        else:
            score += 0.0

        # Factor 3: No artifacts (0.2 weight)
        if not self._detect_artifacts(script):
            score += 0.2

        # Factor 4: Reasonable reasoning/script ratio (0.2 weight)
        if reasoning:
            reasoning_word_count = len(reasoning.split())
            ratio = reasoning_word_count / word_count if word_count > 0 else 0
            if 0.1 <= ratio <= 0.5:  # Reasoning is 10-50% of script
                score += 0.2
            elif ratio < 0.1:  # Minimal reasoning is OK
                score += 0.1
        else:
            # No reasoning section - that's fine for podcast scripts
            score += 0.2

        return min(score, 1.0)  # Cap at 1.0
