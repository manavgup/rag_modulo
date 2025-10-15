#!/bin/bash

# Environment Validation Script for RAG Modulo
# This script validates that all required environment variables are set

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✓ OK${NC}: $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠ WARNING${NC}: $message"
            ;;
        "ERROR")
            echo -e "${RED}✗ ERROR${NC}: $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ INFO${NC}: $message"
            ;;
    esac
}

# Function to check if a variable is set and not empty
check_variable() {
    local var_name=$1
    local var_value="${!var_name}"
    local required=$2
    local description=$3
    
    if [ -z "$var_value" ]; then
        if [ "$required" = "true" ]; then
            print_status "ERROR" "$var_name is not set (REQUIRED: $description)"
            return 1
        else
            print_status "WARNING" "$var_name is not set (OPTIONAL: $description)"
            return 0
        fi
    else
        if [ "$required" = "true" ]; then
            print_status "OK" "$var_name is set: $var_value"
        else
            print_status "OK" "$var_name is set: $var_value"
        fi
        return 0
    fi
}

# Function to validate environment file
validate_env_file() {
    print_status "INFO" "Validating environment configuration"
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_status "ERROR" ".env file not found"
        print_status "INFO" "Please copy env.example to .env and configure the values"
        return 1
    fi
    
    print_status "OK" ".env file found"
    
    # Source the .env file to check variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi
    
    return 0
}

# Function to validate critical variables
validate_critical_variables() {
    print_status "INFO" "Checking critical environment variables"
    
    local critical_vars=(
        "MINIO_ROOT_USER:true:MinIO root username for object storage"
        "MINIO_ROOT_PASSWORD:true:MinIO root password for object storage"
        "MLFLOW_TRACKING_USERNAME:true:MLflow tracking username"
        "MLFLOW_TRACKING_PASSWORD:true:MLflow tracking password"
        "COLLECTIONDB_NAME:true:PostgreSQL database name"
        "COLLECTIONDB_USER:true:PostgreSQL database user"
        "COLLECTIONDB_PASS:true:PostgreSQL database password"
    )
    
    local error_count=0
    
    for var_info in "${critical_vars[@]}"; do
        IFS=':' read -r var_name required description <<< "$var_info"
        if ! check_variable "$var_name" "$required" "$description"; then
            error_count=$((error_count + 1))
        fi
    done
    
    return $error_count
}

# Function to validate optional variables
validate_optional_variables() {
    print_status "INFO" "Checking optional environment variables"
    
    local optional_vars=(
        "OIDC_DISCOVERY_ENDPOINT:false:OIDC discovery endpoint for authentication"
        "OIDC_AUTH_URL:false:OIDC authorization URL"
        "OIDC_TOKEN_URL:false:OIDC token endpoint"
        "FRONTEND_URL:false:Frontend application URL"
        "IBM_CLIENT_ID:false:IBM WatsonX client ID"
        "IBM_CLIENT_SECRET:false:IBM WatsonX client secret"
        "WATSONX_INSTANCE_ID:false:IBM WatsonX instance ID"
        "WATSONX_APIKEY:false:IBM WatsonX API key"
        "WATSONX_URL:false:IBM WatsonX service URL"
        "MILVUS_PORT:false:Milvus vector database port"
        "VECTOR_DB:false:Vector database type (default: milvus)"
        "PROJECT_NAME:false:Project name (default: rag-modulo)"
        "PYTHON_VERSION:false:Python version (default: 3.12)"
    )
    
    for var_info in "${optional_vars[@]}"; do
        IFS=':' read -r var_name required description <<< "$var_info"
        check_variable "$var_name" "$required" "$description"
    done
}

# Function to validate database configuration
validate_database_config() {
    print_status "INFO" "Validating database configuration"
    
    # Check if database credentials are properly formatted
    if [ -n "$COLLECTIONDB_HOST" ] && [ -n "$COLLECTIONDB_PORT" ]; then
        print_status "OK" "Database host: $COLLECTIONDB_HOST:$COLLECTIONDB_PORT"
    else
        print_status "WARNING" "Database host/port not explicitly set (using defaults)"
    fi
    
    # Check if MinIO credentials are secure
    if [ "$MINIO_ROOT_PASSWORD" = "minioadmin123" ]; then
        print_status "WARNING" "Using default MinIO password - consider changing for production"
    fi
    
    if [ "$MLFLOW_TRACKING_PASSWORD" = "mlflow123" ]; then
        print_status "WARNING" "Using default MLflow password - consider changing for production"
    fi
}

# Function to validate network configuration
validate_network_config() {
    print_status "INFO" "Validating network configuration"
    
    # Check if ports are within valid ranges
    if [ -n "$MILVUS_PORT" ]; then
        if [ "$MILVUS_PORT" -ge 1024 ] && [ "$MILVUS_PORT" -le 65535 ]; then
            print_status "OK" "Milvus port $MILVUS_PORT is within valid range"
        else
            print_status "WARNING" "Milvus port $MILVUS_PORT is outside valid range (1024-65535)"
        fi
    fi
    
    # Check if URLs are properly formatted
    if [ -n "$FRONTEND_URL" ]; then
        if [[ "$FRONTEND_URL" =~ ^https?:// ]]; then
            print_status "OK" "Frontend URL format is valid"
        else
            print_status "WARNING" "Frontend URL should start with http:// or https://"
        fi
    fi
}

# Function to provide setup instructions
provide_setup_instructions() {
    echo ""
    echo "=========================================="
    echo "Environment Setup Instructions"
    echo "=========================================="
    echo ""
    echo "1. Copy the example environment file:"
    echo "   cp env.example .env"
    echo ""
    echo "2. Edit .env and set the required values:"
    echo "   - MINIO_ROOT_USER and MINIO_ROOT_PASSWORD"
    echo "   - MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD"
    echo "   - COLLECTIONDB_NAME, COLLECTIONDB_USER, COLLECTIONDB_PASS"
    echo ""
    echo "3. For production, change default passwords:"
    echo "   - Use strong, unique passwords"
    echo "   - Consider using secrets management"
    echo ""
    echo "4. Run validation again:"
    echo "   ./scripts/validate-env.sh"
    echo ""
}

# Main validation function
main_validation() {
    echo "=========================================="
    echo "RAG Modulo Environment Validation"
    echo "=========================================="
    echo ""
    
    local overall_status=0
    
    # Validate environment file
    if ! validate_env_file; then
        overall_status=1
    fi
    echo ""
    
    # Validate critical variables
    if ! validate_critical_variables; then
        overall_status=1
    fi
    echo ""
    
    # Validate optional variables
    validate_optional_variables
    echo ""
    
    # Validate database configuration
    validate_database_config
    echo ""
    
    # Validate network configuration
    validate_network_config
    echo ""
    
    echo "=========================================="
    echo "Validation Summary"
    echo "=========================================="
    
    if [ $overall_status -eq 0 ]; then
        print_status "OK" "Environment validation passed"
        echo "All required variables are set"
        echo "You can now run 'make run-app' to start the services"
    else
        print_status "ERROR" "Environment validation failed"
        echo "Please fix the issues above before starting services"
        provide_setup_instructions
    fi
    
    return $overall_status
}

# Run validation
main_validation
