# SPIRE Configuration for RAG Modulo

This directory contains configuration files for deploying SPIRE (SPIFFE Runtime Environment)
to manage workload identities for AI agents in RAG Modulo.

## Overview

SPIRE provides cryptographic identity to workloads (including AI agents) without requiring
secrets to be distributed or embedded in applications. Each agent receives a SPIFFE ID
and can obtain short-lived JWT-SVIDs (JSON Web Token SPIFFE Verifiable Identity Documents)
for authentication.

## Architecture Reference

See the full architecture documentation at:
`docs/architecture/spire-integration-architecture.md`

## Files

- `server.conf` - SPIRE Server configuration
- `agent.conf` - SPIRE Agent configuration
- `docker-compose.spire.yml` - Docker Compose for local development

## Quick Start (Development)

### Prerequisites

- Docker and Docker Compose
- Network access to pull SPIRE images from `ghcr.io/spiffe`

### Start SPIRE

```bash
# Start SPIRE services
docker compose -f docker-compose.spire.yml up -d

# Check server health
curl http://localhost:8080/live

# Check agent health
curl http://localhost:8089/live

# View server logs
docker logs rag-modulo-spire-server
```

### Create Registration Entries

Registration entries tell SPIRE which workloads can obtain which identities.

```bash
# Connect to SPIRE server container
docker exec -it rag-modulo-spire-server /bin/sh

# Create an entry for a search-enricher agent
spire-server entry create \
    -socketPath /tmp/spire-server/private/api.sock \
    -spiffeID spiffe://rag-modulo.example.com/agent/search-enricher/agent-001 \
    -parentID spiffe://rag-modulo.example.com/spire/agent/unix \
    -selector docker:label:agent-type:search-enricher \
    -selector docker:label:agent-id:agent-001

# List all entries
spire-server entry show -socketPath /tmp/spire-server/private/api.sock
```

### Fetch SVIDs from Workloads

Once registration entries are created, workloads can fetch SVIDs:

```python
from spiffe import JwtSource

# Create JWT source connected to SPIRE Agent
with JwtSource() as source:
    # Fetch JWT-SVID for authentication to backend-api
    svid = source.fetch_svid(audience={"backend-api"})

    # Use the token in Authorization header
    headers = {"Authorization": f"Bearer {svid.token}"}
    # Make authenticated request...
```

## Kubernetes Deployment

For Kubernetes, use the SPIRE Helm charts or Kubernetes manifests:

### Using Helm

```bash
helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/
helm install spire spiffe/spire \
    --namespace spire \
    --create-namespace \
    --values values-kubernetes.yaml
```

### Kubernetes Registration Entries

```bash
# Create entry for backend-api
kubectl exec -n spire spire-server-0 -- \
    spire-server entry create \
    -spiffeID spiffe://rag-modulo.example.com/workload/backend-api \
    -parentID spiffe://rag-modulo.example.com/spire/agent/k8s/node \
    -selector k8s:ns:rag-modulo \
    -selector k8s:sa:backend-api

# Create entry for search-enricher agents
kubectl exec -n spire spire-server-0 -- \
    spire-server entry create \
    -spiffeID spiffe://rag-modulo.example.com/agent/search-enricher/default \
    -parentID spiffe://rag-modulo.example.com/spire/agent/k8s/node \
    -selector k8s:ns:rag-modulo \
    -selector k8s:sa:search-enricher-agent \
    -selector k8s:pod-label:agent-type:search-enricher
```

## Trust Domain

The default trust domain is `rag-modulo.example.com`. For production deployments,
change this to match your organization's domain (e.g., `rag-modulo.yourcompany.com`).

Update the following files:

- `server.conf` - `trust_domain` setting
- `agent.conf` - `trust_domain` setting
- Registration entries - SPIFFE ID prefixes

## Monitoring

SPIRE exposes Prometheus metrics:

- Server: <http://localhost:9988/metrics>
- Agent: <http://localhost:9989/metrics>

Key metrics to monitor:

- `spire_server_ca_manager_x509_ca_rotate_total` - CA rotations
- `spire_server_svid_issued_total` - SVIDs issued
- `spire_agent_svid_rotations_total` - Agent SVID rotations
- `workload_api_connection_total` - Workload API connections

## Security Considerations

1. **Production Trust Bundle**: Use proper CA certificates in production
2. **Database Security**: Secure the SPIRE database with proper credentials
3. **Network Security**: Limit access to SPIRE Server API
4. **Selector Security**: Use specific selectors to prevent workload impersonation
5. **SVID TTL**: Configure appropriate TTLs for different workload types

## Troubleshooting

### Server won't start

Check database connectivity:

```bash
docker logs rag-modulo-spire-db
docker exec rag-modulo-spire-db pg_isready -U spire
```

### Agent won't connect

Check server address and port:

```bash
docker exec rag-modulo-spire-agent cat /etc/spire/agent/agent.conf | grep server_
```

### Workload can't fetch SVID

1. Verify registration entry exists
2. Check workload selectors match
3. Check agent logs for attestation errors:

```bash
docker logs rag-modulo-spire-agent 2>&1 | grep -i attest
```
