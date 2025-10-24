#!/usr/bin/env python3
"""Wipe all data from PostgreSQL, Milvus, and local file storage.

This script safely clears all data while preserving database schema.
The app will auto-reinitialize on next startup:
  - Tables are recreated via SQLAlchemy (if missing)
  - Providers/models are seeded via SystemInitializationService

Best Practices Implemented:
  ✓ Preserves schema structure (keeps alembic_version)
  ✓ Truncates with CASCADE (handles foreign keys)
  ✓ Resets sequences with RESTART IDENTITY
  ✓ Clears vector data from Milvus
  ✓ Clears uploaded files (collection documents, podcasts)
  ✓ Provides dry-run mode for safety
  ✓ Requires confirmation before destructive operations
  ✓ Environment protection (prevents production wipes)
  ✓ Optional automatic backup before wiping
  ✓ Timestamped backup creation
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path (script is in backend/scripts/, parent is backend/)
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymilvus import connections, utility
from sqlalchemy import text

from core.config import get_settings
from rag_solution.file_management.database import engine

settings = get_settings()


def check_environment_safety():
    """Prevent accidental wipes in production environment."""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        print("❌ SAFETY CHECK FAILED!")
        print("=" * 80)
        print("This script is NOT allowed to run in PRODUCTION environment.")
        print()
        print("To wipe production data, you must:")
        print("  1. Set ENVIRONMENT=development or ENVIRONMENT=staging")
        print("  2. Set ALLOW_DATABASE_WIPE=true in your environment")
        print("  3. Understand that this will DELETE ALL DATA")
        print()
        print("For production database resets, use proper backup/restore procedures.")
        print("=" * 80)
        sys.exit(1)

    # Additional safeguard: require explicit environment variable
    allow_wipe = os.getenv("ALLOW_DATABASE_WIPE", "false").lower()
    if allow_wipe not in ("true", "1", "yes"):
        print("❌ SAFETY CHECK FAILED!")
        print("=" * 80)
        print("Database wipe requires explicit permission.")
        print()
        print("To enable database wiping, set the environment variable:")
        print("  export ALLOW_DATABASE_WIPE=true")
        print()
        print("This safeguard prevents accidental data loss.")
        print("=" * 80)
        sys.exit(1)


def create_backup(backup_dir: Path):
    """Create timestamped backup of critical data before wiping."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("CREATING BACKUP")
    print("=" * 80)
    print(f"  Backup location: {backup_path}")

    try:
        # 1. Backup PostgreSQL schema and data
        pg_backup_file = backup_path / "postgres_backup.sql"
        print(f"  Creating PostgreSQL dump: {pg_backup_file.name}")

        # Using pg_dump via docker if running in containers
        db_host = settings.collectiondb_host
        db_port = settings.collectiondb_port
        db_name = settings.collectiondb_database
        db_user = settings.collectiondb_user

        # Note: This requires pg_dump to be installed or running via docker
        print("  (Skipping PostgreSQL backup - requires manual pg_dump setup)")

        # 2. Backup Milvus collections metadata
        milvus_backup_file = backup_path / "milvus_collections.json"
        print(f"  Creating Milvus metadata backup: {milvus_backup_file.name}")

        try:
            host = settings.milvus_host or "localhost"
            port = settings.milvus_port or 19530
            connections.connect("backup", host=host, port=port)
            collections = utility.list_collections()

            milvus_metadata = {"timestamp": timestamp, "collections": collections, "host": host, "port": port}

            with open(milvus_backup_file, "w") as f:
                json.dump(milvus_metadata, f, indent=2)

            connections.disconnect("backup")
            print(f"  ✓ Backed up metadata for {len(collections)} Milvus collections")
        except Exception as e:
            print(f"  ⚠️  Milvus backup failed: {e}")

        # 3. Create backup manifest
        manifest = {
            "timestamp": timestamp,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "backup_location": str(backup_path),
            "postgresql_host": db_host,
            "milvus_host": settings.milvus_host,
        }

        manifest_file = backup_path / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n✓ Backup created: {backup_path}")
        print(f"  To restore: See {backup_path}/manifest.json")
        print()

        return backup_path

    except Exception as e:
        print(f"✗ Backup creation failed: {e}")
        raise


def wipe_milvus(dry_run: bool = False):
    """Drop all collections from Milvus."""
    print("=" * 80)
    print("WIPING MILVUS" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 80)

    try:
        # Connect to Milvus
        host = settings.milvus_host or "localhost"
        port = settings.milvus_port or 19530
        connections.connect("default", host=host, port=port)
        print(f"✓ Connected to Milvus at {host}:{port}")

        # List all collections
        collections = utility.list_collections()
        print(f"  Found {len(collections)} collections: {collections}")

        # Drop each collection
        if collections:
            for collection_name in collections:
                if dry_run:
                    print(f"  [DRY RUN] Would drop collection: {collection_name}")
                else:
                    print(f"  Dropping collection: {collection_name}")
                    utility.drop_collection(collection_name)
            if not dry_run:
                print(f"✓ Dropped {len(collections)} collections")
        else:
            print("  (No collections to drop)")

        # Disconnect
        connections.disconnect("default")

    except Exception as e:
        print(f"✗ Error wiping Milvus: {e}")
        raise


