# ROKS Cluster Module Outputs

output "cluster_id" {
  description = "ID of the created ROKS cluster"
  value       = ibm_container_vpc_cluster.roks_cluster.id
}

output "cluster_name" {
  description = "Name of the ROKS cluster"
  value       = ibm_container_vpc_cluster.roks_cluster.name
}

output "cluster_crn" {
  description = "CRN of the ROKS cluster"
  value       = ibm_container_vpc_cluster.roks_cluster.crn
}

output "ingress_hostname" {
  description = "Ingress hostname for the cluster"
  value       = ibm_container_vpc_cluster.roks_cluster.ingress_hostname
}

output "ingress_secret" {
  description = "Ingress secret for the cluster"
  value       = ibm_container_vpc_cluster.roks_cluster.ingress_secret
  sensitive   = true
}

output "master_url" {
  description = "Master URL for the cluster"
  value       = ibm_container_vpc_cluster.roks_cluster.master_url
}

output "public_service_endpoint_url" {
  description = "Public service endpoint URL"
  value       = ibm_container_vpc_cluster.roks_cluster.public_service_endpoint_url
}

output "private_service_endpoint_url" {
  description = "Private service endpoint URL"
  value       = ibm_container_vpc_cluster.roks_cluster.private_service_endpoint_url
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = ibm_is_vpc.cluster_vpc.id
}

output "vpc_name" {
  description = "Name of the VPC"
  value       = ibm_is_vpc.cluster_vpc.name
}

output "subnet_ids" {
  description = "IDs of the subnets"
  value       = [for subnet in ibm_is_subnet.cluster_subnet : subnet.id]
}

output "worker_count" {
  description = "Total number of worker nodes"
  value       = var.worker_count_per_zone * length(data.ibm_is_zones.zones.zones)
}

output "worker_flavor" {
  description = "Worker node flavor"
  value       = var.worker_flavor
}

output "openshift_version" {
  description = "OpenShift version"
  value       = var.openshift_version
}
