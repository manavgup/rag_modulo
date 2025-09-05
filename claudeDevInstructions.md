"# claudeDev_docs Project Setup Master Prompt

SOFTWARE TESTING:
The primary goal is to examine the current code base for this highly modular rag solution, review existing test cases, generate and execute tests including those for APIs. DO NOT OVERRIDE EXISTING FILES. BUILD ON WHAT ALREADY EXISTS.

## Project Details
Project Name: rag_modulo
Project Type: web (Web Application / Mobile App / Web and Mobile App)

Project Description: This project is a robust, customizable Retrieval-Augmented Generation (RAG) solution that supports a wide variety of vector databases, embedding models, and document formats. The solution is designed to be flexible and not dependent on popular RAG frameworks like LangChain or LlamaIndex, allowing for greater customization and control.

Key Features:
Modular Architecture: The project is divided into a backend (business logic) and frontend (user interface), each running in separate Docker containers for improved scalability and maintainability.
Multi-Database Support: The solution integrates with various vector databases, including Elasticsearch, Milvus, Pinecone, Weaviate, and ChromaDB, providing flexibility in choosing the most suitable database for specific use cases.
Flexible Document Processing: The system can handle multiple document formats, including PDF, Word documents, Excel spreadsheets, and plain text files, with dedicated processors for each type.
Customizable Embedding: The solution allows for the use of different embedding models, with the current implementation using IBM's WatsonX for generating embeddings.
Efficient Data Ingestion: The system includes a robust data ingestion pipeline that processes documents, chunks them appropriately, and stores them in the chosen vector database.
Advanced Querying Capabilities: The solution supports semantic search and filtering options across the stored documents.
Scalable Data Storage: Metadata is stored in a relational database (PostgreSQL) while embeddings are stored in the chosen vector database, allowing for efficient semantic search and traditional querying.
Repository Pattern: Database operations for the relational database are implemented using the repository pattern with a service layer, promoting clean architecture and separation of concerns.
Abstraction of Vector Databases: All vector database operations are encapsulated by a base VectorStore class, allowing for easy switching between different vector database implementations.
RESTful API: The backend exposes a RESTful API for communication with the frontend and potential integration with other services.Modern Frontend: The user interface is built using React and IBM Carbon Design, providing a sleek and responsive user experience.Containerization: The entire solution is containerized using Docker, ensuring consistency across different environments and easy deployment.
Configurable: The system uses environment variables and configuration files for easy customization of various parameters like chunk sizes, embedding dimensions, and database connection details.
Extensible: The modular design allows for easy addition of new features, document processors, or vector database integrations.
Comprehensive Error Handling: The solution includes custom exception classes and logging for robust error handling and debugging.Testing Suite: A comprehensive set of unit and integration tests is included to ensure reliability and ease of maintenance.
Asynchronous Processing: The system utilizes asynchronous programming techniques for improved performance in data processing and querying.

Technical Stack:
Backend: Python with FastAPI
Frontend: React with IBM Carbon Design.
Databases: PostgreSQL (relational),
Various vector databases (Elasticsearch, Milvus, Pinecone, Weaviate, ChromaDB)
Containerization: Docker and Docker Compose
Embedding: IBM WatsonX (customizable)
Document Processing: PyMuPDF, python-docx, openpyxl
Testing: pytestAPI: RESTful with FastAPI
This RAG solution provides a powerful, flexible, and customizable platform for building advanced information retrieval and generation systems. Its modular design and support for multiple databases and document formats make it suitable for a wide range of applications, from small-scale projects to large enterprise solutions.
User Types and Flows: User Types and Flows:
End User
Primary user of the RAG system for information retrieval
Flows:
a. Search and Query
Log in to the systemEnter a natural language query in the search barView search results with relevant document chunksClick on a result to see the full contextRefine search if necessary
b. Document Exploration
Browse available document collectionsSelect a collection to exploreView document summaries or metadataOpen and read full documents if needed
c. Feedback and Interaction
Rate search results for relevanceProvide feedback on answer qualitySave or bookmark useful results
Content Manager
Responsible for managing document collections and ensuring data quality
Flows:
a. Document Ingestion
Log in to the admin panelSelect ""Add New Documents""Choose document type (PDF, DOCX, TXT, XLSX)Upload documents individually or in bulkMonitor ingestion progressReview and confirm successful ingestion
b. Collection Management
Create new document collectionsEdit collection metadata and settingsOrganize documents within collectionsArchive or delete outdated collections
c. Data Quality Management
View ingestion error reportsManually correct or update document metadataRe-process documents with updated settings
System Administrator
Manages the overall system configuration and performance
Flows:
a. System Configuration
Access the admin configuration panelConfigure vector database settingsSet up or modify embedding model parametersAdjust chunking and processing settingsManage API keys and integrations
b. User Management
Create and manage user accountsAssign roles and permissionsMonitor user activity and system usage
c. Performance Monitoring
View system performance dashboardsMonitor query response timesCheck database health and storage usageReview and analyze system logs
API Developer
Integrates the RAG system with other applications or services
Flows:
a. API Exploration
Access the API documentationReview available endpoints and methodsGenerate API keys for testing
b. Integration Testing
Use provided SDKs or sample codeTest API calls for document ingestionPerform test queries and retrieve resultsValidate response formats and data
Data Analyst
Analyzes system usage and performance metrics
Flows:
a. Usage Analytics
Access the analytics dashboardView query patterns and popular searchesAnalyze user engagement metricsGenerate custom reports
b. Performance Analysis
Review query performance over timeAnalyze document retrieval accuracyIdentify areas for system optimizationGenerate recommendations for improvements

