#!/usr/bin/env python3
"""Apply migration to add agents table for SPIFFE/SPIRE workload identity.

Reference: docs/architecture/spire-integration-architecture.md

Usage:
    python migrations/apply_agents_migration.py
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
    """Apply the agents table migration."""
    print(f"Connecting to database: {DB_NAME} at {DB_HOST}:{DB_PORT}")

    conn = None
    cursor = None

    try:
        # Connect to database
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor()

        print("Connected successfully!")

        # Check if table already exists
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'agents'
            );
        """
        )

        if cursor.fetchone()[0]:
            print("✅ Table 'agents' already exists.")

            # Verify structure
            cursor.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'agents'
                ORDER BY ordinal_position;
            """
            )

            print("\nExisting columns:")
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")

            return True

        print("Creating 'agents' table...")

        # Read and execute migration SQL
        migration_file = Path(__file__).parent / "add_agents_table.sql"
        with open(migration_file) as f:
            migration_sql = f.read()

        cursor.execute(migration_sql)
        print("✅ Successfully created 'agents' table!")

        # Verify the table was created
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'agents'
            ORDER BY ordinal_position;
        """
        )

        results = cursor.fetchall()
        if results:
            print(f"\nTable created with {len(results)} columns:")
            for row in results:
                print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")
        else:
            print("❌ ERROR: Table 'agents' not found after migration!")
            if conn:
                conn.rollback()
            return False

        # Verify indexes
        cursor.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'agents';
        """
        )

        indexes = cursor.fetchall()
        print(f"\nCreated {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx[0]}")

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
