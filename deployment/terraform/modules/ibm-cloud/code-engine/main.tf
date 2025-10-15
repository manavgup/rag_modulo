# IBM Cloud Code Engine Module
# This module provisions Code Engine applications with managed services integration
# and secure, specific image versions

terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.0"
    }
  }
}

# Code Engine project
resource "ibm_code_engine_project" "main" {
  name         = "${var.project_name}-${var.environment}"
  resource_group_id = var.resource_group_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "managed:true"
  ]
  
  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# Backend application
resource "ibm_code_engine_app" "backend" {
  project_id = ibm_code_engine_project.main.id
  name       = "${var.project_name}-backend"
  
  # Use specific, secure image version
  image_reference = "${var.container_registry_url}/${var.project_name}-backend:${var.backend_image_tag}"
  
  # Resource configuration
  image_secret = ibm_code_engine_secret.container_registry_secret.id
  
  # Scaling configuration
  scale {
    min_instances = var.backend_min_scale
    max_instances = var.backend_max_scale
    target_cpu_utilization = 70
  }
  
  # Environment variables from managed services
  env {
    name  = "DATABASE_URL"
    value = "postgresql://${var.postgresql_username}:${var.postgresql_password}@${var.postgresql_host}:${var.postgresql_port}/${var.postgresql_database}?sslmode=require"
  }
  
  env {
    name  = "MILVUS_HOST"
    value = var.zilliz_endpoint
  }
  
  env {
    name  = "MILVUS_API_KEY"
    value = var.zilliz_api_key
  }
  
  env {
    name  = "MINIO_ENDPOINT"
    value = var.object_storage_endpoint
  }
  
  env {
    name  = "MINIO_ACCESS_KEY"
    value = var.object_storage_access_key
  }
  
  env {
    name  = "MINIO_SECRET_KEY"
    value = var.object_storage_secret_key
  }
  
  env {
    name  = "MINIO_BUCKET_NAME"
    value = var.object_storage_bucket_name
  }
  
  env {
    name  = "KAFKA_BROKERS"
    value = var.event_streams_endpoint
  }
  
  env {
    name  = "KAFKA_API_KEY"
    value = var.event_streams_api_key
  }
  
  # Application-specific environment variables
  env {
    name  = "ENVIRONMENT"
    value = var.environment
  }
  
  env {
    name  = "DEBUG"
    value = var.environment == "production" ? "false" : "true"
  }
  
  env {
    name  = "SKIP_AUTH"
    value = var.environment == "production" ? "false" : "true"
  }
  
  env {
    name  = "LOG_LEVEL"
    value = var.environment == "production" ? "INFO" : "DEBUG"
  }
  
  # Health check configuration
  health_check {
    type = "http"
    path = "/health"
    port = 8000
    initial_delay_seconds = 30
    period_seconds = 10
    timeout_seconds = 5
    failure_threshold = 3
    success_threshold = 1
  }
  
  # Resource limits
  resources {
    cpu    = var.backend_cpu
    memory = var.backend_memory
  }
  
  # Security context
  security_context {
    run_as_user = 1000
    run_as_group = 1000
    fs_group = 1000
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:backend",
    "managed:true"
  ]
}

# Frontend application
resource "ibm_code_engine_app" "frontend" {
  project_id = ibm_code_engine_project.main.id
  name       = "${var.project_name}-frontend"
  
  # Use specific, secure image version
  image_reference = "${var.container_registry_url}/${var.project_name}-frontend:${var.frontend_image_tag}"
  
  # Resource configuration
  image_secret = ibm_code_engine_secret.container_registry_secret.id
  
  # Scaling configuration
  scale {
    min_instances = var.frontend_min_scale
    max_instances = var.frontend_max_scale
    target_cpu_utilization = 70
  }
  
  # Environment variables
  env {
    name  = "REACT_APP_API_URL"
    value = "https://${ibm_code_engine_app.backend.endpoint}"
  }
  
  env {
    name  = "REACT_APP_ENVIRONMENT"
    value = var.environment
  }
  
  env {
    name  = "REACT_APP_DEBUG"
    value = var.environment == "production" ? "false" : "true"
  }
  
  # Health check configuration
  health_check {
    type = "http"
    path = "/"
    port = 3000
    initial_delay_seconds = 30
    period_seconds = 10
    timeout_seconds = 5
    failure_threshold = 3
    success_threshold = 1
  }
  
  # Resource limits
  resources {
    cpu    = var.frontend_cpu
    memory = var.frontend_memory
  }
  
  # Security context
  security_context {
    run_as_user = 1000
    run_as_group = 1000
    fs_group = 1000
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:frontend",
    "managed:true"
  ]
}

# Container registry secret
resource "ibm_code_engine_secret" "container_registry_secret" {
  project_id = ibm_code_engine_project.main.id
  name       = "container-registry-secret"
  type       = "registry"
  
  data = {
    username = var.container_registry_username
    password = var.container_registry_password
    server   = var.container_registry_url
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "type:registry-secret"
  ]
}

# Service binding for managed services
resource "ibm_code_engine_binding" "postgresql_binding" {
  project_id = ibm_code_engine_project.main.id
  app_id     = ibm_code_engine_app.backend.id
  name       = "postgresql-binding"
  
  service_instance_id = var.postgresql_instance_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:postgresql"
  ]
}

resource "ibm_code_engine_binding" "object_storage_binding" {
  project_id = ibm_code_engine_project.main.id
  app_id     = ibm_code_engine_app.backend.id
  name       = "object-storage-binding"
  
  service_instance_id = var.object_storage_instance_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:object-storage"
  ]
}

resource "ibm_code_engine_binding" "zilliz_binding" {
  project_id = ibm_code_engine_project.main.id
  app_id     = ibm_code_engine_app.backend.id
  name       = "zilliz-binding"
  
  service_instance_id = var.zilliz_instance_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:vector-database"
  ]
}

resource "ibm_code_engine_binding" "event_streams_binding" {
  project_id = ibm_code_engine_project.main.id
  app_id     = ibm_code_engine_app.backend.id
  name       = "event-streams-binding"
  
  service_instance_id = var.event_streams_instance_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:messaging"
  ]
}