These user types and flows provide a comprehensive overview of the interactions within your RAG solution. When creating wireframes, consider designing interfaces that cater to each of these user types and their specific needs. Key areas to focus on in your wireframes include:
Main search interface for end usersResults display and refinement optionsDocument upload and collection management screensSystem configuration panels for administratorsAnalytics dashboards for data analysisAPI documentation and testing interface
Remember to incorporate the IBM Carbon Design principles in your wireframes to ensure a consistent and user-friendly interface across all parts of the application.
Design Preferences: Dark Theme

## Instructions for Claude Dev

You are tasked with setting up a project using the Claude Dev Design system. Follow these instructions carefully, asking for user feedback and clarification when necessary. Remember, you are using existing files and structures to accelerate the development process later.


### 1. Project Structure Setup

Begin by starting at the project root directory:

cd rag_modulo

Now, based on the project type (web), see the directory structure. Read the Makefile and docker-compose.yml to understand the project structure.

Once you understand the different containers that are created, start by examining the backend folder. Review the rag_solution directory for the modular RAG solution. Start by understanding the support for various vector databases in backend/vectordbs. Review test coverage in backend/tests.

.
├── Dockerfile.backend
├── Makefile
├── README.md
├── __init__.py
├── backend
│   ├── __init__.py
│   ├── auth
│   │   └── oidc.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── auth_middleware.py
│   │   ├── config.py
│   │   └── custom_exceptions.py
│   ├── rag_solution
│   │   ├── __init__.py
│   │   ├── config
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── data_ingestion
│   │   │   ├── __init__.py
│   │   │   ├── base_processor.py
│   │   │   ├── chunking.py
│   │   │   ├── document_processor.py
│   │   │   ├── excel_processor.py
│   │   │   ├── ingestion.py
│   │   │   ├── pdf_processor.py
│   │   │   ├── txt_processor.py
│   │   │   └── word_processor.py
│   │   ├── doc_utils.py
│   │   ├── file_management
│   │   │   ├── __init__.py
│   │   │   └── database.py
│   │   ├── generation
│   │   │   ├── __init__.py
│   │   │   └── generator.py
│   │   ├── models
│   │   │   ├── __init__.py
│   │   │   ├── collection.py
│   │   │   ├── file.py
│   │   │   ├── team.py
│   │   │   ├── user.py
│   │   │   ├── user_collection.py
│   │   │   └── user_team.py
│   │   ├── pipeline
│   │   │   ├── __init__.py
│   │   │   └── pipeline.py
│   │   ├── query_rewriting
│   │   │   ├── __init__.py
│   │   │   └── query_rewriter.py
│   │   ├── repository
│   │   │   ├── __init__.py
│   │   │   ├── collection_repository.py
│   │   │   ├── file_repository.py
│   │   │   ├── team_repository.py
│   │   │   ├── user_collection_repository.py
│   │   │   ├── user_repository.py
│   │   │   └── user_team_repository.py
│   │   ├── retrieval
│   │   │   ├── __init__.py
│   │   │   └── retriever.py
│   │   ├── router
│   │   │   ├── __init__.py
│   │   │   ├── auth_router.py
│   │   │   ├── collection_router.py
│   │   │   ├── file_router.py
│   │   │   ├── health_router.py
│   │   │   ├── team_router.py
│   │   │   ├── user_collection_router.py
│   │   │   ├── user_router.py
│   │   │   └── user_team_router.py
│   │   ├── schemas
│   │   │   ├── __init__.py
│   │   │   ├── collection_schema.py
│   │   │   ├── file_schema.py
│   │   │   ├── team_schema.py
│   │   │   ├── user_collection_schema.py
│   │   │   ├── user_schema.py
│   │   │   └── user_team_schema.py
│   │   └── services
│   │       ├── __init__.py
│   │       ├── collection_service.py
│   │       ├── file_management_service.py
│   │       ├── team_service.py
│   │       ├── user_collection_interaction_service.py
│   │       ├── user_collection_service.py
│   │       ├── user_service.py
│   │       └── user_team_service.py
│   ├── tests
│   │   ├── __init__.py
│   │   ├── chroma.py
│   │   ├── collection
│   │   │   ├── __init__.py
│   │   │   └── test_collection.py
│   │   ├── conftest.py
│   │   ├── data_ingestion
│   │   │   ├── __init__.py
│   │   │   ├── test_chunking.py
│   │   │   ├── test_document_processor.py
│   │   │   ├── test_excel_processor.py
│   │   │   ├── test_ingestion.py
│   │   │   ├── test_pdf_processor.py
│   │   │   ├── test_txt_processor.py
│   │   │   └── test_word_processor.py
│   │   ├── file
│   │   │   ├── __init__.py
│   │   │   └── test_file.py
│   │   ├── generator
│   │   │   └── test_generator.py
│   │   ├── pipeline
│   │   │   └── test_pipeline.py
│   │   ├── query_rewriting
│   │   │   └── test_query_rewriter.py
│   │   ├── retrieval
│   │   │   └── test_retriever.py
│   │   ├── router
│   │   │   ├── __init__.py
│   │   │   └── test_router.py
│   │   ├── team
│   │   │   ├── __init__.py
│   │   │   └── test_team.py
│   │   ├── test_files
│   │   │   ├── __init__.py
│   │   │   └── extracted_images
│   │   │       └── __init__.py
│   │   ├── test_postgresql_connection.py
│   │   ├── user
│   │   │   ├── __init__.py
│   │   │   └── test_user.py
│   │   ├── user_collection
│   │   │   ├── __init__.py
│   │   │   └── test_user_collection.py
│   │   ├── user_team
│   │   │   ├── __init__.py
│   │   │   └── test_user_team.py
│   │   └── vectordbs
│   │       ├── __init__.py
│   │       ├── test_base_store.py
│   │       ├── test_chromadb_store.py
│   │       ├── test_elasticsearch_store.py
│   │       ├── test_milvus_store.py
│   │       ├── test_models.py
│   │       ├── test_pinecone_store.py
│   │       ├── test_vector_store.py
│   │       └── test_weaviate_store.py
│   └── vectordbs
│       ├── __init__.py
│       ├── chroma_store.py
│       ├── data_types.py
│       ├── elasticsearch_store.py
│       ├── error_types.py
│       ├── factory.py
│       ├── milvus_store.py
│       ├── pinecone_store.py
│       ├── py.typed
│       ├── schemas
│       │   ├── __init__.py
│       │   └── weaviate_schema.json
│       ├── setup.py
│       ├── utils
│       │   ├── __init__.py
│       │   └── watsonx.py
│       ├── vector_store.py
│       └── weaviate_store.py
├── chroma
│   ├── __init__.py
│   └── chroma.sqlite3
├── chroma.log
├── constraints.txt
├── docker-compose.yml
├── embedEtcd.yaml
├── embedding.py
├── env.example
├── error_handling.py
├── hello_milvus.py
├── http_ca.crt
├── init-db.sh
├── main.py
├── milvus.log
├── package-lock.json
├── poetry.lock
├── pyproject.toml
├── pytest.ini
├── requirements-all.txt
├── requirements-dev.txt
├── requirements.in
├── requirements.txt
├── requirements_backend.txt
├── requirements_combined.txt
├── requirements_tests.txt
├── requirements_webui.txt
├── run_tests.sh
├── simple.py
├── standalone_embed.sh
├── volumes
│   ├── etcd
│   ├── milvus
│   ├── minio
│   └── postgres
├── webui
│   ├── Dockerfile.frontend
│   ├── README.md
│   ├── __init__.py
│   ├── build
│   │   ├── __init__.py
│   │   ├── asset-manifest.json
│   │   ├── favicon.ico
│   │   ├── index.html
│   │   ├── logo192.png
│   │   ├── logo512.png
│   │   ├── manifest.json
│   │   ├── robots.txt
│   │   └── static
│   │       ├── css
│   │       │   ├── main.3fd646a2.css
│   │       │   └── main.3fd646a2.css.map
│   │       └── js
│   │           ├── main.dcbc7e74.js
│   │           ├── main.dcbc7e74.js.LICENSE.txt
│   │           └── main.dcbc7e74.js.map
│   ├── default.conf
│   ├── package-lock.json
│   ├── package.json
│   ├── public
│   │   ├── __init__.py
│   │   ├── favicon.ico
│   │   ├── index.html
│   │   ├── logo192.png
│   │   ├── logo512.png
│   │   ├── manifest.json
│   │   └── robots.txt
│   └── src
│       ├── App.css
│       ├── App.js
│       ├── App.test.js
│       ├── __init__.py
│       ├── api
│       │   ├── __init__.py
│       │   └── api.js
│       ├── components
│       │   ├── Auth.js
│       │   ├── CollectionForm.js
│       │   ├── Dashboard.js
│       │   ├── DashboardSettings.js
│       │   ├── ErrorBoundary.js
│       │   ├── Header.js
│       │   ├── IngestionSettings.js
│       │   ├── NavigationBar.js
│       │   ├── QueryInput.js
│       │   ├── ResultsDisplay.js
│       │   ├── SideNav.js
│       │   ├── SignIn.js
│       │   └── __init__.py
│       ├── config
│       │   └── config.js
│       ├── contexts
│       │   └── AuthContext.js
│       ├── css
│       │   ├── __init__.py
│       │   └── common.css
│       ├── index.css
│       ├── index.js
│       ├── logo.svg
│       ├── pages
│       │   ├── HomePage.css
│       │   ├── HomePage.js
│       │   └── __init__.py
│       ├── reportWebVitals.js
│       ├── services
│       │   └── authService.js
│       ├── setupTests.js
│       └── styles
│           ├── __init__.py
│           └── carbon-overrides.scss
└── workspace

