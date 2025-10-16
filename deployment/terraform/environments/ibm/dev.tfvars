# Development Environment Configuration
# This file contains development-specific settings for IBM Cloud deployment

# Project configuration
project_name = "rag-modulo"
environment  = "dev"

# IBM Cloud configuration
region            = "us-south"
resource_group_id = "your-resource-group-id"

# Container registry configuration
container_registry_url      = "us.icr.io"
container_registry_username = "iamapikey"
container_registry_password = "your-ibm-cloud-api-key"

# Image tags (development versions)
backend_image_tag  = "dev-latest"
frontend_image_tag = "dev-latest"

# Backend scaling (development - minimal resources)
backend_min_scale = 1
backend_max_scale = 3
backend_cpu       = "0.5"
backend_memory    = "1Gi"

# Frontend scaling (development - minimal resources)
frontend_min_scale = 1
frontend_max_scale = 2
frontend_cpu       = "0.25"
frontend_memory    = "512Mi"

# Managed services configuration (development plans)
postgresql_plan        = "standard"
object_storage_plan    = "standard"
zilliz_plan           = "standard"
event_streams_plan    = "standard"

# PostgreSQL configuration
postgresql_admin_password = "dev-password-123"

# Production safeguards (disabled for development)
enable_production_safeguards = false

# Development-specific settings
debug_enabled = true
skip_auth_enabled = true
log_level = "DEBUG"

# Cost optimization for development
enable_auto_scaling = false
enable_monitoring  = true
enable_backups     = false

# Development tags
tags = [
  "environment:development",
  "cost-center:development",
  "owner:development-team",
  "auto-shutdown:true"
]
