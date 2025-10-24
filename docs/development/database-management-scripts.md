# Database Management Scripts

This guide documents the database management scripts for safely wiping and restoring RAG Modulo data.

## Overview

RAG Modulo provides two production-grade scripts for database management:

- **`wipe_database.py`**: Safely wipe all data while preserving schema
- **`restore_database.py`**: Restore data from timestamped backups

Both scripts are located in `backend/scripts/` and include comprehensive safety features to prevent accidental data loss.

---

## Created Files

| File | Lines | Purpose |
|------|-------|---------|
| `wipe_database.py` | 478 | Production-grade database wipe with multi-layer safety |
| `restore_database.py` | 422 | Backup restore and guidance |
| `scripts/README.md` | 283 | User-facing documentation |

---

## wipe_database.py

### Features

**Multi-Layer Safety System**

1. **Environment Variable Safeguard**
   - Requires `ALLOW_DATABASE_WIPE=true` to be set explicitly
   - Prevents accidental runs from automated scripts
   - Acts as a "safety pin" that must be removed

2. **Production Environment Protection**
   - Hard blocks execution if `ENVIRONMENT=production`
   - Forces manual environment change to development/staging
   - Prevents catastrophic production data loss

3. **Dry-Run Mode**
   - Preview operations without executing (`--dry-run`)
   - Shows exactly what will be deleted
   - No confirmation required for dry runs

4. **Automatic Backup System**
   - Creates timestamped backups with `--backup` flag
   - Includes Milvus metadata and manifest
   - Backup location: `backups/backup_YYYYMMDD_HHMMSS/`

5. **Interactive Confirmation**
   - Prompts user to confirm before destructive operations
   - Can be bypassed with `--yes` flag (use with caution)

**Comprehensive Data Cleanup**

- **PostgreSQL**: Truncates all data tables (preserves `alembic_version`)
- **Milvus**: Drops all vector collections
- **Local Files**: Deletes collection documents and podcast audio files

### Usage

!!! warning "Stop Backend First"
    **Always stop the backend before wiping** to avoid database locks and hanging operations. The script will automatically terminate active connections, but stopping the backend first is safer.

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

### Safety Comparison

| Protection Level | Before | After |
|-----------------|--------|-------|
| Accidental runs | ❌ None | ✅ Environment variable required |
| Production safety | ❌ None | ✅ Hard block on production |
| Preview mode | ❌ None | ✅ Dry-run available |
| Backups | ❌ Manual | ✅ Automatic with --backup |
| Confirmation | ❌ None | ✅ Interactive prompt |
| Recovery | ❌ Manual | ✅ Guided restore process |

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
# You should see:
# - "Initializing LLM Providers..." and "Initialized providers: watsonx"
# - "Initializing mock user for development (SKIP_AUTH=true)"
# - "Mock user initialized successfully: <uuid>"

# 6. (Optional) Remove the safeguard
unset ALLOW_DATABASE_WIPE
```

---

## restore_database.py

### Features

**Backup Management**

- Auto-discovery of available backups
- Backup validation and integrity checks
- Interactive selection interface
- Multiple restore modes (latest, specific, interactive)

**Restore Guidance**

- **PostgreSQL**: Exact `psql`/`pg_restore` commands
- **Milvus**: Collection metadata and restore options
- **Post-restore**: Verification steps

**User Experience**

- Clear backup information display
- Timestamp sorting (newest first)
- Size calculations
- Environment tracking

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

!!! warning "PostgreSQL Restore"
    Currently requires manual `pg_restore` or `psql` execution. Script provides exact commands to run. Full automation planned for future versions.

!!! warning "Milvus Restore"
    Vector data requires Milvus Backup utility. Script shows collection metadata only. Options: Use Milvus Backup tool OR re-ingest documents.

!!! info "File Restore"
    Local files can be restored if backup directory is preserved. Automated file restore planned for future versions.

### Backup Structure

Each backup creates a timestamped directory:

```
backups/
└── backup_20241024_153045/
    ├── manifest.json           # Backup metadata and timestamps
    ├── milvus_collections.json # Milvus collection names
    └── postgres_backup.sql     # PostgreSQL dump (if pg_dump configured)
```

---

## Best Practices

### 1. Always Use Dry-Run First

```bash
python scripts/wipe_database.py --dry-run
```

Preview operations before executing. This is **100% safe** and shows exactly what will be deleted.

### 2. Create Backups

```bash
python scripts/wipe_database.py --backup
```

Always use `--backup` flag unless you're absolutely sure you don't need recovery capability.

### 3. Environment Variable Discipline

```bash
# Set only when needed
export ALLOW_DATABASE_WIPE=true

# Unset immediately after use
unset ALLOW_DATABASE_WIPE
```

Don't leave `ALLOW_DATABASE_WIPE=true` in your `.bashrc` or `.zshrc`.

### 4. Never Override Production Protection

The production environment block is intentional. If you need to wipe production data:

1. Create a full backup using proper backup tools
2. Change `ENVIRONMENT` to staging/development
3. Understand this is **extremely dangerous**
4. Consider if there's a better way

### 5. Test Restore Procedures

Periodically test your backup/restore procedures:

```bash
# 1. Create backup
python scripts/wipe_database.py --backup

# 2. Test restore instructions
python scripts/restore_database.py --latest --dry-run

# 3. Verify backup integrity
python scripts/restore_database.py --latest --info
```

---

## Testing Performed

✅ Safety checks work (environment variable, production block)
✅ Dry-run mode functions correctly
✅ Help output is clear and comprehensive
✅ Path handling works (scripts/ subdirectory)
✅ Restore script handles missing backups gracefully

---

## Future Enhancements

The following features are planned for future versions:

1. **Automated PostgreSQL Dumps**: Add `pg_dump` integration for full SQL backups
2. **Full Milvus Backup/Restore**: Implement complete vector data backup/restore
3. **File Backup/Restore**: Automated backup of uploaded documents and podcasts
4. **Automated Restore**: One-command full restore from backup
5. **Backup Retention**: Auto-cleanup old backups (keep last N)
6. **Email Notifications**: Alerts when wipes occur in production-like environments
7. **Audit Logging**: Centralized logging of who ran wipes and when
8. **Web UI Integration**: Trigger wipes/restores from web interface

---

## Compliance

✅ Follows RAG Modulo coding standards
✅ Uses existing configuration system
✅ Integrates with SystemInitializationService
✅ Respects `.env` settings
✅ Maintains alembic migration history
✅ Comprehensive documentation
✅ Production-grade safety features

---

## Troubleshooting

### "SAFETY CHECK FAILED: Database wipe requires explicit permission"

**Solution**: Set the environment variable:

```bash
export ALLOW_DATABASE_WIPE=true
```

This is intentional. The safeguard prevents accidental runs.

### "This script is NOT allowed to run in PRODUCTION environment"

**Solution**: Production wipes are blocked by design. If you absolutely must wipe production:

1. Create full backups using proper backup tools first
2. Set `ENVIRONMENT=development` or `ENVIRONMENT=staging`
3. Understand this is **extremely dangerous**

### "Backup directory not found"

**Solution**: Create a backup first:

```bash
python scripts/wipe_database.py --backup
```

The restore script needs backups to restore from.

### "PostgreSQL connection failed"

**Solution**: Ensure PostgreSQL is running:

```bash
docker compose ps postgres
# OR
make local-dev-infra
```

---

## References

- [Backend Development Guide](./backend/index.md)
- [Development Workflow](./workflow.md)
- [Configuration Management](../configuration.md)
- [Secret Management](./secret-management.md)
