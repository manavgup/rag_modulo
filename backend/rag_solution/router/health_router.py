import os

from fastapi import APIRouter, Depends, HTTPException
from ibm_watsonx_ai import APIClient, Credentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from core.logging_utils import get_logger
from rag_solution.file_management.database import get_db
from vectordbs.factory import get_datastore

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


def check_vectordb() -> dict[str, str]:
    """Check the health of the vector database."""
    try:
        get_datastore(settings.vector_db)
        return {"status": "healthy", "message": "Vector DB is connected and operational"}
    except Exception as e:
        logger.error(f"Vector DB health check failed: {e!s}")
        return {"status": "unhealthy", "message": f"Vector DB health check failed: {e!s}"}


def check_datastore(db: Session = Depends(get_db)) -> dict[str, str]:
    """Check the health of the relational database."""
    try:
        db.execute(text("Select 1"))
        return {"status": "healthy", "message": "Relational DB is connected and operational"}
    except Exception as e:
        logger.error(f"Relational DB health check failed: {e!s}")
        return {"status": "unhealthy", "message": f"Relational DB health check failed: {e!s}"}


def check_watsonx() -> dict[str, str]:
    """Check the health of the WatsonX service."""
    if not all([settings.wx_project_id, settings.wx_api_key, settings.wx_url]):
        logger.warning("WatsonX not configured - skipping health check")
        return {"status": "skipped", "message": "WatsonX not configured"}

    try:
        APIClient(
            project_id=settings.wx_project_id,
            credentials=Credentials(api_key=settings.wx_api_key, url=settings.wx_url),
        )
        return {"status": "healthy", "message": "WatsonX is connected and operational"}
    except Exception as e:
        logger.error(f"WatsonX health check failed: {e!s}")
        return {"status": "unhealthy", "message": f"WatsonX health check failed: {e!s}"}


def check_file_system() -> dict[str, str]:
    """Check the health of the file system."""
    try:
        upload_dir = settings.file_storage_path
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        test_file = os.path.join(upload_dir, "test_write.txt")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return {"status": "healthy", "message": "File system is accessible and writable"}
    except Exception as e:
        logger.error(f"File system health check failed: {e!s}")
        return {"status": "unhealthy", "message": f"File system health check failed: {e!s}"}


def check_system_health(components: dict[str, dict[str, str]]) -> bool:
    """
    Check if any critical component is unhealthy.

    Args:
        components: Dictionary of component health check results

    Returns:
        bool: True if system is healthy, False otherwise
    """
    for name, status in components.items():
        if status["status"] == "unhealthy":
            return False
    return True


@router.get(
    "/health",
    summary="Perform health check",
    description="Perform a health check on all system components",
    response_model=dict,
    responses={
        200: {"description": "Health check completed successfully"},
        503: {"description": "One or more components are unhealthy"},
    },
)
def health_check(db: Session = Depends(get_db)):
    """
    Perform a health check on all system components.

    Args:
        db: The database session.

    Returns:
        dict: Health check results for all components

    Raises:
        HTTPException: If any component is unhealthy
    """
    components = {
        "vectordb": check_vectordb(),
        "datastore": check_datastore(db),
        "watsonx": check_watsonx(),
        "file_system": check_file_system(),
    }

    is_healthy = check_system_health(components)

    if not is_healthy:
        unhealthy_components = [
            f"{name} ({status['message']})" for name, status in components.items() if status["status"] == "unhealthy"
        ]
        raise HTTPException(status_code=503, detail=f"System unhealthy. Components: {', '.join(unhealthy_components)}")

    return {"status": "healthy", "components": components}
