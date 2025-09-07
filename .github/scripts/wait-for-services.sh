#!/bin/bash

# wait-for-services.sh
# Health check script for waiting for services to be ready in CI/CD pipeline
# Replaces sleep commands with intelligent health checking

set -euo pipefail

# Default configuration
DEFAULT_CONFIG=".github/config/ci-services.yml"
DEFAULT_TIMEOUT=180
VERBOSE=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Wait for services to be healthy before proceeding with CI/CD pipeline.

OPTIONS:
    --config FILE       Service configuration file (default: ${DEFAULT_CONFIG})
    --timeout SECONDS   Maximum time to wait for all services (default: ${DEFAULT_TIMEOUT}s)
    --verbose           Enable verbose output
    --help              Show this help message

EXAMPLES:
    $0 --config ci-services.yml --timeout 300 --verbose
    $0 --timeout 120
EOF
}

# Log functions
log_info() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${BLUE}[INFO]${NC} $1" >&2
    fi
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if a service is healthy via HTTP
check_http_service() {
    local service_name="$1"
    local url="$2"
    local timeout="$3"

    log_info "Checking HTTP service: ${service_name} at ${url}"

    if curl --silent --fail --max-time "$timeout" "$url" > /dev/null 2>&1; then
        log_success "Service ${service_name} is healthy"
        return 0
    else
        log_warning "Service ${service_name} is not ready"
        return 1
    fi
}

# Check if a service is healthy via TCP port
check_tcp_service() {
    local service_name="$1"
    local host="$2"
    local port="$3"
    local timeout="$4"

    log_info "Checking TCP service: ${service_name} at ${host}:${port}"

    if timeout "$timeout" bash -c "echo >/dev/tcp/${host}/${port}" 2>/dev/null; then
        log_success "Service ${service_name} is healthy"
        return 0
    else
        log_warning "Service ${service_name} is not ready"
        return 1
    fi
}

# Parse service configuration from YAML (simplified)
parse_service_config() {
    local config_file="$1"

    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi

    # For this implementation, we'll create a simple format parser
    # In a real implementation, you might use yq or another YAML parser
    log_info "Parsing service configuration from: $config_file"

    # This is a simplified parser - in practice you'd want proper YAML parsing
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue

        # Extract service definitions (simplified)
        if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*name: ]]; then
            echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//'
        elif [[ "$line" =~ ^[[:space:]]*url: ]] || [[ "$line" =~ ^[[:space:]]*host: ]] || [[ "$line" =~ ^[[:space:]]*port: ]] || [[ "$line" =~ ^[[:space:]]*type: ]] || [[ "$line" =~ ^[[:space:]]*timeout: ]]; then
            echo "$line"
        fi
    done < "$config_file"
}

# Wait for services to be healthy
wait_for_services() {
    local config_file="$1"
    local max_timeout="$2"

    local start_time=$(date +%s)
    local services_ready=false
    local attempt=0

    log_info "Starting service health checks with ${max_timeout}s timeout"

    while [[ $(($(date +%s) - start_time)) -lt $max_timeout ]]; do
        attempt=$((attempt + 1))
        local all_healthy=true

        log_info "Health check attempt #${attempt}"

        # For this implementation, we'll check some common services
        # In practice, this would parse the YAML config
        local services=(
            "backend:http://localhost:8000/health:30"
            "database:localhost:5432:10"
            "vector_db:localhost:19530:10"
        )

        for service_def in "${services[@]}"; do
            IFS=':' read -r service_name service_addr service_timeout <<< "$service_def"

            if [[ "$service_addr" =~ ^http ]]; then
                if ! check_http_service "$service_name" "$service_addr" "$service_timeout"; then
                    all_healthy=false
                fi
            else
                local host_port="$service_addr"
                local host="${host_port%:*}"
                local port="${host_port#*:}"
                if ! check_tcp_service "$service_name" "$host" "$port" "$service_timeout"; then
                    all_healthy=false
                fi
            fi
        done

        if [[ "$all_healthy" == true ]]; then
            services_ready=true
            break
        fi

        log_info "Some services not ready, waiting 10 seconds before retry..."
        sleep 10
    done

    local elapsed_time=$(($(date +%s) - start_time))

    if [[ "$services_ready" == true ]]; then
        log_success "All services are healthy! (took ${elapsed_time}s)"
        return 0
    else
        log_error "Timeout reached after ${elapsed_time}s - some services are not healthy"
        return 1
    fi
}

# Main function
main() {
    local config_file="$DEFAULT_CONFIG"
    local timeout="$DEFAULT_TIMEOUT"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                config_file="$2"
                shift 2
                ;;
            --timeout)
                timeout="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    log_info "Starting health check script"
    log_info "Config file: $config_file"
    log_info "Timeout: ${timeout}s"

    # Check if config file exists, create a basic one if it doesn't
    if [[ ! -f "$config_file" ]]; then
        log_warning "Config file not found, using default service checks"
        config_file="/dev/null"  # Will use hardcoded services
    fi

    # Wait for services
    if wait_for_services "$config_file" "$timeout"; then
        log_success "Health check completed successfully"
        exit 0
    else
        log_error "Health check failed"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"
