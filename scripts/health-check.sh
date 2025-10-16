#!/bin/bash

# Health Check Script for RAG Modulo Services
# This script checks the health of all running containers and services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✓ OK${NC}: $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠ WARNING${NC}: $message"
            ;;
        "ERROR")
            echo -e "${RED}✗ ERROR${NC}: $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ INFO${NC}: $message"
            ;;
    esac
}

# Function to check if a service is running
check_service_running() {
    local service_name=$1
    if docker ps --format "table {{.Names}}" | grep -q "^${service_name}$"; then
        return 0
    else
        return 1
    fi
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$service_name" 2>/dev/null || echo "unknown")

    case $health_status in
        "healthy")
            print_status "OK" "$service_name is healthy"
            return 0
            ;;
        "unhealthy")
            print_status "ERROR" "$service_name is unhealthy"
            return 1
            ;;
        "starting")
            print_status "WARNING" "$service_name is starting"
            return 0
            ;;
        *)
            print_status "WARNING" "$service_name health status: $health_status"
            return 0
            ;;
    esac
}

# Function to check service logs for errors
check_service_logs() {
    local service_name=$1
    local max_lines=50

    print_status "INFO" "Checking recent logs for $service_name"

    # Check for error patterns in recent logs
    local error_count=$(docker logs --tail $max_lines "$service_name" 2>/dev/null | grep -i -E "(error|exception|failed|panic|fatal)" | wc -l)

    if [ $error_count -gt 0 ]; then
        print_status "WARNING" "$service_name has $error_count error(s) in recent logs"
        docker logs --tail 10 "$service_name" 2>/dev/null | grep -i -E "(error|exception|failed|panic|fatal)" | head -5
    else
        print_status "OK" "$service_name logs look clean"
    fi
}

# Function to check network connectivity
check_network_connectivity() {
    local service_name=$1
    local target_service=$2
    local target_port=$3

    if docker exec "$service_name" sh -c "nc -z $target_service $target_port" 2>/dev/null; then
        print_status "OK" "$service_name can connect to $target_service:$target_port"
        return 0
    else
        print_status "ERROR" "$service_name cannot connect to $target_service:$target_port"
        return 1
    fi
}

# Function to check environment variables
check_environment_variables() {
    print_status "INFO" "Checking critical environment variables"

    # Check if .env file exists
    if [ -f ".env" ]; then
        print_status "OK" ".env file exists"

        # Check critical variables
        local critical_vars=("MINIO_ROOT_USER" "MINIO_ROOT_PASSWORD" "MLFLOW_TRACKING_USERNAME" "MLFLOW_TRACKING_PASSWORD")
        local missing_vars=()

        for var in "${critical_vars[@]}"; do
            if grep -q "^${var}=" .env; then
                print_status "OK" "$var is set"
            else
                missing_vars+=("$var")
            fi
        done

        if [ ${#missing_vars[@]} -gt 0 ]; then
            print_status "WARNING" "Missing critical environment variables: ${missing_vars[*]}"
        fi
    else
        print_status "ERROR" ".env file not found"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    print_status "INFO" "Checking disk space"

    local usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
    local available=$(df -h . | tail -1 | awk '{print $4}')

    if [ $usage -gt 90 ]; then
        print_status "ERROR" "Disk usage is ${usage}% - only ${available} available"
        return 1
    elif [ $usage -gt 80 ]; then
        print_status "WARNING" "Disk usage is ${usage}% - ${available} available"
    else
        print_status "OK" "Disk usage is ${usage}% - ${available} available"
    fi
}

# Function to check Docker resources
check_docker_resources() {
    print_status "INFO" "Checking Docker resources"

    # Check Docker daemon
    if docker info >/dev/null 2>&1; then
        print_status "OK" "Docker daemon is running"
    else
        print_status "ERROR" "Docker daemon is not accessible"
        return 1
    fi

    # Check available memory
    local mem_info=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}")
    print_status "INFO" "Docker system usage:\n$mem_info"
}

# Main health check function
main_health_check() {
    echo "=========================================="
    echo "RAG Modulo Health Check"
    echo "=========================================="
    echo ""

    local overall_status=0

    # Check Docker resources
    if ! check_docker_resources; then
        overall_status=1
    fi
    echo ""

    # Check environment variables
    if ! check_environment_variables; then
        overall_status=1
    fi
    echo ""

    # Check disk space
    if ! check_disk_space; then
        overall_status=1
    fi
    echo ""

    # Check if containers are running
    print_status "INFO" "Checking container status"

    local services=("postgres" "minio" "milvus-etcd" "milvus-standalone" "mlflow-server" "backend" "frontend")
    local running_count=0

    for service in "${services[@]}"; do
        if check_service_running "$service"; then
            print_status "OK" "$service is running"
            running_count=$((running_count + 1))

            # Check health status if available
            check_service_health "$service"

            # Check recent logs for errors
            check_service_logs "$service"

        else
            print_status "ERROR" "$service is not running"
            overall_status=1
        fi
        echo ""
    done

    # Check network connectivity between key services
    print_status "INFO" "Checking service connectivity"

    if check_service_running "backend"; then
        if check_service_running "postgres"; then
            check_network_connectivity "backend" "postgres" "5432"
        fi
        if check_service_running "milvus-standalone"; then
            check_network_connectivity "backend" "milvus-standalone" "19530"
        fi
    fi

    echo ""
    echo "=========================================="
    echo "Health Check Summary"
    echo "=========================================="
    echo "Services running: $running_count/${#services[@]}"

    if [ $overall_status -eq 0 ]; then
        print_status "OK" "All critical checks passed"
        echo "System appears to be healthy"
    else
        print_status "ERROR" "Some critical checks failed"
        echo "Please review the errors above"
    fi

    return $overall_status
}

# Run health check
main_health_check
