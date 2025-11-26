# IBM ROKS (Red Hat OpenShift on IBM Cloud) Cluster Module
# Provisions a production-ready OpenShift cluster with appropriate worker node sizing

terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.0"
    }
  }
}

# Data sources
data "ibm_resource_group" "resource_group" {
  name = var.resource_group_name
}

# Get available zones for the region
data "ibm_is_zones" "zones" {
  region = var.region
}

# VPC for the cluster
resource "ibm_is_vpc" "cluster_vpc" {
  name           = "${var.cluster_name}-vpc"
  resource_group = data.ibm_resource_group.resource_group.id
  tags           = concat(var.tags, ["vpc", "roks"])
}

# Public Gateway for outbound internet access (required for pulling images, etc.)
resource "ibm_is_public_gateway" "cluster_gateway" {
  count          = var.enable_public_gateway ? length(data.ibm_is_zones.zones.zones) : 0
  name           = "${var.cluster_name}-gateway-${count.index + 1}"
  vpc            = ibm_is_vpc.cluster_vpc.id
  zone           = data.ibm_is_zones.zones.zones[count.index]
  resource_group = data.ibm_resource_group.resource_group.id
  tags           = concat(var.tags, ["gateway", "roks"])
}

# Subnets for each zone
resource "ibm_is_subnet" "cluster_subnet" {
  count                    = length(data.ibm_is_zones.zones.zones)
  name                     = "${var.cluster_name}-subnet-${count.index + 1}"
  vpc                      = ibm_is_vpc.cluster_vpc.id
  zone                     = data.ibm_is_zones.zones.zones[count.index]
  total_ipv4_address_count = var.subnet_ip_count
  resource_group           = data.ibm_resource_group.resource_group.id
  public_gateway           = var.enable_public_gateway ? ibm_is_public_gateway.cluster_gateway[count.index].id : null
  tags                     = concat(var.tags, ["subnet", "roks", "zone-${count.index + 1}"])
}

# Security Group for cluster
resource "ibm_is_security_group" "cluster_sg" {
  name           = "${var.cluster_name}-sg"
  vpc            = ibm_is_vpc.cluster_vpc.id
  resource_group = data.ibm_resource_group.resource_group.id
  tags           = concat(var.tags, ["security-group", "roks"])
}

# Security Group Rules
resource "ibm_is_security_group_rule" "cluster_sg_rule_outbound" {
  group     = ibm_is_security_group.cluster_sg.id
  direction = "outbound"
  remote    = "0.0.0.0/0"  # Outbound to internet is typically required
}

resource "ibm_is_security_group_rule" "cluster_sg_rule_inbound_icmp" {
  count     = length(var.allowed_icmp_cidr_blocks)
  group     = ibm_is_security_group.cluster_sg.id
  direction = "inbound"
  remote    = var.allowed_icmp_cidr_blocks[count.index]
  icmp {
    type = 8  # Echo request
  }
}

resource "ibm_is_security_group_rule" "cluster_sg_rule_inbound_https" {
  count     = length(var.allowed_cidr_blocks)
  group     = ibm_is_security_group.cluster_sg.id
  direction = "inbound"
  remote    = var.allowed_cidr_blocks[count.index]
  tcp {
    port_min = 443
    port_max = 443
  }
}

resource "ibm_is_security_group_rule" "cluster_sg_rule_inbound_http" {
  count     = length(var.allowed_cidr_blocks)
  group     = ibm_is_security_group.cluster_sg.id
  direction = "inbound"
  remote    = var.allowed_cidr_blocks[count.index]
  tcp {
    port_min = 80
    port_max = 80
  }
}

# OpenShift Cluster
resource "ibm_container_vpc_cluster" "roks_cluster" {
  name              = var.cluster_name
  vpc_id            = ibm_is_vpc.cluster_vpc.id
  flavor            = var.worker_flavor
  worker_count      = var.worker_count_per_zone
  kube_version      = var.openshift_version
  resource_group_id = data.ibm_resource_group.resource_group.id
  cos_instance_crn  = var.cos_instance_crn

  # Deploy across multiple zones for high availability
  dynamic "zones" {
    for_each = ibm_is_subnet.cluster_subnet
    content {
      name      = zones.value.zone
      subnet_id = zones.value.id
    }
  }

  # Disable public service endpoint if required
  disable_public_service_endpoint = var.disable_public_service_endpoint

  # Wait for cluster to be fully ready
  wait_till = "IngressReady"

  tags = concat(var.tags, ["roks", "openshift", var.environment])

  # Timeouts
  timeouts {
    create = "2h"
    delete = "2h"
    update = "2h"
  }
}

# Worker Pool for additional capacity (optional)
resource "ibm_container_vpc_worker_pool" "additional_pool" {
  count             = var.create_additional_worker_pool ? 1 : 0
  cluster           = ibm_container_vpc_cluster.roks_cluster.id
  worker_pool_name  = "${var.cluster_name}-pool-2"
  flavor            = var.additional_worker_flavor
  vpc_id            = ibm_is_vpc.cluster_vpc.id
  worker_count      = var.additional_worker_count_per_zone
  resource_group_id = data.ibm_resource_group.resource_group.id

  dynamic "zones" {
    for_each = ibm_is_subnet.cluster_subnet
    content {
      name      = zones.value.zone
      subnet_id = zones.value.id
    }
  }

  labels = var.additional_worker_labels

  taints {
    key    = var.additional_worker_taint_key
    value  = var.additional_worker_taint_value
    effect = var.additional_worker_taint_effect
  }
}

# Cluster configuration for kubectl/oc
resource "null_resource" "cluster_config" {
  depends_on = [ibm_container_vpc_cluster.roks_cluster]

  provisioner "local-exec" {
    command = "ibmcloud ks cluster config --cluster ${ibm_container_vpc_cluster.roks_cluster.id} --admin"
  }

  triggers = {
    cluster_id = ibm_container_vpc_cluster.roks_cluster.id
  }
}
