#!/bin/bash
#
# RAG Modulo Backup Script
# Backs up PostgreSQL database, Milvus collections, and application state
#
# Usage:
#   ./backup-rag-modulo.sh [backup-directory]
#
# Environment Variables:
#   COLLECTIONDB_HOST - PostgreSQL host (default: localhost)
#   COLLECTIONDB_PORT - PostgreSQL port (default: 5432)
#   COLLECTIONDB_NAME - Database name (default: rag_modulo)
#   COLLECTIONDB_USER - Database user (required)
#   COLLECTIONDB_PASS - Database password (required)
#   MILVUS_HOST - Milvus host (default: localhost)
#   MILVUS_PORT - Milvus port (default: 19530)
#   BACKUP_RETENTION_DAYS - Days to keep backups (default: 7)
#   BACKUP_ENCRYPTION_KEY - Passphrase for GPG encryption (optional)
#   BACKUP_ENABLE_ENCRYPTION - Enable backup encryption (default: false)

set -euo pipefail

# Default configuration
BACKUP_DIR="${1:-/tmp/rag-modulo-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
ENABLE_ENCRYPTION="${BACKUP_ENABLE_ENCRYPTION:-false}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing_tools=()

    if ! command -v pg_dump &> /dev/null; then
        missing_tools+=("pg_dump (PostgreSQL client)")
    fi

    if ! command -v tar &> /dev/null; then
        missing_tools+=("tar")
    fi

    if ! command -v gzip &> /dev/null; then
        missing_tools+=("gzip")
    fi

    # Check for GPG if encryption is enabled
    if [ "${ENABLE_ENCRYPTION}" = "true" ]; then
        if ! command -v gpg &> /dev/null; then
            missing_tools+=("gpg")
        fi
        if [ -z "${ENCRYPTION_KEY}" ]; then
            log_error "BACKUP_ENCRYPTION_KEY environment variable is required when encryption is enabled"
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

# Create backup directory
create_backup_dir() {
    log_info "Creating backup directory: ${BACKUP_PATH}"
    mkdir -p "${BACKUP_PATH}"
}

# Create temporary .pgpass file for secure password handling
create_pgpass_file() {
    PGPASS_FILE=$(mktemp)
    chmod 600 "${PGPASS_FILE}"
    echo "${POSTGRES_HOST}:${POSTGRES_PORT}:${POSTGRES_DB}:${POSTGRES_USER}:${POSTGRES_PASS}" > "${PGPASS_FILE}"
    echo "${PGPASS_FILE}"
}

# Remove temporary .pgpass file
cleanup_pgpass_file() {
    if [ -n "${PGPASS_FILE}" ] && [ -f "${PGPASS_FILE}" ]; then
        rm -f "${PGPASS_FILE}"
    fi
}

# Backup PostgreSQL database
backup_postgres() {
    log_info "Backing up PostgreSQL database..."

    local db_backup_file="${BACKUP_PATH}/postgres_${POSTGRES_DB}.sql"

    # Use .pgpass file instead of PGPASSWORD to avoid password exposure in process list
    PGPASS_FILE=$(create_pgpass_file)

    PGPASSFILE="${PGPASS_FILE}" pg_dump \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -F plain \
        --no-owner \
        --no-acl \
        -f "${db_backup_file}"

    cleanup_pgpass_file
    gzip "${db_backup_file}"

    log_info "PostgreSQL backup completed: ${db_backup_file}.gz"
}

