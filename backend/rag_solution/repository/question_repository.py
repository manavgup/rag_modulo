"""Repository for managing suggested questions."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from rag_solution.models.collection import Collection
from rag_solution.models.question import SuggestedQuestion
from rag_solution.schemas.question_schema import QuestionInDB, QuestionInput
from core.custom_exceptions import NotFoundException
from core.logging_utils import get_logger

logger = get_logger("repository.question")


class QuestionRepository:
    """Repository for managing suggested questions."""

    def __init__(self, session: Session):
        """
        Initialize question repository.

        Args:
            session: Database session
        """
        self.session = session

    def create_question(self, question_input: QuestionInput) -> SuggestedQuestion:
        """
        Create a new suggested question.

        Args:
            question_input: Question input data

        Returns:
            SuggestedQuestion: Created question model

        Raises:
            SQLAlchemyError: If there's a database error
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
            return db_question
        except SQLAlchemyError as e:
            logger.error(f"Error creating suggested question: {e}", exc_info=True)
            self.session.rollback()
            raise

    def create_questions(
        self, 
        collection_id: UUID, 
        questions: List[SuggestedQuestion]
    ) -> List[SuggestedQuestion]:
        """
        Create multiple suggested questions.

        Args:
            collection_id: ID of the collection
            questions: List of SuggestedQuestion instances

        Returns:
            List[SuggestedQuestion]: List of created questions

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            # Ensure all questions have the correct collection_id
            for question in questions:
                question.collection_id = collection_id
            
            self.session.add_all(questions)
            self.session.commit()
            for question in questions:
                self.session.refresh(question)
            
            logger.info(f"Created {len(questions)} questions for collection {collection_id}")
            return questions
        except SQLAlchemyError as e:
            logger.error(f"Error creating suggested questions: {e}", exc_info=True)
            self.session.rollback()
            raise

    def get_questions_by_collection(self, collection_id: UUID) -> List[SuggestedQuestion]:
        """
        Get all suggested questions for a collection.

        Args:
            collection_id: ID of the collection

        Returns:
            List[SuggestedQuestion]: List of questions

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            # Check if the collection exists
            exists = self.session.query(
                self.session.query(Collection)
                .filter(Collection.id == collection_id)
                .exists()
            ).scalar()
            if not exists:
                raise NotFoundException(
                    resource_type="Collection",
                    resource_id=collection_id,
                    message=f"Collection with ID {collection_id} not found."
                )

            # Fetch questions for the collection
            questions = self.session.query(SuggestedQuestion).filter(
                SuggestedQuestion.collection_id == collection_id
            ).order_by(SuggestedQuestion.id).all()
            
            logger.info(f"Retrieved {len(questions)} questions for collection {collection_id}")
            return questions
        except SQLAlchemyError as e:
            logger.error(f"Error getting questions for collection {collection_id}: {e}", exc_info=True)
            raise

    def delete_questions_by_collection(self, collection_id: UUID) -> int:
        """
        Delete all suggested questions for a collection.

        Args:
            collection_id: ID of the collection

        Returns:
            int: Number of questions deleted

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            count = self.session.query(SuggestedQuestion).filter(
                SuggestedQuestion.collection_id == collection_id
            ).delete()
            self.session.commit()
            logger.info(f"Deleted {count} questions for collection {collection_id}")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error deleting questions for collection {collection_id}: {e}", exc_info=True)
            self.session.rollback()
            raise

    def delete_question(self, question_id: UUID) -> bool:
        """
        Delete a specific suggested question.

        Args:
            question_id: ID of the question to delete

        Returns:
            bool: True if question was deleted, False if not found

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            question = self.session.query(SuggestedQuestion).filter(
                SuggestedQuestion.id == question_id
            ).first()
            if question:
                self.session.delete(question)
                self.session.commit()
                logger.info(f"Deleted question {question_id}")
                return True
            else:
                logger.warning(f"Question {question_id} not found for deletion")
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting question {question_id}: {e}", exc_info=True)
            self.session.rollback()
            raise
