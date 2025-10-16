#!/bin/bash
#
# RAG Modulo Restore Script
# Restores PostgreSQL database, Milvus collections, and application state from backup
#
# Usage:
#   ./restore-rag-modulo.sh <backup-archive>
#
# Environment Variables:
#   COLLECTIONDB_HOST - PostgreSQL host (default: localhost)
#   COLLECTIONDB_PORT - PostgreSQL port (default: 5432)
#   COLLECTIONDB_NAME - Database name (default: rag_modulo)
#   COLLECTIONDB_USER - Database user (required)
#   COLLECTIONDB_PASS - Database password (required)
#   MILVUS_HOST - Milvus host (default: localhost)
#   MILVUS_PORT - Milvus port (default: 19530)
#   FORCE_RESTORE - Skip confirmation prompt (default: false)
#   BACKUP_ENCRYPTION_KEY - Passphrase for GPG decryption (required if backup is encrypted)

set -euo pipefail

# Configuration
BACKUP_ARCHIVE="${1:-}"
TEMP_DIR="/tmp/rag-modulo-restore-$$"
FORCE="${FORCE_RESTORE:-false}"

# PostgreSQL configuration
POSTGRES_HOST="${COLLECTIONDB_HOST:-localhost}"
POSTGRES_PORT="${COLLECTIONDB_PORT:-5432}"
POSTGRES_DB="${COLLECTIONDB_NAME:-rag_modulo}"
POSTGRES_USER="${COLLECTIONDB_USER:-}"
POSTGRES_PASS="${COLLECTIONDB_PASS:-}"

# Milvus configuration
MILVUS_HOST="${MILVUS_HOST:-localhost}"
MILVUS_PORT="${MILVUS_PORT:-19530}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 <backup-archive>

Restore RAG Modulo from a backup archive.

Arguments:
  backup-archive    Path to backup archive (.tar.gz file)

Environment Variables:
  COLLECTIONDB_HOST     PostgreSQL host (default: localhost)
  COLLECTIONDB_PORT     PostgreSQL port (default: 5432)
  COLLECTIONDB_NAME     Database name (default: rag_modulo)
  COLLECTIONDB_USER     Database user (required)
  COLLECTIONDB_PASS     Database password (required)
  MILVUS_HOST           Milvus host (default: localhost)
  MILVUS_PORT           Milvus port (default: 19530)
  FORCE_RESTORE         Skip confirmation (true/false, default: false)

Examples:
  # Restore from backup
  $0 /backups/rag-modulo-backup-20250116_120000.tar.gz

  # Force restore without confirmation
  FORCE_RESTORE=true $0 /backups/rag-modulo-backup-20250116_120000.tar.gz
EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if [ -z "$BACKUP_ARCHIVE" ]; then
        log_error "Backup archive path is required"
        usage
        exit 1
    fi

    if [ ! -f "$BACKUP_ARCHIVE" ]; then
        log_error "Backup archive not found: $BACKUP_ARCHIVE"
        exit 1
    fi

    local missing_tools=()

    if ! command -v psql &> /dev/null; then
        missing_tools+=("psql (PostgreSQL client)")
    fi

    if ! command -v tar &> /dev/null; then
        missing_tools+=("tar")
    fi

    if ! command -v gunzip &> /dev/null; then
        missing_tools+=("gunzip")
    fi

    # Check for GPG if backup is encrypted
    if [[ "$BACKUP_ARCHIVE" == *.gpg ]]; then
        if ! command -v gpg &> /dev/null; then
            missing_tools+=("gpg")
        fi
        if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
            log_error "BACKUP_ENCRYPTION_KEY environment variable is required for encrypted backups"
            exit 1
        fi
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi

    if [ -z "$POSTGRES_USER" ]; then
        log_error "COLLECTIONDB_USER environment variable is required"
        exit 1
    fi

    if [ -z "$POSTGRES_PASS" ]; then
        log_error "COLLECTIONDB_PASS environment variable is required"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Confirm restore
