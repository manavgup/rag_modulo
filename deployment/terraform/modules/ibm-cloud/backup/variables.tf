# Variables for IBM Cloud Backup Module

variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "region" {
  description = "IBM Cloud region"
  type        = string
  default     = "us-south"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.region))
    error_message = "Region must be a valid IBM Cloud region."
  }
}

variable "resource_group_id" {
  description = "IBM Cloud resource group ID"
  type        = string
}

# Service instance IDs
variable "postgresql_instance_id" {
  description = "PostgreSQL service instance ID"
  type        = string
}

variable "object_storage_instance_id" {
  description = "Object Storage service instance ID"
  type        = string
}

variable "zilliz_instance_id" {
  description = "Zilliz Cloud service instance ID"
  type        = string
}

# Backup configuration
variable "backup_plan" {
  description = "Backup service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.backup_plan)
    error_message = "Backup plan must be one of: standard, premium, enterprise."
  }
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}

variable "backup_schedule" {
  description = "Backup schedule (cron format)"
  type        = string
  default     = "0 2 * * *"  # Daily at 2 AM UTC
}

# Disaster recovery configuration
variable "rto_minutes" {
  description = "Recovery Time Objective in minutes"
  type        = number
  default     = 60
  validation {
    condition     = var.rto_minutes >= 15 && var.rto_minutes <= 1440
    error_message = "RTO must be between 15 and 1440 minutes (24 hours)."
  }
}

variable "rpo_minutes" {
  description = "Recovery Point Objective in minutes"
  type        = number
  default     = 15
  validation {
    condition     = var.rpo_minutes >= 5 && var.rpo_minutes <= 1440
    error_message = "RPO must be between 5 and 1440 minutes (24 hours)."
  }
}

# Backup encryption
variable "enable_backup_encryption" {
  description = "Enable backup encryption"
  type        = bool
  default     = true
}

variable "backup_encryption_key" {
  description = "Backup encryption key"
  type        = string
  sensitive   = true
  default     = ""
}

# Backup monitoring
variable "enable_backup_monitoring" {
  description = "Enable backup monitoring and alerting"
  type        = bool
  default     = true
}

variable "backup_alert_webhook_url" {
  description = "Webhook URL for backup alerts"
  type        = string
  default     = ""
}

# Backup testing
variable "enable_backup_testing" {
  description = "Enable automated backup testing"
  type        = bool
  default     = true
}

variable "backup_test_frequency" {
  description = "Backup test frequency (cron format)"
  type        = string
  default     = "0 0 * * 0"  # Weekly on Sunday at midnight
}

# Cross-region backup
variable "enable_cross_region_backup" {
  description = "Enable cross-region backup replication"
  type        = bool
  default     = false
}

variable "backup_replication_region" {
  description = "Region for backup replication"
  type        = string
  default     = "us-east"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.backup_replication_region))
    error_message = "Backup replication region must be a valid IBM Cloud region."
  }
}

# Backup compression
variable "enable_backup_compression" {
  description = "Enable backup compression"
  type        = bool
  default     = true
}

variable "backup_compression_level" {
  description = "Backup compression level (1-9)"
  type        = number
  default     = 6
  validation {
    condition     = var.backup_compression_level >= 1 && var.backup_compression_level <= 9
    error_message = "Backup compression level must be between 1 and 9."
  }
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = list(string)
  default     = []
}
