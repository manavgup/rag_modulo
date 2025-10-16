# Outputs for IBM Cloud Code Engine Module

# Project outputs
output "project_id" {
  description = "Code Engine project ID"
  value       = ibm_code_engine_project.main.id
  sensitive   = false
}

output "project_name" {
  description = "Code Engine project name"
  value       = ibm_code_engine_project.main.name
  sensitive   = false
}

# Backend application outputs
output "backend_app_id" {
  description = "Backend application ID"
  value       = ibm_code_engine_app.backend.id
  sensitive   = false
}

output "backend_app_name" {
  description = "Backend application name"
  value       = ibm_code_engine_app.backend.name
  sensitive   = false
}

output "backend_endpoint" {
  description = "Backend application endpoint"
  value       = ibm_code_engine_app.backend.endpoint
  sensitive   = false
}

output "backend_status" {
  description = "Backend application status"
  value       = ibm_code_engine_app.backend.status
  sensitive   = false
}

# Frontend application outputs
output "frontend_app_id" {
  description = "Frontend application ID"
  value       = ibm_code_engine_app.frontend.id
  sensitive   = false
}

output "frontend_app_name" {
  description = "Frontend application name"
  value       = ibm_code_engine_app.frontend.name
  sensitive   = false
}

output "frontend_endpoint" {
  description = "Frontend application endpoint"
  value       = ibm_code_engine_app.frontend.endpoint
  sensitive   = false
}

output "frontend_status" {
  description = "Frontend application status"
  value       = ibm_code_engine_app.frontend.status
  sensitive   = false
}

# Service binding outputs
output "postgresql_binding_id" {
  description = "PostgreSQL service binding ID"
  value       = ibm_code_engine_binding.postgresql_binding.id
  sensitive   = false
}

output "object_storage_binding_id" {
  description = "Object Storage service binding ID"
  value       = ibm_code_engine_binding.object_storage_binding.id
  sensitive   = false
}

output "zilliz_binding_id" {
  description = "Zilliz Cloud service binding ID"
  value       = ibm_code_engine_binding.zilliz_binding.id
  sensitive   = false
}

output "event_streams_binding_id" {
  description = "Event Streams service binding ID"
  value       = ibm_code_engine_binding.event_streams_binding.id
  sensitive   = false
}

# Container registry secret outputs
output "container_registry_secret_id" {
  description = "Container registry secret ID"
  value       = ibm_code_engine_secret.container_registry_secret.id
  sensitive   = false
}

# Health check endpoints
output "backend_health_endpoint" {
  description = "Backend health check endpoint"
  value       = "${ibm_code_engine_app.backend.endpoint}/api/health"
  sensitive   = false
}

output "frontend_health_endpoint" {
  description = "Frontend health check endpoint"
  value       = "${ibm_code_engine_app.frontend.endpoint}/"
  sensitive   = false
}

# Application URLs for external access
output "backend_url" {
  description = "Backend application URL"
  value       = "https://${ibm_code_engine_app.backend.endpoint}"
  sensitive   = false
}

output "frontend_url" {
  description = "Frontend application URL"
  value       = "https://${ibm_code_engine_app.frontend.endpoint}"
  sensitive   = false
}

# Scaling information
output "backend_scaling" {
  description = "Backend scaling configuration"
  value = {
    min_instances = var.backend_min_scale
    max_instances = var.backend_max_scale
    current_instances = ibm_code_engine_app.backend.status == "ready" ? var.backend_min_scale : 0
  }
  sensitive = false
}

output "frontend_scaling" {
  description = "Frontend scaling configuration"
  value = {
    min_instances = var.frontend_min_scale
    max_instances = var.frontend_max_scale
    current_instances = ibm_code_engine_app.frontend.status == "ready" ? var.frontend_min_scale : 0
  }
  sensitive = false
}

# Resource usage information
output "backend_resources" {
  description = "Backend resource allocation"
  value = {
    cpu    = var.backend_cpu
    memory = var.backend_memory
  }
  sensitive = false
}

output "frontend_resources" {
  description = "Frontend resource allocation"
  value = {
    cpu    = var.frontend_cpu
    memory = var.frontend_memory
  }
  sensitive = false
}
