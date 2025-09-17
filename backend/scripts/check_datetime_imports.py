#!/usr/bin/env python3
"""Check that SQLAlchemy models have proper datetime imports.

This script verifies that all models using Mapped[datetime] have datetime imported
at runtime, not just in TYPE_CHECKING blocks.
"""

import sys
from pathlib import Path


def check_datetime_imports():
    """Check datetime imports in all model files."""
    models_dir = Path("rag_solution/models")
    errors = []

    for model_file in models_dir.glob("*.py"):
        if model_file.name == "__init__.py":
            continue

        content = model_file.read_text()

        # Check if file uses Mapped[datetime]
        if "Mapped[datetime]" not in content:
            continue

        # Check if datetime is imported at runtime
        if "from datetime import datetime" not in content.split("if TYPE_CHECKING:")[0]:
            errors.append(str(model_file))

    return errors


if __name__ == "__main__":
    errors = check_datetime_imports()
    if errors:
        print("❌ SQLAlchemy models missing runtime datetime imports:")
        for file in errors:
            print(f"  - {file}")
        print()
        print("💡 Fix: Add 'from datetime import datetime' outside TYPE_CHECKING blocks")
        print("   in files that use 'Mapped[datetime]' annotations")
        sys.exit(1)
    else:
        print("✅ All SQLAlchemy models have proper datetime imports")
        sys.exit(0)
