# CoT Regression Tests - Prevent Reasoning Leakage

## Overview

Comprehensive test suite to ensure Chain of Thought (CoT) reasoning never leaks into user-facing responses.

---

## Test Strategy

### Test Pyramid

```
         /\
        /  \  E2E Tests (5%)
       /____\
      /      \  Integration Tests (30%)
     /________\
    /          \  Unit Tests (65%)
   /____________\
```

**Distribution**:

- **65% Unit Tests**: Fast, isolated, test individual functions
- **30% Integration Tests**: Test component interactions
- **5% E2E Tests**: Full system tests

---

## Unit Tests

### 1. Artifact Detection Tests

**File**: `tests/unit/services/test_cot_artifact_detection.py`

```python
"""Unit tests for CoT artifact detection."""

import pytest

from rag_solution.services.chain_of_thought_service import ChainOfThoughtService


class TestArtifactDetection:
    """Test artifact detection in CoT responses."""

    @pytest.fixture
    def cot_service(self, db_session, mock_settings):
        """Create CoT service fixture."""
        return ChainOfThoughtService(
            settings=mock_settings,
            llm_service=None,
            search_service=None,
            db=db_session
        )

    @pytest.mark.parametrize("text,expected", [
        # Should detect artifacts
        ("based on the analysis of revenue", True),
        ("(in the context of User, Assistant)", True),
        ("furthermore, we can see", True),
        ("additionally, the data shows", True),
        ("## instruction: answer the question", True),
        ("Answer: The revenue was $73.6B", True),
        ("<thinking>reasoning here</thinking>", True),

        # Should NOT detect artifacts (clean answers)
        ("The revenue was $73.6 billion in 2022.", False),
        ("IBM's CEO is Arvind Krishna.", False),
        ("The context does not contain this information.", False),
    ])
    def test_contains_artifacts(self, cot_service, text, expected):
        """Test artifact detection with various inputs."""
        assert cot_service._contains_artifacts(text) == expected

    def test_contains_artifacts_case_insensitive(self, cot_service):
        """Test artifact detection is case insensitive."""
        assert cot_service._contains_artifacts("BASED ON THE ANALYSIS")
        assert cot_service._contains_artifacts("Based On The Analysis")
        assert cot_service._contains_artifacts("based on the analysis")
```

---

### 2. Quality Scoring Tests

**File**: `tests/unit/services/test_cot_quality_scoring.py`

```python
"""Unit tests for CoT quality scoring."""

import pytest

from rag_solution.services.chain_of_thought_service import ChainOfThoughtService


class TestQualityScoring:
    """Test quality scoring for CoT responses."""

    @pytest.fixture
    def cot_service(self, db_session, mock_settings):
        """Create CoT service fixture."""
        return ChainOfThoughtService(
            settings=mock_settings,
            llm_service=None,
            search_service=None,
            db=db_session
        )

    def test_perfect_answer_scores_100(self, cot_service):
        """Test that perfect answer gets score of 1.0."""
        answer = "IBM's revenue in 2022 was $73.6 billion."
        question = "What was IBM revenue?"

        score = cot_service._assess_answer_quality(answer, question)

        assert score == 1.0

    def test_answer_with_artifacts_loses_points(self, cot_service):
        """Test that artifacts reduce score."""
        answer = "Based on the analysis: IBM's revenue was $73.6B"
        question = "What was IBM revenue?"

        score = cot_service._assess_answer_quality(answer, question)

        assert score < 0.7  # Should lose at least 0.4 for artifacts

    def test_too_short_answer_loses_points(self, cot_service):
        """Test that very short answers lose points."""
        answer = "Yes"
        question = "Was revenue high?"

        score = cot_service._assess_answer_quality(answer, question)

        assert score < 0.8  # Should lose at least 0.3 for being too short

    def test_duplicate_sentences_lose_points(self, cot_service):
        """Test that duplicate sentences reduce score."""
        answer = "Revenue was $73.6B. Revenue was $73.6B."
        question = "What was revenue?"

        score = cot_service._assess_answer_quality(answer, question)

        assert score < 0.9  # Should lose at least 0.2 for duplicates

    def test_question_repeated_loses_points(self, cot_service):
        """Test that repeating the question loses points."""
        answer = "What was IBM revenue? IBM revenue was $73.6B."
        question = "What was IBM revenue?"

        score = cot_service._assess_answer_quality(answer, question)

        assert score < 1.0  # Should lose at least 0.1

    @pytest.mark.parametrize("answer,expected_min_score", [
        ("IBM's revenue was $73.6 billion.", 0.9),  # Good answer
        ("Revenue: $73.6B in 2022.", 0.9),  # Good, concise
        ("See IBM's annual report.", 0.8),  # Short but acceptable
        ("Based on analysis: $73.6B", 0.5),  # Has artifacts
        ("Yes", 0.3),  # Too short
        ("", 0.0),  # Empty
    ])
    def test_quality_thresholds(self, cot_service, answer, expected_min_score):
        """Test quality score thresholds for various answers."""
        question = "What was revenue?"
        score = cot_service._assess_answer_quality(answer, question)

        assert score >= expected_min_score, f"Score {score} < {expected_min_score}"
```

