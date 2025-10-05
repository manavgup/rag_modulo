# Deploying to IBM Cloud Code Engine

This document provides instructions on how to deploy the RAG Modulo application to IBM Cloud Code Engine, a serverless platform that runs containers.

## Prerequisites

Before you begin, you will need:

*   An [IBM Cloud account](https://cloud.ibm.com/registration).
*   The [IBM Cloud CLI](https://cloud.ibm.com/docs/cli/cli) installed on your local machine.

## GitHub Secrets Setup

To deploy to IBM Cloud Code Engine, you need to configure the following secret in your GitHub repository:

*   `IBM_CLOUD_API_KEY`: Your IBM Cloud API key. You can create one [here](https://cloud.ibm.com/iam/apikeys).

To add a secret to your GitHub repository, go to **Settings > Secrets and variables > Actions** and click **New repository secret**.

## Deployment Steps

1.  Go to the **Actions** tab in your GitHub repository.
2.  Under **Workflows**, select **Deploy to IBM Cloud Code Engine**.
3.  Click **Run workflow**.
4.  Fill in the required input parameters:
    *   **IBM Cloud region**: The IBM Cloud region where you want to deploy the application (e.g., `us-south`).
    *   **IBM Cloud resource group**: The IBM Cloud resource group to use (e.g., `Default`).
    *   **Code Engine project name**: The name of the Code Engine project to create or use.
    *   **Code Engine app name**: The name of the application to create in Code Engine.
    *   **Docker image name**: The name of the Docker image to build and push. This should be in the format `us.icr.io/<namespace>/<image>`, where `<namespace>` is your container registry namespace and `<image>` is the name of the image.
5.  Click **Run workflow**.

## Vector Database

Please note that the default vector database for this deployment is Elasticsearch. If you want to use a different vector database, you will need to modify the `VECTOR_DB` environment variable in the `backend/core/config.py` file.

### Elasticsearch Embedding Dimensions

The embedding dimension for Elasticsearch is now configurable via the `EMBEDDING_DIM` setting. However, there is no automatic migration path for existing Elasticsearch indices. If you have an existing index and you change the embedding dimension, you will need to re-index your data.
