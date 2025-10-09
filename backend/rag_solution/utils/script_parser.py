"""
Podcast script parser.

Parses LLM-generated podcast scripts into structured PodcastScript objects
with HOST and EXPERT turns for multi-voice audio generation.
"""

import logging
import re
from typing import ClassVar

from rag_solution.schemas.podcast_schema import (
    PodcastScript,
    PodcastTurn,
    ScriptParsingResult,
    Speaker,
)

logger = logging.getLogger(__name__)


class ScriptParsingError(Exception):
    """Exception raised when script parsing fails."""


class PodcastScriptParser:
    """Parser for converting LLM-generated scripts into structured dialogue."""

    # Patterns for detecting speaker turns
    HOST_PATTERNS: ClassVar[list[str]] = [
        r"^HOST:\s*(.+)$",
        r"^Host:\s*(.+)$",
        r"^H:\s*(.+)$",
        r"^\[HOST\]\s*(.+)$",
    ]

    EXPERT_PATTERNS: ClassVar[list[str]] = [
        r"^EXPERT:\s*(.+)$",
        r"^Expert:\s*(.+)$",
        r"^E:\s*(.+)$",
        r"^\[EXPERT\]\s*(.+)$",
    ]

    def __init__(self, average_wpm: int = 150):
        """
        Initialize script parser.

        Args:
            average_wpm: Average words per minute for duration estimation
        """
        self.average_wpm = average_wpm

    def parse(self, raw_script: str) -> ScriptParsingResult:
        """
        Parse raw script text into structured PodcastScript.

        Args:
            raw_script: LLM-generated script text

        Returns:
            ScriptParsingResult with parsed script and metadata

        Raises:
            ScriptParsingError: If script cannot be parsed
        """
        try:
            turns = self._extract_turns(raw_script)

            if not turns:
                raise ScriptParsingError(
                    "No dialogue turns found in script. Expected format: 'HOST: ...' and 'EXPERT: ...'"
                )

            # Calculate totals
            total_words = sum(len(turn.text.split()) for turn in turns)
            total_duration = (total_words / self.average_wpm) * 60.0  # seconds

            script = PodcastScript(
                turns=turns,
                total_duration=total_duration,
                total_words=total_words,
            )

            # Collect warnings
            warnings = self._validate_script(script)

            logger.info(
                "Parsed script: %d turns, %d words, %.1f seconds",
                len(turns),
                total_words,
                total_duration,
            )

            return ScriptParsingResult(
                script=script,
                raw_text=raw_script,
                parsing_warnings=warnings,
            )

        except ScriptParsingError:
            raise
        except Exception as e:
            raise ScriptParsingError(f"Failed to parse script: {e}") from e

    def _extract_turns(self, raw_script: str) -> list[PodcastTurn]:
        """
        Extract dialogue turns from raw script.

        Args:
            raw_script: Raw script text

        Returns:
            List of PodcastTurn objects

        Raises:
            ScriptParsingError: If no valid turns found
        """
        turns = []
        lines = raw_script.strip().split("\n")

        current_speaker: Speaker | None = None
        current_text_parts: list[str] = []

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()

            if not line:
                # Empty line - skip
                continue

            # Try to match speaker patterns
            speaker, text = self._match_speaker_line(line)

            if speaker is not None:
                # Found new speaker - save previous turn if exists
                if current_speaker is not None and current_text_parts:
                    turn = self._create_turn(
                        current_speaker,
                        " ".join(current_text_parts),
                    )
                    turns.append(turn)

                # Start new turn
                current_speaker = speaker
                current_text_parts = [text] if text else []

            elif current_speaker is not None:
                # Continuation of current speaker's text
                current_text_parts.append(line)
            else:
                # Text before any speaker label - log warning
                logger.warning(
                    "Line %d has no speaker label, skipping: %s",
                    line_num,
                    line[:50],
                )

        # Add final turn
        if current_speaker is not None and current_text_parts:
            turn = self._create_turn(
                current_speaker,
                " ".join(current_text_parts),
            )
            turns.append(turn)

        return turns

    def _match_speaker_line(self, line: str) -> tuple[Speaker | None, str]:
        """
        Try to match line against speaker patterns.

        Args:
            line: Single line from script

        Returns:
            Tuple of (Speaker, remaining_text) or (None, "") if no match
        """
        # Try HOST patterns
        for pattern in self.HOST_PATTERNS:
            match = re.match(pattern, line, re.IGNORECASE | re.MULTILINE)
            if match:
                return (Speaker.HOST, match.group(1).strip())

        # Try EXPERT patterns
        for pattern in self.EXPERT_PATTERNS:
            match = re.match(pattern, line, re.IGNORECASE | re.MULTILINE)
            if match:
                return (Speaker.EXPERT, match.group(1).strip())

        return (None, "")

    def _create_turn(self, speaker: Speaker, text: str) -> PodcastTurn:
        """
        Create PodcastTurn with duration estimation.

        Args:
            speaker: Speaker for this turn
            text: Turn text

        Returns:
            PodcastTurn object
        """
        words = len(text.split())
        duration = (words / self.average_wpm) * 60.0  # seconds

        return PodcastTurn(
            speaker=speaker,
            text=text,
            estimated_duration=duration,
        )

    def _validate_script(self, script: PodcastScript) -> list[str]:
        """
        Validate parsed script and return warnings.

        Args:
            script: Parsed PodcastScript

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for empty turns
        for idx, turn in enumerate(script.turns):
            if len(turn.text) < 10:
                warnings.append(f"Turn {idx + 1} is very short ({len(turn.text)} chars)")

        # Check speaker distribution
        host_turns = sum(1 for t in script.turns if t.speaker == Speaker.HOST)
        expert_turns = sum(1 for t in script.turns if t.speaker == Speaker.EXPERT)

        if host_turns == 0:
            warnings.append("No HOST turns found in script")
        if expert_turns == 0:
            warnings.append("No EXPERT turns found in script")

        # Check if script is too unbalanced
        if host_turns > 0 and expert_turns > 0:
            ratio = max(host_turns, expert_turns) / min(host_turns, expert_turns)
            if ratio > 3:
                warnings.append(f"Unbalanced dialogue: {host_turns} HOST turns vs {expert_turns} EXPERT turns")

        # Check total duration
        if script.total_duration < 30:
            warnings.append(f"Script is very short ({script.total_duration:.1f} seconds)")
        elif script.total_duration > 900:  # 15 minutes
            warnings.append(f"Script is very long ({script.total_duration / 60:.1f} minutes)")

        return warnings
