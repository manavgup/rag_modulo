# Outputs for IBM Cloud Managed Services Module

# PostgreSQL outputs
output "postgresql_host" {
  description = "PostgreSQL host endpoint"
  value       = ibm_database.postgresql.connectionstrings[0].hosts[0].hostname
  sensitive   = false
}

output "postgresql_port" {
  description = "PostgreSQL port"
  value       = ibm_database.postgresql.connectionstrings[0].hosts[0].port
  sensitive   = false
}

output "postgresql_database" {
  description = "PostgreSQL database name"
  value       = ibm_database.postgresql.connectionstrings[0].database
  sensitive   = false
}

output "postgresql_username" {
  description = "PostgreSQL username"
  value       = ibm_database.postgresql.connectionstrings[0].username
  sensitive   = false
}

output "postgresql_password" {
  description = "PostgreSQL password"
  value       = ibm_database.postgresql.connectionstrings[0].password
  sensitive   = true
}

output "postgresql_ssl_cert" {
  description = "PostgreSQL SSL certificate"
  value       = ibm_database.postgresql.connectionstrings[0].certname
  sensitive   = false
}

# Object Storage outputs
output "object_storage_endpoint" {
  description = "Object Storage endpoint"
  value       = ibm_resource_instance.object_storage.endpoints.public
  sensitive   = false
}

output "object_storage_bucket_name" {
  description = "Object Storage bucket name"
  value       = ibm_cos_bucket.app_data.bucket_name
  sensitive   = false
}

output "object_storage_access_key" {
  description = "Object Storage access key"
  value       = ibm_resource_key.object_storage_credentials.credentials.apikey
  sensitive   = true
}

output "object_storage_secret_key" {
  description = "Object Storage secret key"
  value       = ibm_resource_key.object_storage_credentials.credentials.secret_key
  sensitive   = true
}

# Zilliz Cloud outputs
output "zilliz_endpoint" {
  description = "Zilliz Cloud endpoint"
  value       = ibm_resource_instance.zilliz_cloud.endpoints.public
  sensitive   = false
}

output "zilliz_api_key" {
  description = "Zilliz Cloud API key"
  value       = ibm_resource_key.zilliz_credentials.credentials.apikey
  sensitive   = true
}

# Event Streams outputs
output "event_streams_endpoint" {
  description = "Event Streams endpoint"
  value       = ibm_resource_instance.event_streams.endpoints.public
  sensitive   = false
}

output "event_streams_api_key" {
  description = "Event Streams API key"
  value       = ibm_resource_key.event_streams_credentials.credentials.apikey
  sensitive   = true
}

# Service credentials (for applications)
output "postgresql_credentials" {
  description = "PostgreSQL service credentials"
  value       = ibm_resource_key.postgresql_credentials.credentials
  sensitive   = true
}

output "object_storage_credentials" {
  description = "Object Storage service credentials"
  value       = ibm_resource_key.object_storage_credentials.credentials
  sensitive   = true
}

output "zilliz_credentials" {
  description = "Zilliz Cloud service credentials"
  value       = ibm_resource_key.zilliz_credentials.credentials
  sensitive   = true
}

output "event_streams_credentials" {
  description = "Event Streams service credentials"
  value       = ibm_resource_key.event_streams_credentials.credentials
  sensitive   = true
}

# Service instance IDs (for monitoring and management)
output "postgresql_instance_id" {
  description = "PostgreSQL service instance ID"
  value       = ibm_database.postgresql.id
  sensitive   = false
}

output "object_storage_instance_id" {
  description = "Object Storage service instance ID"
  value       = ibm_resource_instance.object_storage.id
  sensitive   = false
}

output "zilliz_instance_id" {
  description = "Zilliz Cloud service instance ID"
  value       = ibm_resource_instance.zilliz_cloud.id
  sensitive   = false
}

output "event_streams_instance_id" {
  description = "Event Streams service instance ID"
  value       = ibm_resource_instance.event_streams.id
  sensitive   = false
}
