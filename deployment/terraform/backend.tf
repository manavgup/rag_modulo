# Terraform Backend Configuration
# This file configures the remote state backend using IBM Cloud Object Storage

terraform {
  backend "s3" {
    # IBM Cloud Object Storage S3-compatible endpoint
    endpoint = "s3.us-south.cloud-object-storage.appdomain.cloud"
    
    # Bucket configuration
    bucket = "rag-modulo-terraform-state"
    key    = "ibm/environments/terraform.tfstate"
    region = "us-south"
    
    # Enable versioning and encryption
    versioning = true
    encrypt   = true
    
    # State locking (using IBM Cloud Databases for PostgreSQL)
    dynamodb_endpoint = "https://dynamodb.us-south.cloud-object-storage.appdomain.cloud"
    dynamodb_table   = "rag-modulo-terraform-locks"
    
    # Skip SSL verification for IBM Cloud Object Storage
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    force_path_style           = true
  }
}

# Alternative backend configuration using IBM Cloud Object Storage
# Uncomment this section if the S3-compatible backend doesn't work
/*
terraform {
  backend "http" {
    address = "https://us-south.cloud-object-storage.appdomain.cloud/rag-modulo-terraform-state/ibm/environments/terraform.tfstate"
    lock_address = "https://us-south.cloud-object-storage.appdomain.cloud/rag-modulo-terraform-state/ibm/environments/terraform.tfstate.lock"
    unlock_address = "https://us-south.cloud-object-storage.appdomain.cloud/rag-modulo-terraform-state/ibm/environments/terraform.tfstate.unlock"
  }
}
*/

# Local backend fallback (for development only)
# Uncomment this section for local development
/*
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
*/