1.2. Create the following files in the claudeDev_docs directory:
- designDocumentSummary.md
- wireframes.csv
- claudeDevInstructions.md
- devNotes.md

1.3. Create the sprintDocs folder in claudeDev_docs and add the following files:
- 01_projectSetup.md
- 02_backendSetup.md
- 03_frontendStructure.md
- 04_coreFunctionality.md
- 05_dataIntegration.md
- 06_refinementAndPolish.md
- 07_deploymentPreparation.md

1.4. After creating each file or directory, ask the user for feedback and confirmation before proceeding.

### 2. Technology Stack Definition

2.1. Based on the project type and requirements, define a suitable technology stack. Consider the following options:

[Keep the existing technology stack options]

2.2. Present these recommendations to the user and ask for approval or adjustments.

2.3. After user approval, use this defined tech stack when creating the sprint documents.

### 3. File Content Creation

3.1. Generate content for each file based on the project details provided:

- currentTask.md: Use the following template:

""# Current Task

## Project: {project_name}

### Current Stage: [e.g., Frontend Development]

### Current Task: [Specific task description]

### Current Step: [Specific step within the current task]

### Last Completed Task: [Description of the last completed task]

### Next Steps:
1. [Next immediate step]
2. [Following step]
3. [Further step]

### User Feedback: [Any feedback from the last iteration]

