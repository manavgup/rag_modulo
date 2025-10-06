# OpenShift Deployment Progress & Future Work

**Related PR:** #261
**Status:** Work in Progress - Paused for Terraform/Ansible Migration
**Date:** 2025-10-04

## Current State - What We've Accomplished

### ✅ Completed Work

#### 1. **Environment Configuration** (.env.example, .env.ci)
Added deployment configuration variables:
- `DEPLOYMENT_ENVIRONMENT` - local|staging|production
- `DEPLOY_TO_OPENSHIFT` - Enable/disable OpenShift deployment
- `DEPLOY_TO_CODE_ENGINE` - Enable/disable Code Engine deployment
- `CLOUD_PROVIDER` - aws|azure|ibm|gcp
- `CONTAINER_REGISTRY` - Configurable registry per environment
- `IBM_CLOUD_API_KEY` - Required for IBM Cloud deployments

#### 2. **GitHub Actions Workflow** (.github/workflows/openshift-staging.yml)
Created automated deployment workflow with:
- Conditional deployment based on `DEPLOY_TO_OPENSHIFT` GitHub variable
- Manual trigger with force deploy option
- Automated image building and pushing to both GHCR and ICR
- Database image distribution (PostgreSQL, etcd, MinIO, Milvus)
- StatefulSet deployment for databases
- Helm chart deployment with environment-specific registry
- OpenShift routes creation for external access

#### 3. **OpenShift Manifests** (deployment/openshift/)
Created Kubernetes manifests for:
- `postgresql.yaml` - PostgreSQL with pgvector extension
- `etcd.yaml` - etcd for Milvus metadata storage
- `minio.yaml` - MinIO S3-compatible object storage
- `milvus.yaml` - Milvus vector database
- `routes.yaml` - OpenShift routes for external access
- `backend-alias.yaml` - Service alias for nginx compatibility

#### 4. **Helm Chart Updates** (deployment/helm/rag-modulo/)
Fixed critical OpenShift compatibility issues:
- **Configurable Registry**: Added `images.registry` variable
  - Default: `ghcr.io/manavgup/rag_modulo`
  - IBM Cloud: `ca.icr.io/rag-modulo`
- **Backend Fixes**:
  - Health check path: `/api/health` (was `/health`)
  - Added `COLLECTIONDB_PASS` environment variable (backend code requirement)
- **Frontend Fixes**:
  - Container port: 8080 (nginx default, was 3000)
  - Added writable volumes for OpenShift security constraints:
    - `/var/cache/nginx`
    - `/var/run`
    - `/tmp`

#### 5. **Deployment Automation** (deployment/scripts/)
Created `deploy-openshift-staging.sh` with:
- Automated namespace cleanup and recreation
- Secrets and ConfigMap creation
- ICR authentication using API key (not short-lived tokens)
- StatefulSet deployment with readiness checks
- Helm chart deployment
- OpenShift routes creation
- Deployment verification and URL output

#### 6. **Documentation** (deployment/README.md)
Added comprehensive CI/CD section:
- How to enable/disable automated deployments
- GitHub secrets and variables setup guide
- Container registry strategy explanation
- OpenShift-specific configuration documentation
- Troubleshooting guide

### 🔧 OpenShift on IBM Cloud Specific Fixes

These fixes were required due to IBM Cloud VPC networking and OpenShift security constraints:

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Image pull failures | VPC has no outbound internet to ghcr.io | Push images to IBM Cloud Container Registry (ICR) |
| Backend health checks fail | Endpoint at `/api/health` not `/health` | Updated Helm template probe paths |
| Backend won't start | Uses `COLLECTIONDB_PASS` not `COLLECTIONDB_PASSWORD` | Added both env vars to Helm template |
| Frontend crashes on startup | Nginx can't write to `/var/cache`, `/var/run`, `/tmp` | Added emptyDir volumes for writable directories |
| Frontend port mismatch | Container runs on 8080, service expected 3000 | Updated Helm to use port 8080 |
| Frontend can't connect to backend | Nginx expects service named `backend` | Created ExternalName service alias |

### 📊 Deployment Architecture

```
OpenShift Namespace: rag-modulo-staging
├── StatefulSets (Databases)
│   ├── postgresql-0          (pgvector, 10Gi storage)
│   ├── milvus-etcd-0          (metadata, 5Gi storage)
│   ├── minio-0                (S3 storage, 10Gi)
│   └── milvus-standalone-0    (vectors, 10Gi storage)
├── Deployments (Applications)
│   ├── rag-modulo-backend     (2 replicas, FastAPI)
│   └── rag-modulo-frontend    (2 replicas, React + nginx)
├── Services
│   ├── postgresql
│   ├── milvus-etcd
│   ├── minio
│   ├── milvus-standalone
│   ├── backend                (alias → rag-modulo-backend)
│   ├── rag-modulo-backend
│   └── rag-modulo-frontend
└── Routes (External Access)
    ├── rag-modulo-backend     (HTTPS, edge termination)
    └── rag-modulo-frontend    (HTTPS, edge termination)
```

