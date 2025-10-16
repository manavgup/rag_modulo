# Variables for IBM Cloud Managed Services Module

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

# PostgreSQL configuration
variable "postgresql_plan" {
  description = "PostgreSQL service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.postgresql_plan)
    error_message = "PostgreSQL plan must be one of: standard, premium, enterprise."
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

# Object Storage configuration
variable "object_storage_plan" {
  description = "Object Storage service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.object_storage_plan)
    error_message = "Object Storage plan must be one of: standard, premium, enterprise."
  }
}

# Zilliz Cloud configuration
variable "zilliz_plan" {
  description = "Zilliz Cloud service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.zilliz_plan)
    error_message = "Zilliz Cloud plan must be one of: standard, premium, enterprise."
  }
}

# Event Streams configuration
variable "event_streams_plan" {
  description = "Event Streams service plan"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium", "enterprise"], var.event_streams_plan)
    error_message = "Event Streams plan must be one of: standard, premium, enterprise."
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
