import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.rag_solution.models.user import User
from backend.rag_solution.schemas.team_schema import TeamOutput
from backend.rag_solution.schemas.user_schema import UserInput, UserOutput

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: UserInput) -> UserOutput:
        try:
            db_user = User(
                ibm_id=user.ibm_id,
                email=user.email,
                name=user.name
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.flush()
            self.db.refresh(db_user)
            return self._user_to_output(db_user)
        except IntegrityError as e:
            self.db.rollback()
            if "ix_users_ibm_id" in str(e):
                raise ValueError("IBM ID already exists")
            elif "ix_users_email" in str(e):
                raise ValueError("Email already exists")
            else:
                raise ValueError("An error occurred while creating the user")

    def get_by_id(self, user_id: UUID) -> Optional[UserOutput]:
        try:
            user = self.db.query(User).filter(User.id == user_id).options(joinedload(User.teams)).first()
            return self._user_to_output(user) if user else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise

    def get_user_by_ibm_id(self, ibm_id: str) -> Optional[UserOutput]:
        try:
            user = self.db.query(User).filter(User.ibm_id == ibm_id).first()
            return self._user_to_output(user) if user else None
        except Exception as e:
            logger.error(f"Error getting user by IBM ID {ibm_id}: {str(e)}")
            raise

    def update(self, user_id: UUID, user_update: UserInput) -> Optional[UserInput]:
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in user_update.model_dump().items():
                    setattr(user, key, value)
                self.db.commit()
                self.db.refresh(user)
                return user_update
            return None
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            self.db.rollback()
            raise

    def delete(self, user_id: UUID) -> bool:
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                self.db.delete(user)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            self.db.rollback()
            raise

    def list_users(self, skip: int = 0, limit: int = 100) -> List[UserOutput]:
        try:
            users = self.db.query(User).offset(skip).limit(limit).all()
            return [self._user_to_output(user) for user in users]
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            raise

    @staticmethod
    def _user_to_output(user: User) -> UserOutput:
        return UserOutput(
            id=user.id,
            ibm_id=user.ibm_id,
            email=user.email,
            name=user.name,
            teams=[TeamOutput.model_validate(team) for team in user.teams],
            created_at=user.created_at,
            updated_at=user.updated_at
        )
