# Deploying to IBM Cloud Code Engine

This guide provides instructions for deploying the RAG Modulo application to IBM Cloud Code Engine, a fully managed, serverless platform.

## Prerequisites

Before you begin, ensure you have the following:

- An IBM Cloud account with the necessary permissions to create and manage Code Engine projects, Container Registry namespaces, and services.
- The [IBM Cloud CLI](https://cloud.ibm.com/docs/cli/cli) installed and configured on your local machine.
- The [Docker CLI](https://docs.docker.com/get-docker/) installed on your local machine.

## 1. Configure Environment Variables

The deployment script uses environment variables for configuration. Create a `.env` file in the root of the project and add the following variables:

```bash
# IBM Cloud API Key
IBMCLOUD_API_KEY="your_ibm_cloud_api_key"

# IBM Cloud Region (e.g., us-south, eu-de)
IBMCLOUD_REGION="us-south"

# IBM Cloud Resource Group
RESOURCE_GROUP="Default"

# Code Engine Project Name
CE_PROJECT_NAME="rag-modulo"

# Container Registry Namespace
REGISTRY_NAMESPACE="rag-modulo-ns"

# --- Managed Service Credentials ---
# These should be created in your IBM Cloud account.

# URL for your managed PostgreSQL database
DATABASE_URL="your_postgres_connection_url"

# Watsonx API Key and Instance ID
WATSONX_APIKEY="your_watsonx_api_key"
WATSONX_INSTANCE_ID="your_watsonx_instance_id"
```

**Note:** You can also set these variables directly in your terminal session or in your CI/CD environment.

## 2. Run the Deployment Script

The `deploy_codeengine.sh` script automates the entire deployment process. It will:

1.  Log in to IBM Cloud.
2.  Set up the Container Registry.
3.  Create or select a Code Engine project.
4.  Build and push the backend and frontend Docker images.
5.  Create a secret in Code Engine to store your credentials.
6.  Deploy the backend and frontend applications.

To run the script, execute the following command from the root of the project:

```bash
./scripts/deploy_codeengine.sh
```

The script will output the URLs for the frontend and backend applications upon successful completion.

## 3. Verifying the Deployment

Once the script has finished, you can verify the deployment in the IBM Cloud console:

1.  Navigate to your Code Engine project.
2.  You should see the `rag-modulo-backend` and `rag-modulo-frontend` applications running.
3.  You can view the logs for each application to ensure they started correctly.
4.  Access the frontend URL provided by the script to use the application.

## 4. Cleaning Up

To remove the deployed applications and their associated resources, you can use the IBM Cloud CLI to delete the applications and the secret from your Code Engine project.