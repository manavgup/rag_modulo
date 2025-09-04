#!/usr/bin/env python3
"""
Validate that CI environment fixes are properly implemented in the code.
This checks the source files directly without needing Docker.
"""

import os
import sys
import re

def check_file_contains(filepath, patterns, description):
    """Check if a file contains specific patterns."""
    if not os.path.exists(filepath):
        print(f"❌ {description}: File not found - {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    all_found = True
    for pattern in patterns:
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            print(f"✅ {description}: Found pattern '{pattern[:50]}...'")
        else:
            print(f"❌ {description}: Missing pattern '{pattern[:50]}...'")
            all_found = False
    
    return all_found

def main():
    print("=" * 60)
    print("CI Environment Fix Validation")
    print("=" * 60)
    print()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Check auth/oidc.py for conditional OIDC registration
    print("1. Checking auth/oidc.py for conditional OIDC registration...")
    if check_file_contains(
        "backend/auth/oidc.py",
        [
            r"skip_auth = os\.getenv\(.SKIP_AUTH",
            r"development_mode = os\.getenv\(.DEVELOPMENT_MODE",
            r"testing_mode = os\.getenv\(.TESTING",
            r"if not \(skip_auth or development_mode or testing_mode\):",
            r"logger\.info\(.*OIDC registration skipped"
        ],
        "OIDC conditional registration"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    print()
    
    # Test 2: Check authentication middleware for skip logic
    print("2. Checking authentication_middleware.py for skip logic...")
    if check_file_contains(
        "backend/core/authentication_middleware.py",
        [
            r"skip_auth = os\.getenv\(.SKIP_AUTH",
            r"development_mode = os\.getenv\(.DEVELOPMENT_MODE",
            r"testing_mode = os\.getenv\(.TESTING",
            r"if skip_auth or development_mode or testing_mode:",
            r"request\.state\.user = \{"
        ],
        "Authentication middleware skip logic"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    print()
    
    # Test 3: Check docker-compose.yml for environment variables
    print("3. Checking docker-compose.yml for CI environment variables...")
    if check_file_contains(
        "docker-compose.yml",
        [
            r"- SKIP_AUTH=\$\{SKIP_AUTH:-false\}",
            r"- DEVELOPMENT_MODE=\$\{DEVELOPMENT_MODE:-false\}",
            r"- TESTING=\$\{TESTING:-false\}"
        ],
        "Docker Compose environment variables"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    print()
    
    # Test 4: Check GitHub Actions workflow for environment variables
    print("4. Checking CI workflow for environment variables...")
    if check_file_contains(
        ".github/workflows/ci.yml",
        [
            r"TESTING: true",
            r"SKIP_AUTH: true",
            r"DEVELOPMENT_MODE: true",
            r"export TESTING=true",
            r"-e TESTING=true"
        ],
        "GitHub Actions environment variables"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    print()
    
    # Test 5: Check .env.ci file has proper values
    print("5. Checking .env.ci for CI configuration...")
    if check_file_contains(
        ".env.ci",
        [
            r"DEVELOPMENT_MODE=true",
            r"SKIP_AUTH=true",
            r"OIDC_DISCOVERY_ENDPOINT=https://mock-oidc"
        ],
        ".env.ci configuration"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    print()
    print("=" * 60)
    print("Validation Summary")
    print("=" * 60)
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print()
    
    if tests_failed == 0:
        print("🎉 All validation checks passed!")
        print("The CI environment fixes are correctly implemented in the code.")
        print()
        print("Next steps:")
        print("1. Build the backend image: make build-backend")
        print("2. Push the changes to GitHub")
        print("3. Monitor the CI pipeline to ensure it passes")
        return 0
    else:
        print("⚠️  Some validation checks failed!")
        print("Please review the failures above before pushing to GitHub.")
        return 1

if __name__ == "__main__":
    sys.exit(main())