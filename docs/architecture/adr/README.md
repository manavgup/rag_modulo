# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the RAG Modulo project.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs help teams:
- Understand why decisions were made
- Evaluate alternatives considered
- Track architectural evolution over time
- Onboard new team members

## ADR Index

### Podcast Generation (Issue #240)

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](./001-podcast-content-retrieval-strategy.md) | Podcast Content Retrieval Strategy | Proposed | 2025-10-02 |
| [002](./002-audio-generation-provider-selection.md) | Audio Generation Provider Selection (TTS vs Multi-Modal LLMs) | Proposed | 2025-10-02 |
| [003](./003-podcast-background-task-processing.md) | Podcast Background Task Processing | Proposed | 2025-10-02 |
| [004](./004-podcast-audio-storage-strategy.md) | Podcast Audio Storage Strategy | Proposed | 2025-10-02 |

## ADR Decisions Summary

### ADR-001: Content Retrieval
**Decision:** Use existing RAG pipeline with synthetic queries
- ✅ Leverage reranking and hierarchical chunking
- ✅ Better content quality through semantic search
- ✅ Token-efficient (top-k limits)
- 🎙️ **Q&A Format:** Script generated as HOST/EXPERT dialogue

### ADR-002: Audio Generation
**Decision:** Traditional TTS APIs (OpenAI + WatsonX)
- ✅ Production-ready quality
- ✅ Low latency (30-60s)
- ✅ Simple integration (no GPU hosting)
- 🎙️ **Multi-Voice:** HOST (alloy) + EXPERT (onyx) with 500ms pauses
- 🔮 Future: Multi-modal LLMs when mature

### ADR-003: Background Tasks
**Decision:** Hybrid approach
- **Phase 1 (MVP):** FastAPI BackgroundTasks (simple, no infrastructure)
- **Phase 2 (Production):** Celery + Redis (scalable, reliable)
- 📊 Migrate when >50 podcasts/day or >10 concurrent
- 📈 **Progress Tracking:** Per-turn monitoring (completed_turns / total_turns)

### ADR-004: Storage
**Decision:** MinIO (S3-compatible)
- ✅ Already deployed in stack
- ✅ Cost-effective (~$20/month for 1TB)
- ✅ S3 API for easy migration
- 🔮 Future: Cloudflare R2 (zero egress) if bandwidth costs spike

## ADR Template

All ADRs follow this structure:

```markdown
# ADR-XXX: [Decision Title]

- **Status:** [Proposed/Accepted/Deprecated/Superseded]
- **Date:** YYYY-MM-DD
- **Deciders:** [Decision Makers]

## Context
[Problem description and constraints]

## Decision
[The decision made]

## Consequences
[Positive and negative impacts]

## Alternatives Considered
[Other options and why they were rejected]

## Status
[Implementation status and next steps]
```

## Proposing a New ADR

1. Copy the template above
2. Number sequentially (next: 005)
3. Write clearly and concisely
4. Include diagrams where helpful
5. Consider alternatives thoroughly
6. Submit for team review

## ADR Lifecycle

- **Proposed** → Under discussion, not yet implemented
- **Accepted** → Approved and being implemented
- **Deprecated** → No longer recommended
- **Superseded** → Replaced by newer ADR

## Related Documentation

- [Architecture Overview](../README.md)
- [System Design](../system-design.md)
- [Development Guide](../../development/README.md)
