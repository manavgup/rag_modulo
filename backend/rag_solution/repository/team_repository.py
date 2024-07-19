from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from typing import List, Optional

from ..models.team import Team, UserTeam
from ..models.user import User
from ..schemas.team_schema import TeamInDB, TeamInput, TeamOutput, UserTeamInDB, UserTeamOutput
from ..schemas.user_schema import UserOutput

class TeamRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, team: TeamInput) -> TeamInDB:
        try:
            db_team = Team(**team.model_dump())
            self.session.add(db_team)
            self.session.commit()
            self.session.refresh(db_team)
            return TeamInDB.model_validate(db_team)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def get(self, team_id: UUID) -> Optional[TeamInDB]:
        team = self.session.query(Team).filter(Team.id == team_id).first()
        return TeamInDB.model_validate(team) if team else None

    def update(self, team_id: UUID, team_data: dict) -> Optional[TeamInDB]:
        try:
            db_team = self.session.query(Team).filter(Team.id == team_id).first()
            if db_team:
                for key, value in team_data.items():
                    setattr(db_team, key, value)
                self.session.commit()
                self.session.refresh(db_team)
                return TeamInDB.model_validate(db_team)
            return None
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def delete(self, team_id: UUID) -> bool:
        try:
            db_team = self.session.query(Team).filter(Team.id == team_id).first()
            if db_team:
                self.session.delete(db_team)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def list(self, skip: int = 0, limit: int = 100) -> List[TeamInDB]:
        teams = self.session.query(Team).offset(skip).limit(limit).all()
        return [TeamInDB.model_validate(team) for team in teams]

    def add_user_to_team(self, user_id: UUID, team_id: UUID) -> UserTeamInDB:
        try:
            user_team = UserTeam(user_id=user_id, team_id=team_id)
            self.session.add(user_team)
            self.session.commit()
            self.session.refresh(user_team)
            return UserTeamInDB.model_validate(user_team)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def remove_user_from_team(self, user_id: UUID, team_id: UUID) -> bool:
        try:
            user_team = self.session.query(UserTeam).filter(
                UserTeam.user_id == user_id,
                UserTeam.team_id == team_id
            ).first()
            if user_team:
                self.session.delete(user_team)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e

    def get_team_users(self, team_id: UUID) -> List[UserTeamOutput]:
        user_teams = self.session.query(UserTeam).filter(UserTeam.team_id == team_id).all()
        return [UserTeamOutput.model_validate(ut) for ut in user_teams]

    def get_team_output(self, team_id: UUID) -> Optional[TeamOutput]:
        team = self.get(team_id)
        if not team:
            return None

        users = self.session.query(User).join(UserTeam).filter(UserTeam.team_id == team_id).all()
        user_outputs = [UserOutput.model_validate(user) for user in users]

        return TeamOutput(
            name=team.name,
            description=team.description,
            users=user_outputs
        )
