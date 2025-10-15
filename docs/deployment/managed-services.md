# Managed Services Strategy

This document describes the managed services strategy for RAG Modulo deployment, replacing self-hosted containers with IBM Cloud managed services for improved reliability, security, and operational efficiency.

## Overview

Instead of deploying self-hosted containers for data persistence services, RAG Modulo uses IBM Cloud managed services to ensure:

- **Data Persistence**: No data loss on pod restarts
- **High Availability**: Built-in redundancy and failover
- **Security**: Enterprise-grade security and compliance
- **Operational Efficiency**: Reduced maintenance overhead
- **Cost Optimization**: Pay-as-you-use pricing model

## Service Mapping

| Self-Hosted Service | IBM Cloud Managed Service | Benefits |
|-------------------|---------------------------|----------|
| PostgreSQL Container | IBM Cloud Databases for PostgreSQL | Automated backups, scaling, HA |
| MinIO Container | IBM Cloud Object Storage | Unlimited scalability, durability |
| Milvus Container | Zilliz Cloud | Managed vector database |
| etcd Container | IBM Cloud Event Streams | Managed messaging service |

## IBM Cloud Databases for PostgreSQL

### Features

- **Automated Backups**: Point-in-time recovery
- **High Availability**: Multi-zone deployment
- **Auto-scaling**: Automatic resource adjustment
- **Security**: Encryption at rest and in transit
- **Monitoring**: Built-in performance metrics

### Configuration

```hcl
# Terraform configuration
resource "ibm_database" "postgresql" {
  name              = "${var.project_name}-postgresql"
  service           = "databases-for-postgresql"
  plan              = var.postgresql_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  adminpassword = var.postgresql_admin_password
  service_endpoints = "public-and-private"

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:postgresql",
    "managed:true"
  ]
}
```

### Connection Details

```bash
# Environment variables for applications
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
POSTGRESQL_HOST=hostname
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=database_name
POSTGRESQL_USERNAME=username
POSTGRESQL_PASSWORD=password
```

## IBM Cloud Object Storage

### Features

