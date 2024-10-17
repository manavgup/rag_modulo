from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from rag_solution.file_management.database import get_db
from rag_solution.schemas.assistant_schema import AssistantInput, AssistantOutput
from rag_solution.services.assistant_service import AssistantService

router = APIRouter(prefix="/api/assistants", tags=["assistants"])

# @router.post("/test_query", 
#     response_model=AssistantOutput,
#     summary="Test a query",
#     description="Test a query and get the response from the LLM",
#     responses={
#         200: {"description": "Query successfully tested"},
#         404: {"description": "Assistant not found"},
#         500: {"description": "Internal server error"}
#     }
# )
# def test_query(query: AssistantInput, db: Session = Depends(get_db)):
#     service = AssistantService(db)
#     return service.test_query(query)

# @router.post("/save_query", 
#     response_model=bool,
#     summary="Save a query",
#     description="Save a query to the database",
#     responses={
#         200: {"description": "Query successfully saved"},
#         404: {"description": "Assistant not found"},
#         500: {"description": "Internal server error"}
#     }
# )
# def save_query(query: AssistantInput, db: Session = Depends(get_db)):
#     service = AssistantService(db)
#     return service.save_query(query)

@router.get("/query-llm", 
    summary="Query a LLM. The result can  be used to create a new assistant",
    description="Query a LLM. The result can  be used to create a new assistant",
    responses={
        200: {"description": "Successfully queried LLM"},
        500: {"description": "Internal server error"}
    }
)
def query_llm(db: Session = Depends(get_db)):
    service = AssistantService(db)
    return service.query_llm()

@router.get("/", 
    response_model=List[AssistantOutput],
    summary="List all assistants",
    description="Retrieve a list of all assistants",
    responses={
        200: {"description": "Assistants retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
def list_assistants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = AssistantService(db)
    return service.list_assistants(skip, limit)


@router.post("/", 
    response_model=AssistantOutput,
    summary="Create a new assistant",
    description="Create a new assistant",
    responses={
        200: {"description": "Assistant created successfully"},
        500: {"description": "Internal server error"}
    }
)
def create_assistant(assistant: AssistantInput, db: Session = Depends(get_db)):
    service = AssistantService(db)
    return service.create_assistant(assistant)


# @router.get("/assistants/{user_id}", 
#     response_model=List[AssistantOutput],
#     summary="List all assistants owned by a specific user",
#     description="Retrieve a list of all assistants owned by a specific user",
#     responses={
#         200: {"description": "Assistants retrieved successfully"},
#         404: {"description": "User not found"},
#         500: {"description": "Internal server error"}
#     }
# )
# def list_user_assistants(user_id: UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     service = AssistantService(db)
#     return service.list_user_assistants(user_id, skip, limit)


