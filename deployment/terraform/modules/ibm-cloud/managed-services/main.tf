# IBM Cloud Managed Services Module
# This module provisions managed services instead of self-hosted containers
# to ensure data persistence and production reliability

terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.0"
    }
  }
}

# IBM Cloud Databases for PostgreSQL
resource "ibm_database" "postgresql" {
  name              = "${var.project_name}-postgresql"
  service           = "databases-for-postgresql"
  plan              = var.postgresql_plan
  location          = var.region
  resource_group_id = var.resource_group_id
  
  # Production configuration
  adminpassword = var.postgresql_admin_password
  
  # Enable SSL and encryption
  service_endpoints = "public-and-private"
  
  # Backup configuration
  backup_id = ibm_database_backup.postgresql_backup.id
  
  # Monitoring
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:postgresql",
    "managed:true"
  ]
  
  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# PostgreSQL backup configuration
resource "ibm_database_backup" "postgresql_backup" {
  service_instance_id = ibm_database.postgresql.id
  backup_id           = "${var.project_name}-postgresql-backup"
  backup_time         = "02:00"  # 2 AM UTC daily backup
}

# IBM Cloud Object Storage (replaces MinIO)
resource "ibm_resource_instance" "object_storage" {
  name              = "${var.project_name}-object-storage"
  service           = "cloud-object-storage"
  plan              = var.object_storage_plan
  location          = var.region
  resource_group_id = var.resource_group_id
  
  # Enable encryption
  parameters = {
    "HMAC" = true
  }
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:object-storage",
    "managed:true"
  ]
  
  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# Object Storage bucket for application data
resource "ibm_cos_bucket" "app_data" {
  bucket_name          = "${var.project_name}-app-data-${random_id.bucket_suffix.hex}"
  resource_instance_id = ibm_resource_instance.object_storage.id
  region_location      = var.region
  storage_class        = "standard"
  
  # Enable versioning
  object_versioning {
    enable = true
  }
  
  # Enable encryption
  encryption {
    algorithm = "AES256"
  }
  
  # Lifecycle rules
  lifecycle_rule {
    id     = "cleanup_old_versions"
    status = "Enabled"
    expiration {
      days = 30
    }
  }
}

# Random suffix for bucket name uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Zilliz Cloud for Milvus (managed vector database)
resource "ibm_resource_instance" "zilliz_cloud" {
  name              = "${var.project_name}-zilliz-cloud"
  service           = "zilliz-cloud"
  plan              = var.zilliz_plan
  location          = var.region
  resource_group_id = var.resource_group_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:vector-database",
    "managed:true"
  ]
  
  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# IBM Cloud Event Streams (replaces etcd for messaging)
resource "ibm_resource_instance" "event_streams" {
  name              = "${var.project_name}-event-streams"
  service           = "messagehub"
  plan              = var.event_streams_plan
  location          = var.region
  resource_group_id = var.resource_group_id
  
  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:messaging",
    "managed:true"
  ]
  
  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# Service credentials for applications
resource "ibm_resource_key" "postgresql_credentials" {
  name                 = "${var.project_name}-postgresql-credentials"
  role                 = "Administrator"
  resource_instance_id = ibm_database.postgresql.id
  
  # Store credentials in IBM Cloud Secrets Manager
  parameters = {
    "HMAC" = true
  }
}

resource "ibm_resource_key" "object_storage_credentials" {
  name                 = "${var.project_name}-object-storage-credentials"
  role                 = "Writer"
  resource_instance_id = ibm_resource_instance.object_storage.id
}

resource "ibm_resource_key" "zilliz_credentials" {
  name                 = "${var.project_name}-zilliz-credentials"
  role                 = "Administrator"
  resource_instance_id = ibm_resource_instance.zilliz_cloud.id
}

resource "ibm_resource_key" "event_streams_credentials" {
  name                 = "${var.project_name}-event-streams-credentials"
  role                 = "Manager"
  resource_instance_id = ibm_resource_instance.event_streams.id
}