- **Unlimited Scalability**: No storage limits
- **Durability**: 99.999999999% (11 9's) durability
- **Availability**: 99.9% availability SLA
- **Security**: Encryption and access controls
- **Lifecycle Management**: Automatic tier transitions

### Configuration

```hcl
# Terraform configuration
resource "ibm_resource_instance" "object_storage" {
  name              = "${var.project_name}-object-storage"
  service           = "cloud-object-storage"
  plan              = var.object_storage_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  parameters = {
    "HMAC" = true
  }
}

resource "ibm_cos_bucket" "app_data" {
  bucket_name          = "${var.project_name}-app-data-${random_id.bucket_suffix.hex}"
  resource_instance_id = ibm_resource_instance.object_storage.id
  region_location      = var.region
  storage_class        = "standard"

  object_versioning {
    enable = true
  }

  encryption {
    algorithm = "AES256"
  }
}
```

### Connection Details

```bash
# Environment variables for applications
MINIO_ENDPOINT=object-storage-endpoint
MINIO_ACCESS_KEY=access-key
MINIO_SECRET_KEY=secret-key
MINIO_BUCKET_NAME=bucket-name
```

## Zilliz Cloud (Vector Database)

### Features

- **Managed Milvus**: Fully managed vector database
- **Auto-scaling**: Automatic resource adjustment
- **High Performance**: Optimized for vector operations
- **Security**: Enterprise-grade security
- **Monitoring**: Built-in performance metrics

### Configuration

```hcl
# Terraform configuration
resource "ibm_resource_instance" "zilliz_cloud" {
  name              = "${var.project_name}-zilliz-cloud"
  service           = "zilliz-cloud"
  plan              = var.zilliz_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:vector-database",
    "managed:true"
  ]
}
```

### Connection Details

```bash
# Environment variables for applications
MILVUS_HOST=zilliz-endpoint
MILVUS_API_KEY=zilliz-api-key
```

## IBM Cloud Event Streams

### Features

- **Managed Kafka**: Fully managed Apache Kafka service
- **High Throughput**: Handle millions of messages per second
- **Durability**: Persistent message storage
- **Security**: Encryption and access controls
- **Monitoring**: Built-in performance metrics

### Configuration

```hcl
# Terraform configuration
resource "ibm_resource_instance" "event_streams" {
  name              = "${var.project_name}-event-streams"
  service           = "messagehub"
  plan              = var.event_streams_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:messaging",
    "managed:true"
  ]
}
```

### Connection Details

```bash
# Environment variables for applications
KAFKA_BROKERS=event-streams-endpoint
KAFKA_API_KEY=event-streams-api-key
```

## Service Integration

### Service Bindings

Code Engine applications automatically bind to managed services:

```hcl
# Service binding for PostgreSQL
resource "ibm_code_engine_binding" "postgresql_binding" {
  project_id = ibm_code_engine_project.main.id
  app_id     = ibm_code_engine_app.backend.id
  name       = "postgresql-binding"

  service_instance_id = var.postgresql_instance_id
}

# Service binding for Object Storage
resource "ibm_code_engine_binding" "object_storage_binding" {
  project_id = ibm_code_engine_project.main.id
  app_id     = ibm_code_engine_app.backend.id
  name       = "object-storage-binding"

  service_instance_id = var.object_storage_instance_id
}
```

### Environment Variables

Service bindings automatically inject connection details as environment variables:

```bash
# PostgreSQL connection
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require

# Object Storage connection
MINIO_ENDPOINT=object-storage-endpoint
MINIO_ACCESS_KEY=access-key
MINIO_SECRET_KEY=secret-key
MINIO_BUCKET_NAME=bucket-name

# Vector database connection
MILVUS_HOST=zilliz-endpoint
MILVUS_API_KEY=zilliz-api-key

# Messaging connection
KAFKA_BROKERS=event-streams-endpoint
KAFKA_API_KEY=event-streams-api-key
```

## Security Features

### 1. Encryption

- **At Rest**: All data encrypted using AES-256
- **In Transit**: All communications use TLS 1.2+
- **Key Management**: IBM Cloud Key Protect integration

### 2. Access Control

- **IAM Integration**: Role-based access control
- **Service-to-Service**: Secure authentication
- **Network Security**: Private endpoints available

### 3. Compliance

- **SOC 2 Type II**: Security and availability controls
- **ISO 27001**: Information security management
- **GDPR**: Data protection compliance
- **HIPAA**: Healthcare data protection (optional)

## Monitoring and Observability

### 1. Built-in Metrics

Each managed service provides:

- **Performance Metrics**: Response time, throughput
- **Resource Metrics**: CPU, memory, storage usage
- **Error Metrics**: Error rates, failed requests
- **Availability Metrics**: Uptime, health status

### 2. Logging

- **Centralized Logging**: All logs in IBM Cloud Log Analysis
- **Log Retention**: Configurable retention periods
- **Log Search**: Full-text search and filtering
- **Log Analytics**: AI-powered log analysis

### 3. Alerting

- **Threshold-based Alerts**: Custom alert rules
- **Webhook Integration**: Custom notification channels
- **Escalation Policies**: Automated incident response

## Backup and Disaster Recovery

### 1. Automated Backups

- **PostgreSQL**: Daily automated backups with point-in-time recovery
- **Object Storage**: Built-in redundancy and versioning
- **Vector Database**: Automated snapshots and backups
- **Event Streams**: Message retention and replay

### 2. Cross-Region Replication

- **Object Storage**: Cross-region replication available
- **Database**: Read replicas in multiple regions
- **Vector Database**: Multi-region deployment
- **Event Streams**: Cross-region message replication

### 3. Recovery Procedures

- **RTO**: 60 minutes (Recovery Time Objective)
- **RPO**: 15 minutes (Recovery Point Objective)
- **Automated Recovery**: Self-healing capabilities
- **Manual Recovery**: Documented recovery procedures

## Cost Optimization

### 1. Pay-as-You-Use

- **No Upfront Costs**: Pay only for what you use
- **Automatic Scaling**: Resources scale with demand
- **Reserved Capacity**: Optional reserved capacity discounts

### 2. Resource Optimization

- **Right-sizing**: Optimal resource allocation
- **Lifecycle Policies**: Automatic tier transitions
- **Compression**: Data compression to reduce costs
- **Deduplication**: Eliminate duplicate data

### 3. Cost Monitoring

- **Real-time Tracking**: Live cost monitoring
- **Budget Alerts**: Automated budget notifications
- **Cost Analysis**: Detailed cost breakdown
- **Optimization Recommendations**: AI-powered suggestions

## Migration from Self-Hosted

### 1. Data Migration

```bash
# PostgreSQL migration
pg_dump source_database | psql target_database

# Object Storage migration
aws s3 sync s3://source-bucket s3://target-bucket

# Vector database migration
# Export vectors from Milvus and import to Zilliz Cloud
```

### 2. Configuration Updates

```bash
# Update connection strings
export DATABASE_URL="postgresql://new-host:5432/database"
export MINIO_ENDPOINT="new-object-storage-endpoint"
export MILVUS_HOST="new-zilliz-endpoint"
```

### 3. Testing

```bash
# Test database connectivity
psql $DATABASE_URL -c "SELECT 1"

# Test object storage
aws s3 ls s3://bucket-name

# Test vector database
curl -X GET "https://zilliz-endpoint/health"
```

## Best Practices

### 1. Service Selection

- **Choose Appropriate Plans**: Match service plans to requirements
- **Consider SLA Requirements**: Select services based on availability needs
- **Plan for Growth**: Choose services that can scale with demand

### 2. Security

- **Use Private Endpoints**: Enable private endpoints for sensitive data
- **Rotate Credentials**: Regular credential rotation
- **Monitor Access**: Track and audit service access

### 3. Monitoring

- **Set Up Alerts**: Configure appropriate alert thresholds
- **Monitor Costs**: Track and optimize service costs
- **Regular Reviews**: Periodic service performance reviews

### 4. Backup

- **Test Backups**: Regular backup restoration testing
- **Document Procedures**: Maintain recovery procedures
- **Cross-Region**: Consider cross-region backup replication

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   - Check network connectivity
   - Verify service endpoints
   - Review firewall rules

2. **Authentication Failures**
   - Verify credentials
   - Check IAM permissions
   - Review service bindings

3. **Performance Issues**
   - Monitor resource usage
   - Check service limits
   - Review scaling configuration

### Debug Commands

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT version()"

# Test object storage
aws s3 ls s3://$MINIO_BUCKET_NAME

# Test vector database
curl -X GET "https://$MILVUS_HOST/health"

# Test event streams
kafka-topics --bootstrap-server $KAFKA_BROKERS --list
```

## Related Documentation

- [Terraform + Ansible Architecture](terraform-ansible-architecture.md)
- [IBM Cloud Code Engine Deployment](ibm-cloud-code-engine.md)
- [Ansible Automation Guide](ansible-automation.md)
- [Monitoring and Observability](monitoring-observability.md)
- [Backup and Disaster Recovery](backup-disaster-recovery.md)
