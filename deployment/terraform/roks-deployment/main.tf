terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.0"
    }
  }
}

provider "ibm" {
  region = "ca-tor"
}

module "roks_cluster" {
  source = "../modules/ibm-cloud/roks-cluster"

  cluster_name          = "rag-modulo-dev"
  resource_group_name   = "default"
  region                = "ca-tor"
  environment           = "dev"
  worker_flavor         = "bx2.8x32"
  worker_count_per_zone = 2
  openshift_version     = "4.14_openshift"
  cos_instance_crn      = "crn:v1:bluemix:public:cloud-object-storage:global:a/4b5f219cdaee498f9dac672a894e6a7e:af9cb74b-2f13-44bd-937c-b850dd71ed58::"

  tags = ["environment:dev", "project:rag-modulo", "managed-by:terraform"]
}

output "cluster_id" {
  value = module.roks_cluster.cluster_id
}

output "cluster_name" {
  value = module.roks_cluster.cluster_name
}

output "ingress_hostname" {
  value = module.roks_cluster.ingress_hostname
}

output "master_url" {
  value = module.roks_cluster.master_url
}