---

### 3. Multi-Layer Parsing Tests

**File**: `tests/unit/services/test_cot_parsing_layers.py`

```python
"""Unit tests for multi-layer parsing."""

import pytest

from rag_solution.services.chain_of_thought_service import ChainOfThoughtService


class TestMultiLayerParsing:
    """Test multi-layer parsing fallbacks."""

    @pytest.fixture
    def cot_service(self, db_session, mock_settings):
        """Create CoT service fixture."""
        return ChainOfThoughtService(
            settings=mock_settings,
            llm_service=None,
            search_service=None,
            db=db_session
        )

    # Layer 1: XML Tags
    @pytest.mark.parametrize("response,expected", [
        (
            "<thinking>reasoning</thinking><answer>Clean answer</answer>",
            "Clean answer"
        ),
        (
            "<THINKING>reasoning</THINKING><ANSWER>Clean answer</ANSWER>",
            "Clean answer"  # Case insensitive
        ),
        (
            "Some text <answer>Clean answer</answer> more text",
            "Clean answer"
        ),
    ])
    def test_parse_xml_tags(self, cot_service, response, expected):
        """Test XML tag parsing (Layer 1)."""
        result = cot_service._parse_xml_tags(response)
        assert result == expected

    def test_parse_xml_after_thinking(self, cot_service):
        """Test extracting answer after </thinking> tag."""
        response = "<thinking>reasoning</thinking>Clean answer here"
        result = cot_service._parse_xml_tags(response)
        assert result == "Clean answer here"

    # Layer 2: JSON Structure
    @pytest.mark.parametrize("response,expected", [
        (
            '{"answer": "Clean answer"}',
            "Clean answer"
        ),
        (
            '{"reasoning": "...", "answer": "Clean answer"}',
            "Clean answer"
        ),
        (
            'Some text {"answer": "Clean answer"} more text',
            "Clean answer"
        ),
    ])
    def test_parse_json_structure(self, cot_service, response, expected):
        """Test JSON structure parsing (Layer 2)."""
        result = cot_service._parse_json_structure(response)
        assert result == expected

    def test_parse_json_invalid_returns_none(self, cot_service):
        """Test that invalid JSON returns None."""
        response = '{"answer": invalid json}'
        result = cot_service._parse_json_structure(response)
        assert result is None

    # Layer 3: Final Answer Marker
    @pytest.mark.parametrize("response,expected", [
        (
            "Reasoning here\n\nFinal Answer: Clean answer",
            "Clean answer"
        ),
        (
            "Reasoning here\n\nFINAL ANSWER: Clean answer",
            "Clean answer"  # Case insensitive
        ),
        (
            "Some text Final answer: Clean answer here",
            "Clean answer here"
        ),
    ])
    def test_parse_final_answer_marker(self, cot_service, response, expected):
        """Test Final Answer marker parsing (Layer 3)."""
        result = cot_service._parse_final_answer_marker(response)
        assert result == expected

    # Layer 4: Regex Cleaning
    def test_clean_with_regex_removes_prefixes(self, cot_service):
        """Test regex cleaning removes common prefixes."""
        response = "Based on the analysis of revenue: $73.6B in 2022"
        result = cot_service._clean_with_regex(response)

        assert "based on the analysis" not in result.lower()
        assert "$73.6B" in result

    def test_clean_with_regex_removes_context_markers(self, cot_service):
        """Test regex cleaning removes context markers."""
        response = "Revenue was $73.6B (in the context of annual report)"
        result = cot_service._clean_with_regex(response)

        assert "(in the context of" not in result.lower()
        assert "$73.6B" in result

    def test_clean_with_regex_removes_duplicates(self, cot_service):
        """Test regex cleaning removes duplicate sentences."""
        response = "Revenue was $73.6B. Revenue was $73.6B. It was high."
        result = cot_service._clean_with_regex(response)

        # Should only appear once
        assert result.count("Revenue was $73.6B") == 1
        assert "It was high" in result

    # Layer 5: Full Fallback
    def test_parse_structured_response_tries_all_layers(self, cot_service):
        """Test that structured response parsing tries all layers."""
        # This should fail XML, JSON, marker, but succeed with regex
        response = "Based on analysis: The answer is $73.6B"
        result = cot_service._parse_structured_response(response)

        assert result is not None
        assert len(result) > 0
        assert "based on" not in result.lower()
```

