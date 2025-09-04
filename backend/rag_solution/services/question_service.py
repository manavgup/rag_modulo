"""Service for handling question suggestion functionality."""

import asyncio
import re
import time
from pydantic import UUID4

from sqlalchemy.orm import Session

from core.config import settings
from core.custom_exceptions import NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.models.question import SuggestedQuestion
from rag_solution.repository.question_repository import QuestionRepository
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.prompt_template_service import PromptTemplateService

logger = get_logger("services.question")


class QuestionService:
    """Service for managing question suggestions."""

    def __init__(self, db: Session) -> None:
        """
        Initialize question service.

        Args:
            db: Database session

        Raises:
            ValidationError: If configuration is invalid
        """
        self.db = db
        self._question_repository: QuestionRepository | None = None
        self._prompt_template_service: PromptTemplateService | None = None
        self._llm_parameters_service: LLMParametersService | None = None
        self._provider_factory = LLMProviderFactory(db)

    @property
    def question_repository(self) -> QuestionRepository:
        """Lazy initialization of question repository."""
        if self._question_repository is None:
            self._question_repository = QuestionRepository(self.db)
        return self._question_repository

    @property
    def prompt_template_service(self) -> PromptTemplateService:
        """Lazy initialization of prompt template service."""
        if self._prompt_template_service is None:
            self._prompt_template_service = PromptTemplateService(self.db)
        return self._prompt_template_service

    @property
    def llm_parameters_service(self) -> LLMParametersService:
        """Lazy initialization of LLM parameters service."""
        if self._llm_parameters_service is None:
            self._llm_parameters_service = LLMParametersService(self.db)
        return self._llm_parameters_service

    def _validate_question(self, question: str, context: str) -> tuple[bool, str]:
        """
        Validate and clean a question.

        Args:
            question: Question to validate
            context: Context to validate against

        Returns:
            Tuple of (is_valid, cleaned_question)
        """
        # Basic formatting checks
        if not question or not question.endswith("?"):
            logger.debug(f"Question rejected: No question mark or empty: {question}")
            return False, question

        question = question.strip()

        # Remove any numbering prefix
        cleaned_question = re.sub(r"^\d+\.\s*", "", question)

        # Check for multiple question marks
        if cleaned_question.count("?") > 1:
            return False, cleaned_question

        # Extract words and get count
        question_words = set(re.findall(r"\b\w+\b", cleaned_question.lower()))
        word_count = len(question_words)

        # Check for minimum word count
        if word_count < 2:
            return False, cleaned_question

        # Handle questions based on word count
        # Calculate relevance with more lenient threshold
        context_words = set(re.findall(r"\b\w+\b", context.lower()))

        if word_count <= 3:
            # For short questions, require at least one content word match
            content_words = question_words - {"what", "who", "when", "where", "why", "how", "is", "are", "do", "does"}
            is_valid = bool(content_words.intersection(context_words))
        else:  # word_count > 3
            # Handle questions with more than 3 words (longer questions)
            relevance_score = len(question_words.intersection(context_words)) / word_count
            min_relevance = 0.25  # Stricter threshold for relevance
            is_valid = relevance_score >= min_relevance

        return is_valid, cleaned_question

    def _rank_questions(self, questions: list[str], context: str) -> list[str]:
        """
        Rank questions by relevance and quality.

        Args:
            questions: List of questions to rank
            context: Context text to rank against

        Returns:
            List[str]: Ranked list of questions
        """
        scored_questions: list[tuple[str, float]] = []

        for question in questions:
            is_valid, cleaned_question = self._validate_question(question, context)
            if is_valid:
                # Calculate relevance based on word overlap instead of entities
                question_words = set(re.findall(r"\b\w+\b", cleaned_question.lower()))
                context_words = set(re.findall(r"\b\w+\b", context.lower()))

                # Calculate relevance score with more weight on context overlap
                relevance_score = len(question_words.intersection(context_words)) / len(question_words)

                # Add smaller complexity bonus for longer questions
                complexity_bonus: float = min(len(question_words) * 0.02, 0.15)  # Reduced bonus

                # Only apply complexity bonus if question has minimum relevance
                final_score: float = relevance_score + (complexity_bonus if relevance_score >= 0.25 else 0)

                scored_questions.append((cleaned_question, final_score))

        scored_questions.sort(key=lambda x: x[1], reverse=True)
        return [q[0] for q in scored_questions]

    def _filter_duplicate_questions(self, questions: list[str]) -> list[str]:
        """
        Remove duplicate questions using normalized comparison.

        Args:
            questions: List of questions to deduplicate

        Returns:
            List[str]: Deduplicated list of questions
        """
        seen = set()
        unique_questions = []

        for question in questions:
            # More aggressive normalization
            normalized = question.lower()
            normalized = re.sub(r"^\d+\.\s*", "", normalized)  # Remove numbering
            normalized = re.sub(r"[^\w\s]", "", normalized)  # Remove all punctuation
            normalized = re.sub(r"\s+", " ", normalized.strip())  # Normalize whitespace

            if normalized not in seen:
                seen.add(normalized)
                unique_questions.append(question)

        return unique_questions

    def _combine_text_chunks(self, texts: list[str], available_context_length: int) -> list[str]:
        """Combine text chunks while respecting context length limits."""
        combined_texts = []
        current_batch = []
        current_length = 0

        for text in texts:
            text_length = len(text)
            if current_length + text_length <= available_context_length:
                current_batch.append(text)
                current_length += text_length
            else:
                if current_batch:
                    combined_texts.append(" ".join(current_batch))
                    current_batch = [text]
                    current_length = text_length

        if current_batch:
            combined_texts.append(" ".join(current_batch))

        return combined_texts

    async def suggest_questions(
        self,
        texts: list[str],
        collection_id: UUID4,
        user_id: UUID4,
        provider_name: str,
        template: PromptTemplateBase,
        parameters: LLMParametersInput,
        num_questions: int | None = None,
    ) -> list[SuggestedQuestion]:
        """Generate suggested questions based on the provided texts.

        Args:
            texts: List of text chunks to generate questions from
            collection_id: Collection UUID
            user_id: User UUID
            provider_name: Name of LLM provider to use
            template: Prompt template for question generation
            parameters: LLM parameters to use
            num_questions: Optional number of questions to generate

        Returns:
            List of generated question models

        Raises:
            ValidationError: If parameters validation fails
            LLMProviderError: If provider errors occur
            QuestionGenerationError: If question generation fails
        """
        start_time = time.time()
        
        try:
            if not texts:
                return []

            # Setup generation components
            provider, combined_texts, generation_stats = self._setup_question_generation(
                texts, provider_name, template, parameters
            )

            # Generate questions from text chunks
            all_questions = await self._generate_questions_from_texts(
                combined_texts, provider, user_id, template, parameters, num_questions, generation_stats
            )

            if not all_questions:
                logger.warning("No valid questions were generated")
                return []

            # Process and finalize questions
            final_questions = self._process_generated_questions(all_questions, texts, num_questions)
            
            # Store questions in database
            stored_questions = await self._store_questions(collection_id, final_questions)

            logger.info(
                f"Generated {len(final_questions)} questions in {time.time() - start_time:.2f}s. "
                f"Stats: {generation_stats}"
            )
            return stored_questions

        except ValidationError:
            raise
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error suggesting questions: {e}")
            logger.exception(e)
            raise

    def _setup_question_generation(
        self, texts: list[str], provider_name: str, template: PromptTemplateBase, parameters: LLMParametersInput
    ) -> tuple[object, list[str], dict]:
        """Setup components for question generation."""
        logger.info(f"Using template: {template}")
        logger.info(f"Using parameters: {parameters}")
        
        # Get provider from factory
        provider = self._provider_factory.get_provider(provider_name)
        logger.debug(f"Provider: {provider}")
        
        # Combine texts respecting context length
        available_context_length = settings.max_context_length - settings.max_new_tokens
        combined_texts = self._combine_text_chunks(texts, available_context_length)
        
        generation_stats = {"total_chunks": len(texts), "successful_generations": 0, "failed_generations": 0}
        
        return provider, combined_texts, generation_stats

    async def _generate_questions_from_texts(
        self,
        combined_texts: list[str],
        provider: object,
        user_id: UUID4,
        template: PromptTemplateBase,
        parameters: LLMParametersInput,
        num_questions: int | None,
        stats: dict
    ) -> list[str]:
        """Generate questions from combined text chunks using LLM."""
        all_questions = []
        
        # Process in batches respecting concurrency limit
        for i in range(0, len(combined_texts), settings.llm_concurrency):
            batch = combined_texts[i : i + settings.llm_concurrency]
            
            try:
                # Generate questions for batch
                variables = {"num_questions": str(num_questions if num_questions else 3)}
                
                responses = provider.generate_text(
                    user_id=user_id,
                    prompt=batch,
                    model_parameters=parameters,
                    template=template,
                    variables=variables,
                )
                
                batch_questions = self._extract_questions_from_responses(responses)
                all_questions.extend(batch_questions)
                stats["successful_generations"] += 1
                
            except Exception as e:
                logger.error(f"Batch generation failed: {e!s}")
                logger.exception(e)
                stats["failed_generations"] += 1
                continue
        
        return all_questions

    def _extract_questions_from_responses(self, responses) -> list[str]:
        """Extract valid questions from LLM responses."""
        questions = []
        
        if isinstance(responses, list):
            for response in responses:
                response_questions = [q.strip() for q in response.split("\n") if q.strip().endswith("?")]
                questions.extend(response_questions)
        else:
            response_questions = [q.strip() for q in responses.split("\n") if q.strip().endswith("?")]
            questions.extend(response_questions)
            
        return questions

    def _process_generated_questions(self, all_questions: list[str], texts: list[str], num_questions: int | None) -> list[str]:
        """Process, filter, and rank generated questions."""
        # Filter valid questions
        valid_questions = [q for q in all_questions if self._validate_question(q, " ".join(texts))[0]]
        
        # Remove duplicates and rank
        unique_questions = self._filter_duplicate_questions(valid_questions)
        ranked_questions = self._rank_questions(questions=unique_questions, context=" ".join(texts))
        
        # Limit to requested number
        return ranked_questions[:num_questions] if num_questions else ranked_questions

    async def _store_questions(self, collection_id: UUID4, final_questions: list[str]) -> list[SuggestedQuestion]:
        """Store questions in the database."""
        if not final_questions:
            return []
            
        questions = [
            SuggestedQuestion(collection_id=collection_id, question=question) 
            for question in final_questions
        ]
        
        return await asyncio.to_thread(
            self.question_repository.create_questions, collection_id, questions
        )

    def create_question(self, question_input: QuestionInput) -> SuggestedQuestion:
        """
        Create a new question.

        Args:
            question_input: QuestionInput schema with question details

        Returns:
            SuggestedQuestion: Created question model

        Raises:
            ValidationError: If question validation fails
        """
        try:
            # Pass the QuestionInput directly to repository
            return self.question_repository.create_question(question_input)
        except Exception as e:
            logger.error(f"Error creating question: {e}")
            raise

    def delete_question(self, question_id: UUID4) -> None:
        """
        Delete a specific question.

        Args:
            question_id: The ID of the question to delete.

        Raises:
            NotFoundError: If the question does not exist.
        """
        try:
            self.question_repository.delete_question(question_id)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting question {question_id}: {e}")
            raise

    def delete_questions_by_collection(self, collection_id: UUID4) -> None:
        """
        Delete all questions for a specific collection.

        Args:
            collection_id: The ID of the collection.

        Raises:
            NotFoundError: If the collection does not exist.
        """
        try:
            self.question_repository.delete_questions_by_collection(collection_id)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting questions for collection {collection_id}: {e}")
            raise

    def get_collection_questions(self, collection_id: UUID4) -> list[SuggestedQuestion]:
        """
        Get stored questions for a collection.

        Args:
            collection_id: ID of the collection to get questions for

        Returns:
            List[SuggestedQuestion]: List of question models for the collection

        Raises:
            Exception: If there's an error retrieving questions
        """
        try:
            return self.question_repository.get_questions_by_collection(collection_id)
        except Exception as e:
            logger.error(f"Error retrieving questions for collection {collection_id}: {e}")
            raise

    async def regenerate_questions(
        self,
        collection_id: UUID4,
        user_id: UUID4,
        texts: list[str],
        provider_name: str,
        template: PromptTemplateBase,
        parameters: LLMParametersInput,
        num_questions: int | None = None,
    ) -> list[SuggestedQuestion]:
        """
        Force regeneration of questions for a collection.

        Args:
            collection_id: ID of the collection to regenerate questions for
            user_id: User UUID
            texts: List of text chunks to generate questions from
            provider_name: Name of LLM provider to use
            template: Prompt template for question generation
            parameters: LLM parameters to use
            num_questions: Optional number of questions to generate

        Returns:
            List[SuggestedQuestion]: List of newly generated question models

        Raises:
            ValidationError: If parameters validation fails
            LLMProviderError: If provider errors occur
            QuestionGenerationError: If question generation fails
        """
        try:
            # Delete existing questions
            self.question_repository.delete_questions_by_collection(collection_id)

            # Generate new questions
            return await self.suggest_questions(
                texts=texts,
                collection_id=collection_id,
                user_id=user_id,
                provider_name=provider_name,
                template=template,
                parameters=parameters,
                num_questions=num_questions,
            )
        except Exception as e:
            logger.error(f"Error regenerating questions for collection {collection_id}: {e}")
            raise
