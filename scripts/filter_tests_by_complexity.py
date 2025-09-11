#!/usr/bin/env python3
"""Quick filter to categorize tests by complexity before conversion."""

import os
import re
from pathlib import Path


def analyze_test_file(file_path: str) -> dict:
    """Quick analysis of a test file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Count test functions
    test_functions = len(re.findall(r'def test_', content))

    # Count fixtures
    fixtures = len(re.findall(r'@pytest\.fixture', content))

    # Check for service imports
    service_imports = len(re.findall(r'from.*service', content))

    # Check for database operations
    db_operations = len(re.findall(r'\.(create|update|delete|save|commit|get|find|query)', content))

    # Check for external dependencies
    external_deps = len(re.findall(r'import (sqlalchemy|pytest|fastapi|pydantic|requests|httpx)', content))

    # Calculate complexity score
    complexity = test_functions * 2 + fixtures * 1 + service_imports * 3 + db_operations * 2 + external_deps * 1

    return {
        'file': file_path,
        'test_functions': test_functions,
        'fixtures': fixtures,
        'service_imports': service_imports,
        'db_operations': db_operations,
        'external_deps': external_deps,
        'complexity': complexity,
        'recommendation': get_recommendation(complexity, db_operations, service_imports)
    }


def get_recommendation(complexity: int, db_ops: int, service_imports: int) -> str:
    """Get recommendation based on analysis."""
    if complexity < 10 and db_ops == 0 and service_imports == 0:
        return "✅ ATOMIC - Good candidate"
    elif complexity < 20 and db_ops < 3:
        return "⚠️  ATOMIC - Moderate candidate"
    elif db_ops > 5 or service_imports > 3:
        return "❌ INTEGRATION - Keep as integration test"
    else:
        return "🤔 REVIEW - Needs manual review"


def main():
    test_dir = "backend/tests/atomic"

    print("🔍 TEST COMPLEXITY ANALYSIS")
    print("=" * 80)

    atomic_candidates = []
    integration_candidates = []
    review_candidates = []

    for test_file in Path(test_dir).glob("test_*.py"):
        analysis = analyze_test_file(str(test_file))

        if "ATOMIC" in analysis['recommendation']:
            atomic_candidates.append(analysis)
        elif "INTEGRATION" in analysis['recommendation']:
            integration_candidates.append(analysis)
        else:
            review_candidates.append(analysis)

    print(f"\n✅ ATOMIC CANDIDATES ({len(atomic_candidates)}):")
    for analysis in atomic_candidates:
        print(f"  • {os.path.basename(analysis['file'])} - {analysis['complexity']} complexity")

    print(f"\n❌ INTEGRATION CANDIDATES ({len(integration_candidates)}):")
    for analysis in integration_candidates:
        print(f"  • {os.path.basename(analysis['file'])} - {analysis['complexity']} complexity, {analysis['db_operations']} DB ops")

    print(f"\n🤔 REVIEW CANDIDATES ({len(review_candidates)}):")
    for analysis in review_candidates:
        print(f"  • {os.path.basename(analysis['file'])} - {analysis['complexity']} complexity")

    print(f"\n📊 SUMMARY:")
    print(f"  Total files: {len(atomic_candidates) + len(integration_candidates) + len(review_candidates)}")
    print(f"  Atomic candidates: {len(atomic_candidates)}")
    print(f"  Integration candidates: {len(integration_candidates)}")
    print(f"  Review candidates: {len(review_candidates)}")


if __name__ == "__main__":
    main()
