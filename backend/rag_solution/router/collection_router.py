from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from backend.rag_solution.services.collection_service import CollectionService, get_collection_service
from backend.rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput

router = APIRouter(prefix="/collections", tags=["collections"])

@router.post("/", response_model=CollectionOutput)
async def create_collection(collection: CollectionInput,
                            collection_service: CollectionService = Depends(get_collection_service)):
    return await collection_service.create_collection(collection)

@router.get("/{collection_id}", response_model=CollectionOutput)
async def get_collection(collection_id: UUID,
                         collection_service: CollectionService = Depends(get_collection_service)):
    collection = collection_service.get_collection(collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection

@router.put("/{collection_id}", response_model=CollectionOutput)
async def update_collection(collection_id: UUID,
                            collection_update: CollectionInput,
                            collection_service: CollectionService = Depends(get_collection_service)):
    updated_collection = collection_service.update_collection(collection_id, collection_update)
    if updated_collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return updated_collection

@router.delete("/{collection_id}")
async def delete_collection(collection_id: UUID, collection_service: CollectionService = Depends(get_collection_service)):
    if not await collection_service.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Collection deleted successfully"}

@router.get("/user/{user_id}", response_model=List[CollectionOutput])
async def get_user_collections(user_id: UUID, collection_service: CollectionService = Depends(get_collection_service)):
    return collection_service.get_user_collections(user_id)
