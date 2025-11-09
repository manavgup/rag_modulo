# Monitoring & Observability Guide

This guide covers comprehensive monitoring, logging, and observability for RAG Modulo in production environments.

## Table of Contents

- [Overview](#overview)
- [Health Checks](#health-checks)
- [Application Logging](#application-logging)
- [Metrics & Prometheus](#metrics--prometheus)
- [Distributed Tracing](#distributed-tracing)
- [Log Aggregation](#log-aggregation)
- [Alerting](#alerting)
- [Performance Monitoring](#performance-monitoring)
- [Dashboard Setup](#dashboard-setup)

## Overview

RAG Modulo implements comprehensive observability with:

- **Health Checks**: Liveness and readiness probes for all services
- **Structured Logging**: JSON and text formats with context tracking
- **Metrics**: Application and infrastructure metrics (future: Prometheus integration)
- **Tracing**: Request correlation and pipeline stage tracking
- **Log Storage**: In-memory queryable log storage with filtering

**Monitoring Stack**:
- Application: Enhanced logging with context tracking
- Infrastructure: Docker health checks, container stats
- Future: Prometheus + Grafana, OpenTelemetry, ELK/Loki

## Health Checks

### Backend Health Endpoint

**Endpoint**: `GET /api/health`

**Location**: `/home/user/rag_modulo/backend/healthcheck.py`

```python
# Health check implementation
import http.client
import sys

def check_health() -> None:
    try:
        conn = http.client.HTTPConnection("localhost", 8000)
        conn.request("GET", "/api/health")
        response = conn.getresponse()
        if response.status == 200:
            sys.exit(0)  # Healthy
        else:
            sys.exit(1)  # Unhealthy
    except Exception:
        sys.exit(1)  # Failed to connect
```

**Docker Health Check Configuration**:

```yaml
# docker-compose.yml
backend:
  healthcheck:
    test: ["CMD", "python", "healthcheck.py"]
    interval: 30s      # Check every 30 seconds
    timeout: 10s       # Fail if check takes >10s
    start_period: 60s  # Grace period during startup
    retries: 5         # Mark unhealthy after 5 failures
```

**Kubernetes Probes**:

```yaml
# backend-deployment.yaml
livenessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 60
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 2
```

### Service Health Checks

**PostgreSQL**:

```yaml
# docker-compose-infra.yml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${COLLECTIONDB_USER} -d ${COLLECTIONDB_NAME}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

```bash
# Manual check
docker compose exec postgres pg_isready -U postgres
```

**Milvus**:

```yaml
milvus-standalone:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
```

```bash
# Manual check
curl http://localhost:9091/healthz
```

**MinIO**:

```yaml
minio:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 10s
```

```bash
# Manual check
curl http://localhost:9000/minio/health/live
```

### Health Check Monitoring

```bash
# Check all service health
docker compose ps

# Watch health status
watch -n 5 'docker compose ps'

# Get detailed health status
docker inspect --format='{{.State.Health.Status}}' rag-modulo-backend-1
```

## Application Logging

### Enhanced Logging System

RAG Modulo implements an enhanced logging system with structured context tracking based on IBM mcp-context-forge patterns.

**Location**: `/home/user/rag_modulo/backend/core/enhanced_logging.py`

**Key Features**:
- Dual output formats (JSON for production, text for development)
- Entity context tracking (collection, user, conversation)
- Request correlation IDs
- Pipeline stage tracking
- Performance timing
- In-memory queryable storage

### Basic Usage

```python
from core.enhanced_logging import get_logger
from core.logging_context import log_operation, pipeline_stage_context, PipelineStage

logger = get_logger(__name__)

# Simple logging
logger.info("Starting search operation")
logger.error("Database connection failed", exc_info=True)

# With operation context
with log_operation(logger, "search_documents", "collection", collection_id, user_id=user_id):
    # All logs within this context include collection_id and user_id
    logger.info("Query rewriting started")

    # Track pipeline stages
    with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
        logger.info("Original query", extra={"query": original_query})
        # ... query rewriting logic ...
        logger.info("Rewritten query", extra={"rewritten": new_query})

    with pipeline_stage_context(PipelineStage.RETRIEVAL):
        logger.info("Retrieving documents", extra={"top_k": 5})
        # ... retrieval logic ...
        logger.info("Retrieved documents", extra={"count": len(results)})
```

### Logging Configuration

**Environment Variables**:

```bash
# .env file
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json             # json or text
LOG_FILE=rag_modulo.log     # Log file name
LOG_FOLDER=/app/logs        # Log directory
LOG_ROTATION=true           # Enable log rotation
LOG_MAX_SIZE_MB=100         # Max log file size
LOG_BACKUP_COUNT=5          # Number of backup files
```

**Configuration in Code**:

```python
# backend/main.py
from pathlib import Path
from core.logging_utils import setup_logging

# Determine log directory (container vs local)
log_dir = Path("/app/logs") if os.getenv("CONTAINER_ENV") else Path(__file__).parent.parent / "logs"

# Initialize logging
setup_logging(log_dir)
logger = get_logger(__name__)
```

### Log Output Formats

**JSON Format** (production):

```json
{
  "asctime": "2025-01-09T14:32:15",
  "name": "rag_solution.services.search_service",
  "levelname": "INFO",
  "message": "Search completed successfully",
  "context": {
    "operation": "search_documents",
    "entity_type": "collection",
    "entity_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "request_id": "req_abc123",
    "pipeline_stage": "response_generation"
  },
  "execution_time_ms": 234.5,
  "timestamp": "2025-01-09T14:32:15.123Z"
}
```

**Text Format** (development):

```
[2025-01-09T14:32:15] INFO     rag_solution.services.search_service: Search completed successfully
```

### Pipeline Stage Tracking

**Available Pipeline Stages** (`core/logging_context.py`):

```python
class PipelineStage:
    QUERY_REWRITING = "query_rewriting"
    RETRIEVAL = "retrieval"
    RERANKING = "reranking"
    PROMPT_BUILDING = "prompt_building"
    GENERATION = "generation"
    RESPONSE_GENERATION = "response_generation"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    SOURCE_ATTRIBUTION = "source_attribution"
```

**Usage Example**:

```python
# In SearchService
async def search(self, search_input: SearchInput):
    with log_operation(self.logger, "search", "collection", search_input.collection_id):
        # Stage 1: Query rewriting
        with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
            rewritten = await self._rewrite_query(search_input.question)

        # Stage 2: Retrieval
        with pipeline_stage_context(PipelineStage.RETRIEVAL):
            docs = await self._retrieve_documents(rewritten)

        # Stage 3: Generation
        with pipeline_stage_context(PipelineStage.GENERATION):
            response = await self._generate_answer(docs, rewritten)

        return response
```

### Log Storage & Querying

**In-Memory Storage** (`core/log_storage_service.py`):

```python
from core.log_storage_service import LogStorageService, LogLevel

# Get log storage instance
log_storage = LogStorageService.get_instance()

# Query logs
logs = log_storage.query_logs(
    level=LogLevel.ERROR,
    entity_type="collection",
    entity_id="550e8400-e29b-41d4-a716-446655440000",
    limit=100
)

# Get recent logs
recent = log_storage.get_recent_logs(limit=50)

# Filter by time range
from datetime import datetime, timedelta
since = datetime.now() - timedelta(hours=1)
recent_hour = log_storage.query_logs(since=since)
```

### Log Aggregation Locations

```bash
/home/user/rag_modulo/
├── logs/                           # Local development logs
│   ├── rag_modulo.log              # Main application log
│   ├── rag_modulo.log.1            # Rotated log (if rotation enabled)
│   └── ...
└── backend/
    └── main.py                     # Logging initialization

# Container logs
/app/logs/
├── rag_modulo.log
└── ...

# Docker logs (ephemeral)
docker compose logs backend          # View backend logs
docker compose logs -f backend       # Follow logs
docker compose logs --since 1h       # Last hour
docker compose logs --tail 100       # Last 100 lines
```

## Metrics & Prometheus

### Application Metrics (Future Enhancement)

**Planned Metrics**:

```python
# Future: backend/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# RAG-specific metrics
rag_searches_total = Counter(
    'rag_searches_total',
    'Total RAG search requests',
    ['collection', 'status']
)

rag_search_duration_seconds = Histogram(
    'rag_search_duration_seconds',
    'RAG search latency',
    ['collection', 'pipeline_stage']
)

vector_db_operations = Counter(
    'vector_db_operations_total',
    'Vector database operations',
    ['operation', 'status']
)

llm_api_calls = Counter(
    'llm_api_calls_total',
    'LLM API calls',
    ['provider', 'model', 'status']
)

active_connections = Gauge(
    'active_connections',
    'Active WebSocket connections'
)
```

### Infrastructure Metrics

**Docker Container Metrics**:

```bash
# Real-time container stats
docker stats

# Specific container
docker stats rag-modulo-backend-1

# One-shot stats (no streaming)
docker stats --no-stream

# JSON format for parsing
docker stats --format "{{json .}}" --no-stream
```

**Milvus Metrics**:

```bash
# Milvus exposes metrics on port 9091
curl http://localhost:9091/metrics

# Collection statistics
curl -X POST http://localhost:9091/api/v1/collection/statistics \
  -d '{"collection_name": "your_collection"}'
```

**PostgreSQL Metrics**:

```sql
-- Connection count
SELECT count(*) FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('rag_modulo_db'));

-- Slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

### Prometheus Setup (Future)

**Prometheus Configuration**:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'rag-modulo-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'milvus'
    static_configs:
      - targets: ['milvus-standalone:9091']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

## Distributed Tracing

### Request Correlation

**Automatic Correlation ID**:

```python
# Middleware adds correlation_id to all requests
# backend/core/authentication_middleware.py

import uuid
from fastapi import Request

async def add_correlation_id(request: Request):
    correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    logger.info("Request received", extra={"correlation_id": correlation_id})
```

**Using Correlation IDs**:

```python
# In any request handler
from fastapi import Request

@router.post("/search")
async def search(request: Request, search_input: SearchInput):
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.info("Search started", extra={"correlation_id": correlation_id})
    # ... process search ...
    return results
```

### Tracing Across Services

**Future: OpenTelemetry Integration**:

```python
# Future: backend/core/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider

tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

tracer = trace.get_tracer(__name__)

# Usage
with tracer.start_as_current_span("search_operation"):
    # ... search logic ...
    with tracer.start_as_current_span("query_rewrite"):
        # ... query rewriting ...
        pass
```

## Log Aggregation

### Docker Logs

**Viewing Logs**:

```bash
# All services
docker compose logs

# Specific service
docker compose logs backend
docker compose logs postgres

# Follow logs (tail -f)
docker compose logs -f backend

# Since timestamp
docker compose logs --since 2025-01-09T14:00:00

# Last N lines
docker compose logs --tail 100 backend

# Multiple services
docker compose logs backend postgres milvus-standalone
```

### ELK Stack Integration (Future)

**Filebeat Configuration**:

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /app/logs/*.log
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      service: rag-modulo-backend

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "rag-modulo-%{+yyyy.MM.dd}"
```

### Loki Integration (Future)

**Promtail Configuration**:

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: rag-modulo
    static_configs:
      - targets:
          - localhost
        labels:
          job: rag-modulo-backend
          __path__: /app/logs/*.log
```

## Alerting

### Health Check Alerts

```bash
# Simple script to check health and alert
#!/bin/bash
# File: scripts/health_monitor.sh

BACKEND_URL="http://localhost:8000/api/health"
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

check_health() {
    response=$(curl -s -o /dev/null -w "%{http_code}" $BACKEND_URL)
    if [ $response -ne 200 ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 Backend health check failed: HTTP $response\"}" \
            $SLACK_WEBHOOK
    fi
}

# Run every 60 seconds
while true; do
    check_health
    sleep 60
done
```

### Prometheus Alertmanager (Future)

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: 'RAG Modulo Alert'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

**Alert Rules**:

```yaml
# alerts.yml
groups:
  - name: rag_modulo_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: SlowSearches
        expr: histogram_quantile(0.95, rag_search_duration_seconds) > 10
        for: 5m
        annotations:
          summary: "95th percentile search latency > 10s"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        annotations:
          summary: "PostgreSQL is down"
```

## Performance Monitoring

### Application Performance

```python
# Performance tracking in logs
import time

start_time = time.time()
# ... operation ...
elapsed_ms = (time.time() - start_time) * 1000

logger.info(
    "Operation completed",
    extra={
        "operation": "search",
        "execution_time_ms": elapsed_ms,
        "collection_id": collection_id
    }
)
```

### Database Query Performance

```sql
-- Enable query logging (PostgreSQL)
ALTER DATABASE rag_modulo_db SET log_statement = 'all';
ALTER DATABASE rag_modulo_db SET log_duration = on;
ALTER DATABASE rag_modulo_db SET log_min_duration_statement = 1000; -- Log queries > 1s

-- View slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### Vector Database Performance

```bash
# Milvus query performance
curl -X POST http://localhost:9091/api/v1/query/performance

# Collection stats
curl -X POST http://localhost:9091/api/v1/collection/statistics \
  -d '{"collection_name": "documents"}'
```

## Dashboard Setup

### Grafana Dashboard (Future)

**Backend Dashboard**:

```json
{
  "dashboard": {
    "title": "RAG Modulo Backend",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {"expr": "rate(http_requests_total[5m])"}
        ]
      },
      {
        "title": "Request Latency (p95)",
        "targets": [
          {"expr": "histogram_quantile(0.95, http_request_duration_seconds)"}
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {"expr": "rate(http_requests_total{status=~\"5..\"}[5m])"}
        ]
      },
      {
        "title": "Search Performance",
        "targets": [
          {"expr": "rate(rag_searches_total[5m])"},
          {"expr": "histogram_quantile(0.95, rag_search_duration_seconds)"}
        ]
      }
    ]
  }
}
```

### Simple Monitoring Dashboard

```bash
# Create simple monitoring script
# File: scripts/monitor_dashboard.sh

#!/bin/bash
while true; do
    clear
    echo "=== RAG Modulo Status Dashboard ==="
    echo ""
    echo "Backend Health:"
    curl -s http://localhost:8000/api/health || echo "❌ Backend unhealthy"
    echo ""
    echo "Container Status:"
    docker compose ps
    echo ""
    echo "Resource Usage:"
    docker stats --no-stream
    echo ""
    sleep 5
done
```

## Related Documentation

- [Cloud Deployment](cloud.md) - Production deployment guide
- [Troubleshooting: Debugging](../troubleshooting/debugging.md) - Debug tools and techniques
- [Troubleshooting: Performance](../troubleshooting/performance.md) - Performance optimization
- [Logging Documentation](../development/logging.md) - Enhanced logging system details
