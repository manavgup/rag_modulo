# RAG Modulo Configuration Guide

This document outlines the configuration structure for the RAG Modulo application.

## Core Configuration

The core configuration (`config.py`) contains essential startup settings that are required for the application to initialize. These settings are loaded from environment variables and are immutable during runtime.

### Critical Settings

#### Security Credentials
- `jwt_secret_key` (required): Secret key for JWT token generation
- `jwt_algorithm`: JWT algorithm (default: "HS256")

#### IBM/WatsonX Credentials
- `wx_project_id`: WatsonX instance ID
- `wx_api_key`: WatsonX API key
- `wx_url`: WatsonX base URL
- `ibm_client_id`: IBM OIDC client ID
- `ibm_client_secret`: IBM OIDC client secret

#### Database Settings
- `collectiondb_user`: Database username
- `collectiondb_pass`: Database password
- `collectiondb_host`: Database host
- `collectiondb_port`: Database port (default: 5432)
- `collectiondb_name`: Database name

### Environment Variables

Settings can be configured through environment variables or a `.env` file. Example:

```env
JWT_SECRET_KEY=your-secret-key
WATSONX_INSTANCE_ID=your-instance-id
WATSONX_APIKEY=your-api-key
COLLECTIONDB_USER=rag_modulo_user
COLLECTIONDB_PASS=rag_modulo_password
```

## Runtime Configuration

Other settings have been moved to runtime configuration modules:

- LLM Parameters → `rag_solution/models/llm_parameters.py`
- Prompt Templates → `rag_solution/models/prompt_template.py`
- Runtime Settings → `rag_solution/models/runtime_config.py`
- Provider Settings → `rag_solution/models/provider_config.py`

Refer to their respective documentation for details.