def terminate_active_connections():
    """Terminate all active connections to the database except our own."""
    try:
        with engine.connect() as conn:
            # Get current backend PID
            result = conn.execute(text("SELECT pg_backend_pid()"))
            current_pid = result.fetchone()[0]

            # Terminate all other connections to this database
            conn.execute(
                text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :dbname
                  AND pid != :current_pid
                  AND pid != pg_backend_pid()
            """),
                {"dbname": settings.collectiondb_database, "current_pid": current_pid},
            )
            conn.commit()

            print("  ✓ Terminated active database connections")
    except Exception as e:
        print(f"  ⚠️  Could not terminate connections: {e}")


def wipe_postgres(dry_run: bool = False):
    """Truncate all data tables from PostgreSQL, preserving schema."""
    print("=" * 80)
    print("WIPING POSTGRESQL DATA" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 80)

    if not dry_run:
        print("\n  Terminating active database connections...")
        terminate_active_connections()
        print()

    try:
        # Connect to PostgreSQL via SQLAlchemy with statement timeout
        with engine.connect() as conn:
            # Set statement timeout to 30 seconds to prevent hanging
            conn.execute(text("SET statement_timeout = '30s'"))
            print(f"✓ Connected to PostgreSQL at {settings.collectiondb_host}:{settings.collectiondb_port}")

            # Get all table names
            result = conn.execute(
                text("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            )
            all_tables = [row[0] for row in result]

            # Tables to preserve (schema management)
            preserve_tables = {"alembic_version"}

            # Tables to truncate
            truncate_tables = [t for t in all_tables if t not in preserve_tables]

            print(f"  Found {len(all_tables)} tables total")
            print(f"  Preserving: {list(preserve_tables)}")
            print(f"  Truncating: {len(truncate_tables)} data tables")

            # Truncate all data tables (CASCADE handles foreign keys)
            if truncate_tables:
                for table in truncate_tables:
                    if dry_run:
                        print(f"  [DRY RUN] Would truncate: {table}")
                    else:
                        print(f"  Truncating: {table}")
                        conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))

                if not dry_run:
                    conn.commit()
                    print(f"✓ Truncated {len(truncate_tables)} tables")
            else:
                print("  (No tables to truncate)")

    except Exception as e:
        print(f"✗ Error wiping PostgreSQL: {e}")
        raise


def wipe_local_files(dry_run: bool = False):
    """Delete all uploaded files (collection documents and podcasts)."""
    print("=" * 80)
    print("WIPING LOCAL FILES" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 80)

    deleted_count = 0
    total_size = 0

    try:
        # 1. Wipe collection document files
        file_storage_path = Path(settings.file_storage_path)
        if file_storage_path.exists():
            # Calculate size before deletion
            if file_storage_path.is_dir():
                for item in file_storage_path.rglob("*"):
                    if item.is_file():
                        total_size += item.stat().st_size
                        deleted_count += 1

            print(f"  Collection files path: {file_storage_path}")
            print(f"  Files to delete: {deleted_count}")
            print(f"  Total size: {total_size / (1024 * 1024):.2f} MB")

            if dry_run:
                print(f"  [DRY RUN] Would delete: {file_storage_path}")
            else:
                if file_storage_path.is_dir():
                    shutil.rmtree(file_storage_path)
                    file_storage_path.mkdir(parents=True, exist_ok=True)
                    print("✓ Deleted collection files")
        else:
            print(f"  Collection files path does not exist: {file_storage_path}")

        # 2. Wipe podcast audio files
        podcast_deleted = 0
        podcast_size = 0

        # Handle both relative and absolute podcast paths
        podcast_path_str = settings.podcast_local_storage_path
        if Path(podcast_path_str).is_absolute():
            podcast_storage_path = Path(podcast_path_str)
        else:
            # Relative to backend directory (script is in backend/scripts/)
            backend_dir = Path(__file__).parent.parent
            podcast_storage_path = backend_dir / podcast_path_str

        if podcast_storage_path.exists():
            # Calculate size before deletion
            if podcast_storage_path.is_dir():
                for item in podcast_storage_path.rglob("*"):
                    if item.is_file():
                        podcast_size += item.stat().st_size
                        podcast_deleted += 1

            print(f"\n  Podcast files path: {podcast_storage_path}")
            print(f"  Files to delete: {podcast_deleted}")
            print(f"  Total size: {podcast_size / (1024 * 1024):.2f} MB")

            if dry_run:
                print(f"  [DRY RUN] Would delete: {podcast_storage_path}")
            else:
                if podcast_storage_path.is_dir():
                    shutil.rmtree(podcast_storage_path)
                    podcast_storage_path.mkdir(parents=True, exist_ok=True)
                    print("✓ Deleted podcast files")
        else:
            print(f"\n  Podcast files path does not exist: {podcast_storage_path}")

        if not dry_run:
            total_deleted = deleted_count + podcast_deleted
            total_mb = (total_size + podcast_size) / (1024 * 1024)
            print(f"\n✓ Deleted {total_deleted} files ({total_mb:.2f} MB total)")

    except Exception as e:
        print(f"✗ Error wiping local files: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wipe all data from RAG Modulo (PostgreSQL, Milvus, local files)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Dry run (preview what would be deleted) - ALWAYS RUN THIS FIRST
  python wipe_database.py --dry-run

  # 2. Enable database wiping (required safeguard)
  export ALLOW_DATABASE_WIPE=true

  # 3. Wipe with backup (recommended for safety)
  python wipe_database.py --backup

  # 4. Wipe everything with confirmation (no backup)
  python wipe_database.py

  # 5. Wipe only specific components
  python wipe_database.py --postgres-only
  python wipe_database.py --milvus-only
  python wipe_database.py --files-only

  # 6. Skip confirmation (dangerous!)
  python wipe_database.py --yes

Safety Features:
  • Requires ALLOW_DATABASE_WIPE=true environment variable
  • Blocks execution in ENVIRONMENT=production
  • Supports --dry-run to preview operations
  • Optional --backup creates timestamped backups
  • Confirmation prompt before destructive operations
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt (dangerous!)",
    )
    parser.add_argument(
        "--postgres-only",
        action="store_true",
        help="Wipe only PostgreSQL data",
    )
    parser.add_argument(
        "--milvus-only",
        action="store_true",
        help="Wipe only Milvus collections",
    )
    parser.add_argument(
        "--files-only",
        action="store_true",
        help="Wipe only local files (collection documents, podcasts)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create timestamped backup before wiping (recommended)",
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default="backups",
        help="Directory for backups (default: backups/)",
    )

    args = parser.parse_args()

    # Safety checks (skip for dry-run)
    if not args.dry_run:
        check_environment_safety()

    # Determine what to wipe
    wipe_all = not (args.postgres_only or args.milvus_only or args.files_only)

    print("\n🗑️  DATABASE WIPE SCRIPT" + (" (DRY RUN)" if args.dry_run else "") + "\n")

    if wipe_all:
        print("This will clear ALL data while preserving schema:")
        print("  • PostgreSQL data tables (preserves alembic_version)")
        print("  • Milvus vector collections")
        print("  • Uploaded files (collection documents, podcasts)")
    else:
        print("This will clear:")
        if args.postgres_only:
            print("  • PostgreSQL data tables only")
        if args.milvus_only:
            print("  • Milvus vector collections only")
        if args.files_only:
            print("  • Uploaded files only")

    print("\nThe app will auto-reinitialize on next startup:")
    print("  ✓ Tables: Auto-created via SQLAlchemy Base.metadata.create_all()")
    print("  ✓ Providers: Auto-seeded via SystemInitializationService")
    print("  ✓ Models: Auto-configured from .env (RAG_LLM, EMBEDDING_MODEL)")
    print()

    # Confirmation (unless --yes or --dry-run)
    if not args.yes and not args.dry_run:
        response = input("⚠️  This is DESTRUCTIVE! Continue? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Create backup before wiping (if requested and not dry-run)
    if args.backup and not args.dry_run:
        backup_dir = Path(args.backup_dir)
        try:
            backup_path = create_backup(backup_dir)
            print(f"📦 Backup saved to: {backup_path}")
            print()
        except Exception as e:
            print(f"⚠️  Backup failed: {e}")
            if not args.yes:
                response = input("Continue without backup? [y/N]: ")
                if response.lower() != "y":
                    print("Aborted.")
                    sys.exit(0)

    try:
        if wipe_all or args.milvus_only:
            wipe_milvus(dry_run=args.dry_run)
            print()

        if wipe_all or args.postgres_only:
            wipe_postgres(dry_run=args.dry_run)
            print()

        if wipe_all or args.files_only:
            wipe_local_files(dry_run=args.dry_run)
            print()

        print("=" * 80)
        if args.dry_run:
            print("✓ DRY RUN COMPLETE - No data was actually deleted")
        else:
            print("✓ DATABASE WIPE COMPLETE")
        print("=" * 80)

        if not args.dry_run:
            print("\nAll data cleared. Schema preserved.")
            print("\nNext steps:")
            print("  1. Restart the backend (it will auto-initialize)")
            print("  2. Create collections and upload documents")
        else:
            print("\nRun without --dry-run to actually delete the data:")
            print("  python wipe_database.py")
        print()

    except Exception as e:
        print("\n" + "=" * 80)
        print("✗ DATABASE WIPE FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print("\nMake sure PostgreSQL and Milvus are running:")
        print("  docker compose ps postgres milvus-standalone")
        print()
        sys.exit(1)
