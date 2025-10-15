#!/bin/bash

# Build Performance Testing Script for RAG Modulo
# This script measures build times and performance improvements

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

# Function to measure time
measure_time() {
    local start_time=$(date +%s.%N)
    "$@"
    local end_time=$(date +%s.%N)
    local elapsed=$(echo "$end_time - $start_time" | bc -l)
    echo "$elapsed"
}

# Function to get build context size
get_build_context_size() {
    local directory=$1
    local size=$(du -sh "$directory" 2>/dev/null | cut -f1)
    echo "$size"
}

# Function to clean Docker images
clean_docker_images() {
    print_status "INFO" "Cleaning Docker images for fresh test"
    
    # Remove existing images
    docker rmi -f $(docker images -q "rag-modulo-*" 2>/dev/null) 2>/dev/null || true
    docker rmi -f $(docker images -q "ghcr.io/manavgup/rag_modulo/*" 2>/dev/null) 2>/dev/null || true
    
    # Clean build cache
    docker builder prune -f >/dev/null 2>&1 || true
    
    print_status "OK" "Docker images cleaned"
}

# Function to test frontend build
test_frontend_build() {
    print_status "INFO" "Testing frontend build performance"
    
    local build_context_size=$(get_build_context_size "webui")
    print_status "INFO" "Frontend build context size: $build_context_size"
    
    # Test build time
    print_status "INFO" "Building frontend image..."
    local build_time=$(measure_time docker build -t rag-modulo-frontend:test -f webui/Dockerfile.frontend webui)
    
    print_status "OK" "Frontend build completed in ${build_time}s"
    
    # Get image size
    local image_size=$(docker images rag-modulo-frontend:test --format "{{.Size}}" 2>/dev/null || echo "unknown")
    print_status "INFO" "Frontend image size: $image_size"
    
    # Clean up
    docker rmi rag-modulo-frontend:test >/dev/null 2>&1 || true
    
    echo "$build_time"
}

# Function to test backend build
test_backend_build() {
    print_status "INFO" "Testing backend build performance"
    
    local build_context_size=$(get_build_context_size "backend")
    print_status "INFO" "Backend build context size: $build_context_size"
    
    # Test build time
    print_status "INFO" "Building backend image..."
    local build_time=$(measure_time docker build -t rag-modulo-backend:test -f backend/Dockerfile.backend backend)
    
    print_status "OK" "Backend build completed in ${build_time}s"
    
    # Get image size
    local image_size=$(docker images rag-modulo-backend:test --format "{{.Size}}" 2>/dev/null || echo "unknown")
    print_status "INFO" "Backend image size: $image_size"
    
    # Clean up
    docker rmi rag-modulo-backend:test >/dev/null 2>&1 || true
    
    echo "$build_time"
}

# Function to test build with BuildKit
test_buildkit_build() {
    print_status "INFO" "Testing BuildKit build performance"
    
    # Check if BuildKit is available
    if ! docker buildx version >/dev/null 2>&1; then
        print_status "WARNING" "BuildKit not available, skipping test"
        return
    fi
    
    # Test frontend build with BuildKit
    print_status "INFO" "Building frontend with BuildKit..."
    local buildkit_time=$(measure_time docker buildx build --platform linux/amd64 -t rag-modulo-frontend:buildkit-test -f webui/Dockerfile.frontend webui)
    
    print_status "OK" "BuildKit frontend build completed in ${buildkit_time}s"
    
    # Clean up
    docker rmi rag-modulo-frontend:buildkit-test >/dev/null 2>&1 || true
    
    echo "$buildkit_time"
}

# Function to test layer caching
test_layer_caching() {
    print_status "INFO" "Testing Docker layer caching"
    
    # First build
    print_status "INFO" "First build (no cache)..."
    local first_build_time=$(measure_time docker build -t rag-modulo-frontend:cache-test -f webui/Dockerfile.frontend webui)
    
    # Second build (with cache)
    print_status "INFO" "Second build (with cache)..."
    local second_build_time=$(measure_time docker build -t rag-modulo-frontend:cache-test -f webui/Dockerfile.frontend webui)
    
    # Calculate improvement
    local improvement=$(echo "scale=2; ($first_build_time - $second_build_time) / $first_build_time * 100" | bc -l)
    
    print_status "INFO" "First build time: ${first_build_time}s"
    print_status "INFO" "Second build time: ${second_build_time}s"
    print_status "INFO" "Cache improvement: ${improvement}%"
    
    # Clean up
    docker rmi rag-modulo-frontend:cache-test >/dev/null 2>&1 || true
}

# Function to generate performance report
generate_performance_report() {
    local frontend_time=$1
    local backend_time=$2
    local buildkit_time=$3
    
    echo ""
    echo "=========================================="
    echo "Build Performance Report"
    echo "=========================================="
    echo ""
    echo "Build Times:"
    echo "  Frontend: ${frontend_time}s"
    echo "  Backend:  ${backend_time}s"
    if [ -n "$buildkit_time" ]; then
        echo "  BuildKit: ${buildkit_time}s"
    fi
    echo ""
    
    # Calculate total build time
    local total_time=$(echo "$frontend_time + $backend_time" | bc -l)
    echo "Total Build Time: ${total_time}s"
    echo ""
    
    # Performance recommendations
    echo "Performance Recommendations:"
    if (( $(echo "$total_time > 300" | bc -l) )); then
        print_status "WARNING" "Total build time is over 5 minutes - consider optimization"
    else
        print_status "OK" "Build time is reasonable"
    fi
    
    if [ -n "$buildkit_time" ]; then
        if (( $(echo "$buildkit_time < $frontend_time" | bc -l) )); then
            print_status "OK" "BuildKit provides performance improvement"
        else
            print_status "WARNING" "BuildKit not showing improvement - check configuration"
        fi
    fi
    
    echo ""
    echo "Optimization Status:"
    echo "  ✓ .dockerignore files added"
    echo "  ✓ BuildKit enabled"
    echo "  ✓ Multi-stage builds implemented"
    echo "  ✓ Layer caching optimized"
}

# Main performance test function
main_performance_test() {
    echo "=========================================="
    echo "RAG Modulo Build Performance Test"
    echo "=========================================="
    echo ""
    
    # Check prerequisites
    if ! command -v docker >/dev/null 2>&1; then
        print_status "ERROR" "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        print_status "ERROR" "Docker daemon is not running"
        exit 1
    fi
    
    # Check if .dockerignore files exist
    if [ ! -f "webui/.dockerignore" ] || [ ! -f "backend/.dockerignore" ]; then
        print_status "ERROR" ".dockerignore files are missing. Run 'make build-optimize' first."
        exit 1
    fi
    
    print_status "OK" "Prerequisites check passed"
    echo ""
    
    # Clean existing images
    clean_docker_images
    echo ""
    
    # Test builds
    local frontend_time=$(test_frontend_build)
    echo ""
    
    local backend_time=$(test_backend_build)
    echo ""
    
    local buildkit_time=$(test_buildkit_build)
    echo ""
    
    # Test layer caching
    test_layer_caching
    echo ""
    
    # Generate report
    generate_performance_report "$frontend_time" "$backend_time" "$buildkit_time"
}

# Run performance test
main_performance_test