### Notes: [Any relevant notes or considerations]

### Completion Checklist:
- [ ] Feature implementation complete
- [ ] Error handling implemented
- [ ] Tests passed
- [ ] User feedback addressed
- [ ] Code reviewed and refactored if necessary

### Opening Message for Next Session: [To be filled by Claude Dev at the end of each session]
""

- designDocumentSummary.md: Summarize the project based on the information provided.

- wireframes.csv: Create a CSV structure with columns for User Type, Screen, Layout, Interactions, Navigation, and Key Features. If the user hasn't provided wireframe information, infer the necessary screens and their details. After creating this file, present it to the user for review and ask for any necessary changes or additions. Emphasize to Claude Dev in the instructions that wireframes.csv should be used as the primary source of truth for UI implementation and should be referenced frequently throughout the development process.

3.2. FOR ALL SPRINT DOCS, create detailed content for each phase of development, tailored to the specific project requirements. Create explicit, numbered to-do items within each sprint document for clarity and easier tracking of progress. THIS STEP IS CRUCIAL AND MUST NOT BE SKIPPED. COMPLETE THE CONTENT FOR EVERY SPRINT DOCUMENT BEFORE FINISHING THE SETUP TASK.

- Clear objectives
- Detailed steps for implementation
- Code snippets or pseudocode where applicable
- Guidance on using the chosen UI component library
- Instructions for updating and using the theme file
- Completion criteria
- Next steps
- Next Steps section that explicitly mentions the next sprint document (e.g., 'Proceed to 02_frontendStructure.md')
- References to wireframes when creating routing or screens
- Identify the highest priority features and low priority features

