"""Collection router for managing collection-related API endpoints."""

from typing import Annotated

from core.config import Settings, get_settings
from core.custom_exceptions import NotFoundError, ValidationError
from core.logging_utils import get_logger
from core.mock_auth import ensure_mock_user_exists
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import AlreadyExistsError
from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput
from rag_solution.schemas.file_schema import DocumentDelete, FileMetadata, FileOutput
from rag_solution.schemas.question_schema import QuestionInput, QuestionOutput
from rag_solution.schemas.user_collection_schema import UserCollectionOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.question_service import QuestionService
from rag_solution.services.user_collection_service import UserCollectionService

logger = get_logger("router.collections")

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.post("/debug-form-data")
async def debug_form_data(
    request: Request,
    collection_name: str = Form(...),
) -> dict:
    """Debug endpoint to test form data parsing without database dependency."""
    # Get user from authenticated JWT token
    current_user = request.state.user
    user_id = current_user.get("uuid")

    logger.debug("=== DEBUG FORM DATA ===")
    logger.debug("Collection name: %s", collection_name)
    logger.debug("User ID from JWT: %s", user_id)
    logger.debug("Request URL: %s", request.url)
    logger.debug("Request query params: %s", dict(request.query_params))
    logger.debug("=== END DEBUG FORM DATA ===")

    return {"collection_name": collection_name, "user_id": str(user_id), "query_params": dict(request.query_params)}


@router.post("/debug-form-data-with-db")
async def debug_form_data_with_db(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    collection_name: str = Form(...),
) -> dict:
    """Debug endpoint to test form data parsing WITH database dependency."""
    # Get user from authenticated JWT token
    current_user = request.state.user
    user_id = current_user.get("uuid")

    logger.info("=== DEBUG FORM DATA WITH DB ===")
    logger.info("Collection name: %s", collection_name)
    logger.info("User ID from JWT: %s", user_id)
    logger.info("Request URL: %s", request.url)
    logger.info("Request query params: %s", dict(request.query_params))
    logger.info("=== END DEBUG FORM DATA WITH DB ===")

    return {
        "collection_name": collection_name,
        "user_id": str(user_id),
        "query_params": dict(request.query_params),
        "db_connected": db is not None,
    }


# TEST ENDPOINT - Remove this after debugging
@router.get(
    "/test",
    summary="Test endpoint to list collections without auth",
    response_model=list[CollectionOutput],
)
async def test_list_collections(
    db: Annotated[Session, Depends(get_db)],
) -> list[CollectionOutput]:
    """Test endpoint to list collections without authentication."""
    try:
        # Use a mock user ID for testing

        settings = get_settings()
        mock_user_id = ensure_mock_user_exists(db, settings)

        user_collection_service = UserCollectionService(db)
        collections = user_collection_service.get_user_collections(mock_user_id)

        logger.info("TEST: Retrieved %d collections for mock user %s", len(collections), str(mock_user_id))
        return collections

    except Exception as e:
        logger.error("TEST: Error listing collections: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving collections: {e!s}") from e


