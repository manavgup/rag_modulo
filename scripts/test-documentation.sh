#!/bin/bash

# Documentation Testing Script
# This script validates that all documentation is accurate and commands work as documented

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📚 Documentation Testing Script${NC}"
echo "================================================"
echo "This script validates documentation accuracy"
echo "and ensures all documented commands work."
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

# Function to test command from documentation
test_command() {
    local command="$1"
    local description="$2"
    local expected_output="$3"

    echo -e "${BLUE}Testing: $description${NC}"
    echo "Command: $command"

    if eval "$command" > /dev/null 2>&1; then
        print_success "$description works"
        return 0
    else
        print_error "$description failed"
        return 1
    fi
}

# Test counter
tests_passed=0
tests_failed=0

print_step "1" "Testing README.md commands"

# Test README quick start commands
test_command "make dev-init" "make dev-init" && ((tests_passed++)) || ((tests_failed++))
test_command "make dev-build" "make dev-build" && ((tests_passed++)) || ((tests_failed++))
test_command "make dev-up" "make dev-up" && ((tests_passed++)) || ((tests_failed++))
test_command "make dev-validate" "make dev-validate" && ((tests_passed++)) || ((tests_failed++))

print_step "2" "Testing development workflow commands"

# Test development workflow commands from docs/development/workflow.md
test_command "make dev-status" "make dev-status" && ((tests_passed++)) || ((tests_failed++))
test_command "make dev-logs" "make dev-logs" && ((tests_passed++)) || ((tests_failed++))
test_command "make dev-restart" "make dev-restart" && ((tests_passed++)) || ((tests_failed++))
test_command "make dev-down" "make dev-down" && ((tests_passed++)) || ((tests_failed++))
test_command "make dev-reset" "make dev-reset" && ((tests_passed++)) || ((tests_failed++))
test_command "make clean-all" "make clean-all" && ((tests_passed++)) || ((tests_failed++))

print_step "3" "Testing advanced features"

# Test advanced features
test_command "make dev-setup" "make dev-setup" && ((tests_passed++)) || ((tests_failed++))
test_command "make help" "make help" && ((tests_passed++)) || ((tests_failed++))

print_step "4" "Testing help command output"

# Test that help command shows expected sections
if make help | grep -q "Development Workflow"; then
    print_success "Help command shows Development Workflow section"
    ((tests_passed++))
else
    print_error "Help command missing Development Workflow section"
    ((tests_failed++))
fi

if make help | grep -q "dev-init"; then
    print_success "Help command shows dev-init"
    ((tests_passed++))
else
    print_error "Help command missing dev-init"
    ((tests_failed++))
fi

if make help | grep -q "dev-build"; then
    print_success "Help command shows dev-build"
    ((tests_passed++))
else
    print_error "Help command missing dev-build"
    ((tests_failed++))
fi

print_step "5" "Testing file creation"

# Test that commands create expected files
if [ -f ".env.dev" ]; then
    print_success ".env.dev file exists"
    ((tests_passed++))
else
    print_error ".env.dev file missing"
    ((tests_failed++))
fi

if [ -d "volumes" ]; then
    print_success "volumes directory exists"
    ((tests_passed++))
else
    print_error "volumes directory missing"
    ((tests_failed++))
fi

print_step "6" "Testing Docker integration"

# Test Docker commands work
if command -v docker &> /dev/null; then
    if docker ps > /dev/null 2>&1; then
        print_success "Docker is running"
        ((tests_passed++))
    else
        print_error "Docker is not running"
        ((tests_failed++))
    fi
else
    print_error "Docker is not installed"
    ((tests_failed++))
fi

print_step "7" "Testing environment variables"

# Test that .env.dev has expected content
if [ -f ".env.dev" ]; then
    if grep -q "DEVELOPMENT_MODE=true" .env.dev; then
        print_success ".env.dev contains DEVELOPMENT_MODE=true"
        ((tests_passed++))
    else
        print_error ".env.dev missing DEVELOPMENT_MODE=true"
        ((tests_failed++))
    fi

    if grep -q "TESTING=true" .env.dev; then
        print_success ".env.dev contains TESTING=true"
        ((tests_passed++))
    else
        print_error ".env.dev missing TESTING=true"
        ((tests_failed++))
    fi

    if grep -q "SKIP_AUTH=true" .env.dev; then
        print_success ".env.dev contains SKIP_AUTH=true"
        ((tests_passed++))
    else
        print_error ".env.dev missing SKIP_AUTH=true"
        ((tests_failed++))
    fi
fi

print_step "8" "Testing documentation files exist"

# Test that documentation files exist
docs_to_check=(
    "README.md"
    "docs/development/workflow.md"
    "docs/development/codespaces.md"
    "docs/development/environment-setup.md"
    "docs/development/contributing.md"
    "docs/testing/MANUAL_VALIDATION_CHECKLIST.md"
)

for doc in "${docs_to_check[@]}"; do
    if [ -f "$doc" ]; then
        print_success "$doc exists"
        ((tests_passed++))
    else
        print_error "$doc missing"
        ((tests_failed++))
    fi
done

print_step "9" "Testing workflow files exist"

# Test that workflow files exist
workflows_to_check=(
    ".github/workflows/pr-codespace.yml"
    ".github/workflows/codespace-testing.yml"
    ".github/workflows/codespace-validation.yml"
)

for workflow in "${workflows_to_check[@]}"; do
    if [ -f "$workflow" ]; then
        print_success "$workflow exists"
        ((tests_passed++))
    else
        print_error "$workflow missing"
        ((tests_failed++))
    fi
done

print_step "10" "Testing Dev Container configuration"

# Test Dev Container files
if [ -f ".devcontainer/devcontainer.json" ]; then
    print_success ".devcontainer/devcontainer.json exists"
    ((tests_passed++))

    # Test that Dev Container config is valid JSON
    if python3 -m json.tool .devcontainer/devcontainer.json > /dev/null 2>&1; then
        print_success "Dev Container config is valid JSON"
        ((tests_passed++))
    else
        print_error "Dev Container config is invalid JSON"
        ((tests_failed++))
    fi
else
    print_error ".devcontainer/devcontainer.json missing"
    ((tests_failed++))
fi

# Summary
echo ""
echo -e "${BLUE}📊 Documentation Testing Summary${NC}"
echo "================================================"
echo -e "${GREEN}✅ Tests Passed: $tests_passed${NC}"
echo -e "${RED}❌ Tests Failed: $tests_failed${NC}"
echo ""

if [ $tests_failed -eq 0 ]; then
    echo -e "${GREEN}🎉 All documentation tests PASSED!${NC}"
    echo "Documentation is accurate and all commands work as documented."
    exit 0
else
    echo -e "${RED}❌ Some documentation tests FAILED!${NC}"
    echo "Please review the failed tests and update documentation accordingly."
    exit 1
fi
