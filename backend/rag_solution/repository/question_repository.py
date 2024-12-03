"""Repository for managing suggested questions."""

import logging
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from rag_solution.models.question import SuggestedQuestion
from rag_solution.schemas.question_schema import QuestionInDB, QuestionInput

logger = logging.getLogger(__name__)


class QuestionRepository:
    """Repository for managing suggested questions."""

    def __init__(self, session: Session):
        """
        Initialize question repository.

        Args:
            session: Database session
        """
        self.session = session

    def create_question(self, question_input: QuestionInput) -> QuestionInDB:
        """
        Create a new suggested question.

        Args:
            question_input: Question input data

        Returns:
            QuestionInDB: Created question
        """
        try:
            db_question = SuggestedQuestion(
                collection_id=question_input.collection_id,
                question=question_input.question
            )
            self.session.add(db_question)
            self.session.commit()
            self.session.refresh(db_question)
            logger.info(f"Created question '{question_input.question}' for collection {question_input.collection_id}")
            return QuestionInDB.model_validate(db_question)
        except SQLAlchemyError as e:
            logger.error(f"Error creating suggested question: {e}", exc_info=True)
            self.session.rollback()
            raise

    def create_questions(self, collection_id: UUID, questions: List[str]) -> List[QuestionInDB]:
        """
        Create multiple suggested questions.

        Args:
            collection_id: ID of the collection
            questions: List of question texts

        Returns:
            List[QuestionInDB]: List of created questions
        """
        try:
            db_questions = [
                SuggestedQuestion(collection_id=collection_id, question=q)
                for q in questions
            ]
            self.session.add_all(db_questions)
            self.session.commit()
            for question in db_questions:
                self.session.refresh(question)
            
            logger.info(f"Created {len(questions)} questions for collection {collection_id}")
            return [QuestionInDB.model_validate(q) for q in db_questions]
        except SQLAlchemyError as e:
            logger.error(f"Error creating suggested questions: {e}", exc_info=True)
            self.session.rollback()
            raise

    def get_questions_by_collection(self, collection_id: UUID) -> List[QuestionInDB]:
        """
        Get all suggested questions for a collection.

        Args:
            collection_id: ID of the collection

        Returns:
            List[QuestionInDB]: List of questions
        """
        try:
            questions = self.session.query(SuggestedQuestion).filter(
                SuggestedQuestion.collection_id == collection_id
            ).all()
            
            logger.info(f"Retrieved {len(questions)} questions for collection {collection_id}")
            return [QuestionInDB.model_validate(q) for q in questions]
        except SQLAlchemyError as e:
            logger.error(f"Error getting questions for collection {collection_id}: {e}", exc_info=True)
            raise

    def delete_questions_by_collection(self, collection_id: UUID) -> None:
        """
        Delete all suggested questions for a collection.

        Args:
            collection_id: ID of the collection
        """
        try:
            self.session.query(SuggestedQuestion).filter(
                SuggestedQuestion.collection_id == collection_id
            ).delete()
            self.session.commit()
            logger.info(f"Deleted all questions for collection {collection_id}")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting questions for collection {collection_id}: {e}", exc_info=True)
            self.session.rollback()
            raise

    def delete_question(self, question_id: UUID) -> None:
        """
        Delete a specific suggested question.

        Args:
            question_id: ID of the question to delete
        """
        try:
            question = self.session.query(SuggestedQuestion).filter(
                SuggestedQuestion.id == question_id
            ).first()
            if question:
                self.session.delete(question)
                self.session.commit()
                logger.info(f"Deleted question {question_id}")
            else:
                logger.warning(f"Question {question_id} not found for deletion")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting question {question_id}: {e}", exc_info=True)
            self.session.rollback()
            raise
