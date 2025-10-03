# ADR-004: Podcast Audio Storage Strategy

- **Status:** Proposed
- **Date:** 2025-10-02
- **Deciders:** Engineering Team, Infrastructure

## Context

Generated podcast audio files need persistent storage with the following requirements:

### Podcast Audio Characteristics
- **File sizes:** 5-60 MB per podcast (MP3 format)
  - 5-min podcast: ~5 MB
  - 15-min podcast: ~15 MB
  - 30-min podcast: ~30 MB
  - 60-min podcast: ~60 MB
- **Formats:** MP3, WAV, OGG, FLAC (configurable)
- **Lifespan:** Indefinite (user content)
- **Access pattern:** Read-heavy (stream/download)
- **Growth:** 100-1000+ podcasts/month at scale

### Key Requirements

1. **Reliability:** No data loss
2. **Scalability:** Handle TB+ of audio files
3. **Performance:** Fast upload (generation) and download (playback)
4. **Cost-Effective:** Reasonable storage costs at scale
5. **Access Control:** User-specific permissions
6. **URL Generation:** Signed URLs for secure access
7. **Streaming Support:** HTTP range requests for audio playback
8. **Backup/DR:** Data redundancy and disaster recovery

## Decision

**We will use MinIO (S3-compatible object storage) as the primary storage solution, leveraging existing infrastructure.**

MinIO is already deployed in the RAG Modulo stack for document storage, making it the natural choice for podcast audio files.

## Consequences

### ✨ Positive Consequences

1. **Leverage Existing Infrastructure**
   - MinIO already running in docker-compose stack
   - No additional infrastructure needed
   - Familiar to team
   - Consistent storage strategy across system

2. **S3-Compatible API**
   - Industry-standard API
   - Easy migration to AWS S3/GCS if needed
   - Rich ecosystem of tools and libraries
   - Well-documented

3. **Cost-Effective**
   - Self-hosted: Only storage media costs
   - No per-request pricing
   - Predictable costs at scale
   - Example: 1TB storage ≈ $0.02/GB/month = $20/month on commodity hardware

4. **High Performance**
   - Direct object access
   - Streaming support (HTTP range requests)
   - CDN-friendly (can add CloudFlare/CloudFront later)
   - Multi-part upload for large files

5. **Access Control**
   - Bucket policies for fine-grained permissions
   - Presigned URLs for temporary access
   - User-specific access keys
   - Audit logging

6. **Scalability**
   - Horizontal scaling (add more MinIO nodes)
   - Handles millions of objects
   - Erasure coding for redundancy
   - Multi-region support if needed

7. **Developer Experience**
   - `boto3` Python client (same as AWS S3)
   - Simple API (PUT, GET, DELETE)
   - Local development matches production
   - Easy testing

### ⚠️ Potential Challenges

1. **Operational Overhead**
   - Requires infrastructure management (backups, monitoring)
   - **Mitigation:** Already managing MinIO for documents; same playbooks apply

2. **Single Point of Failure**
   - Self-hosted solution needs HA setup
   - **Mitigation:** MinIO distributed mode with erasure coding (Phase 2)

3. **Bandwidth Costs**
   - Audio streaming consumes bandwidth
   - **Mitigation:** Add CDN (CloudFlare/CloudFront) when needed; implement download limits

4. **Storage Growth**
   - Unlimited retention can lead to high storage costs
   - **Mitigation:** Implement lifecycle policies (archive old podcasts to cheaper storage tier)

## Alternatives Considered

### Option 1: AWS S3

| Aspect | Details |
|--------|---------|
| **Pros** | • Fully managed (no ops overhead)<br>• Infinite scalability<br>• 99.999999999% durability<br>• Global edge locations<br>• Rich feature set (lifecycle, versioning, etc.) |
| **Cons** | • Monthly costs: $0.023/GB storage + $0.09/GB egress<br>• Example: 1TB storage + 500GB/mo downloads = $68/month<br>• Vendor lock-in<br>• API call costs ($0.005 per 1000 PUT) |
| **Total Cost (1TB storage, 500GB egress/mo)** | ~$68/month |
| **Why Not** | ⚠️ Higher costs than self-hosted MinIO. Better for multi-region/global deployments. Good migration target if traffic scales significantly. |

