from uuid import UUID, uuid4
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import Depends, UploadFile, BackgroundTasks
from backend.rag_solution.services.file_management_service import FileManagementService, get_file_management_service
from backend.rag_solution.schemas.collection_schema import CollectionInput, CollectionInDB, CollectionOutput
from backend.rag_solution.repository.collection_repository import CollectionRepository
from backend.vectordbs.factory import get_datastore
from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.data_ingestion.ingestion import ingest_documents
import logging
from backend.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollectionService:
    def __init__(self, db: Session, file_management_service: FileManagementService):
        self.collection_repository = CollectionRepository(db)
        self.file_management_service = file_management_service
        self.vector_store = get_datastore(settings.vector_db)

    async def create_collection(self, collection: CollectionInput) -> CollectionInDB:
        """
        Create a new collection.

        Args:
            collection (CollectionInput): The collection data to create.

        Returns:
            CollectionInDB: The created collection.
        """
        try:
            collection_id = uuid4()
            await self.vector_store.create_collection_async(str(collection_id),
                                                            {"is_private": collection.is_private})
            return self.collection_repository.create(CollectionInput(
                id=collection_id,
                name=collection.name,
                is_private=collection.is_private,
                user_id=collection.user_id
            ))
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise

    def get_collection(self, collection_id: UUID) -> Optional[CollectionOutput]:
        """
        Get a collection by its ID.

        Args:
            collection_id (UUID): The ID of the collection to retrieve.

        Returns:
            Optional[CollectionOutput]: The collection if found, None otherwise.
        """
        return self.collection_repository.get_collection_output(collection_id)

    def update_collection(self, collection_id: UUID, collection_update: CollectionInput) -> Optional[CollectionInDB]:
        """
        Update an existing collection.

        Args:
            collection_id (UUID): The ID of the collection to update.
            collection_update (CollectionInput): The update data for the collection.

        Returns:
            Optional[CollectionInDB]: The updated collection if found, None otherwise.
        """
        return self.collection_repository.update(collection_id, collection_update.model_dump(exclude_unset=True))

    async def delete_collection(self, collection_id: UUID) -> bool:
        """
        Delete a collection by its ID.

        Args:
            collection_id (UUID): The ID of the collection to delete.

        Returns:
            bool: True if the collection was deleted, False otherwise.
        """
        try:
            await self.vector_store.delete_collection_async(str(collection_id))
            return self.collection_repository.delete(collection_id)
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise

    def get_user_collections(self, user_id: UUID) -> List[CollectionInDB]:
        """
        Get all collections belonging to a user.

        Args:
            user_id (UUID): The ID of the user.

        Returns:
            List[CollectionInDB]: The list of collections belonging to the user.
        """
        return self.collection_repository.get_user_collections(user_id)

    async def create_collection_with_documents(
        self,
        collection_name: str,
        is_private: bool,
        user_id: UUID,
        files: List[UploadFile],
        background_tasks: BackgroundTasks
    ) -> CollectionInDB:
        try:
            # 1. Create collection in vector store
            collection_id = uuid4()
            await self.vector_store.create_collection_async(str(collection_id), {"is_private": is_private})

            # 2. Create collection in database
            collection = await self.create_collection(CollectionInput(
                id=collection_id,
                name=collection_name,
                is_private=is_private,
                user_id=user_id
            ))

            # 3. Save files and create file records
            for file in files:
                file_path = await self.file_management_service.save_file(file, user_id, collection_id)
                await self.file_management_service.create_file_record(
                    collection_id=collection_id,
                    filename=file.filename,
                    filepath=str(file_path),
                    file_type=file.content_type
                )

            # 4. Schedule asynchronous document ingestion
            background_tasks.add_task(
                ingest_documents,
                [str(self.file_management_service.get_file_path(user_id, collection_id, file.filename)) for file in files],
                self.vector_store,
                str(collection_id)
            )

            return collection
        except Exception as e:
            logger.error(f"Error in create_collection_with_documents: {str(e)}")
            # Here you might want to add cleanup logic if something fails
            raise

def get_collection_service(
    db: Session = Depends(get_db),
    file_management_service: FileManagementService = Depends(get_file_management_service),
) -> CollectionService:
    return CollectionService(db, file_management_service)