Ensure that each sprint document includes a clear 'Completion Criteria' section. Claude Dev should not move to the next document until all criteria in the current document are met.

3.3. After creating the content for each file, present it to the user for review and ask for any necessary changes or additions.

3.4. Create a devNotes.md file in the claudeDev_docs directory with the following template:

```markdown
# Development Notes

This document tracks important development practices, solutions to common problems, and error handling for the project.

## Development Practices
[Document key development practices and patterns used in the project]

## Common Solutions
[Document solutions to frequently encountered issues]

## Error Handling

### Error Template

#### Error Description
[Describe the error message and context]

#### Solution
[Explain how the error was resolved]

#### Prevention
[Steps to prevent this error in the future]

---

[Development notes, solutions, and errors will be logged below this line]

### 4. Technology Stack and UI Components

4.1. Based on the project type and requirements, define a specific technology stack by choosing one option from each category. Create a techStack.md file in the claudeDev_docs directory to document these choices.

For Web Application:
- Frontend:
  * React with Create React App (recommended for simplicity and quick setup)
  * Next.js (choose if server-side rendering or advanced routing is required)
- UI Components:
  * Material-UI (recommended for comprehensive, well-documented components)
  * Chakra UI (choose if a more lightweight, accessible library is preferred)
- State Management:
  * React Context API (recommended for simpler state management needs)
  * Redux Toolkit (choose if complex state management is anticipated)
- Backend:
  * Node.js with Express (recommended for JavaScript consistency)
  * Firebase (choose if rapid development and built-in auth are priorities)
- Database:
  * MongoDB (recommended for flexible schema and rapid prototyping)
  * PostgreSQL (choose if structured data and complex queries are needed)

For Mobile App:
- Framework:
  * React Native with Expo (recommended for easiest setup and deployment)
- UI Components:
  * React Native Paper (recommended for Material Design consistency)
- State Management:
  * React Context API (recommended for simpler state management needs)
  * Redux Toolkit (choose if complex state management is anticipated)
- Backend:
  * Node.js with Express (recommended for JavaScript consistency)
  * Firebase (choose if rapid development and real-time features are needed)
- Database:
  * MongoDB (recommended for flexible schema and rapid prototyping)
  * PostgreSQL (choose if structured data and complex queries are needed)
- Deployment Options:
  * Web: Netlify or Vercel (for React/Next.js apps)
  * Mobile: Expo (for React Native apps)
  * Backend: Heroku (for Node.js/Express)

Choose the deployment option that best fits the project's tech stack for quick MVP deployment.


For Web and Mobile App (Monorepo):
- Web: Choose from Web Application options
- Mobile: Choose from Mobile App options
- Shared: JavaScript for shared code

After making these decisions, create a techStack.md file in the claudeDev_docs directory with the following structure:

```markdown
# Technology Stack

## Frontend
- Framework: [Chosen frontend framework]
- UI Components: [Chosen UI component library]
- State Management: [Chosen state management solution]

## Backend
- Server: [Chosen backend framework]
- Database: [Chosen database]

## Additional Tools
- [Any other relevant tools or libraries]

Rationale: [Brief explanation of why these choices were made based on the project requirements]

4.2. Recommend creating a theme file (e.g., `theme.js` or `theme.ts`) in the project root or a dedicated `styles` folder. This file should define:

- Color palette
- Typography styles
- Spacing scale
- Breakpoints
- Any other global style variables

4.3. Present these recommendations to the user and ask for approval or adjustments.

4.4 Dependency Installation

Include specific instructions in 01_projectSetup.md for installing dependencies. This should cover:
- Installing dependencies for the web project
- Installing dependencies for the mobile project
- Installing any shared dependencies
- Verifying successful installation and resolving any conflicts or vulnerabilities