### Option 2: Google Cloud Storage

| Aspect | Details |
|--------|---------|
| **Pros** | • Similar to AWS S3<br>• Slightly cheaper egress in some regions<br>• Strong ML integration |
| **Cons** | • Similar pricing to AWS<br>• $0.020/GB storage + $0.12/GB egress<br>• Vendor lock-in |
| **Total Cost (1TB storage, 500GB egress/mo)** | ~$80/month |
| **Why Not** | ⚠️ Similar to AWS S3. No compelling advantage for our use case. |

### Option 3: Local Filesystem

| Aspect | Details |
|--------|---------|
| **Pros** | • Simplest implementation<br>• No external dependencies<br>• Zero storage API costs<br>• Fast access |
| **Cons** | • Not scalable (single server limit)<br>• No built-in redundancy<br>• Difficult backup/restore<br>• Hard to implement CDN<br>• Server disk space limits growth<br>• No presigned URLs (security risk) |
| **Why Not** | ⛔ Not production-ready. Fine for development/testing only. Doesn't scale beyond single server. |

### Option 4: Azure Blob Storage

| Aspect | Details |
|--------|---------|
| **Pros** | • Microsoft ecosystem integration<br>• Competitive pricing |
| **Cons** | • Similar pricing to AWS/GCS<br>• Less familiar to team<br>• Vendor lock-in |
| **Why Not** | ⚠️ No advantage over AWS S3. Not currently using Azure ecosystem. |

### Option 5: PostgreSQL Large Objects (LO)

| Aspect | Details |
|--------|---------|
| **Pros** | • Already using PostgreSQL<br>• Transactional consistency with metadata<br>• Simpler architecture (fewer systems) |
| **Cons** | • PostgreSQL not optimized for binary storage<br>• Bloats database size<br>• Difficult to stream efficiently<br>• Vacuum overhead<br>• Backup/restore complexity<br>• Max file size limits |
| **Why Not** | ⛔ Anti-pattern. Databases should store metadata, not large binaries. Performance issues at scale. |

### Option 6: Cloudflare R2

| Aspect | Details |
|--------|---------|
| **Pros** | • S3-compatible API<br>• Zero egress costs 🎉<br>• $0.015/GB storage<br>• Good for high-bandwidth use cases |
| **Cons** | • Newer service (less mature)<br>• Requires Cloudflare account<br>• $0.015/GB storage (higher than S3 for storage-only) |
| **Total Cost (1TB storage, 500GB egress/mo)** | ~$15/month (no egress!) |
| **Why Not** | ✅ **Actually viable!** Strong candidate for future migration if egress costs become significant. Zero egress is compelling for podcast streaming. |

## Comparison Matrix

| Factor | MinIO (✅ Chosen) | AWS S3 | Local Filesystem | Cloudflare R2 |
|--------|------------------|---------|------------------|---------------|
| **Storage Cost (1TB)** | ~$20/mo ⭐⭐⭐⭐⭐ | ~$23/mo ⭐⭐⭐⭐ | Disk cost ⭐⭐⭐⭐⭐ | ~$15/mo ⭐⭐⭐⭐⭐ |
| **Egress Cost (500GB/mo)** | $0 ⭐⭐⭐⭐⭐ | ~$45/mo ⭐⭐ | $0 ⭐⭐⭐⭐⭐ | $0 ⭐⭐⭐⭐⭐ |
| **Total Monthly Cost** | ~$20 💰 | ~$68 💰💰💰 | Disk only 💰 | ~$15 💰 |
| **Scalability** | High ⭐⭐⭐⭐ | Infinite ⭐⭐⭐⭐⭐ | Low ⭐⭐ | High ⭐⭐⭐⭐⭐ |
| **Reliability** | High ⭐⭐⭐⭐ | Extreme ⭐⭐⭐⭐⭐ | Medium ⭐⭐⭐ | High ⭐⭐⭐⭐ |
| **Ops Overhead** | Medium ⭐⭐⭐ | None ⭐⭐⭐⭐⭐ | Low ⭐⭐⭐⭐ | None ⭐⭐⭐⭐⭐ |
| **Already Deployed** | ✅ Yes | ❌ No | ✅ Yes | ❌ No |
| **S3 Compatibility** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **Migration Path** | Easy to S3/R2 | N/A | Hard | N/A |

