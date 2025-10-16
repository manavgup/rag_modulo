# Outputs for IBM Cloud Environment Configuration

# Project outputs
output "project_name" {
  description = "Project name"
  value       = var.project_name
  sensitive   = false
}

output "environment" {
  description = "Environment name"
  value       = var.environment
  sensitive   = false
}

# Code Engine outputs
output "code_engine_project_id" {
  description = "Code Engine project ID"
  value       = module.code_engine.project_id
  sensitive   = false
}

output "code_engine_project_name" {
  description = "Code Engine project name"
  value       = module.code_engine.project_name
  sensitive   = false
}

# Backend application outputs
output "backend_app_id" {
  description = "Backend application ID"
  value       = module.code_engine.backend_app_id
  sensitive   = false
}

output "backend_endpoint" {
  description = "Backend application endpoint"
  value       = module.code_engine.backend_endpoint
  sensitive   = false
}

output "backend_url" {
  description = "Backend application URL"
  value       = module.code_engine.backend_url
  sensitive   = false
}

output "backend_status" {
  description = "Backend application status"
  value       = module.code_engine.backend_status
  sensitive   = false
}

# Frontend application outputs
output "frontend_app_id" {
  description = "Frontend application ID"
  value       = module.code_engine.frontend_app_id
  sensitive   = false
}

output "frontend_endpoint" {
  description = "Frontend application endpoint"
  value       = module.code_engine.frontend_endpoint
  sensitive   = false
}

output "frontend_url" {
  description = "Frontend application URL"
  value       = module.code_engine.frontend_url
  sensitive   = false
}

output "frontend_status" {
  description = "Frontend application status"
  value       = module.code_engine.frontend_status
  sensitive   = false
}

# Managed services outputs
output "postgresql_host" {
  description = "PostgreSQL host endpoint"
  value       = module.managed_services.postgresql_host
  sensitive   = false
}

output "postgresql_port" {
  description = "PostgreSQL port"
  value       = module.managed_services.postgresql_port
  sensitive   = false
}

output "postgresql_database" {
  description = "PostgreSQL database name"
  value       = module.managed_services.postgresql_database
  sensitive   = false
}

output "object_storage_endpoint" {
  description = "Object Storage endpoint"
  value       = module.managed_services.object_storage_endpoint
  sensitive   = false
}

output "object_storage_bucket_name" {
  description = "Object Storage bucket name"
  value       = module.managed_services.object_storage_bucket_name
  sensitive   = false
}

output "zilliz_endpoint" {
  description = "Zilliz Cloud endpoint"
  value       = module.managed_services.zilliz_endpoint
  sensitive   = false
}

output "event_streams_endpoint" {
  description = "Event Streams endpoint"
  value       = module.managed_services.event_streams_endpoint
  sensitive   = false
}

# Health check endpoints
output "backend_health_endpoint" {
  description = "Backend health check endpoint"
  value       = module.code_engine.backend_health_endpoint
  sensitive   = false
}

output "frontend_health_endpoint" {
  description = "Frontend health check endpoint"
  value       = module.code_engine.frontend_health_endpoint
  sensitive   = false
}

# Service instance IDs
output "postgresql_instance_id" {
  description = "PostgreSQL service instance ID"
  value       = module.managed_services.postgresql_instance_id
  sensitive   = false
}

output "object_storage_instance_id" {
  description = "Object Storage service instance ID"
  value       = module.managed_services.object_storage_instance_id
  sensitive   = false
}

output "zilliz_instance_id" {
  description = "Zilliz Cloud service instance ID"
  value       = module.managed_services.zilliz_instance_id
  sensitive   = false
}

output "event_streams_instance_id" {
  description = "Event Streams service instance ID"
  value       = module.managed_services.event_streams_instance_id
  sensitive   = false
}

# Scaling information
output "backend_scaling" {
  description = "Backend scaling configuration"
  value       = module.code_engine.backend_scaling
  sensitive   = false
}

output "frontend_scaling" {
  description = "Frontend scaling configuration"
  value       = module.code_engine.frontend_scaling
  sensitive   = false
}

# Resource usage information
output "backend_resources" {
  description = "Backend resource allocation"
  value       = module.code_engine.backend_resources
  sensitive   = false
}

output "frontend_resources" {
  description = "Frontend resource allocation"
  value       = module.code_engine.frontend_resources
  sensitive   = false
}

# Monitoring outputs (if enabled)
output "monitoring_dashboard_url" {
  description = "Monitoring dashboard URL"
  value       = var.enable_monitoring ? module.monitoring[0].dashboard_url : null
  sensitive   = false
}

output "monitoring_alert_webhook_url" {
  description = "Monitoring alert webhook URL"
  value       = var.enable_monitoring ? module.monitoring[0].alert_webhook_url : null
  sensitive   = false
}

# Backup outputs (if enabled)
output "backup_schedule" {
  description = "Backup schedule"
  value       = var.enable_backups ? module.backup[0].backup_schedule : null
  sensitive   = false
}

output "backup_retention_days" {
  description = "Backup retention days"
  value       = var.enable_backups ? module.backup[0].backup_retention_days : null
  sensitive   = false
}

# Deployment summary
output "deployment_summary" {
  description = "Deployment summary information"
  value = {
    project_name = var.project_name
    environment  = var.environment
    region       = var.region
    backend_url  = module.code_engine.backend_url
    frontend_url = module.code_engine.frontend_url
    status = {
      backend  = module.code_engine.backend_status
      frontend = module.code_engine.frontend_status
    }
    services = {
      postgresql     = module.managed_services.postgresql_host
      object_storage = module.managed_services.object_storage_endpoint
      zilliz         = module.managed_services.zilliz_endpoint
      event_streams  = module.managed_services.event_streams_endpoint
    }
    features = {
      monitoring = var.enable_monitoring
      backups    = var.enable_backups
    }
  }
  sensitive = false
}