Emphasize the importance of double-checking that all required dependencies are correctly installed before proceeding with development tasks.

### 5. Wireframe Creation Process

5.1. If the user hasn't provided wireframes:
- Use the information in wireframes.csv to create detailed Galileo prompts for each screen.
- Present these prompts to the user for approval or modification.
- Instruct the user to use these prompts with Galileo to generate wireframe images.
- Ask the user to place the generated images in the claudeDev_docs/wireframes directory.

5.2. If the user has provided wireframes:
- Review the wireframes and update wireframes.csv if necessary.
- Ask the user to confirm that the wireframes are in the claudeDev_docs/wireframes directory.

### 6. Final Review and Next Steps

6.1. Perform a final review of all created files and structures.
6.2. Ask the user for any last-minute changes or additions.
6.3. Instruct the user to replace the current custom instructions in Claude Dev with the content of claudeDevInstructions.md.
6.4. Remind the user that the next step is to begin the actual development process guided by the new custom instructions and the sprint documents.

Remember to maintain clear and professional communication throughout the process, and always prioritize the user's goals and preferences for the project.

6.5. As the final step, create the claudeDevInstructions.md file using the template provided. Instruct the user to replace the current custom instructions in Claude Dev with this content for the actual build process, which they can then commence:

- claudeDevInstructions.md: Use the following template, customizing it for this specific project:

""# Claude Dev Instructions for rag_modulo

====

CLAUDE DEV PROJECT DEVELOPMENT GUIDELINES

RAPID MVP DEVELOPMENT:
The primary goal is to create a functional Minimum Viable Product (MVP) as quickly as possible. Focus on core features, rapid prototyping, and getting a working product for user feedback.

PREPARATION:
- Read the 'Opening Message for Next Session' in `currentTask.md`
- Review the current sprint document and task from currentTask.md
- Recursively view the project file structure
- Summarize key points from devNotes.md at the start of each new session

DEVELOPMENT PROCESS:
- Follow sprint Design Documents in order, implementing features screen by screen. Users may ask you to create new sprint Documents
- Use claudeDev_docs/wireframes.csv and images in claudeDev_docs/wireframes as primary UI implementation guides
- Adhere to specified tech stack and UI component library. Utilize these components when building.
- Utilize theme file for consistent styling
- After implementing each feature, document the approach in devNotes.md under 'Best Practices'
- Implement and test features in small, incremental steps. Run the development server frequently to verify changes.
- Focus on manual testing for rapid MVP development. Implement automated tests only for critical, stable features if time allows.
- Prioritize getting user feedback early and often. Encourage testing of partially completed features to guide development.

TOOLS AND RESOURCES:
- wireframes.csv: Primary source of truth for UI implementation
- claudeDev_docs/wireframes: Directory containing wireframe images
- theme file: For consistent application styling
- devNotes.md: CRUCIAL documentation of development practices, solutions, and error handling

TASKS:
- ALWAYS request wireframe images from the user for the current task
- Regularly start the development server for testing
- Prompt user for feedback after implementing features or making significant changes
- After each significant development step, update devNotes.md with new insights or practices

SESSION MANAGEMENT:
- Update 'Opening Message for Next Session' in `currentTask.md`
- Commit changes: `git add . && git commit -m 'Brief description of changes'`
- Review and update devNotes.md with any new information from the session

ERROR HANDLING:
- When encountering errors:
  1. Check devNotes.md for similar issues and solutions
  2. If new, analyze thoroughly and document in devNotes.md:
     - Error description
     - Solution
     - Prevention steps
  3. Apply the solution and update the code accordingly
  4. Ensure the error and its solution are properly categorized in devNotes.md

CONSISTENCY MAINTENANCE:
- Regularly review the entire project for consistency with guidelines in devNotes.md
- Update devNotes.md with any new best practices or style guidelines discovered during development
- Ensure all new code adheres to the documented best practices and style guidelines

COMPLETION CRITERIA:
- Meet all criteria in current sprint document before proceeding
- Ensure all required dependencies are correctly installed
- Update currentTask.md at the end of every session
- Review and update devNotes.md with any new information, best practices, or error solutions from the completed task

NOTE: The devNotes.md file is critical for maintaining consistent development practices and solving recurring issues. Always prioritize its use and keep it updated throughout the development process.

====

Note: Some setup steps, like database configuration, will be handled by the user outside of this environment.
""
"
