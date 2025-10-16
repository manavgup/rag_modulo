# Variables for IBM Cloud Environment Configuration

# Project configuration
variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "rag-modulo"
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

# IBM Cloud configuration
variable "region" {
  description = "IBM Cloud region"
  type        = string
  default     = "us-south"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.region))
    error_message = "Region must be a valid IBM Cloud region."
  }
}

variable "resource_group_name" {
  description = "IBM Cloud resource group name"
  type        = string
  default     = "default"
}

variable "ibmcloud_api_key" {
  description = "IBM Cloud API key"
  type        = string
  sensitive   = true
}

# Container registry configuration
variable "container_registry_url" {
  description = "Container registry URL"
  type        = string
  default     = "us.icr.io"
}

variable "container_registry_username" {
  description = "Container registry username"
  type        = string
  sensitive   = true
}

variable "container_registry_password" {
  description = "Container registry password"
  type        = string
  sensitive   = true
}

# Image tags
variable "backend_image_tag" {
  description = "Backend image tag"
  type        = string
  default     = "v1.0.0"
  validation {
    condition     = !can(regex("latest", var.backend_image_tag))
    error_message = "Backend image tag cannot be 'latest' for security reasons."
  }
}

variable "frontend_image_tag" {
  description = "Frontend image tag"
  type        = string
  default     = "v1.0.0"
  validation {
    condition     = !can(regex("latest", var.frontend_image_tag))
    error_message = "Frontend image tag cannot be 'latest' for security reasons."
  }
}

# Backend scaling configuration
variable "backend_min_scale" {
  description = "Minimum number of backend instances"
  type        = number
  default     = 1
  validation {
    condition     = var.backend_min_scale >= 0 && var.backend_min_scale <= 10
    error_message = "Backend min scale must be between 0 and 10."
  }
}

variable "backend_max_scale" {
  description = "Maximum number of backend instances"
  type        = number
  default     = 10
  validation {
    condition     = var.backend_max_scale >= 1 && var.backend_max_scale <= 100
    error_message = "Backend max scale must be between 1 and 100."
  }
}

variable "backend_cpu" {
  description = "Backend CPU allocation"
  type        = string
  default     = "1"
  validation {
    condition     = can(regex("^[0-9]+(\\.[0-9]+)?$", var.backend_cpu))
    error_message = "Backend CPU must be a valid number."
  }
}

variable "backend_memory" {
  description = "Backend memory allocation"
  type        = string
  default     = "2Gi"
  validation {
    condition     = can(regex("^[0-9]+(\\.[0-9]+)?[GMK]i?$", var.backend_memory))
    error_message = "Backend memory must be a valid Kubernetes memory specification."
  }
}

# Frontend scaling configuration
variable "frontend_min_scale" {
  description = "Minimum number of frontend instances"
  type        = number
  default     = 1
  validation {
    condition     = var.frontend_min_scale >= 0 && var.frontend_min_scale <= 10
    error_message = "Frontend min scale must be between 0 and 10."
  }
}

variable "frontend_max_scale" {
  description = "Maximum number of frontend instances"
  type        = number
  default     = 5
  validation {
    condition     = var.frontend_max_scale >= 1 && var.frontend_max_scale <= 50
    error_message = "Frontend max scale must be between 1 and 50."
  }
}

variable "frontend_cpu" {
  description = "Frontend CPU allocation"
  type        = string
  default     = "0.5"
  validation {
    condition     = can(regex("^[0-9]+(\\.[0-9]+)?$", var.frontend_cpu))
    error_message = "Frontend CPU must be a valid number."
  }
}

variable "frontend_memory" {
  description = "Frontend memory allocation"
  type        = string
  default     = "1Gi"
  validation {
    condition     = can(regex("^[0-9]+(\\.[0-9]+)?[GMK]i?$", var.frontend_memory))
    error_message = "Frontend memory must be a valid Kubernetes memory specification."
  }
}

# Managed services configuration
variable "postgresql_plan" {
  description = "PostgreSQL service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.postgresql_plan)
    error_message = "PostgreSQL plan must be one of: standard, premium, enterprise."
  }
}

variable "object_storage_plan" {
  description = "Object Storage service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.object_storage_plan)
    error_message = "Object Storage plan must be one of: standard, premium, enterprise."
  }
}

variable "zilliz_plan" {
  description = "Zilliz Cloud service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.zilliz_plan)
    error_message = "Zilliz Cloud plan must be one of: standard, premium, enterprise."
  }
}

variable "event_streams_plan" {
  description = "Event Streams service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.event_streams_plan)
    error_message = "Event Streams plan must be one of: standard, premium, enterprise."
  }
}

variable "postgresql_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.postgresql_admin_password) >= 12
    error_message = "PostgreSQL admin password must be at least 12 characters long."
  }
}

# Production safeguards
variable "enable_production_safeguards" {
  description = "Enable production safeguards (prevents insecure settings)"
  type        = bool
  default     = false
}

variable "allowed_debug_settings" {
  description = "Allowed debug settings for production"
  type        = list(string)
  default     = []
  validation {
    condition = var.enable_production_safeguards ? length(var.allowed_debug_settings) == 0 : true
    error_message = "Debug settings are not allowed in production when safeguards are enabled."
  }
}

variable "allowed_skip_auth_settings" {
  description = "Allowed skip auth settings for production"
  type        = list(string)
  default     = []
  validation {
    condition = var.enable_production_safeguards ? length(var.allowed_skip_auth_settings) == 0 : true
    error_message = "Skip auth settings are not allowed in production when safeguards are enabled."
  }
}

# Feature flags
variable "enable_monitoring" {
  description = "Enable monitoring and observability"
  type        = bool
  default     = true
}

variable "enable_backups" {
  description = "Enable backup and disaster recovery"
  type        = bool
  default     = false
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

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = list(string)
  default     = []
}
