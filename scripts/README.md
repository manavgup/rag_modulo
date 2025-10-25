# Database Management Scripts

Utility scripts for database management and administration located in `scripts/` (project root).

## Table of Contents

- [wipe_database.py](#wipe_databasepy) - Safely wipe all data while preserving schema
- [restore_database.py](#restore_databasepy) - Restore data from backups

---

## wipe_database.py

Safely wipes all data from RAG Modulo while preserving database schema structure. The application will automatically reinitialize on next startup.

### What It Wipes

- **PostgreSQL**: All data tables (preserves `alembic_version` for migrations)
- **Milvus**: All vector collections
- **Local Files**: Uploaded collection documents and podcast audio files

### Usage

**⚠️ IMPORTANT: Stop the backend before wiping to avoid database locks**

```bash
# Step 0: Stop the backend to release database connections (RECOMMENDED)
make local-dev-stop
# OR
docker compose stop backend

# Step 1: ALWAYS preview first with dry-run
python scripts/wipe_database.py --dry-run

# Step 2: Enable database wiping (required safeguard)
export ALLOW_DATABASE_WIPE=true

# Step 3: Wipe with automatic backup (RECOMMENDED)
python scripts/wipe_database.py --backup

# Alternative: Wipe without backup (requires confirmation)
python scripts/wipe_database.py

# Wipe only specific components
python scripts/wipe_database.py --postgres-only
python scripts/wipe_database.py --milvus-only
python scripts/wipe_database.py --files-only

# Skip confirmation (dangerous!)
python scripts/wipe_database.py --yes
```

### Best Practices & Safety Features

**Multiple Layers of Protection:**

1. **Environment Variable Safeguard**
   - Requires `ALLOW_DATABASE_WIPE=true` to be set explicitly
   - Prevents accidental runs when variable is not set
   - Acts as a "safety pin" that must be removed

2. **Production Environment Protection**
   - **BLOCKS execution** if `ENVIRONMENT=production`
   - Forces you to change environment first (development/staging)
   - Prevents catastrophic production data loss

3. **Dry-Run Mode**
   - `--dry-run` flag previews operations without executing
   - Shows exactly what would be deleted
   - No confirmation required for dry runs

4. **Automatic Backup Option**
   - `--backup` flag creates timestamped backups before wiping
   - Stores Milvus metadata and manifest
   - Backup location: `backups/backup_YYYYMMDD_HHMMSS/`
   - Allows recovery if needed

5. **Interactive Confirmation**
   - Prompts user to confirm before destructive operations
   - Requires typing 'y' to proceed
   - Can be bypassed with `--yes` flag (use with extreme caution)

6. **Schema Preservation**
   - `alembic_version` table kept intact for migrations
   - Database structure preserved
   - Only data is wiped, not schema

7. **Foreign Key Safety**
   - `TRUNCATE CASCADE` handles dependencies correctly
   - No orphaned references or constraint violations

8. **Sequence Reset**
   - `RESTART IDENTITY` resets auto-increment counters
   - Clean slate for IDs starting from 1

### What Gets Auto-Reinitialized

On next application startup (main.py:lifespan):

1. **Tables** - Created via `Base.metadata.create_all()`
2. **Providers** - Seeded from .env via `SystemInitializationService`
3. **Models** - Configured from RAG_LLM and EMBEDDING_MODEL settings
4. **Users** - Mock user automatically created when SKIP_AUTH=true (development mode)

### Example Workflow

```bash
# 1. Preview the operation (no safeguards needed for dry-run)
python scripts/wipe_database.py --dry-run

# 2. Enable database wiping
export ALLOW_DATABASE_WIPE=true

# 3. Wipe with automatic backup (RECOMMENDED)
python scripts/wipe_database.py --backup
# Backup saved to: backups/backup_20241024_153045/

# 4. Restart the backend to auto-initialize
make local-dev-backend
# OR
docker compose restart backend

# 5. Verify initialization in logs
# You should see: "Initializing LLM Providers..." and "Initialized providers: watsonx"

# 6. (Optional) Remove the safeguard
unset ALLOW_DATABASE_WIPE
```

### Recovering from Backup

If you used `--backup` and need to restore:

```bash
# 1. Check the backup manifest
cat backups/backup_20241024_153045/manifest.json

# 2. Restore Milvus collections (manual - refer to Milvus docs)
# 3. Restore PostgreSQL data (requires pg_restore or manual SQL)

# Note: Full automated restore is not yet implemented
# Backups are primarily for disaster recovery reference
```

### Requirements

- PostgreSQL must be running (for database wipe)
- Milvus must be running (for vector wipe)
- Script will fail gracefully if services are unavailable

### Safety Features

- **Confirmation prompt** before destructive operations
- **Dry-run mode** to preview without deleting
- **Selective wiping** with component-specific flags
- **Preserves schema** structure and migration history
- **Clear error messages** with troubleshooting hints

---

## restore_database.py

Restore RAG Modulo data from backups created by `wipe_database.py`. Provides guidance and metadata for manual restoration.

### What It Restores

- **PostgreSQL**: Provides instructions for restoring from SQL dumps
- **Milvus**: Shows collection metadata and restore guidance
- **Local Files**: Lists backed-up files (if implemented)

### Usage

```bash
# List all available backups
python scripts/restore_database.py --list

# Interactive mode (select from list)
python scripts/restore_database.py

# Restore from latest backup
python scripts/restore_database.py --latest

# Restore from specific backup
python scripts/restore_database.py --backup backup_20241024_153045

# Show backup details without restoring
python scripts/restore_database.py --backup backup_20241024_153045 --info

# Dry run (preview without executing)
python scripts/restore_database.py --backup backup_20241024_153045 --dry-run
```

### Features

**1. Backup Discovery**

- Auto-scans backup directory for valid backups
- Sorts by timestamp (newest first)
- Validates backup integrity before restore

**2. Interactive Selection**

- Lists all available backups with metadata
- Shows timestamp, environment, and size
- User-friendly selection interface

**3. Backup Validation**

- Checks manifest.json exists
- Validates Milvus metadata
- Reports any missing components

**4. Restore Guidance**

- PostgreSQL: Exact `psql`/`pg_restore` commands
- Milvus: Collection list and restore options
- Clear next steps for post-restore verification

**5. Multiple Restore Modes**

- `--latest`: Auto-select most recent backup
- `--backup NAME`: Restore specific backup
- Interactive: Choose from list
- `--dry-run`: Preview without changes

### Example Workflow

```bash
# 1. List available backups
python scripts/restore_database.py --list

# Output:
# Found 3 backup(s) in backups/:
#
# 1. backup_20241024_153045
#    Timestamp: 20241024_153045
#    Environment: development
#    Size: 2.34 MB
#
# 2. backup_20241024_120000
#    Timestamp: 20241024_120000
#    Environment: development
#    Size: 1.89 MB

# 2. Check backup details
python scripts/restore_database.py --backup backup_20241024_153045 --info

# 3. Restore (provides instructions)
python scripts/restore_database.py --latest

# 4. Follow the displayed instructions:
#    - Run pg_restore command for PostgreSQL
#    - Re-ingest documents for Milvus vectors
#    - Restart backend

# 5. Verify restoration
curl http://localhost:8000/health
# Check collections in UI
```

### Current Limitations

**PostgreSQL Restore:**

- ⚠️ Currently requires manual `pg_restore` or `psql` execution
- Script provides exact commands to run
- Full automation planned for future versions

**Milvus Restore:**

- ⚠️ Vector data requires Milvus Backup utility
- Script shows collection metadata only
- Options: Use Milvus Backup tool OR re-ingest documents

**File Restore:**

- Local files can be restored if backup directory is preserved
- Automated file restore planned for future versions

### Backup Structure

Each backup creates a timestamped directory:

```
backups/
└── backup_20241024_153045/
    ├── manifest.json           # Backup metadata and timestamps
    ├── milvus_collections.json # Milvus collection names
    └── postgres_backup.sql     # PostgreSQL dump (if pg_dump configured)
```

### Requirements

- Python 3.8+
- Access to backup directory (default: `backups/`)
- PostgreSQL client tools (`psql`, `pg_restore`) for database restore
- Milvus connection for collection validation