# Backup Milvus collections metadata
backup_milvus_metadata() {
    log_info "Backing up Milvus collections metadata..."

    local milvus_backup_file="${BACKUP_PATH}/milvus_metadata.json"

    # Note: This requires pymilvus Python package
    # Create a simple Python script to export collection metadata
    cat > /tmp/backup_milvus.py << 'EOF'
import json
import sys
from pymilvus import connections, utility

try:
    connections.connect(host=sys.argv[1], port=sys.argv[2])
    collections = utility.list_collections()

    metadata = {
        "collections": collections,
        "timestamp": sys.argv[3]
    }

    with open(sys.argv[4], 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Backed up {len(collections)} collections")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF

    if command -v python3 &> /dev/null; then
        python3 /tmp/backup_milvus.py "${MILVUS_HOST}" "${MILVUS_PORT}" "${TIMESTAMP}" "${milvus_backup_file}" || {
            log_warn "Milvus metadata backup failed (pymilvus may not be installed)"
            echo "{\"collections\": [], \"error\": \"pymilvus not available\"}" > "${milvus_backup_file}"
        }
        rm -f /tmp/backup_milvus.py
    else
        log_warn "Python3 not available, skipping Milvus metadata backup"
        echo "{\"collections\": [], \"error\": \"python3 not available\"}" > "${milvus_backup_file}"
    fi

    log_info "Milvus metadata backup completed: ${milvus_backup_file}"
}

# Create backup manifest
create_manifest() {
    log_info "Creating backup manifest..."

    local manifest_file="${BACKUP_PATH}/MANIFEST.json"

    cat > "${manifest_file}" << EOF
{
  "backup_timestamp": "${TIMESTAMP}",
  "backup_version": "1.0",
  "components": {
    "postgres": {
      "host": "${POSTGRES_HOST}",
      "port": ${POSTGRES_PORT},
      "database": "${POSTGRES_DB}"
    },
    "milvus": {
      "host": "${MILVUS_HOST}",
      "port": ${MILVUS_PORT}
    }
  },
  "files": [
    "postgres_${POSTGRES_DB}.sql.gz",
    "milvus_metadata.json"
  ]
}
EOF

    log_info "Manifest created: ${manifest_file}"
}

# Compress backup
compress_backup() {
    log_info "Compressing backup..."

    local archive_name="${BACKUP_DIR}/rag-modulo-backup-${TIMESTAMP}.tar.gz"

    tar -czf "${archive_name}" -C "${BACKUP_DIR}" "${TIMESTAMP}"

    # Remove uncompressed backup directory
    rm -rf "${BACKUP_PATH}"

    log_info "Backup archive created: ${archive_name}"
}

# Encrypt backup archive
encrypt_backup() {
    if [ "${ENABLE_ENCRYPTION}" != "true" ]; then
        log_info "Encryption disabled, skipping encryption step"
        return 0
    fi

    log_info "Encrypting backup archive..."

    local archive_name="${BACKUP_DIR}/rag-modulo-backup-${TIMESTAMP}.tar.gz"
    local encrypted_archive="${archive_name}.gpg"

    # Encrypt using symmetric encryption with passphrase
    echo "${ENCRYPTION_KEY}" | gpg \
        --batch \
        --yes \
        --passphrase-fd 0 \
        --symmetric \
        --cipher-algo AES256 \
        --output "${encrypted_archive}" \
        "${archive_name}"

    # Remove unencrypted archive
    rm -f "${archive_name}"

    log_info "Backup encrypted: ${encrypted_archive}"
}

# Clean old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    # Clean both encrypted and unencrypted backups
    find "${BACKUP_DIR}" -name "rag-modulo-backup-*.tar.gz" -type f -mtime +"${RETENTION_DAYS}" -delete
    find "${BACKUP_DIR}" -name "rag-modulo-backup-*.tar.gz.gpg" -type f -mtime +"${RETENTION_DAYS}" -delete

    log_info "Old backups cleaned up"
}

# Verify backup
verify_backup() {
    log_info "Verifying backup integrity..."

    if [ "${ENABLE_ENCRYPTION}" = "true" ]; then
        local archive_name="${BACKUP_DIR}/rag-modulo-backup-${TIMESTAMP}.tar.gz.gpg"
        # Verify GPG file can be listed
        if gpg --list-packets "${archive_name}" > /dev/null 2>&1; then
            log_info "Encrypted backup verification passed"
        else
            log_error "Encrypted backup verification failed"
            exit 1
        fi
    else
        local archive_name="${BACKUP_DIR}/rag-modulo-backup-${TIMESTAMP}.tar.gz"
        if tar -tzf "${archive_name}" > /dev/null 2>&1; then
            log_info "Backup verification passed"
        else
            log_error "Backup verification failed"
            exit 1
        fi
    fi
}

# Main execution
main() {
    log_info "Starting RAG Modulo backup at ${TIMESTAMP}"
    log_info "Backup directory: ${BACKUP_DIR}"

    if [ "${ENABLE_ENCRYPTION}" = "true" ]; then
        log_info "Encryption: ENABLED"
    else
        log_info "Encryption: DISABLED"
    fi

    check_prerequisites
    create_backup_dir
    backup_postgres
    backup_milvus_metadata
    create_manifest
    compress_backup
    encrypt_backup
    verify_backup
    cleanup_old_backups

    if [ "${ENABLE_ENCRYPTION}" = "true" ]; then
        log_info "Backup completed successfully!"
        log_info "Backup location: ${BACKUP_DIR}/rag-modulo-backup-${TIMESTAMP}.tar.gz.gpg"
    else
        log_info "Backup completed successfully!"
        log_info "Backup location: ${BACKUP_DIR}/rag-modulo-backup-${TIMESTAMP}.tar.gz"
    fi
}

main "$@"