**Decision:** MinIO for MVP, migrate to Cloudflare R2 if egress costs become significant (>$100/month).

## Implementation Architecture

### Storage Structure

```
MinIO Bucket: rag-modulo-podcasts

Folder Structure:
/podcasts/
  /{user_id}/
    /{podcast_id}/
      audio.mp3          # Main audio file
      transcript.txt     # Podcast script
      metadata.json      # Generation metadata

Example:
/podcasts/550e8400-e29b-41d4-a716-446655440000/abc123-def456/audio.mp3
```

### Python Implementation

```python
# rag_solution/storage/audio_storage.py

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import timedelta

class AudioStorageService:
    """Service for storing and retrieving podcast audio files."""

    def __init__(self, settings: Settings):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version='s3v4'),
        )
        self.bucket_name = settings.podcast_bucket_name

    async def store_audio(
        self,
        podcast_id: UUID4,
        user_id: UUID4,
        audio_bytes: bytes,
        audio_format: AudioFormat,
    ) -> str:
        """Store podcast audio and return access URL."""

        object_key = f"podcasts/{user_id}/{podcast_id}/audio.{audio_format.value}"

        try:
            # Upload with metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=audio_bytes,
                ContentType=f"audio/{audio_format.value}",
                Metadata={
                    'podcast_id': str(podcast_id),
                    'user_id': str(user_id),
                    'created_at': datetime.utcnow().isoformat(),
                },
                # Enable streaming
                ContentDisposition='inline',
            )

            # Generate presigned URL (valid for 7 days)
            audio_url = self._generate_presigned_url(object_key, expires_in=7*24*3600)

            return audio_url

        except ClientError as e:
            logger.exception("Failed to store audio: %s", e)
            raise AudioStorageError(f"Audio storage failed: {e}")

    async def store_transcript(
        self,
        podcast_id: UUID4,
        user_id: UUID4,
        transcript: str,
    ) -> str:
        """Store podcast transcript."""

        object_key = f"podcasts/{user_id}/{podcast_id}/transcript.txt"

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=object_key,
            Body=transcript.encode('utf-8'),
            ContentType='text/plain',
        )

        return object_key

    def _generate_presigned_url(self, object_key: str, expires_in: int) -> str:
        """Generate presigned URL for secure audio access."""

        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': object_key,
            },
            ExpiresIn=expires_in,
        )

        return url

    async def delete_podcast(self, podcast_id: UUID4, user_id: UUID4) -> None:
        """Delete all podcast files."""

        prefix = f"podcasts/{user_id}/{podcast_id}/"

        # List all objects with prefix
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix,
        )

        if 'Contents' not in response:
            return  # No files to delete

        # Delete all objects
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

        self.s3_client.delete_objects(
            Bucket=self.bucket_name,
            Delete={'Objects': objects_to_delete},
        )

    async def get_audio_size(self, object_key: str) -> int:
        """Get audio file size in bytes."""

        response = self.s3_client.head_object(
            Bucket=self.bucket_name,
            Key=object_key,
        )

        return response['ContentLength']
```

### Configuration

