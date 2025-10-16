# Outputs for IBM Cloud Backup Module

# Backup service outputs
output "backup_instance_id" {
  description = "Backup service instance ID"
  value       = ibm_resource_instance.backup.id
  sensitive   = false
}

output "backup_endpoint" {
  description = "Backup service endpoint"
  value       = ibm_resource_instance.backup.endpoints.public
  sensitive   = false
}

output "backup_credentials" {
  description = "Backup service credentials"
  value       = ibm_resource_key.backup_credentials.credentials
  sensitive   = true
}

# Backup storage outputs
output "backup_storage_bucket_name" {
  description = "Backup storage bucket name"
  value       = ibm_cos_bucket.backup_storage.bucket_name
  sensitive   = false
}

output "backup_storage_endpoint" {
  description = "Backup storage endpoint"
  value       = ibm_cos_bucket.backup_storage.endpoint
  sensitive   = false
}

# Backup policy outputs
output "postgresql_backup_policy_id" {
  description = "PostgreSQL backup policy ID"
  value       = ibm_backup_policy.postgresql_backup.id
  sensitive   = false
}

output "object_storage_backup_policy_id" {
  description = "Object Storage backup policy ID"
  value       = ibm_backup_policy.object_storage_backup.id
  sensitive   = false
}

output "zilliz_backup_policy_id" {
  description = "Zilliz Cloud backup policy ID"
  value       = ibm_backup_policy.zilliz_backup.id
  sensitive   = false
}

# Disaster recovery outputs
output "disaster_recovery_plan_id" {
  description = "Disaster recovery plan ID"
  value       = ibm_backup_dr_plan.disaster_recovery.id
  sensitive   = false
}

output "disaster_recovery_plan_name" {
  description = "Disaster recovery plan name"
  value       = ibm_backup_dr_plan.disaster_recovery.name
  sensitive   = false
}

# Backup monitoring outputs
output "backup_monitor_action_id" {
  description = "Backup monitor action ID"
  value       = ibm_function_action.backup_monitor.id
  sensitive   = false
}

output "backup_test_trigger_id" {
  description = "Backup test trigger ID"
  value       = ibm_function_trigger.backup_test_trigger.id
  sensitive   = false
}

# Backup configuration
output "backup_config" {
  description = "Backup configuration"
  value = {
    retention_days = var.backup_retention_days
    schedule = var.backup_schedule
    rto_minutes = var.rto_minutes
    rpo_minutes = var.rpo_minutes
    encryption_enabled = var.enable_backup_encryption
    monitoring_enabled = var.enable_backup_monitoring
    testing_enabled = var.enable_backup_testing
    cross_region_enabled = var.enable_cross_region_backup
    compression_enabled = var.enable_backup_compression
    compression_level = var.backup_compression_level
  }
  sensitive = false
}

# Backup URLs
output "backup_dashboard_url" {
  description = "Backup dashboard URL"
  value       = "https://${ibm_resource_instance.backup.endpoints.public}/dashboard"
  sensitive   = false
}

output "backup_health_endpoint" {
  description = "Backup health endpoint"
  value       = "https://${ibm_resource_instance.backup.endpoints.public}/health"
  sensitive   = false
}

# Service backup status
output "backup_status" {
  description = "Backup status for all services"
  value = {
    postgresql = {
      policy_id = ibm_backup_policy.postgresql_backup.id
      enabled = true
      schedule = "02:00 UTC daily"
    }
    object_storage = {
      policy_id = ibm_backup_policy.object_storage_backup.id
      enabled = true
      schedule = "03:00 UTC daily"
    }
    zilliz = {
      policy_id = ibm_backup_policy.zilliz_backup.id
      enabled = true
      schedule = "04:00 UTC daily"
    }
  }
  sensitive = false
}

# Recovery procedures
output "recovery_procedures" {
  description = "Disaster recovery procedures"
  value = {
    postgresql = [
      "1. Stop application services",
      "2. Restore PostgreSQL from backup",
      "3. Verify data integrity",
      "4. Start application services"
    ]
    object_storage = [
      "1. Stop application services",
      "2. Restore Object Storage from backup",
      "3. Verify data integrity",
      "4. Start application services"
    ]
    zilliz = [
      "1. Stop application services",
      "2. Restore Zilliz Cloud from backup",
      "3. Verify data integrity",
      "4. Start application services"
    ]
  }
  sensitive = false
}
