# Terraform Backend Configuration
# This file configures the remote state backend using IBM Cloud Object Storage
#
# NOTE: Terraform backend blocks cannot use variables directly.
# For dynamic configuration, use partial backend configuration:
#   terraform init -backend-config="bucket=${TF_BACKEND_BUCKET}" \
#                  -backend-config="region=${TF_BACKEND_REGION}" \
#                  -backend-config="endpoint=${TF_BACKEND_ENDPOINT}"
#
# Environment variables (set in .env):
#   TF_BACKEND_ENDPOINT - S3 endpoint (default: s3.us-south.cloud-object-storage.appdomain.cloud)
#   TF_BACKEND_BUCKET - State bucket name (default: rag-modulo-terraform-state)
#   TF_BACKEND_REGION - Region (default: us-south)
#   TF_BACKEND_KEY - State file key (default: ibm/environments/terraform.tfstate)
#
# For local development, use the local backend (uncomment at bottom)

terraform {
  backend "s3" {
    # IBM Cloud Object Storage S3-compatible endpoint
    # Override via: -backend-config="endpoint=${TF_BACKEND_ENDPOINT}"
    endpoint = "s3.us-south.cloud-object-storage.appdomain.cloud"

    # Bucket configuration
    # Override via: -backend-config="bucket=${TF_BACKEND_BUCKET}"
    bucket = "rag-modulo-terraform-state"
    # Override via: -backend-config="key=${TF_BACKEND_KEY}"
    key    = "ibm/environments/terraform.tfstate"
    # Override via: -backend-config="region=${TF_BACKEND_REGION}"
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
