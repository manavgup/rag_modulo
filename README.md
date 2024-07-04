# RAG Modulo

RAG Modulo is a Retrieval-Augmented Generation (RAG) solution that integrates various vector databases for efficient information retrieval and generation.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Contributing](#contributing)
- [License](#license)

## Features

- Support for multiple vector databases (Elasticsearch, Milvus, Pinecone, Weaviate, ChromaDB)
- Flexible document processing and chunking strategies
- Asynchronous API for efficient data ingestion and querying
- Customizable embedding models
- Comprehensive test suite
- CI/CD pipeline with GitHub Actions

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Poetry for dependency management

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/manavgup/rag-modulo.git
    cd rag-modulo
    ```
2. Install dependencies using Poetry:
    ```sh
    poetry install
    ```
3. Set up your environment variables by copying the `.env.example` file:
    ```sh
    cp .env.example .env
    ```
    Then, edit the `.env` file with your specific configuration.

## Usage

1. Start the required services:
    ```sh
    make run-services
    ```
2. Build and run the application:
    ```sh
    make run-app
    ```
3. Access the API at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Project Structure

```plaintext
rag_modulo/
├── rag_solution/        # Main application code
│   ├── data_ingestion/  # Data ingestion modules
│   ├── generation/      # Text generation modules
│   ├── pipeline/        # RAG pipeline
│   ├── query_rewriting/ # Query rewriting modules
│   └── retrieval/       # Data retrieval modules
├── tests/               # Test files
├── vectordbs/           # Vector database interfaces
├── webui/               # Frontend code
├── .env                 # Environment variables
├── docker-compose.yml   # Docker services configuration
├── Makefile             # Project management commands
├── poetry.lock          # Lock file for dependencies
├── pyproject.toml       # Project and dependency configuration
└── README.md            # Project documentation
```

## Configuration
Configuration is managed through environment variables. Key variables include:

- VECTOR_DB: Choose the vector database (elasticsearch, milvus, pinecone, weaviate, chroma)
- EMBEDDING_MODEL: Specify the embedding model to use
- DATA_DIR: Directory containing the data to be ingested

Refer to the .env.example file for a complete list of configuration options.

## Testing
Run the test suite using:
`make test`

## CI/CD
The project uses GitHub Actions for continuous integration and deployment. The pipeline includes:

- Code formatting
- Linting
- Running tests
- Security audit
- Building Docker containers

Refer to .github/workflows/ci.yml for the complete workflow.

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.