---

## Integration Tests

### 4. End-to-End CoT Tests

**File**: `tests/integration/services/test_cot_no_leakage.py`

```python
"""Integration tests for CoT reasoning without leakage."""

import pytest

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService


@pytest.mark.integration
class TestCoTNoLeakage:
    """Test that CoT reasoning doesn't leak into final answers."""

    @pytest.fixture
    def cot_service(self, db_session, test_settings, mock_llm_service, mock_search_service):
        """Create CoT service with dependencies."""
        return ChainOfThoughtService(
            settings=test_settings,
            llm_service=mock_llm_service,
            search_service=mock_search_service,
            db=db_session
        )

    async def test_cot_response_has_no_artifacts(
        self, cot_service, test_collection_id, test_user_id
    ):
        """Test that CoT response contains no reasoning artifacts."""
        # Create input
        input_data = ChainOfThoughtInput(
            question="What was IBM's revenue in 2022?",
            collection_id=test_collection_id,
            user_id=test_user_id,
            max_depth=2,
        )

        # Execute CoT
        result = await cot_service.execute_chain_of_thought(input_data)

        # Check final answer has no artifacts
        answer = result.final_answer.lower()

        assert "based on the analysis" not in answer
        assert "(in the context of" not in answer
        assert "furthermore" not in answer
        assert "additionally" not in answer
        assert "<thinking>" not in answer
        assert "</thinking>" not in answer
        assert "<answer>" not in answer
        assert "</answer>" not in answer

    async def test_cot_response_quality_above_threshold(
        self, cot_service, test_collection_id, test_user_id
    ):
        """Test that CoT response meets quality threshold."""
        input_data = ChainOfThoughtInput(
            question="Who is IBM's CEO?",
            collection_id=test_collection_id,
            user_id=test_user_id,
        )

        result = await cot_service.execute_chain_of_thought(input_data)

        # Assess quality
        quality = cot_service._assess_answer_quality(
            result.final_answer,
            input_data.question
        )

        assert quality >= 0.6, f"Quality {quality} below threshold"

    async def test_cot_retries_on_low_quality(
        self, cot_service, mock_llm_service, test_collection_id, test_user_id
    ):
        """Test that CoT retries when quality is low."""
        # Mock LLM to return bad answer first, good answer second
        bad_response = "Based on the analysis: answer"
        good_response = "<thinking>...</thinking><answer>Clean answer</answer>"

        mock_llm_service.generate_text_with_usage.side_effect = [
            (bad_response, None),  # First attempt - bad
            (good_response, None),  # Second attempt - good
        ]

        input_data = ChainOfThoughtInput(
            question="What is the revenue?",
            collection_id=test_collection_id,
            user_id=test_user_id,
        )

        result = await cot_service.execute_chain_of_thought(input_data)

        # Should have retried and got clean answer
        assert "based on the analysis" not in result.final_answer.lower()
        assert "clean answer" in result.final_answer.lower()

        # Should have made 2 LLM calls
        assert mock_llm_service.generate_text_with_usage.call_count == 2
```

