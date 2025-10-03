#!/usr/bin/env python3
"""Fix database enum by adding missing RERANKING value to prompttemplatetype enum."""

import os
import sys

# Add the backend directory to sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)

from sqlalchemy import text  # noqa: E402

from rag_solution.file_management.database import engine  # noqa: E402


def fix_enum_migration():
    """Add missing RERANKING value to prompttemplatetype enum."""
    print("🔧 Fixing database enum for prompttemplatetype...")

    try:
        with engine.connect() as connection:
            # Check if RERANKING value exists in the enum
            result = connection.execute(
                text(
                    """
                SELECT enumlabel
                FROM pg_enum
                WHERE enumtypid = (
                    SELECT oid
                    FROM pg_type
                    WHERE typname = 'prompttemplatetype'
                )
                AND enumlabel = 'RERANKING'
            """
                )
            )

            existing_value = result.fetchone()
            if existing_value:
                print("✅ RERANKING enum value already exists")
                return

            # Add RERANKING value to the enum
            print("Adding RERANKING value to prompttemplatetype enum...")
            connection.execute(
                text(
                    """
                ALTER TYPE prompttemplatetype ADD VALUE 'RERANKING'
            """
                )
            )
            connection.commit()
            print("✅ Added RERANKING value to prompttemplatetype enum")

            # Verify the enum values
            result = connection.execute(
                text(
                    """
                SELECT enumlabel
                FROM pg_enum
                WHERE enumtypid = (
                    SELECT oid
                    FROM pg_type
                    WHERE typname = 'prompttemplatetype'
                )
                ORDER BY enumsortorder
            """
                )
            )

            enum_values = [row[0] for row in result.fetchall()]
            print(f"✅ Current enum values: {enum_values}")

    except Exception as e:
        print(f"❌ Error fixing enum: {e}")
        raise


if __name__ == "__main__":
    fix_enum_migration()