@router.get(
    "",
    summary="List all collections for the authenticated user",
    response_model=list[CollectionOutput],
    description="Retrieve all collections accessible to the authenticated user.",
    responses={
        200: {"description": "Collections retrieved successfully"},
        500: {"description": "Internal server error"},
    },
)
async def list_collections(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> list[CollectionOutput]:
    """List all collections for the authenticated user."""
    try:
        # Get the current user from the authenticated request
        current_user = request.state.user
        user_id = current_user.get("uuid")

        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        user_collection_service = UserCollectionService(db)
        collections = user_collection_service.get_user_collections(user_id)

        logger.info("Retrieved %d collections for user %s", len(collections), user_id)
        return collections

    except Exception as e:
        logger.error("Error listing collections: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving collections: {e!s}") from e


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
def create_collection(
    request: Request,
    collection_input: CollectionInput,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CollectionOutput:
    """
    Create a new collection.

    Args:
        request: The request object containing authenticated user info
        collection_input (CollectionInput): The input data for creating a collection.
        db (Session): The database session.
        settings: Application settings

    Returns:
        CollectionOutput: The created collection.

    Raises:
        HTTPException: If validation fails, collection not found, or creation fails
    """
    try:
        # Get current user from authenticated request
        current_user = request.state.user
        user_id = current_user.get("uuid")

        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Add current user to the collection users list
        if not collection_input.users:
            collection_input.users = []

        # Ensure the creating user is always included
        if user_id not in collection_input.users:
            collection_input.users.append(user_id)

        service = CollectionService(db, settings)
        return service.create_collection(collection_input)
    except AlreadyExistsError as e:
        logger.error("Collection already exists: %s", str(e))
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValidationError as e:
        logger.error("Validation error creating collection: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotFoundError as e:
        logger.error("Not found error creating collection: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating collection: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
async def create_collection_with_documents(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    collection_name: str = Form(...),
    is_private: bool = Form(...),
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> CollectionOutput:
    """
    Create a new collection with documents.

    Args:
        request (Request): The HTTP request object containing user authentication.
        collection_name (str): The name of the collection.
        is_private (bool): Whether the collection is private.
        files (List[UploadFile]): The list of files to be added to the collection.
        background_tasks (BackgroundTasks): Background tasks for processing.
        db (Session): The database session.

    Returns:
        CollectionOutput: The created collection with documents.

    Raises:
        HTTPException: If validation fails or creation fails
    """
    # Verify authentication and authorization
    if not request or not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="Not authenticated")

    current_user = request.state.user
    user_id = current_user.get("uuid")

    logger.info("=== COLLECTION ROUTER DEBUG ===")
    logger.info("Creating collection with documents: %s", collection_name)
    logger.info("User ID from JWT: %s", user_id)
    logger.info("Files count: %d", len(files))
    logger.info("Is private: %s", is_private)
    logger.info("Request URL: %s", request.url)
    logger.info("Request query params: %s", dict(request.query_params))
    logger.info("Request headers: %s", dict(request.headers))
    logger.info("=== END COLLECTION ROUTER DEBUG ===")

    try:
        collection_service = CollectionService(db, settings)
        collection = collection_service.create_collection_with_documents(
            collection_name, is_private, user_id, files, background_tasks
        )
        logger.info("Collection created successfully: %s", str(collection.id))
        return collection
    except ValidationError as e:
        logger.error("Validation error creating collection with documents: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotFoundError as e:
        logger.error("Not found error creating collection with documents: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating collection with documents: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def get_collection(
    collection_id: UUID4, db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> CollectionOutput:
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
        service = CollectionService(db, settings)
        collection = service.get_collection(collection_id)
        return collection
    except HTTPException as e:
        # Propagate the HTTPException (e.g., 404 for not found)
        raise e
    except Exception as e:
        logger.error("Error getting collection: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


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
    collection_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    question_input: QuestionInput = Body(..., description="Question input data"),
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
        question_service = QuestionService(db=db, settings=settings)
        # Ensure collection_id matches route parameter
        question_input.collection_id = collection_id
        result = question_service.create_question(question_input)
        return QuestionOutput.model_validate(result)
    except HTTPException as e:
        # Propagate the HTTPException (e.g., 404 for not found)
        raise e
    except Exception as e:
        logger.error("Error creating question for collection %s: %s", str(collection_id), str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def get_collection_questions(
    collection_id: UUID4, db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> list[QuestionOutput]:
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
        question_service = QuestionService(db=db, settings=settings)
        questions = question_service.get_collection_questions(collection_id)
        return [QuestionOutput.model_validate(q) for q in questions]
    except NotFoundError as e:
        logger.error("Not found error getting questions: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting questions for collection %s: %s", str(collection_id), str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{collection_id}/files/{filename}/download",
    summary="Download a file",
    description="Download a specific file from a collection.",
    response_class=FileResponse,
    responses={
        200: {"description": "File downloaded successfully"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
def download_file(
    collection_id: UUID4,
    filename: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    """
    Download a specific file from a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        filename (str): The name of the file.
        db (Session): The database session.
        settings (Settings): The application settings.

    Returns:
        FileResponse: The file to be downloaded.

    Raises:
        HTTPException: If the file is not found.
    """
    try:
        service = FileManagementService(db, settings)
        file_path = service.get_file_path(collection_id, filename)

        if not file_path.exists():
            logger.error("File not found at path: %s", file_path)
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream",
        )
    except NotFoundError as e:
        logger.error("Not found error downloading file: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error downloading file: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def delete_collection_question(
    collection_id: UUID4,
    question_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
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
        question_service = QuestionService(db=db, settings=settings)
        question_service.delete_question(question_id)
        return None
    except NotFoundError as e:
        logger.error("Not found error deleting question: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error deleting question %s from collection %s: %s", str(question_id), str(collection_id), str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def delete_collection_questions(
    collection_id: UUID4, db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> Response:
    """
    Delete all questions for a collection.

    Args:
        collection_id (UUID): The ID of the collection.
        db (Session): The database session.

    Raises:
        HTTPException: If collection not found or deletion fails
    """
    try:
        question_service = QuestionService(db=db, settings=settings)
        question_service.delete_questions_by_collection(collection_id)
        return Response(status_code=204)
    except NotFoundError as e:
        logger.error("Not found error deleting questions: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error deleting questions for collection {collection_id}: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def delete_collection(
    collection_id: UUID4, db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> Response:
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
        service = CollectionService(db, settings)
        service.delete_collection(collection_id)
        return Response(status_code=204)
    except NotFoundError as e:
        logger.error("Not found error deleting collection: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error deleting collection: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def get_collection_users(collection_id: UUID4, db: Annotated[Session, Depends(get_db)]) -> list[UserCollectionOutput]:
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
        logger.error("Not found error getting collection users: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting collection users: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def remove_all_users_from_collection(collection_id: UUID4, db: Annotated[Session, Depends(get_db)]) -> Response:
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
        return Response(status_code=204)
    except NotFoundError as e:
        logger.error("Not found error removing users from collection: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error removing users from collection: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/{collection_id}/documents",
    summary="Upload documents to an existing collection",
    response_model=list[FileOutput],
    description="Upload one or more documents to an existing collection",
    responses={
        200: {"description": "Documents uploaded successfully"},
        400: {"description": "Business validation error"},
        403: {"description": "Not authorized to access this resource"},
        404: {"description": "Collection not found"},
        422: {"description": "Request validation error"},
        500: {"description": "Internal server error"},
    },
)
async def upload_documents_to_collection(
    request: Request,
    collection_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> list[FileOutput]:
    """
    Upload documents to an existing collection.

    Args:
        request (Request): The HTTP request object containing user authentication.
        collection_id (UUID4): The ID of the collection.
        files (List[UploadFile]): The list of files to be added to the collection.
        background_tasks (BackgroundTasks): Background tasks for processing.
        db (Session): The database session.
        settings (Settings): Application settings.

    Returns:
        List[FileOutput]: The uploaded file records.

    Raises:
        HTTPException: If validation fails or upload fails
    """
    # Verify authentication and authorization
    if not request or not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="Not authenticated")

    current_user = request.state.user
    user_id = current_user.get("uuid")

    logger.info("Uploading %d documents to collection %s by user %s", len(files), str(collection_id), str(user_id))

    try:
        collection_service = CollectionService(db, settings)

        # Verify collection exists
        collection = collection_service.get_collection(collection_id)

        # Use shared processing logic
        file_records = collection_service._upload_files_and_trigger_processing(
            files, user_id, collection_id, collection.vector_db_name, background_tasks
        )

        logger.info("Successfully uploaded %d documents to collection %s", len(file_records), str(collection_id))
        return file_records

    except ValidationError as e:
        logger.error("Validation error uploading documents: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotFoundError as e:
        logger.error("Not found error uploading documents: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error uploading documents to collection: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def get_collection_files(
    collection_id: UUID4, db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> list[str]:
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
        service = FileManagementService(db, settings)
        return service.get_files(collection_id)
    except NotFoundError as e:
        logger.error("Not found error getting collection files: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting collection files: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def get_file_path(
    collection_id: UUID4,
    filename: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
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
        service = FileManagementService(db, settings)
        file_path = service.get_file_path(collection_id, filename)
        if not file_path.exists():
            logger.error("File not found: %s", filename)
            raise HTTPException(status_code=404, detail="File not found")
        return {"file_path": str(file_path)}
    except NotFoundError as e:
        logger.error("Not found error getting file path: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting file path: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def delete_files(
    collection_id: UUID4,
    doc_delete: DocumentDelete,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
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
        service = FileManagementService(db, settings)
        service.delete_files(collection_id, doc_delete.filenames)
    except ValidationError as e:
        logger.error("Validation error deleting files: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotFoundError as e:
        logger.error("Not found error deleting files: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error deleting files: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


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
def update_file_metadata(
    collection_id: UUID4,
    file_id: UUID4,
    metadata: FileMetadata,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileOutput:
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
        service = FileManagementService(db, settings)
        return service.update_file_metadata(collection_id, file_id, metadata)
    except ValidationError as e:
        logger.error("Validation error updating file metadata: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotFoundError as e:
        logger.error("Not found error updating file metadata: %s", str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error updating file metadata: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cleanup-orphaned")
async def cleanup_orphaned_collections(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """
    Clean up orphaned collections from the vector database.

    This endpoint identifies collections that exist in the vector database (Milvus)
    but have no corresponding record in PostgreSQL, and removes them.

    Args:
        db (Session): The database session
        settings (Settings): Application settings

    Returns:
        dict: Summary of the cleanup operation with counts

    Raises:
        HTTPException: If cleanup operation fails
    """
    try:
        service = CollectionService(db, settings)
        summary = service.cleanup_orphaned_vector_collections()
        logger.info("Orphaned collection cleanup completed: %s", str(summary))
        return summary
    except Exception as e:
        logger.error("Error during orphaned collection cleanup: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e!s}") from e
