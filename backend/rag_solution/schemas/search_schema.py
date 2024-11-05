from uuid import UUID

from pydantic import BaseModel, ConfigDict

class SearchInput(BaseModel):
    question: str
    collection_id: UUID

class SearchOutput(BaseModel):
    generated_answer: str

    model_config = ConfigDict(from_attributes=True)