### 🧪 Testing Status

**Tested:**
- ✅ Namespace cleanup and recreation
- ✅ Secrets and ConfigMap creation
- ✅ ICR authentication with API key
- ✅ StatefulSet deployment (all 4 databases)
- ✅ Database readiness and connectivity
- ⏸️ **Paused:** Helm chart deployment (timed out, needs completion)
- ⏸️ **Paused:** Full end-to-end verification

**Current State:**
- All database pods running successfully (PostgreSQL, etcd, MinIO, Milvus)
- Application deployment incomplete (Helm timeout)
- Routes not yet tested

---

## 🚀 Future Work - Terraform + Ansible Migration

### Why Migrate?

**Current Limitations:**
- ❌ Tightly coupled to IBM Cloud (`ibmcloud` CLI)
- ❌ Manual infrastructure provisioning
- ❌ No infrastructure state management
- ❌ Difficult to replicate across clouds
- ❌ No secrets management best practices

**Benefits of Terraform + Ansible:**
- ✅ **Cloud-Agnostic**: Deploy to AWS, Azure, GCP, IBM, on-prem
- ✅ **Infrastructure as Code**: Version-controlled, reviewable
- ✅ **State Management**: Track infrastructure changes
- ✅ **Idempotent**: Safe to run multiple times
- ✅ **Secrets Management**: Ansible Vault, cloud KMS integration
- ✅ **Rollback**: Easy infrastructure rollback with Terraform
- ✅ **Modular**: Reusable modules across environments

### Proposed Architecture

```
rag_modulo/
├── terraform/
│   ├── modules/
│   │   ├── kubernetes-cluster/     # Cloud-agnostic K8s provisioning
│   │   │   ├── aws/               # AWS EKS implementation
│   │   │   ├── azure/             # Azure AKS implementation
│   │   │   ├── gcp/               # GCP GKE implementation
│   │   │   └── ibm/               # IBM OpenShift implementation
│   │   ├── container-registry/    # Registry provisioning
│   │   │   ├── aws/               # ECR
│   │   │   ├── azure/             # ACR
│   │   │   ├── gcp/               # GCR
│   │   │   └── ibm/               # ICR
│   │   ├── networking/            # VPC, subnets, security groups
│   │   └── storage/               # Block storage, file storage
│   ├── environments/
│   │   ├── staging/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── terraform.tfvars
│   │   └── production/
│   └── backend.tf                  # Terraform state backend
│
├── ansible/
│   ├── playbooks/
│   │   ├── deploy-all.yml
│   │   ├── deploy-databases.yml
│   │   ├── deploy-application.yml
│   │   └── rollback.yml
│   ├── roles/
│   │   ├── postgresql/
│   │   │   ├── tasks/
│   │   │   ├── templates/
│   │   │   └── defaults/
│   │   ├── milvus/
│   │   ├── backend/
│   │   └── frontend/
│   ├── inventory/
│   │   ├── aws-staging.yml
│   │   ├── azure-staging.yml
│   │   ├── gcp-staging.yml
│   │   ├── ibm-staging.yml
│   │   └── production.yml
│   └── group_vars/
│       ├── all.yml
│       ├── staging.yml
│       └── production.yml
│
└── deployment/
    ├── helm/                       # Keep Helm charts (Ansible uses them)
    └── scripts/                    # Keep as fallback/debugging
```

### Terraform Example (Cloud-Agnostic)

```hcl
# terraform/environments/staging/main.tf

variable "cloud_provider" {
  description = "Cloud provider: aws, azure, gcp, ibm"
  type        = string
}

variable "environment" {
  description = "Environment: staging, production"
  type        = string
  default     = "staging"
}

module "kubernetes_cluster" {
  source = "../../modules/kubernetes-cluster/${var.cloud_provider}"

  cluster_name = "rag-modulo-${var.environment}"
  node_count   = 3
  node_size    = "medium"  # Abstracted across clouds
  region       = var.region

  tags = {
    Project     = "rag-modulo"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

module "container_registry" {
  source = "../../modules/container-registry/${var.cloud_provider}"

  registry_name = "rag-modulo"
  environment   = var.environment
}

output "cluster_endpoint" {
  value = module.kubernetes_cluster.endpoint
}

output "registry_url" {
  value = module.container_registry.url
}
```

### Ansible Example (Cloud-Agnostic)

```yaml
# ansible/playbooks/deploy-all.yml

- name: Deploy RAG Modulo to Kubernetes
  hosts: kubernetes
  vars:
    namespace: "rag-modulo-{{ environment }}"
    registry_url: "{{ cloud_registry_url }}"

  roles:
    - role: postgresql
      vars:
        storage_class: "{{ cloud_storage_class }}"
        storage_size: 10Gi

    - role: milvus
      vars:
        storage_class: "{{ cloud_storage_class }}"
        etcd_enabled: true
        minio_enabled: true

    - role: backend
      vars:
        registry: "{{ registry_url }}"
        image_tag: "{{ backend_version | default('latest') }}"
        replicas: 2

    - role: frontend
      vars:
        registry: "{{ registry_url }}"
        image_tag: "{{ frontend_version | default('latest') }}"
        replicas: 2
```

