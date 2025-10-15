# IBM Cloud Environment Configuration
# This file provisions the complete RAG Modulo infrastructure on IBM Cloud

terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Configure remote state backend
  backend "s3" {
    # This will be configured via backend.tf
    # Using IBM Cloud Object Storage as S3-compatible backend
  }
}

# Configure IBM Cloud provider
provider "ibm" {
  region           = var.region
  resource_group_id = var.resource_group_id

  # Enable debug logging for troubleshooting
  ibmcloud_api_key = var.ibmcloud_api_key
}

# Configure random provider
provider "random" {
  # No specific configuration needed
}

# Data sources
data "ibm_resource_group" "main" {
  name = var.resource_group_name
}

# Managed services module
module "managed_services" {
  source = "../../modules/ibm-cloud/managed-services"

  project_name = var.project_name
  environment  = var.environment
  region       = var.region
  resource_group_id = data.ibm_resource_group.main.id

  # Service plans
  postgresql_plan        = var.postgresql_plan
  object_storage_plan    = var.object_storage_plan
  zilliz_plan           = var.zilliz_plan
  event_streams_plan    = var.event_streams_plan

  # PostgreSQL configuration
  postgresql_admin_password = var.postgresql_admin_password

  # Production safeguards
  enable_production_safeguards = var.enable_production_safeguards
  allowed_debug_settings = var.allowed_debug_settings
  allowed_skip_auth_settings = var.allowed_skip_auth_settings

  tags = var.tags
}

# Code Engine module
module "code_engine" {
  source = "../../modules/ibm-cloud/code-engine"

  project_name = var.project_name
  environment  = var.environment
  resource_group_id = data.ibm_resource_group.main.id

  # Container registry configuration
  container_registry_url      = var.container_registry_url
  container_registry_username = var.container_registry_username
  container_registry_password = var.container_registry_password

  # Image tags
  backend_image_tag  = var.backend_image_tag
  frontend_image_tag = var.frontend_image_tag

  # Backend scaling
  backend_min_scale = var.backend_min_scale
  backend_max_scale = var.backend_max_scale
  backend_cpu       = var.backend_cpu
  backend_memory    = var.backend_memory

  # Frontend scaling
  frontend_min_scale = var.frontend_min_scale
  frontend_max_scale = var.frontend_max_scale
  frontend_cpu       = var.frontend_cpu
  frontend_memory    = var.frontend_memory

  # Managed services integration
  postgresql_host     = module.managed_services.postgresql_host
  postgresql_port     = module.managed_services.postgresql_port
  postgresql_database = module.managed_services.postgresql_database
  postgresql_username = module.managed_services.postgresql_username
  postgresql_password = module.managed_services.postgresql_password
  postgresql_instance_id = module.managed_services.postgresql_instance_id

  object_storage_endpoint     = module.managed_services.object_storage_endpoint
  object_storage_access_key   = module.managed_services.object_storage_access_key
  object_storage_secret_key   = module.managed_services.object_storage_secret_key
  object_storage_bucket_name  = module.managed_services.object_storage_bucket_name
  object_storage_instance_id  = module.managed_services.object_storage_instance_id

  zilliz_endpoint     = module.managed_services.zilliz_endpoint
  zilliz_api_key      = module.managed_services.zilliz_api_key
  zilliz_instance_id  = module.managed_services.zilliz_instance_id

  event_streams_endpoint     = module.managed_services.event_streams_endpoint
  event_streams_api_key      = module.managed_services.event_streams_api_key
  event_streams_instance_id  = module.managed_services.event_streams_instance_id

  # Production safeguards
  enable_production_safeguards = var.enable_production_safeguards

  tags = var.tags
}

# Monitoring module (if enabled)
module "monitoring" {
  count  = var.enable_monitoring ? 1 : 0
  source = "../../modules/ibm-cloud/monitoring"

  project_name = var.project_name
  environment  = var.environment
  resource_group_id = data.ibm_resource_group.main.id

  # Application endpoints
  backend_endpoint  = module.code_engine.backend_endpoint
  frontend_endpoint = module.code_engine.frontend_endpoint

  # Service endpoints
  postgresql_endpoint = module.managed_services.postgresql_host
  object_storage_endpoint = module.managed_services.object_storage_endpoint
  zilliz_endpoint = module.managed_services.zilliz_endpoint
  event_streams_endpoint = module.managed_services.event_streams_endpoint

  tags = var.tags
}

# Backup module (if enabled)
module "backup" {
  count  = var.enable_backups ? 1 : 0
  source = "../../modules/ibm-cloud/backup"

  project_name = var.project_name
  environment  = var.environment
  resource_group_id = data.ibm_resource_group.main.id

  # Service instance IDs
  postgresql_instance_id = module.managed_services.postgresql_instance_id
  object_storage_instance_id = module.managed_services.object_storage_instance_id
  zilliz_instance_id = module.managed_services.zilliz_instance_id

  # Backup configuration
  backup_retention_days = var.backup_retention_days
  backup_schedule = var.backup_schedule

  tags = var.tags
}
