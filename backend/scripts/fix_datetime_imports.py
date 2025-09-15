#!/usr/bin/env python3
"""Fix datetime imports in SQLAlchemy models.

This script ensures that all models using Mapped[datetime] have proper datetime imports
at runtime, not just in TYPE_CHECKING blocks.
"""

import re
from pathlib import Path


def fix_datetime_imports():
    """Fix datetime imports in all model files."""
    models_dir = Path("rag_solution/models")
    fixed_files = []

    for model_file in models_dir.glob("*.py"):
        if model_file.name == "__init__.py":
            continue

        content = model_file.read_text()

        # Check if file uses Mapped[datetime]
        if "Mapped[datetime]" not in content:
            continue

        # Check if datetime is already imported outside TYPE_CHECKING
        if re.search(r"^from datetime import datetime", content, re.MULTILINE):
            continue

        # Check if datetime is only in TYPE_CHECKING block
        type_checking_match = re.search(r"if TYPE_CHECKING:\s*\n((?:\s{4}.*\n)*)", content, re.MULTILINE)

        if type_checking_match:
            type_checking_block = type_checking_match.group(1)
            if "from datetime import datetime" in type_checking_block:
                # Move datetime import outside TYPE_CHECKING
                print(f"Fixing {model_file}")

                # Remove datetime from TYPE_CHECKING block
                new_type_checking = re.sub(r"\s*from datetime import datetime\s*\n", "", type_checking_block)

                # Find the imports section (after __future__ and before sqlalchemy)
                import_section_match = re.search(
                    r"(from __future__ import annotations\s*\n\s*\n)(import.*?\n)(from typing import TYPE_CHECKING)",
                    content,
                    re.MULTILINE | re.DOTALL,
                )

                if import_section_match:
                    future_import = import_section_match.group(1)
                    existing_imports = import_section_match.group(2)
                    typing_import = import_section_match.group(3)

                    # Add datetime import
                    new_imports = existing_imports
                    if "from datetime import datetime" not in existing_imports:
                        new_imports += "from datetime import datetime\n"

                    # Replace the content
                    content = content.replace(
                        import_section_match.group(0), future_import + new_imports + typing_import
                    )

                    # Update TYPE_CHECKING block
                    if new_type_checking.strip():
                        content = content.replace(type_checking_match.group(1), new_type_checking)
                    else:
                        # Remove empty TYPE_CHECKING block if no imports left
                        content = re.sub(r"if TYPE_CHECKING:\s*\n\s*\n", "", content)

                    model_file.write_text(content)
                    fixed_files.append(str(model_file))

    return fixed_files


if __name__ == "__main__":
    fixed = fix_datetime_imports()
    if fixed:
        print(f"Fixed datetime imports in {len(fixed)} files:")
        for file in fixed:
            print(f"  - {file}")
    else:
        print("No files needed datetime import fixes.")
