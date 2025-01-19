"""Service for handling question suggestion functionality."""

from typing import List, Dict, Any, Optional, Set
from uuid import UUID
import asyncio
import re
import time
from sqlalchemy.orm import Session

from rag_solution.models.question import SuggestedQuestion
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.repository.question_repository import QuestionRepository
from core.config import settings
from core.custom_exceptions import ValidationError, NotFoundError, NotFoundException
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.generation.providers.factory import LLMProviderFactory
from core.logging_utils import get_logger

logger = get_logger("services.question")


class QuestionService:
    """Service for managing question suggestions."""

    def __init__(self, db: Session, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize question service.

        Args:
            db: Database session

        Raises:
            ValidationError: If configuration is invalid
        """
        self.db = db
        self._question_repository: Optional[QuestionRepository] = None
        self._prompt_template_service: Optional[PromptTemplateService] = None
        self._llm_parameters_service: Optional[LLMParametersService] = None
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
        question = question.strip()
        if not question or not question.endswith('?'):
            return False, question
            
        # Remove any numbering prefix
        cleaned_question = re.sub(r'^\d+\.\s*', '', question)
        
        # Reduce minimum word requirement for short but valid questions
        question_words = set(re.findall(r'\b\w+\b', cleaned_question.lower()))
        if len(question_words) < 3:  # Changed from 5
            return False, cleaned_question
        
        # Reduce relevance threshold for short questions
        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        relevance_score = len(question_words.intersection(context_words)) / len(question_words)
        min_relevance = 0.2  # Reduced from 0.3
        
        return relevance_score >= min_relevance, cleaned_question
    
    def _rank_questions(self, questions: List[str], context: str, user_id: UUID, provider_name: str) -> List[str]:
        """
        Rank questions by relevance and quality.
        
        Args:
            questions: List of questions to rank
            context: Context text to rank against
            
        Returns:
            List[str]: Ranked list of questions
        """
        # Get provider from factory
        provider = self._provider_factory.get_provider(provider_name)
        scored_questions: List[tuple[str, float]] = []
        
        for question in questions:
            is_valid, cleaned_question = self._validate_question(question, context)
            if is_valid:
                # Calculate relevance based on word overlap instead of entities
                question_words = set(re.findall(r'\b\w+\b', cleaned_question.lower()))
                context_words = set(re.findall(r'\b\w+\b', context.lower()))
                
                # Calculate relevance score based on word overlap
                relevance_score = len(question_words.intersection(context_words)) / len(question_words)
                
                # Add complexity bonus for longer, more detailed questions
                complexity_bonus: float = min(len(question_words) * 0.05, 0.3)
                final_score: float = relevance_score + complexity_bonus
                
                scored_questions.append((cleaned_question, final_score))
        
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        return [q[0] for q in scored_questions]

    def _filter_duplicate_questions(self, questions: List[str]) -> List[str]:
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
            normalized = re.sub(r'^\d+\.\s*', '', normalized)  # Remove numbering
            normalized = re.sub(r'[^\w\s]', '', normalized)   # Remove all punctuation
            normalized = re.sub(r'\s+', ' ', normalized.strip())  # Normalize whitespace
            
            if normalized not in seen:
                seen.add(normalized)
                unique_questions.append(question)
                
        return unique_questions

    async def suggest_questions(
        self,
        texts: List[str],
        collection_id: UUID,
        user_id: UUID,
        provider_name: str,
        num_questions: Optional[int] = None
    ) -> List[SuggestedQuestion]:
        """
        Generate suggested questions based on the provided texts.

        Args:
            texts: List of text chunks to generate questions from
            collection_id: The ID of the collection
            num_questions: Optional number of questions to generate

        Returns:
            List[SuggestedQuestion]: List of generated question models

        Raises:
            ValidationError: If inputs are invalid
            NotFoundError: If required template not found
        """
        start_time = time.time()
        stats = {
            'total_chunks': len(texts),
            'successful_generations': 0,
            'failed_generations': 0
        }

        try:
            if not texts:
                return []

            # Get question generation template for the user
            template = self.prompt_template_service.get_by_type(
                PromptTemplateType.QUESTION_GENERATION,
                user_id
            )
            if not template:
                raise NotFoundException(
                    resource_type="PromptTemplate",
                    resource_id=f"type:{PromptTemplateType.QUESTION_GENERATION}",
                    message="Question generation template not found"
                )

            # Format context using template's strategy
            context_text = self.prompt_template_service.apply_context_strategy(
                template.id,
                texts
            )
            
            all_questions = []
            
            try:
                # Get parameters
                parameters = self.llm_parameters_service.get_user_default(user_id)
                if not parameters:
                    raise ValidationError("No default LLM parameters found")

                # Get provider from factory
                provider = self._provider_factory.get_provider(provider_name)
                logger.debug(f"Provider: {provider}")

                # Format prompt using template
                formatted_prompt = self.prompt_template_service.format_prompt(
                    template.id,
                    {
                        "context": context_text,
                        "num_questions": str(num_questions)
                    }
                )
                logger.debug(f"Formatted Prompt: {formatted_prompt}")

                # Generate questions
                response = provider.generate_text(
                    user_id=user_id,  # Temporary until GenerationService implementation
                    prompt=formatted_prompt,
                    model_parameters=parameters.to_input()
                )
                logger.debug(f"Generated Questions: {response}")
                
                if isinstance(response, list):
                    for r in response:
                        questions = [q.strip() for q in r.split('\n') if q.strip().endswith('?')]
                        filtered = [q for q in questions if self._validate_question(q, context_text)]
                        all_questions.extend(filtered)
                        stats['successful_generations'] += 1
                else:
                    questions = [q.strip() for q in response.split('\n') if q.strip().endswith('?')]
                    filtered = [q for q in questions if self._validate_question(q, context_text)]
                    all_questions.extend(filtered)
                    stats['successful_generations'] += 1

            except ValidationError as e:
                logger.error(f"Template validation error: {str(e)}")
                stats['failed_generations'] += 1
                raise
            except Exception as e:
                logger.error(f"Generation error: {str(e)}")
                stats['failed_generations'] += 1
                raise

            # Post-process questions
            unique_questions = self._filter_duplicate_questions(all_questions)
            ranked_questions = self._rank_questions(questions=unique_questions,
                                            context=context_text,
                                            user_id=user_id,
                                            provider_name=provider_name)
            final_questions = ranked_questions[:num_questions] if num_questions else ranked_questions

            # Create and store question models
            stored_questions: List[SuggestedQuestion] = []
            if final_questions:
                questions = [
                    SuggestedQuestion(
                        collection_id=collection_id,
                        question=question
                    )
                    for question in final_questions
                ]
                
                stored_questions = await asyncio.to_thread(
                    self.question_repository.create_questions,
                    collection_id,
                    questions
                )

            logger.info(
                f"Generated {len(final_questions)} questions in {time.time() - start_time:.2f}s. "
                f"Stats: {stats}"
            )
            return stored_questions

        except ValidationError:
            raise
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error suggesting questions: {e}")
            raise

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
    
    def delete_question(self, question_id: UUID) -> None:
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
    
    def delete_questions_by_collection(self, collection_id: UUID) -> None:
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


    def get_collection_questions(self, collection_id: UUID) -> List[SuggestedQuestion]:
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
        collection_id: UUID,
        user_id: UUID,
        texts: List[str],
        provider_name: str,
        num_questions: Optional[int] = None
    ) -> List[SuggestedQuestion]:
        """
        Force regeneration of questions for a collection.
        
        Args:
            collection_id: ID of the collection to regenerate questions for
            texts: List of text chunks to generate questions from
            num_questions: Optional number of questions to generate
            
        Returns:
            List[SuggestedQuestion]: List of newly generated question models
            
        Raises:
            Exception: If there's an error regenerating questions
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
                num_questions=num_questions
            )
        except Exception as e:
            logger.error(f"Error regenerating questions for collection {collection_id}: {e}")
            raise