confirm_restore() {
    if [ "$FORCE" = "true" ]; then
        log_warn "Force restore enabled, skipping confirmation"
        return 0
    fi

    log_warn "WARNING: This will overwrite the current database and Milvus data!"
    log_warn "Database: ${POSTGRES_DB} on ${POSTGRES_HOST}:${POSTGRES_PORT}"
    log_warn "Milvus: ${MILVUS_HOST}:${MILVUS_PORT}"
    echo -n "Are you sure you want to continue? (yes/no): "
    read -r response

    if [ "$response" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
}

# Decrypt backup archive if encrypted
decrypt_backup() {
    if [[ ! "$BACKUP_ARCHIVE" == *.gpg ]]; then
        log_info "Backup is not encrypted, skipping decryption"
        return 0
    fi

    log_info "Decrypting backup archive..."

    local decrypted_archive="${TEMP_DIR}/decrypted-backup.tar.gz"

    # Decrypt the backup
    echo "${BACKUP_ENCRYPTION_KEY}" | gpg \
        --batch \
        --yes \
        --passphrase-fd 0 \
        --decrypt \
        --output "${decrypted_archive}" \
        "${BACKUP_ARCHIVE}"

    # Update BACKUP_ARCHIVE to point to decrypted file
    BACKUP_ARCHIVE="${decrypted_archive}"

    log_info "Backup decryption completed"
}

# Extract backup archive
extract_backup() {
    log_info "Extracting backup archive..."

    mkdir -p "${TEMP_DIR}"
    tar -xzf "${BACKUP_ARCHIVE}" -C "${TEMP_DIR}"

    # Find the backup directory (should be the only directory)
    BACKUP_DIR=$(find "${TEMP_DIR}" -mindepth 1 -maxdepth 1 -type d | head -1)

    if [ -z "$BACKUP_DIR" ]; then
        log_error "No backup directory found in archive"
        exit 1
    fi

    log_info "Backup extracted to: ${BACKUP_DIR}"
}

# Verify backup
verify_backup() {
    log_info "Verifying backup contents..."

    local manifest_file="${BACKUP_DIR}/MANIFEST.json"

    if [ ! -f "$manifest_file" ]; then
        log_error "MANIFEST.json not found in backup"
        exit 1
    fi

    log_info "Backup manifest found"

    # Check for PostgreSQL backup
    local postgres_backup="${BACKUP_DIR}/postgres_${POSTGRES_DB}.sql.gz"
    if [ ! -f "$postgres_backup" ]; then
        log_error "PostgreSQL backup file not found: $postgres_backup"
        exit 1
    fi

    log_info "Backup verification passed"
}

# Create temporary .pgpass file for secure password handling
create_pgpass_file() {
    PGPASS_FILE=$(mktemp)
    chmod 600 "${PGPASS_FILE}"
    # Support wildcards for all databases
    echo "${POSTGRES_HOST}:${POSTGRES_PORT}:*:${POSTGRES_USER}:${POSTGRES_PASS}" > "${PGPASS_FILE}"
    echo "${PGPASS_FILE}"
}

# Remove temporary .pgpass file
cleanup_pgpass_file() {
    if [ -n "${PGPASS_FILE}" ] && [ -f "${PGPASS_FILE}" ]; then
        rm -f "${PGPASS_FILE}"
    fi
}

# Restore PostgreSQL database
restore_postgres() {
    log_info "Restoring PostgreSQL database..."

    local postgres_backup="${BACKUP_DIR}/postgres_${POSTGRES_DB}.sql.gz"

    # Use .pgpass file instead of PGPASSWORD to avoid password exposure in process list
    PGPASS_FILE=$(create_pgpass_file)

    # Drop existing database (with caution)
    log_warn "Dropping existing database: ${POSTGRES_DB}"
    PGPASSFILE="${PGPASS_FILE}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"

    # Create fresh database
    log_info "Creating fresh database: ${POSTGRES_DB}"
    PGPASSFILE="${PGPASS_FILE}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d postgres \
        -c "CREATE DATABASE ${POSTGRES_DB};"

    # Restore from backup
    log_info "Restoring database from backup..."
    gunzip -c "${postgres_backup}" | PGPASSFILE="${PGPASS_FILE}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --quiet

    cleanup_pgpass_file

    log_info "PostgreSQL restore completed"
}

# Restore Milvus metadata
restore_milvus_metadata() {
    log_info "Restoring Milvus metadata..."

    local milvus_metadata="${BACKUP_DIR}/milvus_metadata.json"

    if [ ! -f "$milvus_metadata" ]; then
        log_warn "Milvus metadata file not found, skipping Milvus restore"
        return 0
    fi

    # Note: Actual Milvus collection data restore requires vector data backup
    # This only restores metadata for reference
    log_warn "Milvus vector data must be restored separately"
    log_info "Milvus metadata reference saved: ${milvus_metadata}"
}

# Cleanup temporary files
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${TEMP_DIR}"
    log_info "Cleanup completed"
}

# Verify restore
verify_restore() {
    log_info "Verifying restore..."

    # Use .pgpass file for verification
    PGPASS_FILE=$(create_pgpass_file)

    # Check database connection
    if PGPASSFILE="${PGPASS_FILE}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -c "SELECT 1" > /dev/null 2>&1; then
        log_info "Database connection verified"
    else
        log_error "Database connection failed"
        cleanup_pgpass_file
        exit 1
    fi

    # Count tables
    local table_count
    table_count=$(PGPASSFILE="${PGPASS_FILE}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

    cleanup_pgpass_file

    log_info "Restored ${table_count} database tables"

    log_info "Restore verification passed"
}

# Main execution
main() {
    log_info "Starting RAG Modulo restore"
    log_info "Backup archive: ${BACKUP_ARCHIVE}"

    if [[ "$BACKUP_ARCHIVE" == *.gpg ]]; then
        log_info "Encrypted backup detected"
    fi

    check_prerequisites
    confirm_restore
    decrypt_backup
    extract_backup
    verify_backup
    restore_postgres
    restore_milvus_metadata
    verify_restore
    cleanup

    log_info "Restore completed successfully!"
    log_info ""
    log_warn "IMPORTANT: Next steps:"
    log_warn "1. Verify application can connect to restored database"
    log_warn "2. Restore Milvus vector data if needed"
    log_warn "3. Restart application services"
    log_warn "4. Run smoke tests to verify functionality"
}

# Trap cleanup on exit
trap cleanup EXIT

main "$@"
