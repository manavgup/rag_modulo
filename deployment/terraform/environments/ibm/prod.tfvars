# Production Environment Configuration
# This file contains production-specific settings for IBM Cloud deployment

# Project configuration
project_name = "rag-modulo"
environment  = "production"

# IBM Cloud configuration
region            = "us-south"
resource_group_id = "your-production-resource-group-id"

# Container registry configuration
container_registry_url      = "us.icr.io"
container_registry_username = "iamapikey"
container_registry_password = "your-production-ibm-cloud-api-key"

# Image tags (production - specific versions only)
backend_image_tag  = "v1.0.0"
frontend_image_tag = "v1.0.0"

# Backend scaling (production - high availability)
backend_min_scale = 3
backend_max_scale = 20
backend_cpu       = "2"
backend_memory    = "4Gi"

# Frontend scaling (production - high availability)
frontend_min_scale = 2
frontend_max_scale = 10
frontend_cpu       = "1"
frontend_memory    = "2Gi"

# Managed services configuration (production plans)
postgresql_plan        = "enterprise"
object_storage_plan    = "enterprise"
zilliz_plan           = "enterprise"
event_streams_plan    = "enterprise"

# PostgreSQL configuration (production - secure password)
postgresql_admin_password = "production-secure-password-256-bits"

# Production safeguards (enabled for production)
enable_production_safeguards = true

# Production-specific settings
debug_enabled = false
skip_auth_enabled = false
log_level = "INFO"

# Production features
enable_auto_scaling = true
enable_monitoring  = true
enable_backups     = true
enable_ssl         = true
enable_encryption  = true

# High availability configuration
enable_multi_zone = true
enable_disaster_recovery = true
backup_retention_days = 30

# Security configuration
enable_security_scanning = true
enable_vulnerability_scanning = true
enable_compliance_scanning = true

# Performance optimization
enable_caching = true
enable_cdn = true
enable_compression = true

# Production tags
tags = [
  "environment:production",
  "cost-center:production",
  "owner:production-team",
  "compliance:required",
  "backup:required",
  "monitoring:required"
]
