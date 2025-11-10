"""
Transcript formatting utilities for podcast downloads.

Supports multiple formats:
- Plain text (.txt): Simple readable format
- Markdown (.md): Formatted with chapters and timestamps
"""

import logging
from datetime import datetime
from enum import Enum

from rag_solution.schemas.podcast_schema import PodcastChapter

logger = logging.getLogger(__name__)


class TranscriptFormat(str, Enum):
    """Supported transcript download formats."""

    TXT = "txt"
    MARKDOWN = "md"


class TranscriptFormatter:
    """Formatter for converting podcast transcripts to downloadable formats."""

    @staticmethod
    def format_time(seconds: float) -> str:
        """
        Format time in seconds to HH:MM:SS format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string (HH:MM:SS or MM:SS)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def clean_transcript(transcript: str) -> str:
        """
        Remove artifacts and metadata from transcript.

        Removes:
        - XML tags (<script>, <thinking>)
        - Metadata comments
        - Excessive whitespace

        Args:
            transcript: Raw transcript text

        Returns:
            Cleaned transcript
        """
        import re

        # Remove XML tags
        cleaned = re.sub(r"<script>|</script>|<thinking>|</thinking>", "", transcript)

        # Remove metadata patterns
        patterns = [
            r"Word count:\s*\d+",
            r"Target:\s*\d+\s+words",
            r"Duration:\s*\d+\s+minutes",
            r"\[.*?\]",  # Remove [HOST], [EXPERT] markers if present
        ]
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Normalize whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # Max 2 newlines
        cleaned = cleaned.strip()

        return cleaned

    def to_txt(
        self,
        transcript: str,
        title: str | None = None,
        duration_seconds: float | None = None,
        chapters: list[PodcastChapter] | None = None,  # noqa: ARG002
    ) -> str:
        """
        Convert transcript to plain text format.

        Format:
        ```
        Title: [title]
        Duration: [MM:SS]
        Generated: [timestamp]

        [transcript content]
        ```

        Args:
            transcript: Raw podcast transcript
            title: Optional podcast title
            duration_seconds: Optional duration in seconds
            chapters: Optional list of chapters (not used in plain text)

        Returns:
            Formatted plain text transcript
        """
        lines = []

        # Header
        lines.append("=" * 60)
        if title:
            lines.append(f"Title: {title}")
        if duration_seconds:
            lines.append(f"Duration: {self.format_time(duration_seconds)}")
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("=" * 60)
        lines.append("")

        # Cleaned transcript
        cleaned = self.clean_transcript(transcript)
        lines.append(cleaned)

        return "\n".join(lines)

    def to_markdown(
        self,
        transcript: str,
        title: str | None = None,
        duration_seconds: float | None = None,
        chapters: list[PodcastChapter] | None = None,
    ) -> str:
        """
        Convert transcript to Markdown format with chapters.

        Format:
        ```markdown
        # [title]

        **Duration:** [MM:SS]
        **Generated:** [timestamp]

        ## Table of Contents
        - [Chapter 1](#chapter-1) ([00:00](#00:00))
        - [Chapter 2](#chapter-2) ([01:23](#01:23))

        ## Chapters

        ### Chapter 1: [title] {#chapter-1}
        **Time:** [00:00](#00:00) - [01:23](#01:23)

        [content]

        ---

        ## Full Transcript
        [full transcript]
        ```

        Args:
            transcript: Raw podcast transcript
            title: Optional podcast title
            duration_seconds: Optional duration in seconds
            chapters: Optional list of chapters with timestamps

        Returns:
            Formatted Markdown transcript
        """
        lines = []

        # Title
        lines.append(f"# {title or 'Podcast Transcript'}")
        lines.append("")

        # Metadata
        if duration_seconds:
            lines.append(f"**Duration:** {self.format_time(duration_seconds)}")
        lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        # Table of contents (if chapters exist)
        if chapters:
            lines.append("## Table of Contents")
            lines.append("")
            for idx, chapter in enumerate(chapters, start=1):
                start_time = self.format_time(chapter.start_time)
                chapter_id = f"chapter-{idx}"
                lines.append(f"- [{chapter.title}](#{chapter_id}) ([{start_time}](#{start_time}))")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Chapters section
        if chapters:
            lines.append("## Chapters")
            lines.append("")

            # Extract content for each chapter based on line numbers
            # This is a simplified approach - assumes HOST/EXPERT lines
            for idx, chapter in enumerate(chapters, start=1):
                chapter_id = f"chapter-{idx}"
                start_time = self.format_time(chapter.start_time)
                end_time = self.format_time(chapter.end_time)

                lines.append(f"### Chapter {idx}: {chapter.title} {{#{chapter_id}}}")
                lines.append(f"**Time:** [{start_time}](#{start_time}) - [{end_time}](#{end_time})")
                lines.append("")

                # Note: In a real implementation, we'd extract the actual chapter content
                # For now, we'll include a note
                lines.append(f"*Content span: {chapter.word_count} words*")
                lines.append("")
                lines.append("---")
                lines.append("")

        # Full transcript
        lines.append("## Full Transcript")
        lines.append("")
        cleaned = self.clean_transcript(transcript)
        lines.append(cleaned)

        return "\n".join(lines)

    def format_transcript(
        self,
        transcript: str,
        format_type: TranscriptFormat,
        title: str | None = None,
        duration_seconds: float | None = None,
        chapters: list[PodcastChapter] | None = None,
    ) -> str:
        """
        Format transcript to specified format.

        Args:
            transcript: Raw podcast transcript
            format_type: Desired output format
            title: Optional podcast title
            duration_seconds: Optional duration in seconds
            chapters: Optional list of chapters

        Returns:
            Formatted transcript string

        Raises:
            ValueError: If format_type is unsupported
        """
        if format_type == TranscriptFormat.TXT:
            return self.to_txt(transcript, title, duration_seconds, chapters)
        if format_type == TranscriptFormat.MARKDOWN:
            return self.to_markdown(transcript, title, duration_seconds, chapters)
        raise ValueError(f"Unsupported format: {format_type}")