### Deployment Workflow

```bash
# 1. Provision infrastructure with Terraform
cd terraform/environments/staging
terraform init
terraform plan -var="cloud_provider=aws"
terraform apply -var="cloud_provider=aws"

# 2. Deploy application with Ansible
cd ansible
ansible-playbook playbooks/deploy-all.yml \
  -i inventory/aws-staging.yml \
  -e environment=staging

# 3. Verify deployment
ansible-playbook playbooks/verify-deployment.yml
```

### CI/CD Integration

```yaml
# .github/workflows/deploy-terraform-ansible.yml

name: Deploy with Terraform + Ansible

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      cloud_provider:
        description: 'Cloud provider'
        required: true
        type: choice
        options: [aws, azure, gcp, ibm]
      environment:
        description: 'Environment'
        required: true
        type: choice
        options: [staging, production]

jobs:
  terraform:
    runs-on: ubuntu-latest
    outputs:
      cluster_endpoint: ${{ steps.terraform.outputs.cluster_endpoint }}
      registry_url: ${{ steps.terraform.outputs.registry_url }}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2

      - name: Terraform Apply
        id: terraform
        run: |
          cd terraform/environments/${{ inputs.environment }}
          terraform init
          terraform apply -auto-approve \
            -var="cloud_provider=${{ inputs.cloud_provider }}"

  deploy:
    needs: [terraform]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Ansible
        run: pip install ansible

      - name: Deploy with Ansible
        run: |
          cd ansible
          ansible-playbook playbooks/deploy-all.yml \
            -i inventory/${{ inputs.cloud_provider }}-${{ inputs.environment }}.yml \
            -e registry_url=${{ needs.terraform.outputs.registry_url }}
```

### Migration Plan

**Phase 1: Terraform Infrastructure** (Week 1)
- [ ] Create Terraform modules for AWS
- [ ] Create Terraform modules for Azure
- [ ] Create Terraform modules for GCP
- [ ] Create Terraform modules for IBM Cloud
- [ ] Setup Terraform state backend
- [ ] Test infrastructure provisioning on each cloud

**Phase 2: Ansible Application Deployment** (Week 2)
- [ ] Create Ansible roles for databases
- [ ] Create Ansible roles for applications
- [ ] Create inventory files for each cloud
- [ ] Integrate with existing Helm charts
- [ ] Setup Ansible Vault for secrets
- [ ] Test deployments on each cloud

**Phase 3: CI/CD Integration** (Week 3)
- [ ] Update GitHub Actions workflows
- [ ] Add cloud provider selection
- [ ] Add automated testing
- [ ] Documentation updates
- [ ] Migration guide for existing deployments

**Phase 4: Production Validation** (Week 4)
- [ ] Deploy to staging on all clouds
- [ ] Performance testing
- [ ] Disaster recovery testing
- [ ] Cost optimization
- [ ] Go-live checklist

### Benefits Summary

| Aspect | Current (Bash + Helm) | Future (Terraform + Ansible) |
|--------|----------------------|------------------------------|
| **Cloud Support** | IBM Cloud only | AWS, Azure, GCP, IBM, on-prem |
| **Infrastructure** | Manual CLI commands | Infrastructure as Code |
| **State** | None | Terraform state tracking |
| **Repeatability** | Scripts (fragile) | Idempotent playbooks |
| **Secrets** | Manual kubectl | Ansible Vault, cloud KMS |
| **Rollback** | Manual | `terraform destroy && apply` |
| **Testing** | Manual verification | Automated with Molecule |
| **Multi-cloud** | Not possible | Day 1 support |
| **Learning Curve** | Low | Medium-High |
| **Production Ready** | No | Yes |

---

## 📝 Next Steps

1. **Complete Current Deployment** (Optional)
   - Fix Helm timeout issue
   - Verify application functionality
   - Test routes and external access

2. **Start Terraform Migration** (Recommended)
   - Create GitHub issue for Terraform + Ansible migration
   - Design Terraform module structure
   - Prototype on AWS EKS first (most common)
   - Expand to other clouds

3. **Documentation**
   - Update deployment docs with Terraform approach
   - Create architecture decision records (ADRs)
   - Add runbooks for each cloud provider

---

## 🔗 Related Issues & PRs

- PR #261: CI/CD workflow fixes (current work)
- Issue #222: Simplified pipeline resolution
- Issue #136: Chain of Thought reasoning

---

## 📚 References

- [Terraform Kubernetes Provider](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs)
- [Ansible Kubernetes Collection](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/index.html)
- [Multi-Cloud Kubernetes Best Practices](https://www.cncf.io/blog/2021/04/12/multi-cloud-kubernetes/)
- [Infrastructure as Code Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
