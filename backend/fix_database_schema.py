#!/usr/bin/env python3
"""Fix database schema by adding missing columns to conversation_messages table."""

import os
import sys

# Add the backend directory to sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)

from sqlalchemy import text

from rag_solution.file_management.database import engine


def fix_database_schema():
    """Add missing columns to the conversation_messages table."""
    print("🔧 Fixing database schema...")

    try:
        with engine.connect() as connection:
            # Check if the columns exist
            result = connection.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'conversation_messages'
                AND column_name IN ('token_count', 'execution_time')
            """
                )
            )

            existing_columns = [row[0] for row in result.fetchall()]
            print(f"Existing columns: {existing_columns}")

            # Add token_count column if it doesn't exist
            if "token_count" not in existing_columns:
                print("Adding token_count column...")
                connection.execute(
                    text(
                        """
                    ALTER TABLE conversation_messages
                    ADD COLUMN token_count INTEGER
                """
                    )
                )
                connection.commit()
                print("✅ Added token_count column")
            else:
                print("✅ token_count column already exists")

            # Add execution_time column if it doesn't exist
            if "execution_time" not in existing_columns:
                print("Adding execution_time column...")
                connection.execute(
                    text(
                        """
                    ALTER TABLE conversation_messages
                    ADD COLUMN execution_time FLOAT
                """
                    )
                )
                connection.commit()
                print("✅ Added execution_time column")
            else:
                print("✅ execution_time column already exists")

            # Verify the columns were added
            result = connection.execute(
                text(
                    """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'conversation_messages'
                AND column_name IN ('token_count', 'execution_time')
                ORDER BY column_name
            """
                )
            )

            columns = result.fetchall()
            print(f"Final columns: {columns}")

            print("🎉 Database schema fix completed successfully!")

    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        raise


if __name__ == "__main__":
    fix_database_schema()
