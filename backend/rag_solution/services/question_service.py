"""Service for handling question suggestion functionality."""

import logging
from typing import List, Dict, Any, Optional, Set
from uuid import UUID
import asyncio
import re
from sqlalchemy.orm import Session
import time

from rag_solution.repository.question_repository import QuestionRepository
from rag_solution.data_ingestion.chunking import get_chunking_method
from vectordbs.utils.watsonx import extract_entities
from core.config import settings
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.services.runtime_config_service import RuntimeConfigService

logger = logging.getLogger(__name__)


class QuestionService:
    """Service for managing question suggestions."""

    def __init__(self, db: Session, config: Optional[Dict[str, Any]] = None):
        """
        Initialize question service.

        Args:
            db: Database session
            config: Optional configuration override
        """
        self.db = db
        self.config = config or {}
        self.question_repository = QuestionRepository(db)

        # Load question-specific configuration
        self.num_questions = self.config.get('num_questions', settings.question_suggestion_num)
        self.min_length = self.config.get('min_length', settings.question_min_length)
        self.max_length = self.config.get('max_length', settings.question_max_length)
        self.question_types = self.config.get('question_types', settings.question_types)
        self.required_terms = self.config.get('required_terms', settings.question_required_terms)
        self.question_patterns = self.config.get('question_patterns', settings.question_patterns)

        # Initialize the LLM provider with configuration
        self.llm_factory = LLMProviderFactory(db)
        provider_type = self.config.get('provider', {}).get('type', 'watsonx')
        self.provider = self.llm_factory.get_provider(provider_type)

    def _validate_question(self, question: str, context: str) -> bool:
        """Validate that question is well-formed and relevant to context."""
        # Basic formatting checks
        question = question.strip()
        if not question or not question.endswith('?'):
            logger.debug(f"Question rejected - formatting: {question}")
            return False
            
        # Remove any numbering prefix
        question = re.sub(r'^\d+\.\s*', '', question)
        
        # Reject if it's meta-commentary or contains notes/answers
        meta_patterns = [
            r'note:', r'answer:', r'here are', r'the following',
            r'questions will be', r'let me help'
        ]
        if any(re.search(pattern, question.lower()) for pattern in meta_patterns):
            logger.debug(f"Question rejected - meta-commentary: {question}")
            return False

        # Content relevance check
        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        
        # Calculate overlap score
        relevance_score = len(question_words.intersection(context_words)) / len(question_words)
        min_relevance = 0.3  # At least 30% of question terms should appear in context
        
        if relevance_score < min_relevance:
            logger.debug(f"Question rejected - low relevance ({relevance_score}): {question}")
            return False
            
        # Avoid questions that are too generic or too specific
        if len(question_words) < 5 or len(question_words) > 25:
            logger.debug(f"Question rejected - length: {question}")
            return False

        return True 
    
    def _rank_questions(self, questions: List[str], context: str) -> List[str]:
        """Rank questions by relevance and quality."""
        entities = extract_entities(context)
        entity_set = set(entity['entity'] for entity in entities)
        
        scored_questions = []
        for question in questions:
            if self._validate_question(question, context):
                question_entities = extract_entities(question)
                question_entity_set = set(entity['entity'] for entity in question_entities)
                relevance_score = len(question_entity_set.intersection(entity_set)) / len(question_entity_set) if question_entity_set else 0
                scored_questions.append((question, relevance_score))
        
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        return [q[0] for q in scored_questions]

    def _generate_question_prompt(self, context: str, num_questions: int) -> str:
        return f"""
        Generate exactly {num_questions} specific questions based strictly on the following text. For each question, also list the entities relevant to the question.

        Requirements:
        - Questions MUST be directly answerable from the provided text.
        - Focus ONLY on information explicitly stated in the text.
        - DO NOT make assumptions or generate questions about topics not covered.
        - DO NOT include any meta-commentary or notes about the questions.
        - Each question should end with a question mark.

        Format the output as follows:
        Question 1?
        - Entity1
        - Entity2
        Question 2?
        - Entity3
        - Entity4
        ...

        Text:
        {context}

        Generate {num_questions} questions with their relevant entities:
        """


    def _generate_questions(self, context: str, num_questions: Optional[int] = None) -> List[str]:
        """
        Generate questions for context using the language model.

        Args:
            context: Document context
            num_questions: Number of questions to generate

        Returns:
            List[str]: Generated questions
        """
        num_questions = num_questions or self.num_questions
        prompt = self._generate_question_prompt(context, num_questions)

        try:
            response = self.provider.generate(query='', context=prompt, stop=['\n\n', 'Answer:', 'Question:'])

            # Split the response into lines
            lines = response.strip().split('\n')
            generated_questions = []
            entities_by_question = {}

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.endswith('?'):
                    question = line
                    entities = []
                    i += 1
                    while i < len(lines) and lines[i].startswith('- '):
                        entities.append(lines[i][2:].strip())
                        i += 1
                    generated_questions.append(question)
                    entities_by_question[question] = entities
                else:
                    i += 1

            logger.info(f"Generated questions with entities: {generated_questions}")

            # Validate and select the required number of questions
            valid_questions = []
            for question in generated_questions:
                if self._validate_question(question, context) and question not in valid_questions:
                    logger.info(f"Suggested question: {question}")
                    valid_questions.append(question)
                if len(valid_questions) >= num_questions:
                    break
            logger.info(f"Valid questions after validation: {valid_questions}")
            return valid_questions
        except Exception as e:
            logger.error(f"Error generating questions using LLM: {e}", exc_info=True)
            return []
    
    async def _generate_questions_async(self, chunk: str, num_questions: Optional[int]) -> List[str]:
        return await asyncio.to_thread(self._generate_questions, chunk, num_questions)
    
    def _filter_duplicate_questions(self, questions: List[str]) -> List[str]:
        """Remove duplicate questions using normalized comparison."""
        seen = set()
        unique_questions = []
        
        for question in questions:
            # Normalize question for comparison
            normalized = re.sub(r'\s+', ' ', question.lower().strip())
            if normalized not in seen:
                seen.add(normalized)
                unique_questions.append(question)
                
        return unique_questions
    
    def _combine_text_chunks(self, texts: List[str], available_context_length: int) -> List[str]:
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

    async def suggest_questions(self, texts: List[str], collection_id: UUID, num_questions: Optional[int] = None) -> List[str]:
        """
        Generate suggested questions based on the provided texts.

        Args:
            texts: List of text chunks to generate questions from
            collection_id: The ID of the collection
            num_questions: Optional number of questions to generate

        Returns:
            List[str]: List of generated questions
        """
        start_time = time.time()
        stats = {'total_chunks': len(texts), 'successful_generations': 0, 'failed_generations': 0}

        try:
            if not texts:
                return []

            # Combine texts respecting context length
            available_context_length = settings.max_context_length - settings.max_new_tokens
            combined_texts = self._combine_text_chunks(texts, available_context_length)
            
            all_questions = []
            batch_times = []
            
            for i in range(0, len(combined_texts), settings.llm_concurrency):
                batch = combined_texts[i:i + settings.llm_concurrency]
                prompts = [self._generate_question_prompt(text, num_questions or self.num_questions) for text in batch]
                
                try:
                    # Get runtime config for provider
                    runtime_config = RuntimeConfigService(self.db).get_runtime_config()
                    
                    # Generate text with all required parameters
                    responses = self.provider.generate_text(
                        prompts,
                        model_parameters=runtime_config.llm_parameters,
                        template=runtime_config.prompt_template
                    )
                    
                    if isinstance(responses, list):
                        for response in responses:
                            questions = [q.strip() for q in response.split('\n') if q.strip().endswith('?')]
                            filtered = [q for q in questions if self._validate_question(q, " ".join(texts))]
                            all_questions.extend(filtered)
                            stats['successful_generations'] += 1
              
                except Exception as e:
                    logger.error(f"Batch generation failed: {e}")
                    stats['failed_generations'] += 1

            unique_questions = self._filter_duplicate_questions(all_questions)
            ranked_questions = self._rank_questions(unique_questions, " ".join(texts))
            final_questions = ranked_questions[:num_questions] if num_questions else ranked_questions

            if final_questions:
                await asyncio.to_thread(self.store_questions, collection_id, final_questions)

            logger.info(f"Generated {len(final_questions)} questions in {time.time() - start_time:.2f}s")
            return final_questions

        except Exception as e:
            logger.error(f"Error suggesting questions: {e}")
            raise

    def get_collection_questions(self, collection_id: UUID) -> List[str]:
        """
        Get stored questions for a collection.

        Args:
            collection_id: The ID of the collection

        Returns:
            List[str]: List of suggested questions
        """
        try:
            questions = self.question_repository.get_questions_by_collection(collection_id)
            return [q.question for q in questions]
        except Exception as e:
            logger.error(f"Error retrieving questions for collection {collection_id}: {e}", exc_info=True)
            raise  # Re-raise the exception to notify the caller

    def store_questions(self, collection_id: UUID, questions: List[str]):
        """
        Store questions for a collection.

        Args:
            collection_id: The ID of the collection
            questions: List of questions to store
        """
        try:
            self.question_repository.create_questions(collection_id, questions)
            logger.info(f"Stored {len(questions)} questions for collection {collection_id}")
        except Exception as e:
            logger.error(f"Error storing questions: {e}", exc_info=True)
            raise  # Re-raise the exception to notify the caller

    def regenerate_questions(self, collection_id: UUID, texts: List[str], num_questions: Optional[int] = None) -> List[str]:
        """
        Force regeneration of questions for a collection.

        Args:
            collection_id: The ID of the collection
            texts: List of text chunks to generate questions from
            num_questions: Optional number of questions to generate

        Returns:
            List[str]: List of generated questions
        """
        try:
            # Delete existing questions
            self.question_repository.delete_questions_by_collection(collection_id)

            # Generate new questions
            questions = self.suggest_questions(texts, collection_id, num_questions)

            return questions
        except Exception as e:
            logger.error(f"Error regenerating questions for collection {collection_id}: {e}", exc_info=True)
            raise  # Re-raise the exception to notify the caller
