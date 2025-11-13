"""
Unit tests for TranscriptFormatter.

Tests plain text and markdown formatting with chapters, time formatting,
and transcript cleaning.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from rag_solution.schemas.podcast_schema import PodcastChapter
from rag_solution.utils.transcript_formatter import (
    TranscriptFormat,
    TranscriptFormatter,
)


@pytest.fixture
def formatter():
    """Create formatter instance for testing."""
    return TranscriptFormatter()


@pytest.fixture
def sample_transcript():
    """Sample podcast transcript for testing."""
    return """HOST: Welcome to our podcast about artificial intelligence!

EXPERT: Thank you for having me today.

HOST: Let's discuss machine learning.

EXPERT: Machine learning is transforming industries."""


@pytest.fixture
def sample_chapters():
    """Sample chapter markers for testing."""
    return [
        PodcastChapter(
            title="Introduction",
            start_time=0.0,
            end_time=60.0,
            word_count=120,
        ),
        PodcastChapter(
            title="Machine Learning Basics",
            start_time=60.0,
            end_time=180.0,
            word_count=300,
        ),
        PodcastChapter(
            title="Real-World Applications",
            start_time=180.0,
            end_time=300.0,
            word_count=280,
        ),
    ]


class TestFormatTime:
    """Test time formatting functionality."""

    def test_format_time_hours_minutes_seconds(self, formatter):
        """Test formatting with hours, minutes, and seconds."""
        assert formatter.format_time(3665) == "01:01:05"
        assert formatter.format_time(7384) == "02:03:04"

    def test_format_time_minutes_seconds_only(self, formatter):
        """Test formatting with only minutes and seconds (no hours)."""
        assert formatter.format_time(125) == "02:05"
        assert formatter.format_time(599) == "09:59"

    def test_format_time_zero(self, formatter):
        """Test formatting zero time."""
        assert formatter.format_time(0) == "00:00"

    def test_format_time_one_second(self, formatter):
        """Test formatting single second."""
        assert formatter.format_time(1) == "00:01"

    def test_format_time_exactly_one_hour(self, formatter):
        """Test formatting exactly one hour."""
        assert formatter.format_time(3600) == "01:00:00"

    def test_format_time_fractional_seconds(self, formatter):
        """Test formatting with fractional seconds (rounds down)."""
        assert formatter.format_time(125.7) == "02:05"
        assert formatter.format_time(125.3) == "02:05"

    def test_format_time_large_duration(self, formatter):
        """Test formatting large durations."""
        # 10 hours, 30 minutes, 45 seconds
        assert formatter.format_time(37845) == "10:30:45"


class TestCleanTranscript:
    """Test transcript cleaning functionality."""

    def test_clean_transcript_removes_xml_tags(self, formatter):
        """Test removal of XML tags."""
        transcript = """<thinking>Planning the podcast</thinking>

<script>HOST: Welcome!

EXPERT: Thanks!</script>"""
        cleaned = formatter.clean_transcript(transcript)

        assert "<thinking>" not in cleaned
        assert "</thinking>" not in cleaned
        assert "<script>" not in cleaned
        assert "</script>" not in cleaned
        assert "HOST: Welcome!" in cleaned

    def test_clean_transcript_removes_word_count(self, formatter):
        """Test removal of word count metadata."""
        transcript = """HOST: Hello!

Word count: 3,200

EXPERT: Hi!"""
        cleaned = formatter.clean_transcript(transcript)

        assert "Word count" not in cleaned.lower()
        assert "3,200" not in cleaned

    def test_clean_transcript_removes_target_words(self, formatter):
        """Test removal of target word count."""
        transcript = """HOST: Welcome!

Target: 2500 words

EXPERT: Thanks!"""
        cleaned = formatter.clean_transcript(transcript)

        assert "Target" not in cleaned or "target" not in cleaned

    def test_clean_transcript_removes_duration_metadata(self, formatter):
        """Test removal of duration metadata."""
        transcript = """HOST: Hello!

Duration: 15 minutes

EXPERT: Hi!"""
        cleaned = formatter.clean_transcript(transcript)

        assert "Duration: 15 minutes" not in cleaned

    def test_clean_transcript_removes_brackets(self, formatter):
        """Test removal of bracketed markers."""
        transcript = """[HOST] Welcome!

[EXPERT] Thanks!

[Background music]"""
        cleaned = formatter.clean_transcript(transcript)

        assert "[HOST]" not in cleaned
        assert "[EXPERT]" not in cleaned
        assert "[Background music]" not in cleaned

    def test_clean_transcript_normalizes_whitespace(self, formatter):
        """Test whitespace normalization."""
        transcript = """HOST: Hello!



EXPERT: Hi!"""
        cleaned = formatter.clean_transcript(transcript)

        # Should collapse to max 2 newlines
        assert "\n\n\n" not in cleaned
        assert cleaned.startswith("HOST:")  # No leading whitespace
        assert cleaned.endswith("Hi!")  # No trailing whitespace

    def test_clean_transcript_preserves_content(self, formatter):
        """Test that actual content is preserved."""
        transcript = """HOST: Welcome to our podcast!

