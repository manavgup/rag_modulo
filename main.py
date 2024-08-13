import os
import sys

print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Contents of /app:", os.listdir('/app'))
print("Contents of /app/backend:", os.listdir('/app/backend'))

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.core.config import settings
    print("Successfully imported settings")
except ImportError as e:
    print(f"Error importing settings: {e}")
    raise

from backend.core.config import settings
from backend.rag_solution.router.collection_router import \
    router as collection_router
from backend.rag_solution.router.file_router import router as file_router
from backend.rag_solution.router.team_router import router as team_router
from backend.rag_solution.router.user_router import router as user_router

# Configure logging
logging.basicConfig(level=settings.log_level)

# Initialize FastAPI app
app = FastAPI(title="Vector Store API", description="API for interacting with the Vector Store")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(collection_router)
app.include_router(file_router)
app.include_router(team_router)
app.include_router(user_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
