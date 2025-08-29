from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from rag_solution.schemas.file_schema import DocumentDelete, FileMetadata, FileOutput

# New Imports for LLMParameters and PromptTemplates
from rag_solution.schemas.question_schema import QuestionInput, QuestionOutput
from rag_solution.schemas.user_collection_schema import UserCollectionOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.user_collection_service import UserCollectionService

logger = get_logger("router.collections")

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.post(
    "",
    summary="Create a new collection",
    response_model=CollectionOutput,
    description="Create a new collection with the provided input data.",
    responses={
        200: {"description": "Collection created successfully"},
        400: {"description": "Business validation error"},
        404: {"description": "Collection not found"},
        422: {"description": "Request validation error"},
        500: {"description": "Internal server error"},
    },
)
def create_collection(collection_input: CollectionInput, db: Session = Depends(get_db)):
    """
    Create a new collection.

    Args:
        collection_input (CollectionInput): The input data for creating a collection.
        db (Session): The database session.

    Returns:
        CollectionOutput: The created collection.

    Raises:
        HTTPException: If validation fails, collection not found, or creation fails
    """
    try:
        service = CollectionService(db)
        return service.create_collection(collection_input)
    except ValidationError as e:
        logger.error(f"Validation error creating collection: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        logger.error(f"Not found error creating collection: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating collection: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/with-files",
    summary="Create a new collection with documents",
    response_model=CollectionOutput,
    description="Create a new collection and upload documents to it.",
    responses={
        200: {"description": "Collection created with documents successfully"},
        400: {"description": "Business validation error"},
        403: {"description": "Not authorized to access this resource"},
        404: {"description": "Collection not found"},
        422: {"description": "Request validation error"},
        500: {"description": "Internal server error"},
    },
)
async def create_collection_with_documents(
    request: Request,
    collection_name: str = Form(...),
    is_private: bool = Form(...),
    user_id: UUID = Form(...),
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """
    Create a new collection with documents.

    Args:
        request (Request): The FastAPI request object.
        collection_name (str): The name of the collection.
        is_private (bool): Whether the collection is private.
        user_id (uuid.UUID): The ID of the user creating the collection.
        files (List[UploadFile]): The list of files to be added to the collection.
        background_tasks (BackgroundTasks): Background tasks for processing.
        db (Session): The database session.

    Returns:
        CollectionOutput: The created collection with documents.

    Raises:
        HTTPException: If authorization fails, validation fails, or creation fails
    """
    # Check authorization
    if not hasattr(request.state, "user") or request.state.user["uuid"] != str(user_id):
        logger.error(f"Authorization failed for user {user_id}")
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")

    try:
        collection_service = CollectionService(db)
        collection = collection_service.create_collection_with_documents(
            collection_name, is_private, user_id, files, background_tasks
        )
        logger.info(f"Collection created successfully: {collection.id}")
        return collection
    except ValidationError as e:
        logger.error(f"Validation error creating collection with documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        logger.error(f"Not found error creating collection with documents: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating collection with documents: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{collection_id}",
    summary="Retrieve a collection by id.",
    response_model=CollectionOutput,
    description="Retrieve a collection by it's unique id.",
    responses={
        200: {"description": "Collection retrieved successfully"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
def get_collection(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve a collection by id.

    Args:
        collection_id (UUID): The ID of the collection to retrieve.
        db (Session): The database session.

    Returns:
        CollectionOutput: The retrieved collection.

    Raises:
        HTTPException: If collection not found
    """
    try:
        service = CollectionService(db)
        collection = service.get_collection(collection_id)
        return collection
    except HTTPException as e:
        # Propagate the HTTPException (e.g., 404 for not found)
        raise e
    except Exception as e:
        logger.error(f"Error getting collection: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{collection_id}/questions",
    summary="Create a question for a collection",
    response_model=QuestionOutput,
    description="Create a new question for the specified collection",
    responses={
        200: {"description": "Question created successfully"},
        400: {"description": "Business validation error"},
        422: {"description": "Request validation error"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
def create_collection_question(
    collection_id: UUID,
    question_input: QuestionInput = Body(..., description="Question input data"),
    db: Session = Depends(get_db),
) -> QuestionOutput:
    """Create a new question for a collection.

    Args:
        collection_id: ID of the collection
        question_input: Question input data
        db: Database session

    Returns:
        QuestionOutput: Created question

    Raises:
        HTTPException: If question creation fails
    """
    try:
        # Create question service instance
        question_service = QuestionService(db=db)
        # Ensure collection_id matches route parameter
        question_input.collection_id = collection_id
        result = question_service.create_question(question_input)
        return QuestionOutput.model_validate(result)
    except HTTPException as e:
        # Propagate the HTTPException (e.g., 404 for not found)
        raise e
    except Exception as e:
        logger.error(f"Error creating question for collection {collection_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{collection_id}/questions",
    summary="Get questions for a collection",
    response_model=list[QuestionOutput],
    description="Get all questions for the specified collection",
    responses={
        200: {"description": "Questions retrieved successfully"},
        404: {"description": "Collection not found"},
        422: {"description": "Invalid UUID format"},
        500: {"description": "Internal server error"},
    },
)
def get_collection_questions(collection_id: UUID, db: Session = Depends(get_db)) -> list[QuestionOutput]:
    """
    Get all questions for a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Returns:
        List[QuestionOutput]: List of questions in the collection.

    Raises:
        HTTPException: If collection not found or retrieval fails
    """
    try:
        question_service = QuestionService(db=db)
        questions = question_service.get_collection_questions(collection_id)
        return [QuestionOutput.model_validate(q) for q in questions]
    except NotFoundError as e:
        logger.error(f"Not found error getting questions: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting questions for collection {collection_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{collection_id}/questions/{question_id}",
    summary="Delete a specific question",
    description="Delete a specific question from a collection",
    responses={
        204: {"description": "Question deleted successfully"},
        404: {"description": "Question not found"},
        422: {"description": "Invalid UUID format"},
        500: {"description": "Internal server error"},
    },
)
def delete_collection_question(collection_id: UUID, question_id: UUID, db: Session = Depends(get_db)) -> None:
    """
    Delete a specific question from a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        question_id (UUID): The ID of the question.
        db (Session): The database session.

    Raises:
        HTTPException: If question not found or deletion fails
    """
    try:
        question_service = QuestionService(db=db)
        question_service.delete_question(question_id)
        return None
    except NotFoundError as e:
        logger.error(f"Not found error deleting question: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting question {question_id} from collection {collection_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{collection_id}/questions",
    summary="Delete all questions for a collection",
    description="Delete all questions associated with the specified collection",
    responses={
        204: {"description": "All questions deleted successfully"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_collection_questions(collection_id: UUID, db: Session = Depends(get_db)) -> None:
    """
    Delete all questions for a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Raises:
        HTTPException: If collection not found or deletion fails
    """
    try:
        question_service = QuestionService(db=db)
        question_service.delete_questions_by_collection(collection_id)
        return Response(status_code=204)
    except NotFoundError as e:
        logger.error(f"Not found error deleting questions: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting questions for collection {collection_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{collection_id}",
    summary="Delete a collection by id.",
    description="Delete a collection by it's unique id.",
    responses={
        204: {"description": "No content on successful collection deletion"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_collection(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a collection by id.

    Args:
        collection_id (UUID): The ID of the collection to delete.
        db (Session): The database session.

    Returns:
        bool: True if the collection was successfully deleted, False otherwise.

    Raises:
        HTTPException: If collection not found or deletion fails
    """
    try:
        service = CollectionService(db)
        service.delete_collection(collection_id)
    except NotFoundError as e:
        logger.error(f"Not found error deleting collection: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting collection: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{collection_id}/users",
    response_model=list[UserCollectionOutput],
    summary="Get collection users",
    description="Get all users associated with a collection",
    responses={
        200: {"description": "Successfully retrieved collection users"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
def get_collection_users(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Get all users associated with a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Returns:
        List[UserCollectionOutput]: List of users associated with the collection.

    Raises:
        HTTPException: If collection not found
    """
    try:
        service = UserCollectionService(db)
        return service.get_collection_users(collection_id)
    except NotFoundError as e:
        logger.error(f"Not found error getting collection users: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting collection users: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{collection_id}/users",
    summary="Remove all users from collection",
    description="Remove all users from a specific collection",
    responses={
        204: {"description": "No content in case all users successfully removed from collection"},
        404: {"description": "Collection not found"},
        500: {"description": "Internal server error"},
    },
)
def remove_all_users_from_collection(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Remove all users from a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Raises:
        HTTPException: If collection not found or removal fails
    """
    try:
        service = UserCollectionService(db)
        service.remove_all_users_from_collection(collection_id)
    except NotFoundError as e:
        logger.error(f"Not found error removing users from collection: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing users from collection: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{collection_id}/files",
    response_model=list[str],
    summary="Get collection files",
    description="Get a list of files in a specific collection for a user",
    responses={
        200: {"description": "Files retrieved successfully"},
        404: {"description": "User or collection not found"},
        500: {"description": "Internal server error"},
    },
)
def get_collection_files(collection_id: UUID, db: Session = Depends(get_db)):
    """
    Get a list of files in a specific collection.

    Args:
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Returns:
        List[str]: A list of filenames in the collection.

    Raises:
        HTTPException: If collection not found
    """
    try:
        service = FileManagementService(db)
        return service.get_files(collection_id)
    except NotFoundError as e:
        logger.error(f"Not found error getting collection files: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting collection files: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{collection_id}/files/{filename}",
    summary="Get file path",
    description="Get the file path for a specific file in a collection",
    responses={
        200: {"description": "File path retrieved successfully"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
def get_file_path(collection_id: UUID, filename: str, db: Session = Depends(get_db)):
    """
    Get the file path for a specific file in a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        filename (str): The name of the file.
        db (Session): The database session.

    Returns:
        dict: A dictionary containing the file path.

    Raises:
        HTTPException: If file not found
    """
    try:
        service = FileManagementService(db)
        file_path = service.get_file_path(collection_id, filename)
        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail="File not found")
        return {"file_path": str(file_path)}
    except NotFoundError as e:
        logger.error(f"Not found error getting file path: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting file path: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{collection_id}/files",
    summary="Delete files",
    description="Delete files from a collection",
    responses={
        204: {"description": "No content if files deleted successfully"},
        400: {"description": "Business validation error"},
        422: {"description": "Request validation error"},
        404: {"description": "Files not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_files(collection_id: UUID, doc_delete: DocumentDelete, db: Session = Depends(get_db)):
    """
    Delete files from a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        doc_delete (DocumentDelete): The document delete request containing list of filenames.
        db (Session): The database session.

    Raises:
        HTTPException: If files not found or deletion fails
    """
    try:
        service = FileManagementService(db)
        service.delete_files(collection_id, doc_delete.filenames)
    except ValidationError as e:
        logger.error(f"Validation error deleting files: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        logger.error(f"Not found error deleting files: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting files: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{collection_id}/files/{file_id}/metadata",
    response_model=FileOutput,
    summary="Update file metadata",
    description="Update the metadata of a specific file",
    responses={
        200: {"description": "File metadata updated successfully"},
        400: {"description": "Business validation error"},
        422: {"description": "Request validation error"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
def update_file_metadata(collection_id: UUID, file_id: UUID, metadata: FileMetadata, db: Session = Depends(get_db)):
    """
    Update metadata for a specific file.

    Args:
        collection_id (UUID): The ID of the collection.
        file_id (UUID): The ID of the file.
        metadata (FileMetadata): The new metadata.
        db (Session): The database session.

    Returns:
        FileOutput: The updated file metadata.

    Raises:
        HTTPException: If validation fails, file not found, or update fails
    """
    try:
        service = FileManagementService(db)
        return service.update_file_metadata(collection_id, file_id, metadata)
    except ValidationError as e:
        logger.error(f"Validation error updating file metadata: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        logger.error(f"Not found error updating file metadata: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating file metadata: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))