EXPERT: Thank you for having me."""
        cleaned = formatter.clean_transcript(transcript)

        assert "HOST: Welcome to our podcast!" in cleaned
        assert "EXPERT: Thank you for having me." in cleaned


class TestToTxt:
    """Test plain text formatting."""

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_txt_with_all_metadata(self, mock_datetime, formatter, sample_transcript):
        """Test TXT format with title, duration, and transcript."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_txt(
            transcript=sample_transcript,
            title="AI Podcast Episode 1",
            duration_seconds=300,
        )

        # Check header elements
        assert "=" * 60 in result
        assert "Title: AI Podcast Episode 1" in result
        assert "Duration: 05:00" in result
        assert "Generated: 2025-01-01 12:00 UTC" in result

        # Check transcript content
        assert "HOST: Welcome to our podcast" in result
        assert "EXPERT: Thank you for having me" in result

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_txt_without_title(self, mock_datetime, formatter, sample_transcript):
        """Test TXT format without title."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_txt(
            transcript=sample_transcript,
            duration_seconds=180,
        )

        assert "Title:" not in result
        assert "Duration: 03:00" in result
        assert "Generated: 2025-01-01 12:00 UTC" in result

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_txt_without_duration(self, mock_datetime, formatter, sample_transcript):
        """Test TXT format without duration."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_txt(
            transcript=sample_transcript,
            title="My Podcast",
        )

        assert "Title: My Podcast" in result
        assert "Duration:" not in result
        assert "Generated: 2025-01-01 12:00 UTC" in result

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_txt_minimal(self, mock_datetime, formatter, sample_transcript):
        """Test TXT format with only transcript."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_txt(transcript=sample_transcript)

        # Only generated timestamp and transcript (no title/duration)
        assert "Title:" not in result
        assert "Duration:" not in result
        assert "Generated: 2025-01-01 12:00 UTC" in result
        assert "HOST: Welcome" in result

    def test_to_txt_cleans_transcript(self, formatter):
        """Test that TXT format cleans the transcript."""
        dirty_transcript = """<script>
HOST: Hello!

Word count: 1,200

EXPERT: Hi!</script>"""

        result = formatter.to_txt(transcript=dirty_transcript, title="Test")

        # XML tags and metadata should be removed
        assert "<script>" not in result
        assert "Word count" not in result
        # Content should remain
        assert "HOST: Hello!" in result


class TestToMarkdown:
    """Test Markdown formatting."""

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_markdown_with_chapters(
        self, mock_datetime, formatter, sample_transcript, sample_chapters
    ):
        """Test Markdown format with all features."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_markdown(
            transcript=sample_transcript,
            title="AI Podcast Episode 1",
            duration_seconds=300,
            chapters=sample_chapters,
        )

        # Check title
        assert "# AI Podcast Episode 1" in result

        # Check metadata
        assert "**Duration:** 05:00" in result
        assert "**Generated:** 2025-01-01 12:00 UTC" in result

        # Check table of contents
        assert "## Table of Contents" in result
        assert "[Introduction](#chapter-1)" in result
        assert "([00:00](#00:00))" in result
        assert "[Machine Learning Basics](#chapter-2)" in result
        assert "([01:00](#01:00))" in result

        # Check chapters section
        assert "## Chapters" in result
        assert "### Chapter 1: Introduction {#chapter-1}" in result
        assert "**Time:** [00:00](#00:00) - [01:00](#01:00)" in result
        assert "*Content span: 120 words*" in result

        # Check full transcript
        assert "## Full Transcript" in result
        assert "HOST: Welcome" in result

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_markdown_without_chapters(
        self, mock_datetime, formatter, sample_transcript
    ):
        """Test Markdown format without chapters."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_markdown(
            transcript=sample_transcript,
            title="Simple Podcast",
            duration_seconds=180,
        )

        # Should have title and metadata
        assert "# Simple Podcast" in result
        assert "**Duration:** 03:00" in result

        # Should NOT have chapters sections
        assert "## Table of Contents" not in result
        assert "## Chapters" not in result
        assert "#chapter-1" not in result

        # Should have full transcript
        assert "## Full Transcript" in result
        assert "HOST: Welcome" in result

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_markdown_without_title(
        self, mock_datetime, formatter, sample_transcript
    ):
        """Test Markdown format with default title."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_markdown(
            transcript=sample_transcript,
            duration_seconds=120,
        )

        # Should use default title
        assert "# Podcast Transcript" in result
        assert "**Duration:** 02:00" in result

    @patch("rag_solution.utils.transcript_formatter.datetime")
    def test_to_markdown_without_duration(
        self, mock_datetime, formatter, sample_transcript
    ):
        """Test Markdown format without duration."""
        mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)

        result = formatter.to_markdown(
            transcript=sample_transcript,
            title="Test Podcast",
        )

        assert "# Test Podcast" in result
        assert "**Duration:**" not in result
        assert "**Generated:**" in result

    def test_to_markdown_chapter_links(self, formatter, sample_transcript, sample_chapters):
        """Test Markdown chapter links are properly formatted."""
        result = formatter.to_markdown(
            transcript=sample_transcript,
            title="Test",
            chapters=sample_chapters,
        )

        # Check anchor links
        assert "(#chapter-1)" in result
        assert "(#chapter-2)" in result
        assert "(#chapter-3)" in result

        # Check time links
        assert "(#00:00)" in result
        assert "(#01:00)" in result
        assert "(#03:00)" in result

    def test_to_markdown_cleans_transcript(self, formatter):
        """Test that Markdown format cleans the transcript."""
        dirty_transcript = """<thinking>Planning content</thinking>

<script>HOST: Hello!

[BACKGROUND MUSIC]

EXPERT: Hi!</script>"""

        result = formatter.to_markdown(transcript=dirty_transcript, title="Test")

        # XML tags and brackets should be removed
        assert "<thinking>" not in result
        assert "[BACKGROUND MUSIC]" not in result
        # Content should remain
        assert "HOST: Hello!" in result


