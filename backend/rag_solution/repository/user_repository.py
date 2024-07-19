from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from typing import List, Optional

from ..models.user import User
from ..schemas.user_schema import UserInDB, UserInput, UserOutput

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user: UserInput) -> UserInDB:
        try:
            db_user = User(**user.model_dump())
            self.session.add(db_user)
            self.session.commit()
            self.session.refresh(db_user)
            return UserInDB.model_validate(db_user)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def get(self, user_id: UUID) -> Optional[UserInDB]:
        user = self.session.query(User).filter(User.id == user_id).first()
        return UserInDB.model_validate(user) if user else None

    def get_by_ibm_id(self, ibm_id: str) -> Optional[UserInDB]:
        user = self.session.query(User).filter(User.ibm_id == ibm_id).first()
        return UserInDB.model_validate(user) if user else None

    def update(self, user_id: UUID, user_data: dict) -> Optional[UserInDB]:
        try:
            db_user = self.session.query(User).filter(User.id == user_id).first()
            if db_user:
                for key, value in user_data.items():
                    setattr(db_user, key, value)
                self.session.commit()
                self.session.refresh(db_user)
                return UserInDB.model_validate(db_user)
            return None
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def delete(self, user_id: UUID) -> bool:
        try:
            db_user = self.session.query(User).filter(User.id == user_id).first()
            if db_user:
                self.session.delete(db_user)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def list(self, skip: int = 0, limit: int = 100) -> List[UserInDB]:
        users = self.session.query(User).offset(skip).limit(limit).all()
        return [UserInDB.model_validate(user) for user in users]

    def get_user_output(self, user_id: UUID) -> Optional[UserOutput]:
        user = self.get(user_id)
        return UserOutput.model_validate(user) if user else None
