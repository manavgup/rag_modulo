#!/usr/bin/env python3
"""Check that SQLAlchemy models have proper uuid imports.

This script verifies that all models using Mapped[uuid.UUID] have uuid imported
at runtime, not just in TYPE_CHECKING blocks.
"""

import sys
from pathlib import Path


def check_uuid_imports():
    """Check uuid imports in all model files."""
    models_dir = Path("rag_solution/models")
    errors = []

    for model_file in models_dir.glob("*.py"):
        if model_file.name == "__init__.py":
            continue

        content = model_file.read_text()

        # Check if file uses Mapped[uuid.UUID]
        if "Mapped[uuid.UUID]" not in content:
            continue

        # Check if uuid is imported at runtime (before TYPE_CHECKING block)
        before_type_checking = content.split("if TYPE_CHECKING:")[0]
        if "import uuid" not in before_type_checking:
            errors.append(str(model_file))

    return errors


if __name__ == "__main__":
    errors = check_uuid_imports()
    if errors:
        print("❌ SQLAlchemy models missing runtime uuid imports:")
        for file in errors:
            print(f"  - {file}")
        print()
        print("💡 Fix: Add 'import uuid' outside TYPE_CHECKING blocks")
        print("   in files that use 'Mapped[uuid.UUID]' annotations")
        sys.exit(1)
    else:
        print("✅ All SQLAlchemy models have proper uuid imports")
        sys.exit(0)
