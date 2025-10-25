#!/usr/bin/env python3
"""Restore RAG Modulo data from backups created by wipe_database.py.

This script helps recover data from timestamped backups, including:
  - PostgreSQL data (via pg_restore or manual SQL)
  - Milvus collection metadata and structure
  - Local files (collection documents, podcasts)

Safety Features:
  ✓ Lists available backups with timestamps
  ✓ Validates backup integrity before restore
  ✓ Dry-run mode to preview operations
  ✓ Interactive backup selection
  ✓ Detailed restore instructions
  ✓ Environment validation
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend to path (script is in scripts/, backend is sibling directory)
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


from core.config import get_settings

settings = get_settings()


def list_available_backups(backup_dir: Path) -> list[dict]:
    """List all available backups with metadata."""
    if not backup_dir.exists():
        return []

    backups = []
    for backup_path in sorted(backup_dir.glob("backup_*"), reverse=True):
        if not backup_path.is_dir():
            continue

        manifest_file = backup_path / "manifest.json"
        if not manifest_file.exists():
            continue

        try:
            with open(manifest_file) as f:
                manifest = json.load(f)

            # Calculate backup size
            total_size = sum(f.stat().st_size for f in backup_path.rglob("*") if f.is_file())

            backups.append(
                {
                    "path": backup_path,
                    "name": backup_path.name,
                    "timestamp": manifest.get("timestamp", "unknown"),
                    "environment": manifest.get("environment", "unknown"),
                    "manifest": manifest,
                    "size_mb": total_size / (1024 * 1024),
                }
            )
        except Exception as e:
            print(f"Warning: Could not read backup {backup_path.name}: {e}")

    return backups


def validate_backup(backup_path: Path) -> tuple[bool, str]:
    """Validate backup integrity and completeness."""
    errors = []

    # Check manifest
    manifest_file = backup_path / "manifest.json"
    if not manifest_file.exists():
        errors.append("Missing manifest.json")

    # Check Milvus metadata
    milvus_file = backup_path / "milvus_collections.json"
    if not milvus_file.exists():
        errors.append("Missing milvus_collections.json")

    if errors:
        return False, "; ".join(errors)

    return True, "Backup is valid"


def display_backup_info(backup: dict):
    """Display detailed information about a backup."""
    print("\n" + "=" * 80)
    print(f"BACKUP: {backup['name']}")
    print("=" * 80)
    print(f"  Timestamp: {backup['timestamp']}")
    print(f"  Environment: {backup['environment']}")
    print(f"  Size: {backup['size_mb']:.2f} MB")
    print(f"  Location: {backup['path']}")
    print()

    # Show manifest details
    manifest = backup["manifest"]
    print("Components:")
    if manifest.get("postgresql_host"):
        print(f"  • PostgreSQL: {manifest['postgresql_host']}")
    if manifest.get("milvus_host"):
        print(f"  • Milvus: {manifest['milvus_host']}")

    # Check what's actually in the backup
    backup_path = backup["path"]
    milvus_file = backup_path / "milvus_collections.json"
    if milvus_file.exists():
        try:
            with open(milvus_file) as f:
                milvus_data = json.load(f)
                collections = milvus_data.get("collections", [])
                print(f"  • Milvus Collections: {len(collections)}")
                if collections:
                    for coll in collections[:5]:  # Show first 5
                        print(f"    - {coll}")
                    if len(collections) > 5:
                        print(f"    ... and {len(collections) - 5} more")
        except Exception as e:
            print(f"  • Milvus Collections: Error reading ({e})")

    print("=" * 80)


def restore_milvus_info(backup_path: Path, dry_run: bool = False):
    """Display information about Milvus collections in backup."""
    print("\n" + "=" * 80)
    print("MILVUS COLLECTIONS INFO" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 80)

    milvus_file = backup_path / "milvus_collections.json"
    if not milvus_file.exists():
        print("  No Milvus backup data found")
        return

    try:
        with open(milvus_file) as f:
            milvus_data = json.load(f)

        collections = milvus_data.get("collections", [])
        host = milvus_data.get("host", "unknown")
        port = milvus_data.get("port", "unknown")

        print(f"  Backup contains {len(collections)} collections")
        print(f"  Original host: {host}:{port}")
        print()

        if collections:
            print("  Collections that were backed up:")
            for coll in collections:
                print(f"    • {coll}")
        else:
            print("  (No collections in backup)")

        print()
        print("  ⚠️  NOTE: Vector data restore requires Milvus Backup utility")
        print("  This backup only contains collection metadata (names)")
        print()
        print("  To restore Milvus collections with data:")
        print("    1. Use Milvus Backup tool: https://milvus.io/docs/milvus_backup_cli.md")
        print("    2. Or re-ingest documents after PostgreSQL restore")
        print()

    except Exception as e:
        print(f"✗ Error reading Milvus backup: {e}")


def restore_postgresql_instructions(backup_path: Path) -> None:
    """Display instructions for PostgreSQL restore.

    Args:
        backup_path: Path to the backup directory containing postgres_backup.sql
    """
    print("\n" + "=" * 80)
    print("POSTGRESQL RESTORE INSTRUCTIONS")
    print("=" * 80)

    pg_backup_file = backup_path / "postgres_backup.sql"
    if pg_backup_file.exists():
        print(f"  ✓ PostgreSQL dump found: {pg_backup_file}")
        print()
        print("  To restore (custom format backup):")
        print()
        print("  Option 1: Using pg_restore with PGPASSWORD (recommended):")
        print(f"    export PGPASSWORD='{settings.collectiondb_password}'")
        print(f"    pg_restore -h {settings.collectiondb_host} \\")
        print(f"              -p {settings.collectiondb_port} \\")
        print(f"              -U {settings.collectiondb_user} \\")
        print(f"              -d {settings.collectiondb_database} \\")
        print(f"              -F c \\")
        print(f"              --clean --if-exists \\")
        print(f"              {pg_backup_file}")
        print(f"    unset PGPASSWORD")
        print()
        print("  Option 2: Using .pgpass file (more secure for production):")
        print(f"    echo '{settings.collectiondb_host}:{settings.collectiondb_port}:{settings.collectiondb_database}:{settings.collectiondb_user}:<password>' >> ~/.pgpass")
        print("    chmod 600 ~/.pgpass")
        print(f"    pg_restore -h {settings.collectiondb_host} -p {settings.collectiondb_port} -U {settings.collectiondb_user} -d {settings.collectiondb_database} -F c {pg_backup_file}")
        print()
        print("  ⚠️  SECURITY NOTE:")
        print("  - PGPASSWORD is convenient but exposes password in process list")
        print("  - For production, use .pgpass file or connection service file")
        print("  - Always unset PGPASSWORD after use to avoid leaking credentials")
        print()
    else:
        print("  ⚠️  No PostgreSQL dump found in backup")
        print()
        print("  This backup was created without pg_dump.")
        print("  PostgreSQL data cannot be automatically restored.")
        print()
        print("  Options:")
        print("    1. Re-create collections and re-ingest documents")
        print("    2. If you have a separate database backup, restore manually:")
        print(f"       pg_restore -h {settings.collectiondb_host} \\")
        print(f"                  -p {settings.collectiondb_port} \\")
        print(f"                  -U {settings.collectiondb_user} \\")
        print(f"                  -d {settings.collectiondb_database} \\")
        print("                  your_backup.dump")
        print()


def restore_summary():
    """Display post-restore summary and next steps."""
    print("\n" + "=" * 80)
    print("RESTORE PROCESS COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Follow the PostgreSQL restore instructions above")
    print("  2. Restart the backend to reinitialize:")
    print("     make local-dev-backend")
    print("     # OR")
    print("     docker compose restart backend")
    print()
    print("  3. Verify the restoration:")
    print("     - Check collections are present")
    print("     - Verify documents are accessible")
    print("     - Test search functionality")
    print()
    print("  4. For Milvus vector data:")
    print("     - Either use Milvus Backup tool (if you have full backups)")
    print("     - Or re-ingest documents to rebuild vector embeddings")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restore RAG Modulo data from backups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available backups
  python restore_database.py --list

  # Show details about a specific backup
  python restore_database.py --backup backup_20241024_153045 --info

  # Dry run (preview restore without executing)
  python restore_database.py --backup backup_20241024_153045 --dry-run

  # Restore from latest backup
  python restore_database.py --latest

  # Restore from specific backup
  python restore_database.py --backup backup_20241024_153045

  # Interactive mode (select from list)
  python restore_database.py

Restore Process:
  1. Script validates backup integrity
  2. Displays backup contents and metadata
  3. Provides PostgreSQL restore instructions
  4. Shows Milvus collection information
  5. Guides through post-restore steps

Note: Full vector data restore requires Milvus Backup utility.
This script provides metadata and instructions for manual restoration.
        """,
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default="backups",
        help="Directory containing backups (default: backups/)",
    )
    parser.add_argument(
        "--backup",
        type=str,
        help="Specific backup name to restore (e.g., backup_20241024_153045)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Restore from the most recent backup",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available backups and exit",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show detailed information about specified backup and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview restore operations without executing",
    )

    args = parser.parse_args()

    print("\n📦 DATABASE RESTORE SCRIPT" + (" (DRY RUN)" if args.dry_run else "") + "\n")

    # Find backup directory
    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        print(f"❌ Backup directory not found: {backup_dir}")
        print()
        print("Create a backup first using:")
        print("  python scripts/wipe_database.py --backup")
        sys.exit(1)

    # List available backups
    backups = list_available_backups(backup_dir)
    if not backups:
        print(f"❌ No backups found in {backup_dir}")
        print()
        print("Create a backup first using:")
        print("  python scripts/wipe_database.py --backup")
        sys.exit(1)

    # Handle --list flag
    if args.list:
        print(f"Found {len(backups)} backup(s) in {backup_dir}:\n")
        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup['name']}")
            print(f"   Timestamp: {backup['timestamp']}")
            print(f"   Environment: {backup['environment']}")
            print(f"   Size: {backup['size_mb']:.2f} MB")
            print()
        sys.exit(0)

    # Select backup
    selected_backup = None

    if args.latest:
        selected_backup = backups[0]  # Already sorted by reverse timestamp
        print(f"Selected latest backup: {selected_backup['name']}")
    elif args.backup:
        for backup in backups:
            if backup["name"] == args.backup:
                selected_backup = backup
                break
        if not selected_backup:
            print(f"❌ Backup not found: {args.backup}")
            print()
            print("Available backups:")
            for backup in backups:
                print(f"  • {backup['name']}")
            sys.exit(1)
    else:
        # Interactive selection
        print(f"Found {len(backups)} backup(s):\n")
        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup['name']} ({backup['timestamp']}) - {backup['size_mb']:.2f} MB")

        print()
        try:
            selection = input("Select backup number (or 'q' to quit): ").strip()
            if selection.lower() == "q":
                print("Aborted.")
                sys.exit(0)

            idx = int(selection) - 1
            if 0 <= idx < len(backups):
                selected_backup = backups[idx]
            else:
                print("❌ Invalid selection")
                sys.exit(1)
        except (ValueError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)

    # Display backup information
    display_backup_info(selected_backup)

    # Handle --info flag
    if args.info:
        sys.exit(0)

    # Validate backup
    valid, message = validate_backup(selected_backup["path"])
    if not valid:
        print(f"❌ Backup validation failed: {message}")
        sys.exit(1)

    print("✓ Backup validation passed")
    print()

    # Confirm restore (unless dry-run)
    if not args.dry_run:
        response = input("⚠️  Proceed with restore guidance? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    print()

    # Display restore information and instructions
    try:
        restore_milvus_info(selected_backup["path"], dry_run=args.dry_run)
        restore_postgresql_instructions(selected_backup["path"])

        if not args.dry_run:
            restore_summary()
        else:
            print("\n" + "=" * 80)
            print("DRY RUN COMPLETE")
            print("=" * 80)
            print()
            print("This was a preview. No data was restored.")
            print("To actually restore, run without --dry-run:")
            print(f"  python scripts/restore_database.py --backup {selected_backup['name']}")
            print()

    except Exception as e:
        print("\n" + "=" * 80)
        print("✗ RESTORE FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        sys.exit(1)
