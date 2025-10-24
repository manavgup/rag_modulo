# Implementation Plan: Issue #461 - Fix CoT Reasoning Leak

**Issue**: https://github.com/manavgup/rag_modulo/issues/461
**Created**: 2025-10-21
**Status**: Ready for Implementation
**Approach**: Two-phase implementation (Quick Fix → Robust Solution)

---

## Executive Summary

**Problem**: Chain of Thought (CoT) internal reasoning is leaking into user-facing responses, producing garbage output with hallucinated content, internal instructions, and bloated responses (1,716 tokens instead of ~200).

**Root Cause**: Conversation metadata (entities, history, context) is being concatenated as plain text strings into LLM prompts, causing the LLM to echo them back in responses.

**Solution**: Two-phase approach:
1. **Phase 1 (Quick Fix)**: Fix prompt formatting to eliminate metadata leakage (~4 hours)
2. **Phase 2 (Robust Solution)**: Implement type-safe structured context architecture (~16 hours)

**Total Effort**: 20 hours (2.5 days)
**Priority**: 🔴 CRITICAL - Blocks production deployment

---

## Table of Contents

1. [Pre-Implementation Checklist](#pre-implementation-checklist)
2. [Phase 1: Quick Fix (4 hours)](#phase-1-quick-fix-4-hours)
3. [Phase 2: Robust Solution (16 hours)](#phase-2-robust-solution-16-hours)
4. [Testing Strategy](#testing-strategy)
5. [Rollback Plan](#rollback-plan)
6. [Success Criteria](#success-criteria)
7. [Post-Implementation](#post-implementation)

---

## Pre-Implementation Checklist

### 1. Environment Setup ✅

```bash
# Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# Create feature branch
git checkout -b fix/issue-461-cot-reasoning-leak

# Verify environment
cd backend
poetry install --with dev,test
poetry run pytest tests/unit/test_chain_of_thought*.py -v  # Baseline tests

# Start local development
make local-dev-infra  # Start infrastructure only
make local-dev-backend  # Start backend with hot-reload
```

### 2. Baseline Metrics 📊

```bash
# Test current behavior (BEFORE fix)
./test_search.sh > /tmp/before_fix.json

# Check response characteristics
cat /tmp/before_fix.json | jq '.answer' | wc -c  # Character count
cat /tmp/before_fix.json | jq '.answer' | grep -c "Based on the analysis"  # Leaked prefix
cat /tmp/before_fix.json | jq '.answer' | grep -c "in the context of"  # Leaked metadata
```

**Expected Baseline** (BROKEN):
- ❌ Response length: ~1,716 tokens (should be ~200)
- ❌ Contains: "Based on the analysis of"
- ❌ Contains: "(in the context of...)"
- ❌ Contains: Hallucinated conversations

### 3. Documentation Review 📚

Read these documents before starting:
- ✅ `backend/ISSUE_461_ROOT_CAUSE_ANALYSIS.md` - Root cause trace
- ✅ `backend/ARCHITECTURE_ANALYSIS_COT_METADATA.md` - Full architecture
- ✅ `docs/development/backend/strict-typing-guidelines.md` - Type safety rules

---

## Phase 1: Quick Fix (4 hours)

**Goal**: Eliminate metadata leakage from LLM prompts with minimal code changes.

**Strategy**: Fix only the prompt formatting in `chain_of_thought_service.py` without architectural changes.

### Step 1.1: Fix `_build_conversation_aware_context()` (1 hour)

**File**: `backend/rag_solution/services/chain_of_thought_service.py:528-551`

**Current Code** (BROKEN):
```python
def _build_conversation_aware_context(
    self, context_documents: list[str], context_metadata: dict[str, Any] | None
) -> list[str]:
    """Build conversation-aware context for CoT reasoning."""
    enhanced_context = list(context_documents)

    if context_metadata:
        # ❌ PROBLEM: Appending metadata AS TEXT to context!
        conversation_context = context_metadata.get("conversation_context")
        if conversation_context:
            enhanced_context.append(f"Conversation context: {conversation_context}")

        conversation_entities = context_metadata.get("conversation_entities", [])
        if conversation_entities:
            enhanced_context.append(f"Previously discussed: {', '.join(conversation_entities)}")

        message_history = context_metadata.get("message_history", [])
        if message_history:
            recent_messages = message_history[-3:]
            enhanced_context.append(f"Recent discussion: {' '.join(recent_messages)}")

    return enhanced_context
```

**Fixed Code**:
```python
def _build_conversation_aware_context(
    self, context_documents: list[str], context_metadata: dict[str, Any] | None
) -> list[str]:
    """Build context for CoT reasoning WITHOUT leaking metadata.

    IMPORTANT: Metadata is used for query expansion and understanding,
    but should NOT be appended as text strings to the LLM prompt.

    Args:
        context_documents: Retrieved document chunks (SEND to LLM)
        context_metadata: Conversation metadata (USE internally, DON'T send)

    Returns:
        List of document strings ONLY (no metadata strings)
    """
    # ✅ FIX: Return ONLY documents, no metadata strings
    # Metadata should be used for query expansion BEFORE retrieval,
    # not sent to the LLM during reasoning
    return list(context_documents)

    # NOTE: If we need to use metadata for context understanding,
    # it should be done through query rewriting or entity resolution,
    # NOT by appending it as text to the prompt.
```

**Testing**:
```bash
# Run unit tests
poetry run pytest tests/unit/test_chain_of_thought_service.py::test_build_conversation_aware_context -v

# Expected: Context should contain ONLY document texts, no metadata strings
```

---

### Step 1.2: Fix `_generate_llm_response()` Prompt (1 hour)

**File**: `backend/rag_solution/services/chain_of_thought_service.py:227-279`

**Current Code** (BROKEN):
```python
def _generate_llm_response(
    self, llm_service: LLMBase, question: str, context: list[str], user_id: str
) -> tuple[str, Any]:
    # ❌ PROBLEM: Simple string join with no structure
    prompt = f"Question: {question}\n\nContext: {' '.join(context)}\n\nAnswer:"
```

**Fixed Code**:
```python
def _generate_llm_response(
    self, llm_service: LLMBase, question: str, context: list[str], user_id: str
) -> tuple[str, Any]:
    """Generate response using LLM service with structured prompt.

    IMPORTANT: Prompt should have clear instructions to prevent leakage
    of reasoning process or internal context.
    """
    if not hasattr(llm_service, "generate_text_with_usage"):
        logger.warning("LLM service %s does not have generate_text_with_usage method", type(llm_service))
        return f"Unable to generate response - LLM service unavailable", None

    # ✅ FIX: Create structured prompt with clear instructions
    # Format documents as numbered list for clarity
    formatted_docs = "\n\n".join([
        f"Document {i+1}:\n{doc}"
        for i, doc in enumerate(context)
    ]) if context else "No context available."

    # Create prompt with explicit instructions
    prompt = f"""You are a helpful AI assistant. Answer the user's question based ONLY on the provided documents below.

IMPORTANT RULES:
- Answer based ONLY on the information in the documents
- Do NOT mention the documents, your reasoning process, or any internal context
- Do NOT include phrases like "Based on the analysis" or "in the context of"
- Provide a direct, clear answer to the question
- If the documents don't contain the answer, state this clearly

Documents:
{formatted_docs}

Question: {question}

Provide a concise, direct answer:"""

    try:
        from rag_solution.schemas.llm_usage_schema import ServiceType

        cot_template = self._create_reasoning_template(user_id)

        # Use template consistently for ALL providers with token tracking
        llm_response, usage = llm_service.generate_text_with_usage(
            user_id=UUID(user_id),
            prompt=prompt,
            service_type=ServiceType.SEARCH,
            template=cot_template,
            variables={"context": prompt},
        )

        return (
            str(llm_response).strip() if llm_response else "Unable to generate an answer.",
            usage,
        )

    except Exception as exc:
        if isinstance(exc, LLMProviderError):
            raise
        raise LLMProviderError(
            provider="chain_of_thought",
            error_type="reasoning_step",
            message=f"Failed to execute reasoning step: {exc!s}",
        ) from exc
```

**Testing**:
```bash
# Run integration tests
poetry run pytest tests/integration/test_chain_of_thought_integration.py -v

# Expected: Responses should NOT contain:
# - "Based on the analysis of"
# - "(in the context of...)"
# - Internal reasoning artifacts
```

---

### Step 1.3: Fix `answer_synthesizer.py` (1 hour)

**File**: `backend/rag_solution/services/answer_synthesizer.py:21-55`

**Current Code** (BROKEN):
```python
def synthesize(self, original_question: str, reasoning_steps: list[ReasoningStep]) -> str:
    if not reasoning_steps:
        return "Unable to generate an answer due to insufficient information."

    intermediate_answers = [step.intermediate_answer for step in reasoning_steps if step.intermediate_answer]

    if not intermediate_answers:
        return "Unable to synthesize an answer from the reasoning steps."

    # ❌ PROBLEM: Adds "Based on the analysis" prefix
    if len(intermediate_answers) == 1:
        return intermediate_answers[0]

    # Combine multiple answers
    synthesis = f"Based on the analysis of {original_question}: "  # ← LEAK!

    for i, answer in enumerate(intermediate_answers):
        if i == 0:
            synthesis += answer
        elif i == len(intermediate_answers) - 1:
            synthesis += f" Additionally, {answer.lower()}"
        else:
            synthesis += f" Furthermore, {answer.lower()}"

    return synthesis
```

**Fixed Code**:
```python
def synthesize(self, original_question: str, reasoning_steps: list[ReasoningStep]) -> str:
    """Synthesize final answer from reasoning steps WITHOUT leaking internal reasoning.

    IMPORTANT: The final answer should be clean and user-facing.
    Do NOT include internal prefixes like "Based on the analysis of".

    Args:
        original_question: The original user question
        reasoning_steps: The reasoning steps taken (internal)

    Returns:
        Clean, user-facing answer
    """
    if not reasoning_steps:
        return "Unable to generate an answer due to insufficient information."

    # Extract intermediate answers
    intermediate_answers = [step.intermediate_answer for step in reasoning_steps if step.intermediate_answer]

    if not intermediate_answers:
        return "Unable to synthesize an answer from the reasoning steps."

    # ✅ FIX: Return clean answer without internal prefixes
    # Single answer: return directly (no modification)
    if len(intermediate_answers) == 1:
        return intermediate_answers[0]

    # Multiple answers: combine naturally without "Based on the analysis" prefix
    # Use the first answer as the base
    synthesis = intermediate_answers[0]

    # Add subsequent answers with natural transitions
    for i, answer in enumerate(intermediate_answers[1:], start=1):
        # Clean joining (avoid repetition, maintain flow)
        if not synthesis.endswith(('.', '!', '?')):
            synthesis += '.'

        # Add natural transition
        if i == len(intermediate_answers) - 1:
            synthesis += f" Additionally, {answer}"
        else:
            synthesis += f" {answer}"

    return synthesis
```

**Testing**:
```bash
# Run unit tests
poetry run pytest tests/unit/test_answer_synthesizer.py -v

# Expected: Synthesized answers should:
# - NOT start with "Based on the analysis of"
# - Flow naturally without internal prefixes
# - Combine multiple answers cleanly
```

---

### Step 1.4: Integration Testing (1 hour)

**Test Script**: Create `backend/test_cot_fix.py`

```python
#!/usr/bin/env python3
"""Test CoT fix to ensure no metadata leakage."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from uuid import UUID
from core.config import Settings
from rag_solution.schemas.search_schema import SearchInput


async def test_cot_no_leakage():
    """Test that CoT responses don't leak internal reasoning."""

    # Test data
    user_id = UUID("ee76317f-3b6f-4fea-8b74-56483731f58c")
    collection_id = UUID("5eb82bd8-1fbd-454e-86d6-61199642757c")

    test_cases = [
        {
            "question": "What were IBM's key financial metrics for 2022?",
            "should_not_contain": [
                "Based on the analysis of",
                "(in the context of",
                "Previously discussed:",
                "Conversation context:",
                "instruction:",
                "response:",
            ]
        },
        {
            "question": "What was the total amount spent on research and development?",
            "should_not_contain": [
                "Based on the analysis",
                "in the context of",
                "Recent discussion:",
            ]
        }
    ]

    # Import search service
    from sqlalchemy.orm import Session
    from rag_solution.services.search_service import SearchService
    from core.database import get_db

    settings = Settings()

    # Get DB session
    db_gen = get_db()
    db = next(db_gen)

    try:
        search_service = SearchService(db, settings)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*80}")
            print(f"Test Case {i}: {test_case['question']}")
            print(f"{'='*80}\n")

            search_input = SearchInput(
                question=test_case["question"],
                collection_id=collection_id,
                user_id=user_id,
                config_metadata={"cot_enabled": True}  # Enable CoT
            )

            result = await search_service.search(search_input)

            print(f"Answer ({len(result.answer)} chars):")
            print(result.answer)
            print()

            # Check for leakage
            leaks_found = []
            for forbidden_phrase in test_case["should_not_contain"]:
                if forbidden_phrase.lower() in result.answer.lower():
                    leaks_found.append(forbidden_phrase)

            if leaks_found:
                print(f"❌ FAILED: Found leaked phrases:")
                for leak in leaks_found:
                    print(f"   - '{leak}'")
                return False
            else:
                print(f"✅ PASSED: No metadata leakage detected")

        print(f"\n{'='*80}")
        print("✅ ALL TESTS PASSED")
        print(f"{'='*80}\n")
        return True

    finally:
        db.close()


if __name__ == "__main__":
    result = asyncio.run(test_cot_no_leakage())
    sys.exit(0 if result else 1)
```

**Run Tests**:
```bash
cd backend
PYTHONPATH=/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/backend poetry run python test_cot_fix.py
```

**Success Criteria**:
- ✅ All test cases pass
- ✅ No forbidden phrases in responses
- ✅ Response length reasonable (~100-300 tokens, not 1,716)

---

### Step 1.5: Commit Quick Fix (15 minutes)

```bash
# Stage changes
git add backend/rag_solution/services/chain_of_thought_service.py
git add backend/rag_solution/services/answer_synthesizer.py
git add backend/test_cot_fix.py

# Commit with detailed message
git commit -m "fix: Prevent CoT reasoning metadata from leaking into responses

Fixes #461

Changes:
- chain_of_thought_service.py: Remove metadata string concatenation
- chain_of_thought_service.py: Add structured prompt with clear instructions
- answer_synthesizer.py: Remove 'Based on the analysis' prefix
- test_cot_fix.py: Add integration test for leakage detection

Root cause: Conversation metadata (entities, history) was being
appended as plain text to LLM prompts, causing it to echo them
back in responses.

Fix: Only send document context to LLM, use metadata internally
for query expansion but don't include in prompts.

Testing:
- Verified no 'Based on the analysis of' in responses
- Verified no '(in the context of...)' leakage
- Response length reduced from ~1,716 tokens to ~200 tokens
- All existing tests pass"

# Push to branch
git push origin fix/issue-461-cot-reasoning-leak
```

---

## Phase 2: Robust Solution (16 hours)

**Goal**: Implement type-safe structured context architecture for long-term maintainability.

**Strategy**: Create new Pydantic types following strict typing guidelines, refactor services to use them.

### Step 2.1: Create Strict Type Definitions (4 hours)

#### File 1: `backend/rag_solution/schemas/context_types.py` (NEW)

```python
"""Type-safe context types for RAG reasoning.

This module provides structured, type-safe alternatives to dict[str, Any]
for handling document context, conversation metadata, and prompt instructions.

Follows strict typing guidelines:
- NO dict[str, Any]
- NO isinstance() for logic
- Use Literal, NewType, Protocol for type safety
"""

from typing import Literal, NewType, Protocol, runtime_checkable
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

# Semantic types for IDs
DocumentID = NewType("DocumentID", str)
ChunkID = NewType("ChunkID", str)
SourceID = NewType("SourceID", str)

# Literal types for constrained values
EntityType = Literal["organization", "person", "location", "date", "concept", "other"]
MessageRole = Literal["user", "assistant", "system"]
OutputFormat = Literal["concise", "detailed", "bullet_points", "structured"]
ReasoningVisibility = Literal["hidden", "brief", "detailed"]
ToneType = Literal["professional", "casual", "technical", "friendly"]
ConstraintPriority = Literal["must", "should", "nice_to_have"]


@runtime_checkable
class FormattableForLLM(Protocol):
    """Protocol for objects that can be formatted for LLM consumption."""

    def format_for_llm(self, include_metadata: bool = False) -> str:
        """Format this object for LLM prompt."""
        ...


class DocumentContext(BaseModel):
    """Type-safe document context for LLM reasoning.

    Represents a retrieved document chunk with metadata.
    Immutable for thread safety.
    """

    text: str = Field(..., min_length=1, description="Document text content")
    source_id: SourceID
    document_name: str | None = Field(None, description="Human-readable document name")
    page_number: int | None = Field(None, ge=1, description="Page number in source")
    chunk_index: int | None = Field(None, ge=0, description="Chunk index within document")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to query")
    retrieval_rank: int = Field(..., ge=1, description="Rank in retrieval results")

    class Config:
        frozen = True  # Immutable

    def format_for_llm(self, include_metadata: bool = False) -> str:
        """Format document for LLM consumption."""
        if include_metadata and self.document_name:
            return f"[Source: {self.document_name}, Page {self.page_number or 'N/A'}]\n{self.text}"
        return self.text


class DocumentContextList(BaseModel):
    """Type-safe collection of document contexts."""

    items: list[DocumentContext] = Field(default_factory=list)

    def add_document(self, doc: DocumentContext) -> None:
        """Add document, preventing duplicates by source_id."""
        if not any(d.source_id == doc.source_id for d in self.items):
            self.items.append(doc)

    def get_top_k(self, k: int) -> list[DocumentContext]:
        """Get top-k documents by relevance score."""
        return sorted(self.items, key=lambda d: d.relevance_score, reverse=True)[:k]

    def format_for_llm(
        self,
        numbered: bool = True,
        include_sources: bool = False,
        max_documents: int | None = None
    ) -> str:
        """Format all documents for LLM prompt."""
        docs_to_format = self.items[:max_documents] if max_documents else self.items

        if numbered:
            return "\n\n".join([
                f"Document {i+1}:\n{doc.format_for_llm(include_metadata=include_sources)}"
                for i, doc in enumerate(docs_to_format)
            ])
        else:
            return "\n\n".join([
                doc.format_for_llm(include_metadata=include_sources)
                for doc in docs_to_format
            ])

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)


class ConversationEntity(BaseModel):
    """Type-safe conversation entity tracking."""

    entity_text: str = Field(..., min_length=1, max_length=255)
    entity_type: EntityType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    first_mentioned_turn: int = Field(..., ge=1)
    mention_count: int = Field(default=1, ge=1)

    class Config:
        frozen = True

    @classmethod
    def from_text(
        cls,
        text: str,
        entity_type: EntityType = "other",
        turn_number: int = 1
    ) -> "ConversationEntity":
        """Factory method: Create entity from plain text."""
        return cls(
            entity_text=text.strip(),
            entity_type=entity_type,
            confidence=1.0,
            first_mentioned_turn=turn_number,
            mention_count=1
        )


class ConversationTurn(BaseModel):
    """Type-safe conversation turn."""

    turn_number: int = Field(..., ge=1)
    role: MessageRole
    content: str = Field(..., min_length=1)
    timestamp: datetime | None = None
    entities_mentioned: list[str] = Field(default_factory=list)
    token_count: int | None = Field(None, ge=0)
    model_used: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)

    class Config:
        frozen = True


class PromptConstraint(BaseModel):
    """Type-safe constraint definition."""

    constraint_text: str = Field(..., min_length=10)
    priority: ConstraintPriority = "must"
    enforced: bool = True

    class Config:
        frozen = True


class PromptInstructions(BaseModel):
    """Type-safe prompt instructions - NO dict[str, Any]."""

    system_role: str = Field(
        default="You are a helpful AI assistant.",
        min_length=10
    )
    task_description: str = Field(
        default="Answer the user's question based on the provided documents.",
        min_length=10
    )
    output_format: OutputFormat = "concise"
    output_constraints: list[PromptConstraint] = Field(
        default_factory=lambda: [
            PromptConstraint(
                constraint_text="Answer based ONLY on the provided documents",
                priority="must"
            ),
            PromptConstraint(
                constraint_text="Do not mention the documents, sources, or your reasoning process",
                priority="must"
            ),
            PromptConstraint(
                constraint_text="If the documents don't contain the answer, say so clearly",
                priority="should"
            )
        ]
    )
    tone: ToneType = "professional"
    max_response_length: int | None = Field(None, ge=50, le=4000)
    include_sources: bool = False
    reasoning_visibility: ReasoningVisibility = "hidden"

    class Config:
        frozen = True

    def format_system_prompt(self) -> str:
        """Format complete system prompt from instructions."""
        must_constraints = [c.constraint_text for c in self.output_constraints if c.priority == "must"]
        should_constraints = [c.constraint_text for c in self.output_constraints if c.priority == "should"]

        parts = [
            self.system_role,
            "",
            f"Task: {self.task_description}",
            "",
            f"Output Format: {self.output_format.replace('_', ' ').title()}",
            f"Tone: {self.tone.title()}",
            "",
            "Required Constraints:"
        ]
        parts.extend([f"- {c}" for c in must_constraints])

        if should_constraints:
            parts.append("")
            parts.append("Recommendations:")
            parts.extend([f"- {c}" for c in should_constraints])

        if self.max_response_length:
            parts.append("")
            parts.append(f"Keep your response concise (max {self.max_response_length} tokens).")

        return "\n".join(parts)


class ConversationContext(BaseModel):
    """Type-safe conversation metadata - NO dict[str, Any]."""

    entities: list[ConversationEntity] = Field(default_factory=list)
    message_history: list[ConversationTurn] = Field(default_factory=list)
    current_topic: str | None = None
    conversation_id: UUID | None = None
    session_start_time: datetime | None = None
    total_turns: int = Field(default=0, ge=0)

    def get_recent_turns(self, n: int = 3) -> list[ConversationTurn]:
        """Get the n most recent turns."""
        return self.message_history[-n:] if self.message_history else []

    def get_top_entities(self, k: int = 5) -> list[ConversationEntity]:
        """Get top-k entities by mention count."""
        return sorted(self.entities, key=lambda e: e.mention_count, reverse=True)[:k]

    def format_for_query_expansion(self) -> str:
        """Format for INTERNAL query expansion (safe usage)."""
        top_entities = [e.entity_text for e in self.get_top_entities(k=3)]
        return " ".join(top_entities) if top_entities else ""


class ReasoningContext(BaseModel):
    """Complete context for LLM reasoning - ZERO dict[str, Any]."""

    documents: DocumentContextList = Field(default_factory=DocumentContextList)
    conversation: ConversationContext | None = None
    instructions: PromptInstructions = Field(default_factory=PromptInstructions)

    class Config:
        frozen = True

    def format_for_llm_prompt(
        self,
        question: str,
        include_conversation_hints: bool = False
    ) -> str:
        """Format complete prompt for LLM with NO metadata leakage."""
        system_prompt = self.instructions.format_system_prompt()
        documents_text = self.documents.format_for_llm(
            numbered=True,
            include_sources=self.instructions.include_sources,
            max_documents=10
        )

        prompt_parts = [
            system_prompt,
            "",
            "Documents:",
            documents_text,
            "",
            f"Question: {question}",
            "",
            "Provide a concise, direct answer:"
        ]

        # Conversation hints (SAFE - not sent verbatim)
        if include_conversation_hints and self.conversation:
            entities = [e.entity_text for e in self.conversation.get_top_entities(k=3)]
            if entities:
                entity_context = ", ".join(entities)
                # Insert hint BEFORE the question, not in documents
                prompt_parts.insert(-3, f"(Note: This question relates to {entity_context})")
                prompt_parts.insert(-3, "")

        return "\n".join(prompt_parts)
```

**Timeline**: 3 hours (including documentation and examples)

---

#### File 2: `backend/rag_solution/services/context_adapters.py` (NEW)

```python
"""Adapters for converting between legacy and structured context types.

Enables gradual migration from dict-based to type-safe approach.
"""

from typing import Any
from uuid import UUID

from rag_solution.schemas.context_types import (
    ConversationContext,
    ConversationEntity,
    ConversationTurn,
    DocumentContext,
    DocumentContextList,
    PromptInstructions,
    ReasoningContext,
    SourceID,
)


def legacy_to_structured_context(
    context_documents: list[str],
    context_metadata: dict[str, Any] | None
) -> ReasoningContext:
    """Convert legacy context to structured ReasoningContext.

    Args:
        context_documents: List of document text strings
        context_metadata: Legacy metadata dict (may contain anything)

    Returns:
        Type-safe ReasoningContext
    """
    # Convert documents
    doc_contexts = [
        DocumentContext(
            text=doc,
            source_id=SourceID(f"legacy_doc_{i}"),
            relevance_score=1.0,
            retrieval_rank=i+1
        )
        for i, doc in enumerate(context_documents)
    ]

    # Extract conversation metadata safely
    conversation_ctx = None
    if context_metadata:
        entities = []
        for e in context_metadata.get("conversation_entities", []):
            if isinstance(e, str):  # Validate external input
                entities.append(ConversationEntity.from_text(e, turn_number=1))

        message_history = []
        for i, msg in enumerate(context_metadata.get("message_history", []), start=1):
            if isinstance(msg, str):  # Validate external input
                message_history.append(ConversationTurn(
                    turn_number=i,
                    role="user",
                    content=msg
                ))

        if entities or message_history:
            conversation_ctx = ConversationContext(
                entities=entities,
                message_history=message_history,
                current_topic=context_metadata.get("conversation_context")
            )

    return ReasoningContext(
        documents=DocumentContextList(items=doc_contexts),
        conversation=conversation_ctx,
        instructions=PromptInstructions()
    )


def structured_to_legacy_context(
    reasoning_context: ReasoningContext
) -> tuple[list[str], dict[str, Any]]:
    """Convert structured context back to legacy format.

    Useful during transition period when some code expects old format.
    """
    # Extract document texts
    context_documents = [doc.text for doc in reasoning_context.documents]

    # Convert conversation to metadata dict
    context_metadata: dict[str, Any] = {}
    if reasoning_context.conversation:
        context_metadata["conversation_entities"] = [
            e.entity_text for e in reasoning_context.conversation.entities
        ]
        if reasoning_context.conversation.current_topic:
            context_metadata["conversation_context"] = reasoning_context.conversation.current_topic

        context_metadata["message_history"] = [
            turn.content for turn in reasoning_context.conversation.message_history
        ]

    return context_documents, context_metadata
```

**Timeline**: 1 hour

---

### Step 2.2: Refactor CoT Service to Use Structured Types (6 hours)

**File**: `backend/rag_solution/services/chain_of_thought_service.py`

**Add New Methods** (keep old ones for backward compatibility):

```python
# Add imports
from rag_solution.schemas.context_types import (
    ReasoningContext,
    DocumentContext,
    DocumentContextList,
    PromptInstructions,
    SourceID,
)
from rag_solution.services.context_adapters import legacy_to_structured_context


# NEW METHOD: Build structured context
def _build_structured_reasoning_context(
    self,
    context_documents: list[str],
    conversation: ConversationContext | None = None,
    instructions: PromptInstructions | None = None
) -> ReasoningContext:
    """Build structured reasoning context (NEW, type-safe approach).

    Replaces: _build_conversation_aware_context()

    Args:
        context_documents: Retrieved document texts
        conversation: Optional conversation metadata (type-safe)
        instructions: Optional prompt instructions (type-safe)

    Returns:
        Structured ReasoningContext with NO dict[str, Any]
    """
    # Convert document strings to DocumentContext objects
    doc_contexts = [
        DocumentContext(
            text=doc,
            source_id=SourceID(f"doc_{i}"),
            relevance_score=1.0,
            retrieval_rank=i+1
        )
        for i, doc in enumerate(context_documents)
    ]

    return ReasoningContext(
        documents=DocumentContextList(items=doc_contexts),
        conversation=conversation,
        instructions=instructions or PromptInstructions()
    )


# NEW METHOD: Generate LLM response with structured context
def _generate_llm_response_structured(
    self,
    llm_service: LLMBase,
    question: str,
    reasoning_context: ReasoningContext,
    user_id: str
) -> tuple[str, Any]:
    """Generate response using structured context (NO leakage).

    Replaces: _generate_llm_response()

    Args:
        llm_service: LLM service
        question: Question to answer
        reasoning_context: Structured context (type-safe)
        user_id: User ID

    Returns:
        Tuple of (response_text, usage_stats)
    """
    if not hasattr(llm_service, "generate_text_with_usage"):
        logger.warning("LLM service %s does not have generate_text_with_usage method", type(llm_service))
        return "Unable to generate response - LLM service unavailable", None

    # Format prompt with proper structure (NO metadata leakage)
    prompt = reasoning_context.format_for_llm_prompt(
        question=question,
        include_conversation_hints=False  # Keep metadata internal
    )

    try:
        from rag_solution.schemas.llm_usage_schema import ServiceType

        cot_template = self._create_reasoning_template(user_id)

        # Generate response
        llm_response, usage = llm_service.generate_text_with_usage(
            user_id=UUID(user_id),
            prompt=prompt,
            service_type=ServiceType.SEARCH,
            template=cot_template,
            variables={"context": prompt}
        )

        return (
            str(llm_response).strip() if llm_response else "Unable to generate an answer.",
            usage
        )

    except Exception as exc:
        if isinstance(exc, LLMProviderError):
            raise
        raise LLMProviderError(
            provider="chain_of_thought",
            error_type="reasoning_step",
            message=f"Failed to execute reasoning step: {exc!s}",
        ) from exc


# UPDATE: execute_reasoning_step to support both legacy and structured
async def execute_reasoning_step(
    self,
    step_number: int,
    question: str,
    context: list[str] | ReasoningContext,  # ← Support both types
    previous_answers: list[str],
    retrieved_documents: list[dict[str, str | int | float]] | None = None,
    user_id: str | None = None,
) -> ReasoningStep:
    """Execute a single reasoning step (supports legacy and structured context)."""
    start_time = time.time()

    # Type dispatch: structured vs legacy
    if isinstance(context, ReasoningContext):
        # NEW: Use structured context
        reasoning_context = context
        llm_service = self._get_llm_service_for_user(user_id)
        if not llm_service:
            llm_service = self.llm_service

        if llm_service and user_id:
            intermediate_answer, step_usage = self._generate_llm_response_structured(
                llm_service, question, reasoning_context, user_id
            )
        else:
            intermediate_answer = "Unable to generate response - no LLM service available"
            step_usage = None
    else:
        # LEGACY: Use old approach (backward compatibility)
        full_context = context + previous_answers
        llm_service = self._get_llm_service_for_user(user_id)
        if not llm_service:
            llm_service = self.llm_service

        if llm_service and user_id:
            intermediate_answer, step_usage = self._generate_llm_response(
                llm_service, question, full_context, user_id
            )
        else:
            intermediate_answer = f"Based on the available context: {' '.join(full_context[:300])}"
            step_usage = None

    # ... rest of the method remains the same ...
```

**Timeline**: 4 hours (careful refactoring + testing)

---

### Step 2.3: Update Search Service Integration (3 hours)

**File**: `backend/rag_solution/services/search_service.py`

**Add Method**: Convert pipeline results to ReasoningContext

```python
from rag_solution.schemas.context_types import (
    ReasoningContext,
    DocumentContext,
    DocumentContextList,
    ConversationContext,
    ConversationEntity,
    PromptInstructions,
    SourceID,
)


def _build_reasoning_context_from_results(
    self,
    pipeline_result: PipelineResult,
    search_input: SearchInput
) -> ReasoningContext:
    """Convert pipeline results to structured ReasoningContext.

    This replaces the ad-hoc context building with type-safe approach.
    """
    # Extract documents with metadata
    doc_contexts = []
    for i, result in enumerate(pipeline_result.query_results):
        doc_contexts.append(DocumentContext(
            text=result.chunk.text,
            source_id=SourceID(result.chunk.chunk_id),
            document_name=result.chunk.metadata.get("document_name"),
            page_number=result.chunk.metadata.get("page_number"),
            chunk_index=result.chunk.metadata.get("chunk_number"),
            relevance_score=result.score,
            retrieval_rank=i+1
        ))

    # Build conversation context from search input metadata
    conversation_ctx = None
    if search_input.config_metadata:
        entities_data = search_input.config_metadata.get("conversation_entities", [])
        entities = [
            ConversationEntity.from_text(e, turn_number=1)
            for e in entities_data if isinstance(e, str)
        ]

        if entities or search_input.config_metadata.get("conversation_context"):
            conversation_ctx = ConversationContext(
                entities=entities,
                current_topic=search_input.config_metadata.get("conversation_context")
            )

    # Build instructions (CoT-specific)
    instructions = PromptInstructions(
        output_format="concise",
        reasoning_visibility="hidden",  # ← KEY: Hide internal reasoning!
        output_constraints=[
            PromptConstraint(
                constraint_text="Answer based ONLY on the provided documents",
                priority="must"
            ),
            PromptConstraint(
                constraint_text="Do not mention your reasoning process or internal context",
                priority="must"
            ),
            PromptConstraint(
                constraint_text="Provide a clear, direct answer to the question",
                priority="must"
            )
        ]
    )

    return ReasoningContext(
        documents=DocumentContextList(items=doc_contexts),
        conversation=conversation_ctx,
        instructions=instructions
    )
```

**Update CoT Integration**:

```python
# In search() method, when using CoT:
if use_cot:
    # Build structured reasoning context
    reasoning_context = self._build_reasoning_context_from_results(
        pipeline_result, search_input
    )

    # Execute CoT with structured context
    cot_result = await self.chain_of_thought_service.execute_chain_of_thought_structured(
        cot_input=cot_input,
        reasoning_context=reasoning_context,
        user_id=str(search_input.user_id)
    )
```

**Timeline**: 3 hours

---

### Step 2.4: Comprehensive Testing (3 hours)

#### Unit Tests

**File**: `backend/tests/unit/test_context_types.py` (NEW)

```python
"""Unit tests for type-safe context types."""

import pytest
from pydantic import ValidationError

from rag_solution.schemas.context_types import (
    DocumentContext,
    DocumentContextList,
    ConversationEntity,
    ConversationContext,
    PromptInstructions,
    ReasoningContext,
    SourceID,
)


def test_document_context_immutability():
    """Ensure DocumentContext is immutable."""
    doc = DocumentContext(
        text="test",
        source_id=SourceID("123"),
        relevance_score=0.9,
        retrieval_rank=1
    )

    with pytest.raises(ValidationError):
        doc.text = "modified"  # Should fail (frozen)


def test_document_context_list_deduplication():
    """Test deduplication by source_id."""
    doc_list = DocumentContextList()

    doc1 = DocumentContext(
        text="doc1",
        source_id=SourceID("123"),
        relevance_score=0.9,
        retrieval_rank=1
    )
    doc2 = DocumentContext(
        text="doc1 duplicate",
        source_id=SourceID("123"),
        relevance_score=0.8,
        retrieval_rank=2
    )

    doc_list.add_document(doc1)
    doc_list.add_document(doc2)  # Should be skipped

    assert len(doc_list) == 1


def test_conversation_entity_from_text():
    """Test entity creation from text."""
    entity = ConversationEntity.from_text("IBM", entity_type="organization")

    assert entity.entity_text == "IBM"
    assert entity.entity_type == "organization"
    assert entity.confidence == 1.0
    assert entity.first_mentioned_turn == 1


def test_reasoning_context_format_no_leakage():
    """CRITICAL: Ensure ReasoningContext doesn't leak metadata."""
    doc_ctx = DocumentContext(
        text="IBM revenue was $57.4B in 2022.",
        source_id=SourceID("doc1"),
        relevance_score=0.95,
        retrieval_rank=1
    )

    conversation_ctx = ConversationContext(
        entities=[
            ConversationEntity.from_text("IBM", entity_type="organization")
        ],
        current_topic="financial results"
    )

    reasoning_ctx = ReasoningContext(
        documents=DocumentContextList(items=[doc_ctx]),
        conversation=conversation_ctx,
        instructions=PromptInstructions(
            output_constraints=[
                PromptConstraint(
                    constraint_text="Do not mention your reasoning process",
                    priority="must"
                )
            ]
        )
    )

    prompt = reasoning_ctx.format_for_llm_prompt(
        question="What was IBM's revenue?",
        include_conversation_hints=False
    )

    # Verify NO leakage
    assert "Previously discussed:" not in prompt
    assert "Conversation context:" not in prompt
    assert "entity_text" not in prompt
    assert "financial results" not in prompt  # Topic NOT in prompt

    # Verify documents ARE included
    assert "IBM revenue was $57.4B in 2022" in prompt

    # Verify instructions ARE included
    assert "Do not mention your reasoning process" in prompt
```

#### Integration Tests

**File**: `backend/tests/integration/test_cot_structured_context.py` (NEW)

```python
"""Integration tests for CoT with structured context."""

import pytest
from uuid import UUID

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.search_service import SearchService


@pytest.mark.integration
async def test_cot_with_structured_context_no_leakage(
    db_session,
    test_user,
    test_collection
):
    """End-to-end: CoT with structured context produces clean responses."""

    search_input = SearchInput(
        question="What were IBM's key financial metrics for 2022?",
        collection_id=test_collection.id,
        user_id=test_user.id,
        config_metadata={
            "cot_enabled": True,
            "conversation_entities": ["IBM", "financial results", "2022"]
        }
    )

    search_service = SearchService(db_session, settings)
    result = await search_service.search(search_input)

    # Verify NO leakage in final answer
    assert "Previously discussed:" not in result.answer
    assert "Conversation context:" not in result.answer
    assert "entity_text" not in result.answer
    assert "Based on the analysis of" not in result.answer
    assert "(in the context of" not in result.answer

    # Verify answer IS informative
    assert len(result.answer) > 50
    assert len(result.answer) < 2000  # Not bloated

    # Verify CoT metadata captured (for debugging)
    if result.cot_output:
        assert "reasoning_steps" in result.cot_output
```

**Timeline**: 3 hours (comprehensive testing)

---

### Step 2.5: Documentation & Commit (30 minutes)

```bash
# Stage all changes
git add backend/rag_solution/schemas/context_types.py
git add backend/rag_solution/services/context_adapters.py
git add backend/rag_solution/services/chain_of_thought_service.py
git add backend/rag_solution/services/search_service.py
git add backend/tests/unit/test_context_types.py
git add backend/tests/integration/test_cot_structured_context.py

# Commit with detailed message
git commit -m "refactor: Implement type-safe structured context for CoT reasoning

Related to #461

This is a comprehensive refactor to eliminate dict[str, Any] and
establish strict typing patterns for RAG reasoning context.

New Files:
- schemas/context_types.py: Type-safe context types
- services/context_adapters.py: Legacy/structured converters
- tests/unit/test_context_types.py: Type safety tests
- tests/integration/test_cot_structured_context.py: E2E tests

Changes:
- chain_of_thought_service.py: Add structured context support
- search_service.py: Convert pipeline results to structured types
- Backward compatibility maintained via adapters

Benefits:
- Zero dict[str, Any] - full type safety
- Zero isinstance() - factory methods instead
- Complete IDE autocomplete
- Prevents metadata leakage by design
- Establishes patterns for future refactoring (#211-213)

Testing:
- All unit tests pass
- All integration tests pass
- No metadata leakage in responses
- Backward compatible with existing code"

# Push to branch
git push origin fix/issue-461-cot-reasoning-leak
```

---

## Testing Strategy

### 1. Unit Tests

Run after each phase:

```bash
# Phase 1 tests
poetry run pytest backend/tests/unit/test_chain_of_thought_service.py -v
poetry run pytest backend/tests/unit/test_answer_synthesizer.py -v

# Phase 2 tests
poetry run pytest backend/tests/unit/test_context_types.py -v
poetry run pytest backend/tests/unit/test_chain_of_thought*.py -v
```

### 2. Integration Tests

```bash
# Run all CoT integration tests
poetry run pytest backend/tests/integration/test_chain_of_thought_integration.py -v
poetry run pytest backend/tests/integration/test_cot_structured_context.py -v
```

### 3. Manual Testing

```bash
# Test with real queries
cd /Users/mg/mg-work/manav/work/ai-experiments/rag_modulo
./test_search.sh > /tmp/after_fix.json

# Compare before/after
echo "BEFORE:"
cat /tmp/before_fix.json | jq '.answer' | wc -c
cat /tmp/before_fix.json | jq '.answer' | grep -c "Based on the analysis" || echo "Not found"

echo "AFTER:"
cat /tmp/after_fix.json | jq '.answer' | wc -c
cat /tmp/after_fix.json | jq '.answer' | grep -c "Based on the analysis" || echo "Not found"
```

### 4. Regression Testing

```bash
# Ensure existing tests still pass
make test-unit-fast
make test-integration
```

---

## Rollback Plan

### If Phase 1 Fails

```bash
# Revert quick fix
git reset --hard HEAD~1

# Or revert specific files
git checkout HEAD~1 -- backend/rag_solution/services/chain_of_thought_service.py
git checkout HEAD~1 -- backend/rag_solution/services/answer_synthesizer.py
```

### If Phase 2 Fails

```bash
# Phase 2 is additive (new files), so:
# 1. Remove new files
rm backend/rag_solution/schemas/context_types.py
rm backend/rag_solution/services/context_adapters.py

# 2. Revert service changes
git checkout HEAD~1 -- backend/rag_solution/services/chain_of_thought_service.py
git checkout HEAD~1 -- backend/rag_solution/services/search_service.py

# 3. System still has Phase 1 fix (quick fix is still working)
```

### Emergency Rollback

```bash
# If production is broken, immediately disable CoT
# Set in .env:
COT_ENABLED=false

# Restart backend
make local-dev-backend
```

---

## Success Criteria

### Phase 1 Success Criteria

- ✅ No "Based on the analysis of" in responses
- ✅ No "(in the context of...)" leakage
- ✅ No hallucinated conversations or instructions
- ✅ Response length appropriate (~100-300 tokens)
- ✅ All existing unit tests pass
- ✅ Integration tests pass
- ✅ Manual test queries produce clean responses

### Phase 2 Success Criteria

- ✅ All Phase 1 criteria maintained
- ✅ New type-safe schemas created
- ✅ Zero `dict[str, Any]` in new code
- ✅ Zero `isinstance()` for logic (only for validation)
- ✅ Full mypy --strict compliance
- ✅ Comprehensive unit tests (>90% coverage)
- ✅ Integration tests pass
- ✅ Backward compatibility maintained

### Overall Success Criteria

- ✅ Production-ready CoT with clean responses
- ✅ Type-safe architecture established
- ✅ Patterns documented for future work (#211-213)
- ✅ No regressions in existing functionality
- ✅ Performance impact < 5%

---

## Post-Implementation

### 1. Create Pull Request

```bash
# Push final changes
git push origin fix/issue-461-cot-reasoning-leak

# Create PR
gh pr create \
  --title "fix: Prevent CoT reasoning metadata from leaking into responses (#461)" \
  --body "$(cat <<'EOF'
## Summary

Fixes #461 - Critical issue where Chain of Thought internal reasoning was leaking into user-facing responses.

## Problem

CoT responses were producing garbage output with:
- Leaked internal reasoning: "(in the context of...)"
- Hallucinated conversations and instructions
- Bloated responses (1,716 tokens instead of ~200)

## Root Cause

Conversation metadata (entities, history) was being concatenated as plain text strings into LLM prompts, causing the LLM to echo them back.

## Solution

**Phase 1: Quick Fix (4 hours)**
- Fixed prompt formatting in `chain_of_thought_service.py`
- Removed metadata string concatenation
- Added structured prompts with clear instructions
- Removed "Based on the analysis" prefix from synthesizer

**Phase 2: Robust Solution (16 hours)**
- Created type-safe context schemas (zero `dict[str, Any]`)
- Implemented structured context architecture
- Added backward compatibility via adapters
- Comprehensive testing (unit + integration)

## Testing

- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ No metadata leakage in responses
- ✅ Response length appropriate (~100-300 tokens)
- ✅ Backward compatible with existing code

## Files Changed

### Phase 1
- `backend/rag_solution/services/chain_of_thought_service.py`
- `backend/rag_solution/services/answer_synthesizer.py`
- `backend/test_cot_fix.py` (test script)

### Phase 2
- `backend/rag_solution/schemas/context_types.py` (NEW)
- `backend/rag_solution/services/context_adapters.py` (NEW)
- `backend/tests/unit/test_context_types.py` (NEW)
- `backend/tests/integration/test_cot_structured_context.py` (NEW)
- Updated: `chain_of_thought_service.py`, `search_service.py`

## Benefits

1. **Immediate**: Production-ready CoT with clean responses
2. **Long-term**: Type-safe architecture establishes patterns for #211-213
3. **Maintainability**: Zero `dict[str, Any]`, full IDE support
4. **Quality**: Prevents metadata leakage by design

## Documentation

- Architecture analysis: `backend/ARCHITECTURE_ANALYSIS_COT_METADATA.md`
- Root cause analysis: `backend/ISSUE_461_ROOT_CAUSE_ANALYSIS.md`
- Strict typing guidelines: `docs/development/backend/strict-typing-guidelines.md`
EOF
)" \
  --base main \
  --head fix/issue-461-cot-reasoning-leak
```

### 2. Monitor Deployment

```bash
# After merge, monitor production
make logs | grep -i "cot\|reasoning"

# Check response quality
curl -X POST http://localhost:8000/api/search ... | jq '.answer' | wc -c
```

### 3. Update Documentation

Update `CLAUDE.md`:

```markdown
## Recent Changes

### Issue #461 Fixed (2025-10-21)
- ✅ Fixed CoT reasoning metadata leakage
- ✅ Implemented type-safe structured context
- ✅ Established strict typing patterns
- 📚 See: docs/development/backend/strict-typing-guidelines.md
```

### 4. Close Issue

```bash
# After PR merged and verified in production
gh issue close 461 --comment "Fixed in PR #XXX. CoT responses now clean with no metadata leakage. Type-safe architecture implemented."
```

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Quick Fix** | 4 hours | Production-ready CoT |
| Step 1.1: Fix context builder | 1 hour | No metadata concatenation |
| Step 1.2: Fix LLM prompt | 1 hour | Structured prompt |
| Step 1.3: Fix synthesizer | 1 hour | No "Based on" prefix |
| Step 1.4: Integration testing | 1 hour | Verified no leakage |
| **Phase 2: Robust Solution** | 16 hours | Type-safe architecture |
| Step 2.1: Create types | 4 hours | context_types.py |
| Step 2.2: Refactor CoT service | 6 hours | Structured context |
| Step 2.3: Update search service | 3 hours | Pipeline integration |
| Step 2.4: Testing | 3 hours | Unit + integration tests |
| **Total** | **20 hours** | **Production + Foundation** |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Phase 1 breaks existing tests | Medium | High | Run full test suite before commit |
| Phase 2 introduces regressions | Low | Medium | Maintain backward compatibility |
| Performance degradation | Low | Medium | Benchmark before/after |
| Mypy strict violations | Medium | Low | Fix incrementally, use # type: ignore sparingly |
| Merge conflicts | Low | Low | Frequent rebases with main |

---

## Notes

### Why Two Phases?

1. **Phase 1 (Quick Fix)**: Unblocks production immediately (4 hours)
2. **Phase 2 (Robust)**: Establishes foundation for #211-213 (16 hours)

### Can I Stop After Phase 1?

**Yes**, but Phase 2 is highly recommended because:
- Prevents future metadata leakage issues
- Establishes type safety patterns
- Makes future refactoring easier (#211-213)
- Improves developer experience (IDE support)

### Backward Compatibility

Both phases maintain backward compatibility:
- Phase 1: No API changes, only internal fixes
- Phase 2: New methods added, old methods kept with adapters

---

## Questions?

- **Architecture details**: See `backend/ARCHITECTURE_ANALYSIS_COT_METADATA.md`
- **Root cause trace**: See `backend/ISSUE_461_ROOT_CAUSE_ANALYSIS.md`
- **Type safety rules**: See `docs/development/backend/strict-typing-guidelines.md`
- **GitHub issue**: https://github.com/manavgup/rag_modulo/issues/461
