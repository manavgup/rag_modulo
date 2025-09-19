"""Service for handling question suggestion functionality with Chain of Thought support."""

import asyncio
import re
import time
from typing import Any

from core.config import Settings
from core.custom_exceptions import NotFoundError, ValidationError
from core.logging_utils import get_logger
from pydantic import UUID4
from sqlalchemy.orm import Session

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

    def __init__(self, db: Session, settings: Settings) -> None:
        """
        Initialize question service with Chain of Thought support.

        Args:
            db: Database session
            settings: Configuration settings (injected via dependency injection)

        Raises:
            ValidationError: If configuration is invalid
        """
        self.db = db
        self.settings = settings
        self._question_repository: QuestionRepository | None = None
        self._prompt_template_service: PromptTemplateService | None = None
        self._llm_parameters_service: LLMParametersService | None = None
        self._provider_factory = LLMProviderFactory(db)

        # Enhanced configuration for better question generation
        self.max_questions_per_collection = getattr(settings, "max_questions_per_collection", 15)
        self.max_chunks_to_process = getattr(
            settings, "max_chunks_for_questions", 8
        )  # Increased from 5 to 8 for better coverage
        self.cot_question_ratio = getattr(settings, "cot_question_ratio", 0.4)  # 40% CoT questions

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
            min_relevance = 0.3  # Stricter threshold for relevance
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

    def _select_representative_chunks(self, texts: list[str], max_chunks: int) -> list[str]:
        """
        Select representative chunks from across the document for better coverage.

        Uses a combination of:
        1. Stratified sampling (beginning, middle, end)
        2. Content diversity (different topics/sections)
        3. Length-based selection (prefer informative chunks)

        Args:
            texts: All available text chunks
            max_chunks: Maximum number of chunks to select

        Returns:
            List of selected text chunks with good document coverage
        """
        if len(texts) <= max_chunks:
            return texts

        selected_chunks = []

        # Strategy 1: Always include beginning and end for context
        if max_chunks >= 2:
            selected_chunks.append(texts[0])  # Beginning
            if len(texts) > 1:
                selected_chunks.append(texts[-1])  # End
            remaining_slots = max_chunks - 2
        else:
            # If we can only take 1 chunk, take the longest one
            longest_chunk = max(texts, key=len)
            return [longest_chunk]

        # Strategy 2: Stratified sampling from document sections
        if remaining_slots > 0:
            # Divide document into sections and sample from each
            section_size = len(texts) // (remaining_slots + 1)

            for i in range(remaining_slots):
                # Sample from each section, avoiding already selected chunks
                section_start = (i + 1) * section_size
                section_end = min((i + 2) * section_size, len(texts) - 1)

                if section_start < section_end:
                    # Within each section, prefer chunks with good length and content diversity
                    section_chunks = texts[section_start:section_end]

                    # Score chunks by length and keyword diversity
                    scored_chunks = []
                    for chunk in section_chunks:
                        if chunk not in selected_chunks:
                            # Simple scoring: length + unique words
                            words = set(chunk.lower().split())
                            score = len(chunk) * 0.1 + len(words) * 2.0
                            scored_chunks.append((score, chunk))

                    if scored_chunks:
                        # Select the highest scoring chunk from this section
                        scored_chunks.sort(reverse=True)
                        selected_chunks.append(scored_chunks[0][1])

        # Strategy 3: Fill remaining slots with highest-quality chunks
        while len(selected_chunks) < max_chunks and len(selected_chunks) < len(texts):
            remaining_texts = [t for t in texts if t not in selected_chunks]
            if not remaining_texts:
                break

            # Score remaining chunks for informativeness
            best_chunk = max(remaining_texts, key=lambda x: len(x) + len(set(x.lower().split())) * 2)
            selected_chunks.append(best_chunk)

        logger.info(f"Selected {len(selected_chunks)} representative chunks using stratified sampling strategy")
        return selected_chunks

    def _combine_text_chunks(self, texts: list[str], available_context_length: int) -> list[str]:
        """Combine text chunks while respecting context length limits and processing caps."""
        # IMPROVED: Intelligent chunk sampling for better document coverage
        limited_texts = self._select_representative_chunks(texts, self.max_chunks_to_process)

        if len(texts) > self.max_chunks_to_process:
            logger.info(
                f"Sampled {self.max_chunks_to_process} representative chunks from {len(texts)} total chunks for better document coverage"
            )

        combined_texts = []
        current_batch = []
        current_length = 0

        for text in limited_texts:
            # Truncate texts that are too long for the limit
            if len(text) > available_context_length:
                text = text[:available_context_length]

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
        force_regenerate: bool = False,
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
            force_regenerate: If True, delete existing questions and regenerate all

        Returns:
            List of generated question models

        Raises:
            ValidationError: If parameters validation fails
            LLMProviderError: If provider errors occur
            QuestionGenerationError: If question generation fails
        """
        start_time = time.time()

        try:
            # Handle force regenerate option
            if force_regenerate:
                logger.info(f"Force regenerate requested - deleting existing questions for collection {collection_id}")
                self.question_repository.delete_questions_by_collection(collection_id)

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
        if self.settings is None:
            raise ValueError("Settings must be provided to QuestionService")
        available_context_length = self.settings.max_context_length - self.settings.max_new_tokens
        combined_texts = self._combine_text_chunks(texts, available_context_length)

        generation_stats = {"total_chunks": len(texts), "successful_generations": 0, "failed_generations": 0}

        return provider, combined_texts, generation_stats

    async def _generate_questions_from_texts(
        self,
        combined_texts: list[str],
        provider: Any,
        user_id: UUID4,
        template: PromptTemplateBase,
        parameters: LLMParametersInput,
        num_questions: int | None,
        stats: dict,
    ) -> list[str]:
        """Generate both standard and Chain of Thought questions from combined text chunks."""
        all_questions = []
        target_questions = num_questions or self.max_questions_per_collection

        # Calculate how many questions to generate from each chunk
        questions_per_chunk = max(1, target_questions // len(combined_texts)) if combined_texts else 3

        logger.info(f"Generating {questions_per_chunk} questions per chunk from {len(combined_texts)} text chunks")

        # Process in batches respecting concurrency limit
        for i in range(0, len(combined_texts), self.settings.llm_concurrency):
            batch = combined_texts[i : i + self.settings.llm_concurrency]

            try:
                # Generate standard questions
                standard_variables = {"num_questions": str(questions_per_chunk)}

                responses = provider.generate_text(
                    user_id=user_id,
                    prompt=batch,
                    model_parameters=parameters,
                    template=template,
                    variables=standard_variables,
                )

                batch_questions = self._extract_questions_from_responses(responses)
                all_questions.extend(batch_questions)
                stats["successful_generations"] += 1

                # Early exit if we have enough questions
                if len(all_questions) >= target_questions * 2:  # Generate extra for filtering
                    logger.info(f"Generated sufficient questions ({len(all_questions)}), stopping early")
                    break

            except Exception as e:
                logger.error(f"Batch generation failed: {e!s}")
                logger.exception(e)
                stats["failed_generations"] += 1
                continue

        # Generate Chain of Thought questions if we have multiple text chunks
        if len(combined_texts) > 1 and len(all_questions) > 0:
            cot_questions = await self._generate_cot_questions(
                combined_texts, provider, user_id, template, parameters, target_questions, stats
            )
            all_questions.extend(cot_questions)

        return all_questions

    def _extract_questions_from_responses(self, responses: Any) -> list[str]:
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

    async def _generate_cot_questions(
        self,
        combined_texts: list[str],
        provider: Any,
        user_id: UUID4,
        template: PromptTemplateBase,
        parameters: LLMParametersInput,
        target_questions: int,
        stats: dict,
    ) -> list[str]:
        """Generate Chain of Thought questions that require multi-step reasoning."""
        if len(combined_texts) < 2:
            return []

        try:
            # Calculate how many CoT questions to generate
            cot_count = max(1, int(target_questions * self.cot_question_ratio))

            # Create a comprehensive context from multiple chunks for cross-document reasoning
            full_context = " ".join(combined_texts[:3])  # Use first 3 chunks for context

            # Define CoT question templates
            cot_templates = [
                "Generate {num_questions} complex questions that require comparing information across multiple sections of this document. These questions should need multi-step reasoning to answer fully.",
                "Create {num_questions} analytical questions that explore relationships, causes, and effects mentioned in this content. Focus on questions that require synthesis of multiple concepts.",
                "Develop {num_questions} strategic questions that require understanding trends, patterns, or changes described across different parts of this document.",
            ]

            cot_questions: list[str] = []

            for i, cot_template in enumerate(cot_templates):
                if len(cot_questions) >= cot_count:
                    break

                try:
                    # Format the CoT-specific template
                    cot_prompt = cot_template.format(num_questions=max(1, cot_count // len(cot_templates)))

                    # Use the full context as a single prompt with CoT instruction
                    variables = {"context": full_context, "instruction": cot_prompt}

                    # Generate CoT questions
                    response = provider.generate_text(
                        user_id=user_id,
                        prompt=[full_context],  # Single comprehensive context
                        model_parameters=parameters,
                        template=template,
                        variables=variables,
                    )

                    # Extract questions from response
                    response_text = (response[0] if response else "") if isinstance(response, list) else response

                    batch_cot_questions = [q.strip() for q in response_text.split("\n") if q.strip().endswith("?")]
                    cot_questions.extend(batch_cot_questions)

                    logger.info(f"Generated {len(batch_cot_questions)} CoT questions using template {i+1}")

                except Exception as e:
                    logger.warning(f"Failed to generate CoT questions with template {i+1}: {e}")
                    continue

            stats["cot_questions_generated"] = len(cot_questions)
            logger.info(f"Generated total {len(cot_questions)} Chain of Thought questions")
            return cot_questions

        except Exception as e:
            logger.error(f"Error generating CoT questions: {e}")
            return []

    def _process_generated_questions(
        self, all_questions: list[str], texts: list[str], num_questions: int | None
    ) -> list[str]:
        """Process, filter, and rank generated questions with global limits."""
        # CRITICAL FIX: Apply global limit early to prevent database bloat
        target_questions = num_questions or self.max_questions_per_collection

        # Filter valid questions
        valid_questions = [q for q in all_questions if self._validate_question(q, " ".join(texts))[0]]

        logger.info(f"Filtered {len(all_questions)} raw questions to {len(valid_questions)} valid questions")

        # Remove duplicates and rank
        unique_questions = self._filter_duplicate_questions(valid_questions)
        ranked_questions = self._rank_questions(questions=unique_questions, context=" ".join(texts))

        # Apply strict global limit
        final_questions = ranked_questions[:target_questions]

        logger.info(f"Final question set: {len(final_questions)} questions (target: {target_questions})")
        return final_questions

    async def _store_questions(self, collection_id: UUID4, final_questions: list[str]) -> list[SuggestedQuestion]:
        """
        Store questions in the database with intelligent management for existing collections.

        Handles:
        1. Question limit enforcement across existing + new questions
        2. Duplicate detection and removal
        3. Quality-based replacement when at capacity
        """
        if not final_questions:
            return []

        # Check existing questions for this collection
        existing_questions = self.get_collection_questions(collection_id)
        existing_question_texts = {q.question.strip().lower() for q in existing_questions}

        logger.info(f"Found {len(existing_questions)} existing questions for collection {collection_id}")

        # Filter out duplicates from new questions
        unique_new_questions = []
        for question in final_questions:
            normalized_question = question.strip().lower()
            if normalized_question not in existing_question_texts:
                unique_new_questions.append(question)
                existing_question_texts.add(normalized_question)  # Prevent internal duplicates too

        logger.info(f"Filtered {len(final_questions)} new questions to {len(unique_new_questions)} unique questions")

        if not unique_new_questions:
            logger.info("No new unique questions to add")
            return existing_questions

        # Calculate capacity for new questions
        current_count = len(existing_questions)
        available_slots = max(0, self.max_questions_per_collection - current_count)

        if available_slots == 0:
            logger.info(f"Collection at capacity ({current_count} questions). No new questions added.")
            return existing_questions

        # Limit new questions to available slots
        questions_to_add = unique_new_questions[:available_slots]

        if len(unique_new_questions) > available_slots:
            logger.info(f"Limited {len(unique_new_questions)} new questions to {len(questions_to_add)} due to capacity")

        # Create new question objects
        new_question_objects = [
            SuggestedQuestion(collection_id=collection_id, question=question) for question in questions_to_add
        ]

        # Store new questions
        stored_questions = await asyncio.to_thread(
            self.question_repository.create_questions, collection_id, new_question_objects
        )

        logger.info(
            f"Added {len(stored_questions)} new questions to collection {collection_id}. Total: {current_count + len(stored_questions)}"
        )

        return stored_questions

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
