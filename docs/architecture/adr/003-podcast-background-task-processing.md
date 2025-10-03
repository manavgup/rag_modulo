# ADR-003: Podcast Background Task Processing

- **Status:** Proposed
- **Date:** 2025-10-02
- **Deciders:** Engineering Team, Infrastructure

## Context

Podcast generation (Issue #240) is a long-running operation:
- Document retrieval via RAG: 2-10 seconds
- LLM script generation: 10-30 seconds
- Audio generation (TTS): 30-60 seconds for 15-minute podcast
- **Total: 1-2 minutes for typical podcast**

We cannot block HTTP requests for this duration. We need to:
1. Return immediately with podcast_id and QUEUED status
2. Process generation asynchronously in background
3. Allow users to check status/retrieve results when complete
4. Handle failures gracefully with retries
5. Support concurrent podcast generations

## Decision

**We will implement a hybrid approach using FastAPI BackgroundTasks for MVP, with a migration path to Celery + Redis for production scale.**

**Phase 1 (MVP):** FastAPI BackgroundTasks
**Phase 2 (Production):** Celery + Redis task queue

This staged approach balances simplicity for initial launch with scalability for growth.

## Consequences

### Phase 1: FastAPI BackgroundTasks

#### ✨ Positive Consequences

1. **Zero Additional Infrastructure**
   - No message broker required (Redis/RabbitMQ)
   - No separate worker processes
   - Works with existing FastAPI deployment

2. **Simple Implementation**
   - Built-in to FastAPI framework
   - Minimal code required
   - Easy to debug and test

3. **Fast Time to Market**
   - No new infrastructure provisioning
   - No operational complexity
   - Can ship MVP quickly

4. **Good for Low-Moderate Volume**
   - Handles dozens of concurrent podcasts
   - Suitable for beta/early adoption phase

#### ⚠️ Limitations (Why We Need Phase 2)

1. **Tied to Web Process**
   - Background tasks run in same process as web server
   - If server restarts, in-progress tasks are lost
   - No task persistence across deployments

2. **Limited Scalability**
   - Can't scale background workers independently of web servers
   - Resource contention between web requests and background tasks
   - No distributed task execution

3. **No Retry Mechanism**
   - Failed tasks don't automatically retry
   - Must implement custom retry logic
   - No built-in dead letter queue

4. **No Task Monitoring**
   - Limited visibility into task status
   - No dashboard for task management
   - Harder to debug failures

5. **No Task Prioritization**
   - FIFO execution only
   - Can't prioritize urgent podcasts
   - No resource allocation control

### Phase 2: Celery + Redis

#### ✨ Positive Consequences

1. **Production-Grade Reliability**
   - Tasks persist in Redis
   - Survives worker/server restarts
   - Automatic retries with exponential backoff

2. **Horizontal Scalability**
   - Scale workers independently (10, 50, 100+)
   - Add workers during peak times
   - Remove workers during low traffic

3. **Advanced Task Management**
   - Task prioritization (premium users first)
   - Task scheduling (generate podcasts at off-peak hours)
   - Task chaining (generate → upload → notify)
   - Rate limiting per user

4. **Monitoring & Observability**
   - Flower dashboard for task monitoring
   - Task success/failure metrics
   - Execution time tracking
   - Dead letter queue for failed tasks

5. **Resource Isolation**
   - CPU-intensive tasks don't affect web servers
   - Separate resource pools for different task types
   - Better fault isolation

#### ⚠️ Challenges

1. **Operational Complexity**
   - Redis infrastructure to manage
   - Celery worker processes to monitor
   - More moving parts in deployment

2. **Development Overhead**
   - Additional dependencies
   - More complex local development setup
   - Steeper learning curve

3. **Cost**
   - Redis hosting (~$10-50/month for small instance)
   - Additional worker compute resources

## Alternatives Considered

| Option | Pros | Cons | Why Not? |
|--------|------|------|----------|
| **Celery + RabbitMQ** | More features than Redis; better for complex routing | RabbitMQ more complex than Redis; overkill for podcast use case | Redis simpler and sufficient for our needs |
| **Dramatiq + Redis** | Simpler than Celery; modern async support | Smaller ecosystem; less tooling; fewer integrations | Celery's maturity and Flower monitoring too valuable |
| **AWS SQS + Lambda** | Fully managed; auto-scaling; no infrastructure | Vendor lock-in; cold starts; more expensive at scale | Want to maintain cloud portability |
| **Kubernetes Jobs** | Native to K8s; good isolation | Overhead of K8s if not already using it; job startup latency | Not using K8s currently; too heavy for this |
| **Async TaskGroup (asyncio)** | Built-in Python; no dependencies | No persistence; no distribution; same limitations as BackgroundTasks | Doesn't solve core problems |
| **ARQ (Redis-based)** | Lightweight; async-native; simpler than Celery | Smaller community; less mature; fewer integrations | Good alternative but Celery more proven |

## Implementation Architecture

### Phase 1: FastAPI BackgroundTasks (MVP)

```python
# rag_solution/services/podcast_service.py

from fastapi import BackgroundTasks

class PodcastService:
    async def generate_podcast(
        self,
        podcast_input: PodcastGenerationInput,
        background_tasks: BackgroundTasks,  # Injected by FastAPI
    ) -> PodcastGenerationOutput:
        """Generate podcast - returns immediately with QUEUED status."""

        # 1. Validate inputs
        await self._validate_podcast_request(podcast_input)

        # 2. Create database record
        podcast = await self._create_podcast_record(
            podcast_input,
            status=PodcastStatus.QUEUED,
        )

        # 3. Schedule background processing
        background_tasks.add_task(
            self._process_podcast_generation,
            podcast_id=podcast.podcast_id,
        )

        # 4. Return immediately
        return podcast

    async def _process_podcast_generation(self, podcast_id: UUID4):
        """Background task for podcast generation with progress tracking."""
        try:
            # 1. Retrieve content via RAG
            await self._update_progress(
                podcast_id,
                status=PodcastStatus.GENERATING,
                progress_percentage=10,
                current_step="retrieving_content"
            )
            documents = await self._retrieve_documents(collection_id)

            # 2. Generate Q&A dialogue script
            await self._update_progress(
                podcast_id,
                progress_percentage=30,
                current_step="generating_script"
            )
            script_text = await self._generate_script(documents, duration)

            # 3. Parse script into turns (HOST/EXPERT)
            await self._update_progress(
                podcast_id,
                progress_percentage=40,
                current_step="parsing_turns"
            )
            podcast_script = await self._parse_script(script_text)

            # 4. Generate audio for each turn with multi-voice
            await self._update_progress(
                podcast_id,
                progress_percentage=50,
                current_step="generating_audio",
                step_details={
                    "total_turns": len(podcast_script.turns),
                    "completed_turns": 0,
                }
            )

            audio_segments = []
            for idx, turn in enumerate(podcast_script.turns):
                # Generate audio for this turn
                segment = await self._generate_turn_audio(turn)
                audio_segments.append(segment)

                # Update progress per turn
                await self._update_progress(
                    podcast_id,
                    progress_percentage=50 + int(40 * (idx + 1) / len(podcast_script.turns)),
                    current_step="generating_audio",
                    step_details={
                        "total_turns": len(podcast_script.turns),
                        "completed_turns": idx + 1,
                        "current_speaker": turn.speaker.value,
                    }
                )

            # 5. Combine audio segments
            await self._update_progress(
                podcast_id,
                progress_percentage=90,
                current_step="combining_audio"
            )
            audio_bytes = await self._combine_audio_segments(audio_segments)

            # 6. Store audio
            await self._update_progress(
                podcast_id,
                progress_percentage=95,
                current_step="storing_audio"
            )
            audio_url = await self._store_audio(podcast_id, audio_bytes)

            # 7. Mark complete
            await self._mark_completed(
                podcast_id,
                audio_url=audio_url,
                transcript=script_text,
                audio_size=len(audio_bytes),
            )

        except Exception as e:
            logger.exception("Podcast generation failed: %s", e)
            await self._mark_failed(podcast_id, error_message=str(e))
            # Note: No automatic retry in Phase 1
```

```python
# rag_solution/router/podcast_router.py

@router.post("/podcasts/generate", response_model=PodcastGenerationOutput)
async def generate_podcast(
    podcast_input: PodcastGenerationInput,
    background_tasks: BackgroundTasks,  # FastAPI injects this
    podcast_service: PodcastService = Depends(get_podcast_service),
):
    """Generate a podcast from a collection (async)."""
    return await podcast_service.generate_podcast(
        podcast_input,
        background_tasks,
    )
```

### Phase 2: Celery + Redis (Production)

```python
# rag_solution/tasks/podcast_tasks.py

from celery import Celery, Task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Celery app configuration
celery_app = Celery(
    "rag_modulo",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max
    task_soft_time_limit=1500,  # 25 minutes warning
    task_acks_late=True,  # Re-queue on worker crash
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker
)

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 60 seconds
    autoretry_for=(LLMProviderError, AudioGenerationError),
    retry_backoff=True,  # Exponential backoff
)
def generate_podcast_task(self: Task, podcast_id: str) -> dict:
    """Celery task for podcast generation."""
    try:
        logger.info("Starting podcast generation: %s", podcast_id)

        # Update status
        update_podcast_status(podcast_id, PodcastStatus.GENERATING)

        # 1. Retrieve content
        documents = retrieve_documents_sync(podcast_id)

        # 2. Generate script
        script = generate_script_sync(documents)

        # 3. Generate audio
        audio_bytes = generate_audio_sync(script)

        # 4. Store audio
        audio_url = store_audio_sync(podcast_id, audio_bytes)

        # 5. Mark complete
        complete_podcast(podcast_id, audio_url, script, len(audio_bytes))

        logger.info("Podcast generation completed: %s", podcast_id)
        return {"status": "completed", "audio_url": audio_url}

    except Exception as exc:
        logger.exception("Podcast generation failed: %s", exc)
        mark_podcast_failed(podcast_id, str(exc))

        # Retry if within limit
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise
```

```python
# rag_solution/services/podcast_service.py (Phase 2)

class PodcastService:
    async def generate_podcast(
        self,
        podcast_input: PodcastGenerationInput,
    ) -> PodcastGenerationOutput:
        """Generate podcast using Celery."""

        # 1. Validate
        await self._validate_podcast_request(podcast_input)

        # 2. Create record
        podcast = await self._create_podcast_record(
            podcast_input,
            status=PodcastStatus.QUEUED,
        )

        # 3. Queue Celery task
        from rag_solution.tasks.podcast_tasks import generate_podcast_task

        task = generate_podcast_task.apply_async(
            args=[str(podcast.podcast_id)],
            priority=self._get_user_priority(podcast_input.user_id),
            countdown=0,  # Start immediately
        )

        # Store task_id for monitoring
        await self._store_task_id(podcast.podcast_id, task.id)

        return podcast
```

### Infrastructure Setup

**Phase 2 Docker Compose:**
```yaml
services:
  # Existing services...

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  celery_worker:
    build: ./backend
    command: celery -A rag_solution.tasks.podcast_tasks worker --loglevel=info --concurrency=4
    depends_on:
      - redis
      - postgres
      - milvus
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    volumes:
      - ./backend:/app
    deploy:
      replicas: 2  # Scale workers independently

  flower:
    build: ./backend
    command: celery -A rag_solution.tasks.podcast_tasks flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery_worker
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0

volumes:
  redis_data:
```

## Migration Path

### Step 1: MVP with BackgroundTasks (Week 1-2)
- Implement `PodcastService` with BackgroundTasks
- Basic error handling
- Status polling endpoint
- Launch to limited users

### Step 2: Add Persistence (Week 3)
- Store task state in database
- Implement manual retry endpoint
- Add basic monitoring

### Step 3: Celery Integration (Week 4-6)
- Set up Redis infrastructure
- Migrate to Celery tasks
- Keep BackgroundTasks as fallback
- Deploy Flower dashboard
- Gradual rollout (10% → 50% → 100%)

### Step 4: Advanced Features (Week 7+)
- Task prioritization based on user tier
- Scheduled podcast generation
- Batch processing optimizations
- Auto-scaling workers

## Progress Monitoring Structure

### Real-Time Progress Tracking

**Status Endpoint:** `GET /api/v1/podcasts/{podcast_id}`

**Response Structure:**
```python
{
    "podcast_id": "uuid",
    "status": "GENERATING",  # QUEUED | GENERATING | COMPLETED | FAILED
    "progress_percentage": 65,  # 0-100
    "current_step": "generating_audio",  # retrieving_content | generating_script | parsing_turns | generating_audio | combining_audio | storing_audio
    "step_details": {
        "total_turns": 20,
        "completed_turns": 13,
        "current_speaker": "EXPERT"
    },
    "estimated_time_remaining": 45,  # seconds
    "created_at": "2025-10-02T10:30:00Z",
    "updated_at": "2025-10-02T10:32:15Z"
}
```

### Progress Steps

| Step | Progress % | Description |
|------|-----------|-------------|
| `retrieving_content` | 10-30% | RAG pipeline retrieval |
| `generating_script` | 30-40% | LLM script generation |
| `parsing_turns` | 40-50% | Parse HOST/EXPERT turns |
| `generating_audio` | 50-90% | Multi-voice TTS (per turn tracking) |
| `combining_audio` | 90-95% | Combine segments with pauses |
| `storing_audio` | 95-100% | Upload to storage |

### Per-Turn Progress Calculation

During `generating_audio` step:
```python
progress_percentage = 50 + int(40 * completed_turns / total_turns)

# Example with 20 turns:
# Turn 5/20: 50 + (40 * 5/20) = 60%
# Turn 10/20: 50 + (40 * 10/20) = 70%
# Turn 20/20: 50 + (40 * 20/20) = 90%
```

## Monitoring & Observability

### Phase 1 Metrics
```python
# Database fields for progress tracking
- podcast.status (QUEUED, GENERATING, COMPLETED, FAILED)
- podcast.progress_percentage (0-100)
- podcast.current_step (step identifier)
- podcast.step_details (JSON with turn tracking)
- podcast.created_at, podcast.updated_at, podcast.completed_at
- podcast.error_message
```

### Phase 2 Metrics (Celery + Flower)
```
✅ Tasks started/completed/failed per hour
✅ Average task duration
✅ Worker utilization
✅ Queue depth
✅ Retry rates
✅ Task success rate by user
✅ Average turns per podcast
✅ Audio generation time per turn
```

## Decision Matrix

| Factor | BackgroundTasks | Celery + Redis | Winner |
|--------|----------------|----------------|--------|
| **Time to Ship** | 1 week ⚡ | 3-4 weeks 🐌 | Phase 1 for MVP |
| **Infrastructure** | None ✅ | Redis + Workers | Phase 1 initially |
| **Scalability** | Low ⭐⭐ | High ⭐⭐⭐⭐⭐ | Phase 2 for growth |
| **Reliability** | Medium ⭐⭐⭐ | High ⭐⭐⭐⭐⭐ | Phase 2 for production |
| **Monitoring** | Basic ⭐⭐ | Advanced ⭐⭐⭐⭐⭐ | Phase 2 |
| **Development Complexity** | Low ⭐⭐ | Medium ⭐⭐⭐⭐ | Phase 1 for simplicity |
| **Operational Complexity** | Low ⭐⭐ | Medium ⭐⭐⭐⭐ | Phase 1 |

## Status

**Proposed** - Hybrid approach recommended:
- **MVP:** FastAPI BackgroundTasks
- **Production:** Migrate to Celery + Redis within 6 weeks

## Success Criteria for Migration

Trigger migration to Celery when:
- 📊 **>50 podcasts/day** being generated
- 📈 **>10 concurrent** podcast generations
- 🚨 **>5% failure rate** from lost tasks
- 👥 **Premium users** need priority processing
- 🔄 **Task retry** becomes critical requirement

## References

- [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Flower Monitoring](https://flower.readthedocs.io/)
