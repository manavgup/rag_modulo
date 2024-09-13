# Sprint 1: Project Setup

## Objectives
- Set up the development environment if it doesn't already exist
- Initialize the project structure, if not already initialized
- Install necessary dependencies, if not already installed
- Configure Docker containers, if not already configured

## Steps

1. Clone the project repository
   ```
   git clone [repository_url]
   cd rag_modulo
   ```

2. Set up environment variables
   ```
   cp env.example .env
   # Edit .env file with appropriate values
   ```

3. Install dependencies
   ```
   make init
   ```

4. Set up Docker environment
   - Ensure Docker and Docker Compose are installed on your system
   - Create volume directories:
     ```
     make create-volumes
     ```

5. Build Docker images
   ```
   make build-app
   ```

6. Start the development environment
   ```
   make dev
   ```

7. Verify the setup
   - Check if all containers are running:
     ```
     docker-compose ps
     ```
   - Access the backend API at http://localhost:8000
   - Access the frontend at http://localhost:3000

## Project Structure
```
.
├── backend/
│   ├── auth/
│   ├── core/
│   ├── rag_solution/
│   │   ├── config/
│   │   ├── data_ingestion/
│   │   ├── file_management/
│   │   ├── generation/
│   │   ├── models/
│   │   ├── pipeline/
│   │   ├── query_rewriting/
│   │   ├── repository/
│   │   ├── retrieval/
│   │   ├── router/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   └── vectordbs/
├── webui/
│   ├── public/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── config/
│       ├── contexts/
│       ├── pages/
│       ├── services/
│       └── styles/
├── Dockerfile.backend
├── docker-compose.yml
├── Makefile
├── main.py
└── requirements.txt
```

## Containerization
- Backend: Python 3.12 with FastAPI
- Frontend: React with IBM Carbon Design
- Database: PostgreSQL
- Vector Database: Milvus (with etcd and MinIO)

## Completion Criteria
- [ ] Project repository cloned and set up locally
- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] Docker images built successfully
- [ ] All containers running without errors
- [ ] Backend API accessible
- [ ] Frontend application accessible

## Next Steps
Proceed to 02_backendSetup.md for detailed backend implementation.