# IBM Cloud Backup Module
# This module sets up comprehensive backup and disaster recovery for RAG Modulo

terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.0"
    }
  }
}

# IBM Cloud Backup service
resource "ibm_resource_instance" "backup" {
  name              = "${var.project_name}-backup"
  service           = "cloud-backup"
  plan              = var.backup_plan
  location          = var.region
  resource_group_id = var.resource_group_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:backup",
    "managed:true"
  ]
  
  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# Backup service credentials
resource "ibm_resource_key" "backup_credentials" {
  name                 = "${var.project_name}-backup-credentials"
  role                 = "Manager"
  resource_instance_id = ibm_resource_instance.backup.id
}

# Backup storage (Object Storage for backup data)
resource "ibm_cos_bucket" "backup_storage" {
  bucket_name          = "${var.project_name}-backup-storage-${random_id.backup_suffix.hex}"
  resource_instance_id = var.object_storage_instance_id
  region_location      = var.region
  storage_class        = "standard"
  
  # Enable versioning for backup data
  object_versioning {
    enable = true
  }
  
  # Enable encryption
  encryption {
    algorithm = "AES256"
  }
  
  # Lifecycle rules for backup retention
  lifecycle_rule {
    id     = "backup_retention"
    status = "Enabled"
    expiration {
      days = var.backup_retention_days
    }
  }
  
  # Transition to cheaper storage after 30 days
  lifecycle_rule {
    id     = "backup_transition"
    status = "Enabled"
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:backup-storage",
    "managed:true"
  ]
}

# Random suffix for bucket name uniqueness
resource "random_id" "backup_suffix" {
  byte_length = 4
}

# Backup policies
resource "ibm_backup_policy" "postgresql_backup" {
  name = "${var.project_name}-postgresql-backup-policy"
  
  # Daily backup at 2 AM UTC
  schedule {
    frequency = "daily"
    time      = "02:00"
    timezone  = "UTC"
  }
  
  # Backup retention
  retention {
    days = var.backup_retention_days
  }
  
  # Backup source (PostgreSQL)
  source {
    type = "postgresql"
    instance_id = var.postgresql_instance_id
  }
  
  # Backup destination
  destination {
    type = "object_storage"
    bucket = ibm_cos_bucket.backup_storage.bucket_name
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:postgresql",
    "backup:policy"
  ]
}

resource "ibm_backup_policy" "object_storage_backup" {
  name = "${var.project_name}-object-storage-backup-policy"
  
  # Daily backup at 3 AM UTC
  schedule {
    frequency = "daily"
    time      = "03:00"
    timezone  = "UTC"
  }
  
  # Backup retention
  retention {
    days = var.backup_retention_days
  }
  
  # Backup source (Object Storage)
  source {
    type = "object_storage"
    instance_id = var.object_storage_instance_id
  }
  
  # Backup destination
  destination {
    type = "object_storage"
    bucket = ibm_cos_bucket.backup_storage.bucket_name
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:object-storage",
    "backup:policy"
  ]
}

resource "ibm_backup_policy" "zilliz_backup" {
  name = "${var.project_name}-zilliz-backup-policy"
  
  # Daily backup at 4 AM UTC
  schedule {
    frequency = "daily"
    time      = "04:00"
    timezone  = "UTC"
  }
  
  # Backup retention
  retention {
    days = var.backup_retention_days
  }
  
  # Backup source (Zilliz Cloud)
  source {
    type = "vector_database"
    instance_id = var.zilliz_instance_id
  }
  
  # Backup destination
  destination {
    type = "object_storage"
    bucket = ibm_cos_bucket.backup_storage.bucket_name
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:zilliz",
    "backup:policy"
  ]
}

# Disaster recovery configuration
resource "ibm_backup_dr_plan" "disaster_recovery" {
  name = "${var.project_name}-disaster-recovery-plan"
  
  # Recovery time objective (RTO) in minutes
  rto_minutes = var.rto_minutes
  
  # Recovery point objective (RPO) in minutes
  rpo_minutes = var.rpo_minutes
  
  # Recovery procedures
  recovery_procedures {
    name = "postgresql_recovery"
    description = "Recover PostgreSQL database"
    steps = [
      "1. Stop application services",
      "2. Restore PostgreSQL from backup",
      "3. Verify data integrity",
      "4. Start application services"
    ]
  }
  
  recovery_procedures {
    name = "object_storage_recovery"
    description = "Recover Object Storage data"
    steps = [
      "1. Stop application services",
      "2. Restore Object Storage from backup",
      "3. Verify data integrity",
      "4. Start application services"
    ]
  }
  
  recovery_procedures {
    name = "zilliz_recovery"
    description = "Recover Zilliz Cloud data"
    steps = [
      "1. Stop application services",
      "2. Restore Zilliz Cloud from backup",
      "3. Verify data integrity",
      "4. Start application services"
    ]
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:disaster-recovery",
    "backup:dr-plan"
  ]
}

# Backup monitoring and alerting
resource "ibm_function_action" "backup_monitor" {
  name = "${var.project_name}-backup-monitor"
  
  exec {
    kind = "nodejs:16"
    code = <<EOF
function main(params) {
  const backupStatus = params.backup_status;
  const timestamp = new Date().toISOString();
  
  // Check backup status
  if (backupStatus.status === 'failed') {
    const alert = {
      severity: 'critical',
      message: `Backup failed: ${backupStatus.error}`,
      timestamp: timestamp,
      service: backupStatus.service,
      backup_id: backupStatus.backup_id
    };
    
    // Send alert to monitoring system
    console.log('Backup failure alert:', JSON.stringify(alert, null, 2));
    
    return {
      status: 'alert_sent',
      alert: alert
    };
  }
  
  return {
    status: 'success',
    message: 'Backup completed successfully',
    timestamp: timestamp
  };
}
EOF
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:backup-monitoring"
  ]
}

# Backup test schedule
resource "ibm_function_trigger" "backup_test_trigger" {
  name = "${var.project_name}-backup-test-trigger"
  
  feed {
    name = "/whisk.system/alarms/interval"
    parameters = jsonencode({
      trigger_payload = "backup-test"
      cron = "0 0 * * 0"  # Weekly on Sunday at midnight
    })
  }
  
  user_defined_annotations = jsonencode({
    "description" = "Trigger for weekly backup testing"
  })
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:backup-testing"
  ]
}

# Backup test rule
resource "ibm_function_rule" "backup_test_rule" {
  name = "${var.project_name}-backup-test-rule"
  trigger_name = ibm_function_trigger.backup_test_trigger.name
  action_name = ibm_function_action.backup_monitor.name
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:backup-testing"
  ]
}