---

### 5. Real LLM Integration Tests

**File**: `tests/integration/services/test_cot_real_llm.py`

```python
"""Integration tests with real LLM providers."""

import pytest

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput


@pytest.mark.integration
@pytest.mark.requires_llm
class TestCoTRealLLM:
    """Test CoT with real LLM providers."""

    async def test_watsonx_no_leakage(
        self, cot_service_with_watsonx, test_collection_id, test_user_id
    ):
        """Test that WatsonX responses have no leakage."""
        input_data = ChainOfThoughtInput(
            question="What was IBM's revenue and growth in 2022?",
            collection_id=test_collection_id,
            user_id=test_user_id,
        )

        result = await cot_service_with_watsonx.execute_chain_of_thought(input_data)

        # Check no artifacts
        answer = result.final_answer.lower()
        assert "based on the analysis" not in answer
        assert "(in the context of" not in answer

        # Check quality
        assert len(result.final_answer) > 20
        assert result.confidence_score > 0.6

    async def test_openai_no_leakage(
        self, cot_service_with_openai, test_collection_id, test_user_id
    ):
        """Test that OpenAI responses have no leakage."""
        # Similar test with OpenAI provider
        ...

    async def test_anthropic_no_leakage(
        self, cot_service_with_anthropic, test_collection_id, test_user_id
    ):
        """Test that Anthropic responses have no leakage."""
        # Similar test with Anthropic provider
        ...
```

---

### 6. Retry Mechanism Tests

**File**: `tests/integration/services/test_cot_retry.py`

```python
"""Integration tests for retry mechanism."""

import pytest
from unittest.mock import patch

from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput


@pytest.mark.integration
class TestCoTRetry:
    """Test retry mechanism for low-quality responses."""

    async def test_retry_improves_quality(
        self, cot_service, mock_llm_service, test_collection_id, test_user_id
    ):
        """Test that retry mechanism improves answer quality."""
        # Mock LLM to return progressively better answers
        responses = [
            ("Based on: answer", None),  # Attempt 1: score ~0.4
            ("Furthermore: better answer", None),  # Attempt 2: score ~0.5
            ("<answer>Good clean answer</answer>", None),  # Attempt 3: score ~0.9
        ]
        mock_llm_service.generate_text_with_usage.side_effect = responses

        input_data = ChainOfThoughtInput(
            question="What is the answer?",
            collection_id=test_collection_id,
            user_id=test_user_id,
        )

        result = await cot_service.execute_chain_of_thought(input_data)

        # Should have used third (best) answer
        assert "good clean answer" in result.final_answer.lower()
        assert "based on" not in result.final_answer.lower()

        # Should have made 3 attempts
        assert mock_llm_service.generate_text_with_usage.call_count == 3

    async def test_max_retries_respected(
        self, cot_service, mock_llm_service, test_collection_id, test_user_id
    ):
        """Test that max retries limit is respected."""
        # Mock LLM to always return bad answers
        bad_response = "Based on analysis: bad answer"
        mock_llm_service.generate_text_with_usage.return_value = (bad_response, None)

        input_data = ChainOfThoughtInput(
            question="What is the answer?",
            collection_id=test_collection_id,
            user_id=test_user_id,
        )

        result = await cot_service.execute_chain_of_thought(input_data)

        # Should have tried 3 times (max_retries=3)
        assert mock_llm_service.generate_text_with_usage.call_count == 3

        # Should return last attempt even though quality is low
        assert result.final_answer is not None
```

---

## E2E Tests

