#!/usr/bin/env python3
"""
Apply migration to add chapters column to podcasts table.

Usage:
    python migrations/apply_chapters_migration.py
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("COLLECTIONDB_HOST", "localhost")
DB_PORT = os.getenv("COLLECTIONDB_PORT", "5432")
DB_USER = os.getenv("COLLECTIONDB_USER", "rag_modulo_user")
DB_PASSWORD = os.getenv("COLLECTIONDB_PASSWORD")
DB_NAME = os.getenv("COLLECTIONDB_NAME", "rag_modulo")


def apply_migration():
    """Apply the chapters column migration."""
    print(f"Connecting to database: {DB_NAME} at {DB_HOST}:{DB_PORT}")

    conn = None
    cursor = None

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
        cursor = conn.cursor()

        print("Connected successfully!")

        # Check if column already exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'podcasts' AND column_name = 'chapters';
        """
        )

        if cursor.fetchone():
            print("✅ Column 'chapters' already exists in podcasts table.")
        else:
            print("Adding 'chapters' column to podcasts table...")

            # Add the column
            cursor.execute(
                """
                ALTER TABLE podcasts
                ADD COLUMN chapters JSONB DEFAULT '[]'::jsonb;
            """
            )

            # Add comment
            cursor.execute(
                """
                COMMENT ON COLUMN podcasts.chapters IS
                'Dynamic chapter markers with timestamps (title, start_time, end_time, word_count)';
            """
            )

            print("✅ Successfully added 'chapters' column!")

        # Verify the column
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'podcasts' AND column_name = 'chapters';
        """
        )

        result = cursor.fetchone()
        if result:
            print(f"\nColumn details:")
            print(f"  Name: {result[0]}")
            print(f"  Type: {result[1]}")
            print(f"  Nullable: {result[2]}")
            print(f"  Default: {result[3]}")
        else:
            print("❌ ERROR: Column 'chapters' not found after migration!")
            if conn:
                conn.rollback()
            return False

        # Commit transaction if all successful
        conn.commit()

        print("\n🎉 Migration completed successfully!")
        return True

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
            print("  Transaction rolled back.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
            print("  Transaction rolled back.")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