```python
# core/config.py

class Settings(BaseSettings):
    # MinIO Configuration
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_region: str = "us-east-1"

    # Podcast storage
    podcast_bucket_name: str = "rag-modulo-podcasts"
    podcast_url_expiry_days: int = 7  # Presigned URL validity

    # Storage lifecycle
    podcast_archive_after_days: int = 365  # Archive old podcasts
    podcast_delete_after_days: int = 730   # Delete after 2 years
```

### Docker Compose Setup

```yaml
services:
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # Web Console
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # Bucket creation on startup
  minio_init:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      /usr/bin/mc alias set myminio http://minio:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY};
      /usr/bin/mc mb myminio/rag-modulo-podcasts --ignore-existing;
      /usr/bin/mc anonymous set download myminio/rag-modulo-podcasts;
      exit 0;
      "

volumes:
  minio_data:
```

## Storage Lifecycle Management

### Lifecycle Policies

```python
# Implement lifecycle policies for cost optimization

# Phase 1: Keep all podcasts indefinitely
# - No automatic deletion
# - User can manually delete

# Phase 2: Tiered storage (if costs become issue)
# - Hot tier (0-90 days): MinIO SSD storage
# - Warm tier (91-365 days): MinIO HDD storage
# - Cold tier (366+ days): Glacier/Archive storage

lifecycle_policy = {
    'Rules': [
        {
            'Id': 'ArchiveOldPodcasts',
            'Status': 'Enabled',
            'Prefix': 'podcasts/',
            'Transitions': [
                {
                    'Days': 365,
                    'StorageClass': 'GLACIER',
                },
            ],
        },
    ],
}
```

## Security Considerations

1. **Access Control:**
   - User can only access their own podcasts
   - Presigned URLs expire after 7 days
   - Generate new URLs on each access request

2. **Encryption:**
   - Enable MinIO encryption at rest (AES-256)
   - TLS for data in transit

3. **Backup:**
   - Daily backups of MinIO bucket to separate storage
   - Retention: 30 days

4. **Monitoring:**
   - Storage usage alerts (80%, 90% thresholds)
   - Failed upload/download alerts
   - Unusual access pattern detection

## Cost Projection

### Year 1 Estimates

| Metric | Estimate |
|--------|----------|
| **Podcasts/month** | 500 |
| **Avg podcast size** | 15 MB |
| **Monthly storage growth** | 7.5 GB |
| **Total Year 1 storage** | 90 GB |
| **MinIO cost** | ~$2/month |
| **Bandwidth** | Included (self-hosted) |
| **Total Year 1 cost** | ~$24 |

### Year 2 (Growth)

| Metric | Estimate |
|--------|----------|
| **Podcasts/month** | 2000 |
| **Monthly growth** | 30 GB |
| **Total storage** | 450 GB |
| **MinIO cost** | ~$10/month |
| **Total Year 2 cost** | ~$120 |

### Scale (3-5 years)

| Metric | Estimate |
|--------|----------|
| **Total storage** | 2-5 TB |
| **MinIO cost** | ~$50-100/month |
| **Egress (if 10% downloaded monthly)** | 200-500 GB |
| **Recommended migration** | Cloudflare R2 (zero egress costs) |

## Migration Strategy

### When to migrate to Cloudflare R2:

1. **Storage > 5TB** - Better pricing at scale
2. **Egress > 1TB/month** - Zero egress costs make R2 compelling
3. **Global users** - R2 edge network improves latency

### Migration Process:

```bash
# MinIO to R2 migration (S3 compatible)
rclone copy minio:rag-modulo-podcasts r2:rag-modulo-podcasts --progress

# Update application config
MINIO_ENDPOINT=https://your-account.r2.cloudflarestorage.com
```

## Status

**Proposed** - Recommended approach:
- **MVP:** Use existing MinIO infrastructure
- **Future:** Migrate to Cloudflare R2 if egress costs exceed $100/month

## References

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Boto3 S3 Client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [Cloudflare R2](https://developers.cloudflare.com/r2/)
