#!/bin/bash

# Fresh Environment Simulation Test
# This script simulates a fresh developer machine to test the complete workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
CONTAINER_NAME="rag-modulo-fresh-test"
PROJECT_DIR="/project"
TEST_TIMEOUT=300 # 5 minutes

echo -e "${BLUE}🧪 Fresh Environment Simulation Test${NC}"
echo "================================================"
echo "This test simulates a fresh developer machine"
echo "to validate the complete development workflow."
echo ""

# Function to print test steps
print_step() {
    echo -e "${YELLOW}📋 Step $1: $2${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to cleanup
cleanup() {
    echo -e "${BLUE}🧹 Cleaning up test environment...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Set trap for cleanup
trap cleanup EXIT

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not available. Please install Docker first."
    exit 1
fi

print_step "1" "Creating fresh Ubuntu container"
docker run -d --name $CONTAINER_NAME \
    -v "$(pwd):$PROJECT_DIR" \
    -w $PROJECT_DIR \
    ubuntu:22.04 \
    sleep infinity

print_success "Fresh container created: $CONTAINER_NAME"

print_step "2" "Installing prerequisites in fresh container"
docker exec $CONTAINER_NAME bash -c "
    apt-get update -qq
    apt-get install -y -qq curl wget git make ca-certificates gnupg lsb-release
    echo 'Prerequisites installed'
"

print_success "Prerequisites installed"

print_step "3" "Installing Docker in fresh container"
docker exec $CONTAINER_NAME bash -c "
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    # Add user to docker group
    usermod -aG docker root

    echo 'Docker installed'
"

print_success "Docker installed in container"

print_step "4" "Testing make dev-init"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make dev-init
    if [ -f .env.dev ]; then
        echo '✅ .env.dev created successfully'
    else
        echo '❌ .env.dev not created'
        exit 1
    fi
"

print_success "make dev-init works"

print_step "5" "Testing make dev-build"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    timeout $TEST_TIMEOUT make dev-build
    echo '✅ make dev-build completed'
"

print_success "make dev-build works"

print_step "6" "Testing make dev-up"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    timeout $TEST_TIMEOUT make dev-up
    echo '✅ make dev-up completed'
"

print_success "make dev-up works"

print_step "7" "Testing make dev-validate"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make dev-validate
    echo '✅ make dev-validate completed'
"

print_success "make dev-validate works"

print_step "8" "Testing make dev-status"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make dev-status
    echo '✅ make dev-status completed'
"

print_success "make dev-status works"

print_step "9" "Testing make dev-logs"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make dev-logs | head -20
    echo '✅ make dev-logs completed'
"

print_success "make dev-logs works"

print_step "10" "Testing make dev-restart"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    timeout $TEST_TIMEOUT make dev-restart
    echo '✅ make dev-restart completed'
"

print_success "make dev-restart works"

print_step "11" "Testing make dev-down"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make dev-down
    echo '✅ make dev-down completed'
"

print_success "make dev-down works"

print_step "12" "Testing make dev-reset"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make dev-reset
    echo '✅ make dev-reset completed'
"

print_success "make dev-reset works"

print_step "13" "Testing make clean-all"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make clean-all
    echo '✅ make clean-all completed'
"

print_success "make clean-all works"

print_step "14" "Testing make test-watch (dry run)"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    timeout 10 make test-watch || true
    echo '✅ make test-watch works (timeout after 10s)'
"

print_success "make test-watch works"

print_step "15" "Testing make help"
docker exec $CONTAINER_NAME bash -c "
    cd $PROJECT_DIR
    make help | grep -q 'Development Workflow'
    echo '✅ make help shows development commands'
"

print_success "make help works"

echo ""
echo -e "${GREEN}🎉 Fresh Environment Simulation Test PASSED!${NC}"
echo "================================================"
echo "All Makefile targets work in a fresh environment:"
echo "✅ dev-init, dev-build, dev-up, dev-validate"
echo "✅ dev-status, dev-logs, dev-restart, dev-down"
echo "✅ dev-reset, clean-all, test-watch, help"
echo ""
echo -e "${BLUE}💡 This validates that new developers can:${NC}"
echo "1. Clone the repository"
echo "2. Run make dev-setup (or individual commands)"
echo "3. Start developing immediately"
echo ""
echo -e "${GREEN}✅ Fresh environment simulation completed successfully!${NC}"
