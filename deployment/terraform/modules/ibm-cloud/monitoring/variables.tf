# Variables for IBM Cloud Monitoring Module

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

# Application endpoints
variable "backend_endpoint" {
  description = "Backend application endpoint"
  type        = string
}

variable "frontend_endpoint" {
  description = "Frontend application endpoint"
  type        = string
}

# Service endpoints
variable "postgresql_endpoint" {
  description = "PostgreSQL endpoint"
  type        = string
}

variable "object_storage_endpoint" {
  description = "Object Storage endpoint"
  type        = string
}

variable "zilliz_endpoint" {
  description = "Zilliz Cloud endpoint"
  type        = string
}

variable "event_streams_endpoint" {
  description = "Event Streams endpoint"
  type        = string
}

# Monitoring service plans
variable "monitoring_plan" {
  description = "Monitoring service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.monitoring_plan)
    error_message = "Monitoring plan must be one of: standard, premium, enterprise."
  }
}

variable "log_analysis_plan" {
  description = "Log Analysis service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.log_analysis_plan)
    error_message = "Log Analysis plan must be one of: standard, premium, enterprise."
  }
}

variable "apm_plan" {
  description = "APM service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.apm_plan)
    error_message = "APM plan must be one of: standard, premium, enterprise."
  }
}

variable "dashboard_plan" {
  description = "Dashboard service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.dashboard_plan)
    error_message = "Dashboard plan must be one of: standard, premium, enterprise."
  }
}

# Alert configuration
variable "alert_webhook_url" {
  description = "Webhook URL for alerts"
  type        = string
  default     = ""
}

variable "alert_thresholds" {
  description = "Alert thresholds"
  type        = map(number)
  default = {
    cpu_usage = 80
    memory_usage = 85
    disk_usage = 90
    response_time = 5000
    error_rate = 5
  }
}

# Monitoring configuration
variable "monitoring_interval" {
  description = "Monitoring interval in seconds"
  type        = number
  default     = 60
  validation {
    condition     = var.monitoring_interval >= 30 && var.monitoring_interval <= 300
    error_message = "Monitoring interval must be between 30 and 300 seconds."
  }
}

variable "retention_days" {
  description = "Data retention period in days"
  type        = number
  default     = 30
  validation {
    condition     = var.retention_days >= 7 && var.retention_days <= 365
    error_message = "Retention days must be between 7 and 365."
  }
}

# Dashboard configuration
variable "dashboard_refresh_interval" {
  description = "Dashboard refresh interval in seconds"
  type        = number
  default     = 30
  validation {
    condition     = var.dashboard_refresh_interval >= 10 && var.dashboard_refresh_interval <= 300
    error_message = "Dashboard refresh interval must be between 10 and 300 seconds."
  }
}

variable "enable_real_time_monitoring" {
  description = "Enable real-time monitoring"
  type        = bool
  default     = true
}

variable "enable_historical_monitoring" {
  description = "Enable historical monitoring"
  type        = bool
  default     = true
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = list(string)
  default     = []
}
