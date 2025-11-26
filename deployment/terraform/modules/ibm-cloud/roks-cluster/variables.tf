# ROKS Cluster Module Variables

# Basic Configuration
variable "cluster_name" {
  description = "Name of the ROKS cluster"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.cluster_name))
    error_message = "Cluster name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "resource_group_name" {
  description = "IBM Cloud resource group name"
  type        = string
}

variable "region" {
  description = "IBM Cloud region (e.g., us-south, us-east, eu-de, ca-tor)"
  type        = string
  default     = "ca-tor"
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "dev"
}

# Worker Node Configuration
variable "worker_flavor" {
  description = "Worker node flavor/size (see 'ibmcloud ks flavors --zone <zone> --provider vpc-gen2')"
  type        = string
  default     = "bx2.8x32"  # 8 vCPUs, 32GB RAM - recommended for Milvus + RAG workloads

  # Available flavors (VPC Gen 2):
  # bx2.4x16   - 4 vCPUs, 16GB RAM (minimum for small workloads)
  # bx2.8x32   - 8 vCPUs, 32GB RAM (recommended for production)
  # bx2.16x64  - 16 vCPUs, 64GB RAM (for heavy workloads)
  # bx2.32x128 - 32 vCPUs, 128GB RAM (for very large deployments)
}

variable "worker_count_per_zone" {
  description = "Number of worker nodes per zone"
  type        = number
  default     = 2  # 2 workers x 3 zones = 6 total workers for HA
  validation {
    condition     = var.worker_count_per_zone >= 1 && var.worker_count_per_zone <= 10
    error_message = "Worker count per zone must be between 1 and 10."
  }
}

variable "openshift_version" {
  description = "OpenShift version (check: ibmcloud ks versions --show-version OpenShift)"
  type        = string
  default     = "4.19_openshift"  # Current default (Nov 2025)

  # Note: 4.14 and 4.15 are deprecated and will be unsupported
  # Supported versions: 4.16, 4.17, 4.18, 4.19 (default)
}

# Additional Worker Pool (optional)
variable "create_additional_worker_pool" {
  description = "Create an additional worker pool for specific workloads"
  type        = bool
  default     = false
}

variable "additional_worker_flavor" {
  description = "Flavor for additional worker pool"
  type        = string
  default     = "bx2.16x64"  # Larger nodes for compute-intensive tasks
}

variable "additional_worker_count_per_zone" {
  description = "Worker count per zone for additional pool"
  type        = number
  default     = 1
}

variable "additional_worker_labels" {
  description = "Labels for additional worker pool nodes"
  type        = map(string)
  default = {
    "workload" = "compute-intensive"
    "tier"     = "high-performance"
  }
}

variable "additional_worker_taint_key" {
  description = "Taint key for additional worker pool"
  type        = string
  default     = "dedicated"
}

variable "additional_worker_taint_value" {
  description = "Taint value for additional worker pool"
  type        = string
  default     = "compute"
}

variable "additional_worker_taint_effect" {
  description = "Taint effect for additional worker pool"
  type        = string
  default     = "NoSchedule"
}

# Networking Configuration
variable "subnet_ip_count" {
  description = "Number of IPv4 addresses in each subnet"
  type        = number
  default     = 256
}

variable "enable_public_gateway" {
  description = "Enable public gateway for internet access"
  type        = bool
  default     = true
}

variable "disable_public_service_endpoint" {
  description = "Disable public service endpoint"
  type        = bool
  default     = false
}

# Security Configuration
variable "pod_security_policy" {
  description = "Enable pod security policy"
  type        = bool
  default     = false  # Deprecated in newer OpenShift versions
}

# Storage Configuration
variable "cos_instance_crn" {
  description = "CRN of Cloud Object Storage instance for cluster backups"
  type        = string
  default     = ""
}

# Encryption Configuration
variable "kms_instance_id" {
  description = "KMS instance ID for encryption"
  type        = string
  default     = ""
}

variable "kms_instance_crn" {
  description = "KMS instance CRN for encryption"
  type        = string
  default     = ""
}

variable "kms_private_endpoint" {
  description = "Use KMS private endpoint"
  type        = bool
  default     = false
}

# Security Group Configuration
variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed for inbound HTTP/HTTPS traffic. ⚠️ SECURITY: 0.0.0.0/0 is not allowed in production environments!"
  type        = list(string)
  default     = ["0.0.0.0/0"]

  validation {
    condition     = length(var.allowed_cidr_blocks) > 0
    error_message = "At least one CIDR block must be specified."
  }

  validation {
    condition = var.environment != "production" || !contains(var.allowed_cidr_blocks, "0.0.0.0/0")
    error_message = "Security violation: 0.0.0.0/0 is not allowed in production. Specify restricted CIDR blocks."
  }
}

variable "allowed_icmp_cidr_blocks" {
  description = "List of CIDR blocks allowed for inbound ICMP traffic (default: 0.0.0.0/0)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = list(string)
  default     = []
}
