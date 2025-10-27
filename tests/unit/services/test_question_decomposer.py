"""Comprehensive unit tests for QuestionDecomposer service.

Tests the QuestionDecomposer component for Chain of Thought reasoning.
Covers question decomposition logic, multi-part detection, error handling,
and edge cases with fully mocked dependencies.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from core.config import Settings
from rag_solution.schemas.chain_of_thought_schema import DecomposedQuestion, QuestionDecomposition
from rag_solution.services.question_decomposer import QuestionDecomposer


class TestQuestionDecomposerUnit:
    """Unit tests for QuestionDecomposer with fully mocked dependencies."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.cot_max_depth = 5
        settings.cot_token_multiplier = 2.0
        settings.cot_evaluation_threshold = 0.6
        return settings

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing."""
        mock = AsyncMock()
        mock.generate_text = AsyncMock()
        return mock

    @pytest.fixture
    def decomposer(self, mock_llm_service, mock_settings):
        """Create QuestionDecomposer instance for testing."""
        return QuestionDecomposer(llm_service=mock_llm_service, settings=mock_settings)

    @pytest.fixture
    def decomposer_no_llm(self, mock_settings):
        """Create QuestionDecomposer without LLM service for testing."""
        return QuestionDecomposer(llm_service=None, settings=mock_settings)

    # ============================================================================
    # INITIALIZATION TESTS
    # ============================================================================

    def test_initialization_with_llm_service(self, decomposer, mock_llm_service):
        """Test decomposer initializes correctly with LLM service."""
        assert decomposer is not None
        assert decomposer.llm_service == mock_llm_service
        assert decomposer.settings is not None

    def test_initialization_without_llm_service(self, decomposer_no_llm):
        """Test decomposer initializes correctly without LLM service."""
        assert decomposer_no_llm is not None
        assert decomposer_no_llm.llm_service is None
        assert decomposer_no_llm.settings is not None

    def test_initialization_without_settings(self, mock_llm_service):
        """Test decomposer initializes with default settings when not provided."""
        decomposer = QuestionDecomposer(llm_service=mock_llm_service, settings=None)
        assert decomposer.settings is not None
        assert isinstance(decomposer.settings, Settings)

    # ============================================================================
    # SIMPLE QUESTION TESTS (No Decomposition Needed)
    # ============================================================================

    @pytest.mark.asyncio
    async def test_simple_what_question(self, decomposer_no_llm):
        """Test simple 'what' question returns single sub-question."""
        question = "What is Python?"

        result = await decomposer_no_llm.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) == 1
        assert result.sub_questions[0].sub_question == "What is Python?"
        assert result.sub_questions[0].question_type == "definition"
        assert result.sub_questions[0].reasoning_step == 1
        assert result.sub_questions[0].dependency_indices == []
        assert 0 <= result.sub_questions[0].complexity_score <= 1

    @pytest.mark.asyncio
    async def test_simple_define_question(self, decomposer_no_llm):
        """Test simple 'define' question returns single sub-question."""
        question = "Define machine learning?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) == 1
        assert result.sub_questions[0].question_type == "definition"
        assert result.sub_questions[0].sub_question.endswith("?")

    @pytest.mark.asyncio
    async def test_simple_short_question(self, decomposer_no_llm):
        """Test very short question."""
        question = "Python?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) == 1
        assert result.sub_questions[0].sub_question == "Python?"

    # ============================================================================
    # MULTI-PART QUESTION DECOMPOSITION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_conjunction_and_decomposition(self, decomposer_no_llm):
        """Test decomposition of questions connected with 'and'."""
        question = "What is machine learning and how does it work?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2
        # Each sub-question should end with ?
        for sq in result.sub_questions:
            assert sq.sub_question.endswith("?")
        # Check step numbering
        for i, sq in enumerate(result.sub_questions):
            assert sq.reasoning_step == i + 1

    @pytest.mark.asyncio
    async def test_conjunction_but_decomposition(self, decomposer_no_llm):
        """Test decomposition of questions connected with 'but'."""
        question = "What is supervised learning but how does it differ from unsupervised?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2

    @pytest.mark.asyncio
    async def test_conjunction_however_decomposition(self, decomposer_no_llm):
        """Test decomposition of questions connected with 'however'."""
        question = "What is deep learning however what are its limitations?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2

    @pytest.mark.asyncio
    async def test_multiple_question_marks(self, decomposer_no_llm):
        """Test decomposition of questions with multiple question marks."""
        question = "What is Python? How is it used in data science?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2
        # Both parts should be present
        assert any("Python" in sq.sub_question for sq in result.sub_questions)
        assert any("data science" in sq.sub_question for sq in result.sub_questions)

    @pytest.mark.asyncio
    async def test_implicit_multi_part_how_what(self, decomposer_no_llm):
        """Test implicit multi-part question with 'how' and 'what'."""
        question = "What is neural network how does it learn?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2

    # ============================================================================
    # COMPARISON QUESTION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_compare_question_decomposition(self, decomposer_no_llm):
        """Test decomposition of comparison question with 'compare'."""
        question = "Compare supervised learning and unsupervised learning"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2
        # Should include definition questions and comparison
        question_types = [sq.question_type for sq in result.sub_questions]
        assert "definition" in question_types or "comparison" in question_types

    @pytest.mark.asyncio
    async def test_contrast_question_decomposition(self, decomposer_no_llm):
        """Test decomposition of comparison question with 'contrast'."""
        question = "Contrast CNN and RNN architectures"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2
        question_types = [sq.question_type for sq in result.sub_questions]
        assert "definition" in question_types or "comparison" in question_types

    @pytest.mark.asyncio
    async def test_comparison_complexity_score(self, decomposer_no_llm):
        """Test comparison questions have higher complexity scores."""
        question = "Compare and contrast supervised and unsupervised learning"

        result = await decomposer_no_llm.decompose(question)

        # Comparison type questions should have complexity >= 0.6
        comparison_questions = [sq for sq in result.sub_questions if sq.question_type == "comparison"]
        if comparison_questions:
            for sq in comparison_questions:
                assert sq.complexity_score >= 0.6

    # ============================================================================
    # CAUSAL QUESTION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_why_question_decomposition(self, decomposer_no_llm):
        """Test decomposition of 'why' causal question."""
        question = "Why does regularization prevent overfitting in neural networks?"

        result = await decomposer_no_llm.decompose(question)

        assert len(result.sub_questions) >= 2
        # Should have definition and causal components
        question_types = [sq.question_type for sq in result.sub_questions]
        assert "definition" in question_types or "causal" in question_types

    @pytest.mark.asyncio
    async def test_how_does_question_decomposition(self, decomposer_no_llm):
        """Test decomposition of 'how does' procedural question."""
        question = "How does backpropagation work in neural networks?"

        result = await decomposer_no_llm.decompose(question)

        # Single procedural question without conjunctions returns 1 sub-question
        assert len(result.sub_questions) >= 1
        question_types = [sq.question_type for sq in result.sub_questions]
        # Should be procedural
        assert "procedural" in question_types

    @pytest.mark.asyncio
    async def test_cause_question_decomposition(self, decomposer_no_llm):
        """Test decomposition of question with 'cause' and conjunction."""
        question = "What causes overfitting and how can it be prevented?"

        result = await decomposer_no_llm.decompose(question)

        # Should decompose on 'and' conjunction
        assert len(result.sub_questions) >= 2
        question_types = [sq.question_type for sq in result.sub_questions]
        # Should include definition and procedural types based on question structure
        assert "definition" in question_types or "procedural" in question_types or "causal" in question_types

    @pytest.mark.asyncio
    async def test_causal_complexity_score(self, decomposer_no_llm):
        """Test causal questions have appropriate complexity scores."""
        question = "Why is gradient descent important?"

        result = await decomposer_no_llm.decompose(question)

        # Causal type questions should have complexity >= 0.5
        causal_questions = [sq for sq in result.sub_questions if sq.question_type == "causal"]
        if causal_questions:
            for sq in causal_questions:
                assert sq.complexity_score >= 0.5

    # ============================================================================
    # QUESTION TYPE CLASSIFICATION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_question_type_definition(self, decomposer_no_llm):
        """Test classification of definition questions."""
        test_cases = [
            "What is machine learning?",
            "Define neural network",
            "What is the meaning of overfitting?",
        ]

        for question in test_cases:
            result = await decomposer_no_llm.decompose(question)
            question_types = [sq.question_type for sq in result.sub_questions]
            assert "definition" in question_types

    @pytest.mark.asyncio
    async def test_question_type_comparison(self, decomposer_no_llm):
        """Test classification of comparison questions."""
        test_cases = ["Compare CNN and RNN", "What is the difference between supervised and unsupervised learning?"]

        for question in test_cases:
            result = await decomposer_no_llm.decompose(question)
            question_types = [sq.question_type for sq in result.sub_questions]
            assert "comparison" in question_types or "definition" in question_types

    @pytest.mark.asyncio
    async def test_question_type_causal(self, decomposer_no_llm):
        """Test classification of causal questions."""
        test_cases = [
            "Why is dropout important?",
            "What causes gradient vanishing?",
            "What is the reason for using batch normalization?",
        ]

        for question in test_cases:
            result = await decomposer_no_llm.decompose(question)
            question_types = [sq.question_type for sq in result.sub_questions]
            assert "causal" in question_types or "definition" in question_types

    @pytest.mark.asyncio
    async def test_question_type_procedural(self, decomposer_no_llm):
        """Test classification of procedural questions."""
        test_cases = [
            "How do I train a neural network?",
            "What are the steps to implement backpropagation?",
            "How does the training process work?",
        ]

        for question in test_cases:
            result = await decomposer_no_llm.decompose(question)
            question_types = [sq.question_type for sq in result.sub_questions]
            assert "procedural" in question_types or "definition" in question_types

    @pytest.mark.asyncio
    async def test_question_type_analytical(self, decomposer_no_llm):
        """Test classification of questions without specific keywords."""
        question = "Examine the performance impact of different activation functions"

        result = await decomposer_no_llm.decompose(question)

        # Should have at least one question
        assert len(result.sub_questions) >= 1
        # Question type should be analytical (default when no specific keywords match)
        question_types = [sq.question_type for sq in result.sub_questions]
        assert "analytical" in question_types or "comparison" in question_types

    # ============================================================================
    # DEPENDENCY TRACKING TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_dependency_indices_first_question(self, decomposer_no_llm):
        """Test first sub-question has no dependencies."""
        question = "What is machine learning and how does it work?"

        result = await decomposer_no_llm.decompose(question)

        # First question should have empty dependencies
        assert result.sub_questions[0].dependency_indices == []

    @pytest.mark.asyncio
    async def test_dependency_indices_later_questions(self, decomposer_no_llm):
        """Test later sub-questions have dependencies on earlier ones."""
        question = "What is machine learning and how does it work in practice?"

        result = await decomposer_no_llm.decompose(question)

        # Later questions should depend on earlier ones
        if len(result.sub_questions) > 1:
            for i in range(1, len(result.sub_questions)):
                assert len(result.sub_questions[i].dependency_indices) > 0
                # Dependencies should reference earlier steps
                for dep_idx in result.sub_questions[i].dependency_indices:
                    assert dep_idx < i

    @pytest.mark.asyncio
    async def test_dependency_indices_sequential(self, decomposer_no_llm):
        """Test dependency indices are sequential for multi-part questions."""
        question = "What is A and what is B and what is C?"

        result = await decomposer_no_llm.decompose(question)

        for i, sq in enumerate(result.sub_questions):
            if i == 0:
                assert sq.dependency_indices == []
            else:
                # Should depend on all previous steps
                assert sq.dependency_indices == list(range(i))

    # ============================================================================
    # COMPLEXITY SCORING TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_complexity_score_range(self, decomposer_no_llm):
        """Test complexity scores are within valid range [0, 1]."""
        questions = [
            "What is Python?",
            "Compare supervised and unsupervised learning",
            "Why does regularization prevent overfitting in deep neural networks?",
        ]

        for question in questions:
            result = await decomposer_no_llm.decompose(question)
            for sq in result.sub_questions:
                assert 0 <= sq.complexity_score <= 1

    @pytest.mark.asyncio
    async def test_complexity_score_length_based(self, decomposer_no_llm):
        """Test complexity score increases with question length."""
        short_question = "What is AI?"
        long_question = "What is artificial intelligence and how does it relate to machine learning, deep learning, and neural networks in modern applications?"

        short_result = await decomposer_no_llm.decompose(short_question)
        long_result = await decomposer_no_llm.decompose(long_question)

        # Longer questions should have higher complexity scores
        avg_short_complexity = sum(sq.complexity_score for sq in short_result.sub_questions) / len(
            short_result.sub_questions
        )
        avg_long_complexity = sum(sq.complexity_score for sq in long_result.sub_questions) / len(
            long_result.sub_questions
        )

        assert avg_long_complexity >= avg_short_complexity

    @pytest.mark.asyncio
    async def test_complexity_score_procedural_boost(self, decomposer_no_llm):
        """Test procedural questions have boosted complexity scores."""
        question = "How does gradient descent optimize neural networks?"

        result = await decomposer_no_llm.decompose(question)

        procedural_questions = [sq for sq in result.sub_questions if sq.question_type == "procedural"]
        if procedural_questions:
            for sq in procedural_questions:
                assert sq.complexity_score >= 0.4

    # ============================================================================
    # MAX DEPTH ENFORCEMENT TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_max_depth_default(self, decomposer_no_llm):
        """Test default max depth is 3."""
        question = "A and B and C and D and E and F and G"

        result = await decomposer_no_llm.decompose(question, max_depth=3)

        # Should limit to max_depth sub-questions
        assert len(result.sub_questions) <= 3

    @pytest.mark.asyncio
    async def test_max_depth_custom(self, decomposer_no_llm):
        """Test custom max depth is respected."""
        question = "A and B and C and D and E and F"

        result = await decomposer_no_llm.decompose(question, max_depth=2)

        assert len(result.sub_questions) <= 2

    @pytest.mark.asyncio
    async def test_max_depth_zero(self, decomposer_no_llm):
        """Test max_depth of 0 returns original question."""
        question = "What is machine learning and how does it work?"

        result = await decomposer_no_llm.decompose(question, max_depth=0)

        # Should still return at least the original question
        assert len(result.sub_questions) >= 1

    @pytest.mark.asyncio
    async def test_max_depth_high_value(self, decomposer_no_llm):
        """Test high max depth doesn't create unnecessary sub-questions."""
        question = "What is Python and how is it used?"

        result = await decomposer_no_llm.decompose(question, max_depth=100)

        # Should only create as many sub-questions as naturally exist
        # Not artificially inflate to max_depth
        assert len(result.sub_questions) <= 3

    # ============================================================================
    # EDGE CASES AND ERROR HANDLING
    # ============================================================================

    @pytest.mark.asyncio
    async def test_empty_question(self, decomposer_no_llm):
        """Test handling of empty question string."""
        question = ""

        result = await decomposer_no_llm.decompose(question)

        # Should still return valid QuestionDecomposition
        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) >= 1

    @pytest.mark.asyncio
    async def test_whitespace_only_question(self, decomposer_no_llm):
        """Test handling of whitespace-only question."""
        question = "   "

        result = await decomposer_no_llm.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) >= 1

    @pytest.mark.asyncio
    async def test_question_without_question_mark(self, decomposer_no_llm):
        """Test question without question mark gets one added."""
        question = "What is machine learning"

        result = await decomposer_no_llm.decompose(question)

        # All sub-questions should end with ?
        for sq in result.sub_questions:
            assert sq.sub_question.endswith("?")

    @pytest.mark.asyncio
    async def test_very_long_question(self, decomposer_no_llm):
        """Test handling of very long question (>1000 characters)."""
        question = "What is " + "machine learning " * 100 + "and how does it work?"

        result = await decomposer_no_llm.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) >= 1
        # Complexity score should approach 1.0 for very long questions
        assert any(sq.complexity_score > 0.8 for sq in result.sub_questions)

    @pytest.mark.asyncio
    async def test_special_characters_in_question(self, decomposer_no_llm):
        """Test handling of special characters in question."""
        question = "What is @machine-learning & how does it work with $neural_networks?"

        result = await decomposer_no_llm.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) >= 1

    @pytest.mark.asyncio
    async def test_unicode_characters(self, decomposer_no_llm):
        """Test handling of unicode characters in question."""
        question = "What is machine learning and how does it work with données?"

        result = await decomposer_no_llm.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) >= 1

    @pytest.mark.asyncio
    async def test_question_with_numbers(self, decomposer_no_llm):
        """Test handling of questions with numbers."""
        question = "What is GPT-3 and how does it differ from GPT-2?"

        result = await decomposer_no_llm.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) >= 2

    @pytest.mark.asyncio
    async def test_case_insensitive_conjunctions(self, decomposer_no_llm):
        """Test conjunctions are detected case-insensitively."""
        questions = [
            "What is ML AND how does it work?",
            "What is ML and how does it work?",
            "What is ML And how does it work?",
        ]

        for question in questions:
            result = await decomposer_no_llm.decompose(question)
            assert len(result.sub_questions) >= 2

    # ============================================================================
    # EXTRACT MAIN CONCEPT TESTS (Private Method Testing)
    # ============================================================================

    def test_extract_main_concept_two_words(self, decomposer_no_llm):
        """Test extracting main concept with two meaningful words."""
        question = "Why does regularization prevent overfitting in neural networks?"

        concept = decomposer_no_llm._extract_main_concept(question)

        # Should extract two key words
        assert "and" in concept
        assert len(concept.split()) >= 2

    def test_extract_main_concept_one_word(self, decomposer_no_llm):
        """Test extracting main concept with one meaningful word."""
        question = "Why does overfitting occur?"

        concept = decomposer_no_llm._extract_main_concept(question)

        # Should return single word or default
        assert len(concept) > 0

    def test_extract_main_concept_no_words(self, decomposer_no_llm):
        """Test extracting main concept with minimal meaningful words."""
        question = "Why does the a an?"

        concept = decomposer_no_llm._extract_main_concept(question)

        # Should return at least some concept (may return remaining word or default)
        assert len(concept) > 0
        assert concept in ["an", "the concept"]

    def test_extract_main_concept_removes_stop_words(self, decomposer_no_llm):
        """Test that stop words are removed from extracted concept."""
        question = "Why does the regularization prevent the overfitting?"

        concept = decomposer_no_llm._extract_main_concept(question)

        # Should not contain stop words
        assert "the" not in concept.lower()
        assert "does" not in concept.lower()

    # ============================================================================
    # DETERMINE QUESTION TYPE TESTS (Private Method Testing)
    # ============================================================================

    def test_determine_question_type_definition(self, decomposer_no_llm):
        """Test question type determination for definition questions."""
        questions = ["What is Python?", "Define machine learning", "What is the meaning of AI?"]

        for question in questions:
            q_type = decomposer_no_llm._determine_question_type(question)
            assert q_type == "definition"

    def test_determine_question_type_comparison(self, decomposer_no_llm):
        """Test question type determination for comparison questions."""
        # Pure comparison question without other keywords
        comparison_question = "Compare CNN and RNN"
        q_type = decomposer_no_llm._determine_question_type(comparison_question)
        assert q_type == "comparison"

        # Questions with multiple keywords - checks in priority order
        # The method checks keywords in order: what/define, compare/differ, why/cause, how/steps
        # So 'what' takes precedence over 'versus'
        mixed_questions = [
            ("What is CNN versus RNN?", ["definition", "comparison"]),  # 'what' comes first
            ("How do supervised and unsupervised learning differ?", ["procedural", "comparison"]),  # 'how' comes first
            (
                "What are the differences between supervised and unsupervised learning?",
                ["definition", "procedural", "comparison"],
            ),  # 'what' comes first
        ]
        for question, valid_types in mixed_questions:
            q_type = decomposer_no_llm._determine_question_type(question)
            assert q_type in valid_types

    def test_determine_question_type_causal(self, decomposer_no_llm):
        """Test question type determination for causal questions."""
        # Pure causal questions
        causal_questions = [
            "Why does overfitting occur?",
            "What is the reason for dropout?",
        ]

        for question in causal_questions:
            q_type = decomposer_no_llm._determine_question_type(question)
            # 'why' triggers causal, but 'what' triggers definition first
            assert q_type in ["causal", "definition"]

        # 'cause' keyword triggers causal
        cause_question = "What causes gradient vanishing?"
        q_type = decomposer_no_llm._determine_question_type(cause_question)
        # 'what' comes before 'cause', so definition takes precedence
        assert q_type in ["definition", "causal"]

    def test_determine_question_type_procedural(self, decomposer_no_llm):
        """Test question type determination for procedural questions."""
        # Pure procedural questions with 'how'
        procedural_questions = ["How do I train a model?", "How does the process work?"]

        for question in procedural_questions:
            q_type = decomposer_no_llm._determine_question_type(question)
            assert q_type == "procedural"

        # Questions with 'steps' keyword
        steps_question = "What are the steps to implement?"
        q_type = decomposer_no_llm._determine_question_type(steps_question)
        # 'what' comes before 'steps', so may be definition or procedural
        assert q_type in ["definition", "procedural"]

    def test_determine_question_type_analytical(self, decomposer_no_llm):
        """Test question type determination for analytical questions."""
        question = "Analyze the performance metrics"

        q_type = decomposer_no_llm._determine_question_type(question)

        assert q_type == "analytical"

    def test_determine_question_type_case_insensitive(self, decomposer_no_llm):
        """Test question type determination is case-insensitive."""
        questions = ["WHAT IS PYTHON?", "what is python?", "What Is Python?"]

        for question in questions:
            q_type = decomposer_no_llm._determine_question_type(question)
            assert q_type == "definition"

    # ============================================================================
    # REASONING STEP NUMBERING TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_reasoning_step_sequential(self, decomposer_no_llm):
        """Test reasoning steps are numbered sequentially starting from 1."""
        question = "What is A and what is B and what is C?"

        result = await decomposer_no_llm.decompose(question)

        for i, sq in enumerate(result.sub_questions):
            assert sq.reasoning_step == i + 1

    @pytest.mark.asyncio
    async def test_reasoning_step_single_question(self, decomposer_no_llm):
        """Test single question has reasoning step 1."""
        question = "What is Python?"

        result = await decomposer_no_llm.decompose(question)

        assert result.sub_questions[0].reasoning_step == 1

    # ============================================================================
    # SCHEMA VALIDATION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_decomposed_question_schema_valid(self, decomposer_no_llm):
        """Test all decomposed questions conform to schema."""
        question = "What is machine learning and how does it work?"

        result = await decomposer_no_llm.decompose(question)

        for sq in result.sub_questions:
            # Validate it's a proper DecomposedQuestion instance
            assert isinstance(sq, DecomposedQuestion)
            # Validate required fields
            assert isinstance(sq.sub_question, str)
            assert isinstance(sq.reasoning_step, int)
            assert isinstance(sq.dependency_indices, list)
            assert sq.question_type in ["definition", "comparison", "causal", "procedural", "analytical"]
            assert 0 <= sq.complexity_score <= 1

    @pytest.mark.asyncio
    async def test_question_decomposition_schema_valid(self, decomposer_no_llm):
        """Test QuestionDecomposition result conforms to schema."""
        question = "What is Python?"

        result = await decomposer_no_llm.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert isinstance(result.sub_questions, list)
        assert len(result.sub_questions) > 0
        assert all(isinstance(sq, DecomposedQuestion) for sq in result.sub_questions)

    # ============================================================================
    # ASYNC OPERATION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_async_decompose_completes(self, decomposer_no_llm):
        """Test async decompose method completes successfully."""
        question = "What is machine learning?"

        result = await decomposer_no_llm.decompose(question)

        assert result is not None
        assert isinstance(result, QuestionDecomposition)

    @pytest.mark.asyncio
    async def test_multiple_async_calls(self, decomposer_no_llm):
        """Test multiple async decompose calls work correctly."""
        questions = [
            "What is Python?",
            "Compare supervised and unsupervised learning",
            "How does backpropagation work?",
        ]

        results = []
        for question in questions:
            result = await decomposer_no_llm.decompose(question)
            results.append(result)

        assert len(results) == 3
        assert all(isinstance(r, QuestionDecomposition) for r in results)

    # ============================================================================
    # INTEGRATION WITH LLM SERVICE TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_with_llm_service_available(self, decomposer, mock_llm_service):
        """Test decomposer works with LLM service available."""
        question = "What is machine learning?"

        result = await decomposer.decompose(question)

        assert isinstance(result, QuestionDecomposition)
        assert len(result.sub_questions) >= 1

    @pytest.mark.asyncio
    async def test_llm_service_not_called_for_simple_decomposition(self, decomposer, mock_llm_service):
        """Test LLM service is not called for simple regex-based decomposition."""
        question = "What is Python and how is it used?"

        await decomposer.decompose(question)

        # Currently LLM service is not used in decomposition
        # This test documents that behavior
        assert mock_llm_service.generate_text.call_count == 0

    # ============================================================================
    # COMPREHENSIVE END-TO-END TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_complex_multi_part_question_full_flow(self, decomposer_no_llm):
        """Test complex multi-part question through full decomposition flow."""
        question = "What is machine learning and how does it differ from deep learning, and why is it important for AI?"

        result = await decomposer_no_llm.decompose(question)

        # Should have multiple sub-questions
        assert len(result.sub_questions) >= 3
        # Should have various question types
        question_types = {sq.question_type for sq in result.sub_questions}
        assert len(question_types) >= 2
        # All should have valid complexity scores
        assert all(0 <= sq.complexity_score <= 1 for sq in result.sub_questions)
        # Dependencies should be properly tracked
        assert result.sub_questions[0].dependency_indices == []
        if len(result.sub_questions) > 1:
            assert len(result.sub_questions[1].dependency_indices) > 0

    @pytest.mark.asyncio
    async def test_comparison_question_full_flow(self, decomposer_no_llm):
        """Test comparison question through full decomposition flow."""
        question = "Compare and contrast supervised learning and unsupervised learning"

        result = await decomposer_no_llm.decompose(question)

        # Should decompose into definition and comparison questions
        assert len(result.sub_questions) >= 2
        question_types = [sq.question_type for sq in result.sub_questions]
        assert "definition" in question_types or "comparison" in question_types
        # Comparison questions should have higher complexity
        comparison_questions = [sq for sq in result.sub_questions if sq.question_type == "comparison"]
        if comparison_questions:
            assert all(sq.complexity_score >= 0.6 for sq in comparison_questions)

    @pytest.mark.asyncio
    async def test_causal_chain_full_flow(self, decomposer_no_llm):
        """Test causal question chain through full decomposition flow."""
        question = "Why does regularization prevent overfitting in neural networks?"

        result = await decomposer_no_llm.decompose(question)

        # Should break down into definition and causal components
        assert len(result.sub_questions) >= 2
        question_types = [sq.question_type for sq in result.sub_questions]
        assert "definition" in question_types or "causal" in question_types
        # Later questions should depend on earlier ones
        if len(result.sub_questions) > 1:
            for i in range(1, len(result.sub_questions)):
                assert len(result.sub_questions[i].dependency_indices) > 0