### 7. Full System Tests

**File**: `tests/e2e/test_cot_system.py`

```python
"""End-to-end tests for CoT system."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestCoTSystem:
    """End-to-end tests for CoT system."""

    def test_search_with_cot_returns_clean_answer(
        self, client: TestClient, test_user_token, test_collection_id
    ):
        """Test that search with CoT returns clean answer via API."""
        response = client.post(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "question": "What was IBM's revenue and how much was the growth?",
                "collection_id": str(test_collection_id),
                "use_chain_of_thought": True,
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check answer exists
        assert "answer" in data
        answer = data["answer"].lower()

        # Check no artifacts
        assert "based on the analysis" not in answer
        assert "(in the context of" not in answer
        assert "furthermore" not in answer

        # Check quality indicators
        assert len(data["answer"]) > 20
        if "confidence_score" in data:
            assert data["confidence_score"] > 0.5

    def test_problematic_queries_return_clean_answers(
        self, client: TestClient, test_user_token, test_collection_id
    ):
        """Test that previously problematic queries now return clean answers."""
        problematic_queries = [
            "what was the IBM revenue and how much was the growth?",
            "On what date were the shares purchased?",
            "What was the total amount spent on research, development, and engineering?",
        ]

        for query in problematic_queries:
            response = client.post(
                "/api/v1/search",
                headers={"Authorization": f"Bearer {test_user_token}"},
                json={
                    "question": query,
                    "collection_id": str(test_collection_id),
                    "use_chain_of_thought": True,
                }
            )

            assert response.status_code == 200
            data = response.json()
            answer = data["answer"].lower()

            # No artifacts allowed
            assert "based on the analysis" not in answer, f"Query: {query}"
            assert "(in the context of" not in answer, f"Query: {query}"
```

---

## Regression Test Suite

### Run All Regression Tests

```bash
# Run all CoT regression tests
pytest tests/unit/services/test_cot_*.py \
       tests/integration/services/test_cot_*.py \
       tests/e2e/test_cot_*.py \
       -v --cov=rag_solution.services.chain_of_thought_service

# Run only fast unit tests
pytest tests/unit/services/test_cot_*.py -v

# Run integration tests (requires services)
pytest tests/integration/services/test_cot_*.py -v -m integration

# Run E2E tests (requires full system)
pytest tests/e2e/test_cot_*.py -v -m e2e

# Run real LLM tests (requires API keys)
pytest tests/integration/services/test_cot_real_llm.py -v -m requires_llm
```

---

## Continuous Integration

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running CoT regression tests..."

# Run fast unit tests
pytest tests/unit/services/test_cot_*.py -v

if [ $? -ne 0 ]; then
    echo "❌ CoT unit tests failed!"
    exit 1
fi

echo "✅ CoT regression tests passed!"
exit 0
```

### CI Pipeline

```yaml
# .github/workflows/cot-regression.yml
name: CoT Regression Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Run CoT unit tests
        run: |
          poetry run pytest tests/unit/services/test_cot_*.py -v

      - name: Run CoT integration tests
        run: |
          poetry run pytest tests/integration/services/test_cot_*.py -v -m integration

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Test Coverage Requirements

```bash
# Require 95% coverage for CoT service
pytest tests/unit/services/test_cot_*.py \
       tests/integration/services/test_cot_*.py \
       --cov=rag_solution.services.chain_of_thought_service \
       --cov-fail-under=95
```

---

## Test Summary

| Test Category | Count | Purpose |
|---------------|-------|---------|
| **Artifact Detection** | 10+ | Ensure we catch all known artifacts |
| **Quality Scoring** | 15+ | Validate quality assessment |
| **Parsing Layers** | 20+ | Test all 5 fallback strategies |
| **Integration** | 10+ | Test component interactions |
| **Real LLM** | 5+ | Test with actual LLM providers |
| **Retry Mechanism** | 5+ | Test retry logic works |
| **E2E** | 5+ | Full system tests |
| **Total** | **70+** | Comprehensive coverage |

---

*Last Updated: October 25, 2025*
