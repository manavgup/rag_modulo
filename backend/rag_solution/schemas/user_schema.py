from pydantic import BaseModel
from pydantic.types import EmailStr
from uuid import UUID
from datetime import datetime

class UserInDB(BaseModel):
    id: UUID
    ibm_id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class UserInput(BaseModel):
    ibm_id: str
    email: EmailStr
    name: str

class UserOutput(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
