#!/usr/bin/env python3
"""
Environment validation script for RAG Modulo project.
Checks that all required environment variables are set.
"""

import os
import sys
from typing import Dict, List

# Define required variables with descriptions
REQUIRED_VARS: Dict[str, str] = {
    # Project
    'PROJECT_NAME': 'Project identifier',
    
    # Database
    'COLLECTIONDB_NAME': 'PostgreSQL database name',
    'COLLECTIONDB_USER': 'PostgreSQL username', 
    'COLLECTIONDB_PASS': 'PostgreSQL password',
    
    # MinIO (Critical for Milvus)
    'MINIO_ROOT_USER': 'MinIO access key (required for Milvus)',
    'MINIO_ROOT_PASSWORD': 'MinIO secret key (required for Milvus)',
    
    # Milvus
    'MILVUS_PORT': 'Milvus connection port',
    
    # MLflow
    'MLFLOW_TRACKING_USERNAME': 'MLflow tracking username',
    'MLFLOW_TRACKING_PASSWORD': 'MLflow tracking password',
    
    # Authentication
    'OIDC_DISCOVERY_ENDPOINT': 'OIDC discovery endpoint URL',
    'OIDC_AUTH_URL': 'OIDC authorization URL',
    'OIDC_TOKEN_URL': 'OIDC token endpoint URL',
    'FRONTEND_URL': 'Frontend application URL',
    
    # IBM Watson
    'IBM_CLIENT_ID': 'IBM client identifier',
    'IBM_CLIENT_SECRET': 'IBM client secret',
    'WATSONX_APIKEY': 'Watson AI API key',
    'WATSONX_INSTANCE_ID': 'Watson AI instance identifier',
}

# Optional variables with defaults
OPTIONAL_VARS: Dict[str, str] = {
    'RUNTIME_EVAL': 'false',
    'PYTHON_VERSION': '3.11',
    'WATSONX_URL': 'https://us-south.ml.cloud.ibm.com',
    'BACKEND_IMAGE': 'ghcr.io/manavgup/rag_modulo/backend:latest',
    'FRONTEND_IMAGE': 'ghcr.io/manavgup/rag_modulo/frontend:latest',
    'TEST_IMAGE': 'ghcr.io/manavgup/rag_modulo/backend:latest',
}

def check_environment() -> bool:
    """Check all environment variables and report issues."""
    missing_vars: List[str] = []
    empty_vars: List[str] = []
    
    print("🔍 Validating environment configuration...")
    print()
    
    # Check required variables
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var)
        if value is None:
            missing_vars.append(f"  ❌ {var} - {description}")
        elif not value.strip():
            empty_vars.append(f"  ⚠️  {var} - {description} (empty)")
        else:
            print(f"  ✅ {var}")
    
    # Report optional variables
    print("\n📋 Optional variables:")
    for var, default in OPTIONAL_VARS.items():
        value = os.getenv(var, default)
        print(f"  ℹ️  {var}={value}")
    
    # Report issues
    success = True
    
    if missing_vars:
        success = False
        print("\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(var)
    
    if empty_vars:
        success = False  
        print("\n⚠️  Empty environment variables:")
        for var in empty_vars:
            print(var)
    
    if not success:
        print("\n💡 To fix:")
        print("  1. Copy .env.example to .env")
        print("  2. Fill in all required values")
        print("  3. Run this script again")
        print("\n  cp .env.example .env")
        print("  # Edit .env with your values")
        return False
    
    print("\n✅ All required environment variables are properly configured!")
    return True

def main():
    """Main entry point."""
    if not check_environment():
        sys.exit(1)
    
    print("🚀 Environment validation passed - ready to run!")

if __name__ == "__main__":
    main()