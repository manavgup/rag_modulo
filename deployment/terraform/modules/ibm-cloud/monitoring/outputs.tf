# Outputs for IBM Cloud Monitoring Module

# Monitoring service outputs
output "monitoring_instance_id" {
  description = "Monitoring service instance ID"
  value       = ibm_resource_instance.monitoring.id
  sensitive   = false
}

output "monitoring_endpoint" {
  description = "Monitoring service endpoint"
  value       = ibm_resource_instance.monitoring.endpoints.public
  sensitive   = false
}

output "monitoring_credentials" {
  description = "Monitoring service credentials"
  value       = ibm_resource_key.monitoring_credentials.credentials
  sensitive   = true
}

# Log Analysis outputs
output "log_analysis_instance_id" {
  description = "Log Analysis service instance ID"
  value       = ibm_resource_instance.log_analysis.id
  sensitive   = false
}

output "log_analysis_endpoint" {
  description = "Log Analysis service endpoint"
  value       = ibm_resource_instance.log_analysis.endpoints.public
  sensitive   = false
}

output "log_analysis_credentials" {
  description = "Log Analysis service credentials"
  value       = ibm_resource_key.log_analysis_credentials.credentials
  sensitive   = true
}

# APM outputs
output "apm_instance_id" {
  description = "APM service instance ID"
  value       = ibm_resource_instance.apm.id
  sensitive   = false
}

output "apm_endpoint" {
  description = "APM service endpoint"
  value       = ibm_resource_instance.apm.endpoints.public
  sensitive   = false
}

output "apm_credentials" {
  description = "APM service credentials"
  value       = ibm_resource_key.apm_credentials.credentials
  sensitive   = true
}

# Dashboard outputs
output "dashboard_instance_id" {
  description = "Dashboard service instance ID"
  value       = ibm_resource_instance.dashboard.id
  sensitive   = false
}

output "dashboard_endpoint" {
  description = "Dashboard service endpoint"
  value       = ibm_resource_instance.dashboard.endpoints.public
  sensitive   = false
}

output "dashboard_credentials" {
  description = "Dashboard service credentials"
  value       = ibm_resource_key.dashboard_credentials.credentials
  sensitive   = true
}

# Alerting outputs
output "alert_webhook_action_id" {
  description = "Alert webhook action ID"
  value       = ibm_function_action.alert_webhook.id
  sensitive   = false
}

output "alert_webhook_url" {
  description = "Alert webhook URL"
  value       = var.alert_webhook_url
  sensitive   = false
}

# Monitoring URLs
output "monitoring_dashboard_url" {
  description = "Monitoring dashboard URL"
  value       = "https://${ibm_resource_instance.monitoring.endpoints.public}/dashboard"
  sensitive   = false
}

output "log_analysis_dashboard_url" {
  description = "Log Analysis dashboard URL"
  value       = "https://${ibm_resource_instance.log_analysis.endpoints.public}/dashboard"
  sensitive   = false
}

output "apm_dashboard_url" {
  description = "APM dashboard URL"
  value       = "https://${ibm_resource_instance.apm.endpoints.public}/dashboard"
  sensitive   = false
}

# Service health endpoints
output "monitoring_health_endpoint" {
  description = "Monitoring health endpoint"
  value       = "https://${ibm_resource_instance.monitoring.endpoints.public}/health"
  sensitive   = false
}

output "log_analysis_health_endpoint" {
  description = "Log Analysis health endpoint"
  value       = "https://${ibm_resource_instance.log_analysis.endpoints.public}/health"
  sensitive   = false
}

output "apm_health_endpoint" {
  description = "APM health endpoint"
  value       = "https://${ibm_resource_instance.apm.endpoints.public}/health"
  sensitive   = false
}

# Monitoring configuration
output "monitoring_config" {
  description = "Monitoring configuration"
  value = {
    interval = var.monitoring_interval
    retention_days = var.retention_days
    real_time_enabled = var.enable_real_time_monitoring
    historical_enabled = var.enable_historical_monitoring
    alert_thresholds = var.alert_thresholds
  }
  sensitive = false
}

# Service endpoints for monitoring
output "monitored_endpoints" {
  description = "Endpoints being monitored"
  value = {
    backend = var.backend_endpoint
    frontend = var.frontend_endpoint
    postgresql = var.postgresql_endpoint
    object_storage = var.object_storage_endpoint
    zilliz = var.zilliz_endpoint
    event_streams = var.event_streams_endpoint
  }
  sensitive = false
}
