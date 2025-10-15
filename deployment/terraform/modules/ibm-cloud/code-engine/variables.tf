# Variables for IBM Cloud Code Engine Module

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

variable "resource_group_id" {
  description = "IBM Cloud resource group ID"
  type        = string
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

# Image tags (specific, secure versions)
variable "backend_image_tag" {
  description = "Backend image tag (must be specific version, not 'latest')"
  type        = string
  default     = "v1.0.0"
  validation {
    condition     = !can(regex("latest", var.backend_image_tag))
    error_message = "Backend image tag cannot be 'latest' for security reasons."
  }
}

variable "frontend_image_tag" {
  description = "Frontend image tag (must be specific version, not 'latest')"
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

# Managed services configuration (from managed-services module)
variable "postgresql_host" {
  description = "PostgreSQL host endpoint"
  type        = string
}

variable "postgresql_port" {
  description = "PostgreSQL port"
  type        = number
  default     = 5432
}

variable "postgresql_database" {
  description = "PostgreSQL database name"
  type        = string
}

variable "postgresql_username" {
  description = "PostgreSQL username"
  type        = string
}

variable "postgresql_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "postgresql_instance_id" {
  description = "PostgreSQL service instance ID"
  type        = string
}

variable "object_storage_endpoint" {
  description = "Object Storage endpoint"
  type        = string
}

variable "object_storage_access_key" {
  description = "Object Storage access key"
  type        = string
  sensitive   = true
}

variable "object_storage_secret_key" {
  description = "Object Storage secret key"
  type        = string
  sensitive   = true
}

variable "object_storage_bucket_name" {
  description = "Object Storage bucket name"
  type        = string
}

variable "object_storage_instance_id" {
  description = "Object Storage service instance ID"
  type        = string
}

variable "zilliz_endpoint" {
  description = "Zilliz Cloud endpoint"
  type        = string
}

variable "zilliz_api_key" {
  description = "Zilliz Cloud API key"
  type        = string
  sensitive   = true
}

variable "zilliz_instance_id" {
  description = "Zilliz Cloud service instance ID"
  type        = string
}

variable "event_streams_endpoint" {
  description = "Event Streams endpoint"
  type        = string
}

variable "event_streams_api_key" {
  description = "Event Streams API key"
  type        = string
  sensitive   = true
}

variable "event_streams_instance_id" {
  description = "Event Streams service instance ID"
  type        = string
}

# Production safeguards
variable "enable_production_safeguards" {
  description = "Enable production safeguards (prevents insecure settings)"
  type        = bool
  default     = false
}

# Validation rules for production safeguards
locals {
  # Validate that production safeguards are enabled for production environment
  production_safeguards_validation = var.environment == "production" ? var.enable_production_safeguards : true

  # Validate scaling configuration
  scaling_validation = var.backend_min_scale <= var.backend_max_scale && var.frontend_min_scale <= var.frontend_max_scale
}

# Validation checks
resource "null_resource" "validation_checks" {
  count = 1

  provisioner "local-exec" {
    command = <<-EOT
      if [ "${var.environment}" = "production" ] && [ "${var.enable_production_safeguards}" = "false" ]; then
        echo "ERROR: Production safeguards must be enabled for production environment"
        exit 1
      fi

      if [ ${var.backend_min_scale} -gt ${var.backend_max_scale} ]; then
        echo "ERROR: Backend min scale cannot be greater than max scale"
        exit 1
      fi

      if [ ${var.frontend_min_scale} -gt ${var.frontend_max_scale} ]; then
        echo "ERROR: Frontend min scale cannot be greater than max scale"
        exit 1
      fi
    EOT
  }
}
