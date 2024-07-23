# backend/rag_solution/models/associations.py

from sqlalchemy import Table, Column, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from ..file_management.database import Base

user_team_association = Table('user_teams', Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('team_id', UUID(as_uuid=True), ForeignKey('teams.id'), primary_key=True),
    Column('joined_at', DateTime, default=datetime.now)
)

user_collection_association = Table('user_collections', Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('collection_id', UUID(as_uuid=True), ForeignKey('collections.id'), primary_key=True)
)