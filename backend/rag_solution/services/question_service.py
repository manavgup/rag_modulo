"""Service for handling question suggestion functionality."""

import logging
from typing import List, Dict, Any, Optional, Set
from uuid import UUID
import asyncio
import re
from sqlalchemy.orm import Session
import time
import json
from pprint import pformat

from rag_solution.repository.question_repository import QuestionRepository
from rag_solution.data_ingestion.chunking import get_chunking_method
from vectordbs.utils.watsonx import extract_entities
from core.config import settings
from rag_solution.generation.factories import GeneratorFactory

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
        self.config = config or {}
        self.question_repository = QuestionRepository(db)

        # Load configuration
        self.num_questions = self.config.get('num_questions', settings.question_suggestion_num)
        self.min_length = self.config.get('min_length', settings.question_min_length)
        self.max_length = self.config.get('max_length', settings.question_max_length)
        self.temperature = self.config.get('temperature', settings.question_temperature)
        self.question_types = self.config.get('question_types', settings.question_types)
        self.required_terms = self.config.get('required_terms', settings.question_required_terms)
        self.question_patterns = self.config.get('question_patterns', settings.question_patterns)

        # Initialize the generator
        generator_config = {
            'type': 'watsonx',
            'model_name': 'meta-llama/llama-3-1-8b-instruct',
            'default_params': {
                'max_new_tokens': 150,
                'temperature': 0.7
            }
        }
        self.generator = GeneratorFactory.create_generator(generator_config)

    def _validate_question(self, question: str, context: str) -> bool:
        """Validate that question is well-formed and relevant to context."""
        question_text = question['question'].strip()
        
        # Basic validation
        if not question_text or not question_text.endswith('?'):
            return False, 0.0

        # Remove numbering prefix
        question_text = re.sub(r'^\d+\.\s*', '', question_text)
        
        # Check for meta-commentary
        meta_patterns = [r'note:', r'answer:', r'here are', r'the following']
        if any(re.search(pattern, question_text.lower()) for pattern in meta_patterns):
            return False, 0.0

        # Content relevance using pre-extracted entities
        question_entities = set(e.lower() for e in question.get('entities', []))
        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        
        # Calculate relevance score using entities and word overlap
        entity_score = len(question_entities) / 10  # Normalize by assuming max 10 entities
        word_overlap = len(context_words.intersection(set(re.findall(r'\b\w+\b', question_text.lower())))) / len(question_text.split())
        
        relevance_score = (entity_score + word_overlap) / 2
        return relevance_score >= 0.3, relevance_score 
    
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
        Generate {num_questions} questions from this text with their relevant entities.
        Format your entire response as a JSON array like this, with no other text:
        [
            {{"question": "What is X?", "entities": ["Entity1", "Entity2"]}},
            {{"question": "How does Y work?", "entities": ["Entity3", "Entity4"]}}
        ]

        Text:
        {context}
        """

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into list of questions with entities"""
        try:
            # Clean the response - remove any non-JSON content
            response = response.strip()
            logger.info("--> validating llm response: %s\n", response)
            start = response.find('[')
            end = response.rfind(']') + 1
            if start == -1 or end == 0:
                logger.warning(f"No JSON array found in response: {response}")
                return []
                
            json_str = response[start:end]
            
            # Parse and validate
            questions = json.loads(json_str)
            if not isinstance(questions, list):
                logger.warning("Response not a JSON array")
                return []
                
            # Validate each question has required fields
            validated = []
            for q in questions:
                if isinstance(q, dict) and 'question' in q and 'entities' in q:
                    if not q['question'].endswith('?'):
                        q['question'] += '?'
                    validated.append(q)
                    
            return validated
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return []
       
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
        num_questions = num_questions or self.num_questions

        if not texts:
            return []

        # Combine texts respecting context length
        available_context_length = settings.max_context_length - settings.max_new_tokens
        combined_texts = self._combine_text_chunks(texts, available_context_length)
        
        all_questions = []
        
        # Process texts in batches
        for i in range(0, len(combined_texts), settings.llm_concurrency):
            batch = combined_texts[i:i + settings.llm_concurrency]
            prompts = [self._generate_question_prompt(text, num_questions) for text in batch]
            
            try:
                logger.debug("Generated prompts:\n%s", pformat(prompts))
                responses = self.generator.generate(prompts, context=None, concurrency_limit=settings.llm_concurrency)
                
                if isinstance(responses, list):
                    for response in responses:
                        questions = self._parse_llm_response(response)
                        for q in questions:
                            logger.info("*** Validating question: %s\n", q)
                            valid, score = self._validate_question(q, " ".join(texts))
                            if valid:
                                q['relevance_score'] = score
                                all_questions.append(q)
            except Exception as e:
                logger.error(f"Batch generation failed: {e}")

        # Sort by relevance score and deduplicate
        all_questions.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Deduplicate
        seen = set()
        unique_questions = []
        for q in all_questions:
            normalized = re.sub(r'\s+', ' ', q['question'].lower().strip())
            if normalized not in seen:
                seen.add(normalized)
                unique_questions.append(q['question'])

        final_questions = unique_questions[:num_questions] if num_questions else unique_questions

        if final_questions:
            await asyncio.to_thread(self.store_questions, collection_id, final_questions)

        logger.info(f"Generated {len(final_questions)} questions in {time.time() - start_time:.2f}s")
        return final_questions

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