class TestFormatTranscript:
    """Test format_transcript dispatcher method."""

    def test_format_transcript_txt(self, formatter, sample_transcript):
        """Test dispatching to TXT format."""
        result = formatter.format_transcript(
            transcript=sample_transcript,
            format_type=TranscriptFormat.TXT,
            title="Test",
            duration_seconds=120,
        )

        # Should have TXT format markers
        assert "=" * 60 in result
        assert "Title: Test" in result
        assert "Duration: 02:00" in result

    def test_format_transcript_markdown(self, formatter, sample_transcript, sample_chapters):
        """Test dispatching to Markdown format."""
        result = formatter.format_transcript(
            transcript=sample_transcript,
            format_type=TranscriptFormat.MARKDOWN,
            title="Test",
            duration_seconds=180,
            chapters=sample_chapters,
        )

        # Should have Markdown format markers
        assert "# Test" in result
        assert "**Duration:** 03:00" in result
        assert "## Table of Contents" in result

    def test_format_transcript_unsupported_format(self, formatter, sample_transcript):
        """Test error handling for unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            formatter.format_transcript(
                transcript=sample_transcript,
                format_type="pdf",  # Invalid format
            )


class TestTranscriptFormatEnum:
    """Test TranscriptFormat enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert TranscriptFormat.TXT == "txt"
        assert TranscriptFormat.MARKDOWN == "md"

    def test_enum_from_string(self):
        """Test creating enum from string values."""
        assert TranscriptFormat("txt") == TranscriptFormat.TXT
        assert TranscriptFormat("md") == TranscriptFormat.MARKDOWN

    def test_enum_invalid_value(self):
        """Test invalid enum value raises error."""
        with pytest.raises(ValueError):
            TranscriptFormat("pdf")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_transcript(self, formatter):
        """Test formatting empty transcript."""
        result = formatter.to_txt(transcript="", title="Empty Podcast")

        assert "Title: Empty Podcast" in result
        assert "Generated:" in result
        # Transcript section should be empty or minimal
        assert result.count("\n") >= 5  # Header lines still present

    def test_very_long_title(self, formatter, sample_transcript):
        """Test handling very long titles."""
        long_title = "A" * 200

        result = formatter.to_txt(transcript=sample_transcript, title=long_title)

        assert long_title in result

    def test_special_characters_in_title(self, formatter, sample_transcript):
        """Test special characters in title."""
        special_title = "Podcast: AI & ML (Part 1) - \"Introduction\""

        result = formatter.to_markdown(transcript=sample_transcript, title=special_title)

        assert special_title in result

    def test_non_ascii_characters(self, formatter):
        """Test handling non-ASCII characters."""
        unicode_transcript = """HOST: 你好! Welcome!

EXPERT: Bonjour! Привет!"""

        result = formatter.to_txt(transcript=unicode_transcript, title="Global Podcast")

        assert "你好" in result
        assert "Bonjour" in result
        assert "Привет" in result

    def test_empty_chapters_list(self, formatter, sample_transcript):
        """Test Markdown with empty chapters list."""
        result = formatter.to_markdown(
            transcript=sample_transcript,
            title="Test",
            chapters=[],  # Empty list
        )

        # Should not have chapters sections
        assert "## Table of Contents" not in result
        assert "## Chapters" not in result

    def test_single_chapter(self, formatter, sample_transcript):
        """Test Markdown with single chapter."""
        single_chapter = [
            PodcastChapter(
                title="Full Episode",
                start_time=0.0,
                end_time=300.0,
                word_count=500,
            )
        ]

        result = formatter.to_markdown(
            transcript=sample_transcript,
            title="Test",
            chapters=single_chapter,
        )

        assert "## Table of Contents" in result
        assert "### Chapter 1: Full Episode" in result
