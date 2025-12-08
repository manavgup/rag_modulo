"""Agent executor service for search pipeline hooks.

This module provides the AgentExecutorService that orchestrates agent execution
at the three stages of the search pipeline with circuit breaker pattern for
failure isolation.

The 3-stage pipeline:
- Stage 1: Pre-Search Agents (sequential by priority) - Query enhancement
- Stage 2: Post-Search Agents (sequential by priority) - Result enhancement
- Stage 3: Response Agents (parallel execution) - Artifact generation

Reference: GitHub Issue #697
"""

from __future__ import annotations

import asyncio
import importlib
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from core.logging_utils import get_logger
from rag_solution.models.agent_config import AgentConfig, AgentStage, CollectionAgent
from rag_solution.schemas.agent_config_schema import (
    AgentArtifact,
    AgentContext,
    AgentExecutionStatus,
    AgentExecutionSummary,
    AgentResult,
    AgentStage as SchemaAgentStage,
)

if TYPE_CHECKING:
    from vectordbs.data_types import QueryResult

logger = get_logger("services.agent_executor")


# ============================================================================
# Circuit Breaker Implementation
# ============================================================================


@dataclass
class CircuitBreakerState:
    """State tracking for a circuit breaker.

    Attributes:
        failure_count: Number of consecutive failures
        last_failure_time: Timestamp of last failure
        state: Current state (closed, open, half_open)
        success_count_in_half_open: Successful calls in half-open state
    """

    failure_count: int = 0
    last_failure_time: float = 0.0
    state: str = "closed"  # closed, open, half_open
    success_count_in_half_open: int = 0


class CircuitBreaker:
    """Circuit breaker for isolating agent failures.

    Implements the circuit breaker pattern:
    - CLOSED: Normal operation, failures increment counter
    - OPEN: Requests fail fast, no execution
    - HALF_OPEN: Limited requests allowed to test recovery

    Attributes:
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        half_open_max_calls: Max calls allowed in half-open state
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ) -> None:
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Failures before circuit opens
            recovery_timeout: Seconds before half-open transition
            half_open_max_calls: Calls to allow in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._states: dict[str, CircuitBreakerState] = defaultdict(CircuitBreakerState)

    def _get_state(self, circuit_id: str) -> CircuitBreakerState:
        """Get or create state for a circuit."""
        return self._states[circuit_id]

    def is_open(self, circuit_id: str) -> bool:
        """Check if circuit is open (blocking requests).

        Args:
            circuit_id: Identifier for the circuit (usually agent_config_id)

        Returns:
            True if circuit is open and blocking requests
        """
        state = self._get_state(circuit_id)

        if state.state == "closed":
            return False

        if state.state == "open":
            # Check if recovery timeout has passed
            if time.time() - state.last_failure_time >= self.recovery_timeout:
                state.state = "half_open"
                state.success_count_in_half_open = 0
                logger.info("Circuit %s transitioning to half-open", circuit_id)
                return False
            return True

        # half_open state - allow limited requests
        return False

    def record_success(self, circuit_id: str) -> None:
        """Record a successful execution.

        Args:
            circuit_id: Identifier for the circuit
        """
        state = self._get_state(circuit_id)

        if state.state == "half_open":
            state.success_count_in_half_open += 1
            if state.success_count_in_half_open >= self.half_open_max_calls:
                # Reset to closed state
                state.state = "closed"
                state.failure_count = 0
                state.success_count_in_half_open = 0
                logger.info("Circuit %s closed after successful recovery", circuit_id)
        elif state.state == "closed":
            # Reset failure count on success
            state.failure_count = 0

    def record_failure(self, circuit_id: str) -> None:
        """Record a failed execution.

        Args:
            circuit_id: Identifier for the circuit
        """
        state = self._get_state(circuit_id)
        state.failure_count += 1
        state.last_failure_time = time.time()

        if state.state == "half_open":
            # Any failure in half-open reopens the circuit
            state.state = "open"
            logger.warning("Circuit %s reopened after half-open failure", circuit_id)
        elif state.failure_count >= self.failure_threshold:
            state.state = "open"
            logger.warning("Circuit %s opened after %d failures", circuit_id, state.failure_count)

    def get_state(self, circuit_id: str) -> str:
        """Get the current state of a circuit.

        Args:
            circuit_id: Identifier for the circuit

        Returns:
            Current state: "closed", "open", or "half_open"
        """
        return self._get_state(circuit_id).state


# ============================================================================
# Base Agent Handler
# ============================================================================


class BaseAgentHandler(ABC):
    """Abstract base class for agent handlers.

    All agent implementations must inherit from this class and implement
    the execute method.
    """

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent with the given context.

        Args:
            context: Execution context with search data

        Returns:
            Result of the agent execution
        """

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Get the agent type identifier."""


# ============================================================================
# Agent Executor Service
# ============================================================================


class AgentExecutorService:
    """Service for executing agents at pipeline stages.

    This service manages the execution of agents configured for a collection
    at the three pipeline stages: pre-search, post-search, and response.

    Key features:
    - Sequential execution for pre-search and post-search (by priority)
    - Parallel execution for response agents
    - Circuit breaker for failure isolation
    - Timeout handling
    - Retry logic

    Attributes:
        db: Database session
        settings: Application settings
        circuit_breaker: Circuit breaker instance
    """

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        """Initialize the agent executor service.

        Args:
            db: Database session
            settings: Optional application settings
        """
        self.db = db
        self.settings = settings or Settings()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60.0,
            half_open_max_calls=3,
        )
        self._handler_cache: dict[str, type[BaseAgentHandler]] = {}

    def _get_collection_agents(
        self,
        collection_id: UUID4,
        stage: AgentStage,
    ) -> list[CollectionAgent]:
        """Get enabled agents for a collection at a specific stage.

        Args:
            collection_id: Collection UUID
            stage: Pipeline stage to filter by

        Returns:
            List of CollectionAgent associations ordered by priority
        """
        return (
            self.db.query(CollectionAgent)
            .join(AgentConfig)
            .filter(
                CollectionAgent.collection_id == collection_id,
                CollectionAgent.enabled.is_(True),
                AgentConfig.stage == stage.value,
                AgentConfig.status == "active",
            )
            .order_by(CollectionAgent.priority)
            .all()
        )

    def _load_handler_class(self, agent_config: AgentConfig) -> type[BaseAgentHandler] | None:
        """Dynamically load a handler class.

        Args:
            agent_config: Agent configuration with handler info

        Returns:
            Handler class or None if loading fails
        """
        cache_key = f"{agent_config.handler_module}:{agent_config.handler_class}"

        if cache_key in self._handler_cache:
            return self._handler_cache[cache_key]

        try:
            module = importlib.import_module(agent_config.handler_module)
            handler_class = getattr(module, agent_config.handler_class)

            if not issubclass(handler_class, BaseAgentHandler):
                logger.error(
                    "Handler %s is not a subclass of BaseAgentHandler",
                    cache_key,
                )
                return None

            self._handler_cache[cache_key] = handler_class
            return handler_class

        except (ImportError, AttributeError) as e:
            logger.error("Failed to load handler %s: %s", cache_key, e)
            return None

    async def _execute_single_agent(
        self,
        collection_agent: CollectionAgent,
        context: AgentContext,
    ) -> AgentResult:
        """Execute a single agent with timeout and error handling.

        Args:
            collection_agent: Collection-agent association
            context: Execution context

        Returns:
            Agent result
        """
        agent_config = collection_agent.agent_config
        circuit_id = str(agent_config.id)
        start_time = time.time()

        # Check circuit breaker
        if self.circuit_breaker.is_open(circuit_id):
            logger.warning("Circuit open for agent %s, skipping", agent_config.name)
            return AgentResult(
                agent_config_id=agent_config.id,
                agent_name=agent_config.name,
                agent_type=agent_config.agent_type,
                stage=agent_config.stage,
                status=AgentExecutionStatus.CIRCUIT_OPEN,
                execution_time_ms=0.0,
                error_message="Circuit breaker is open",
            )

        # Merge configuration
        merged_config = collection_agent.get_merged_config()
        context.config = merged_config

        # Load handler
        handler_class = self._load_handler_class(agent_config)
        if handler_class is None:
            return AgentResult(
                agent_config_id=agent_config.id,
                agent_name=agent_config.name,
                agent_type=agent_config.agent_type,
                stage=agent_config.stage,
                status=AgentExecutionStatus.FAILED,
                execution_time_ms=(time.time() - start_time) * 1000,
                error_message="Failed to load handler",
            )

        # Execute with retry and timeout
        retries = 0
        max_retries = agent_config.max_retries
        last_error = None

        while retries <= max_retries:
            try:
                handler = handler_class()
                result = await asyncio.wait_for(
                    handler.execute(context),
                    timeout=agent_config.timeout_seconds,
                )

                # Record success
                self.circuit_breaker.record_success(circuit_id)

                execution_time_ms = (time.time() - start_time) * 1000
                result.execution_time_ms = execution_time_ms

                logger.info(
                    "Agent %s executed successfully in %.2fms",
                    agent_config.name,
                    execution_time_ms,
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {agent_config.timeout_seconds}s"
                retries += 1
                logger.warning(
                    "Agent %s timed out (attempt %d/%d)",
                    agent_config.name,
                    retries,
                    max_retries + 1,
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: We need to catch all exceptions to prevent pipeline failure
                last_error = str(e)
                retries += 1
                logger.warning(
                    "Agent %s failed (attempt %d/%d): %s",
                    agent_config.name,
                    retries,
                    max_retries + 1,
                    e,
                )

        # All retries exhausted
        self.circuit_breaker.record_failure(circuit_id)
        execution_time_ms = (time.time() - start_time) * 1000

        return AgentResult(
            agent_config_id=agent_config.id,
            agent_name=agent_config.name,
            agent_type=agent_config.agent_type,
            stage=agent_config.stage,
            status=AgentExecutionStatus.TIMEOUT if "Timeout" in str(last_error) else AgentExecutionStatus.FAILED,
            execution_time_ms=execution_time_ms,
            error_message=last_error,
        )

    async def execute_pre_search_agents(
        self,
        collection_id: UUID4,
        context: AgentContext,
    ) -> tuple[str, list[AgentResult]]:
        """Execute pre-search agents sequentially by priority.

        Pre-search agents can modify the query before retrieval.
        Each agent receives the modified query from the previous agent.

        Args:
            collection_id: Collection UUID
            context: Execution context

        Returns:
            Tuple of (modified_query, list of results)
        """
        logger.info("Executing pre-search agents for collection %s", collection_id)

        agents = self._get_collection_agents(collection_id, AgentStage.PRE_SEARCH)
        results: list[AgentResult] = []
        current_query = context.query

        for collection_agent in agents:
            # Update context with current query
            context.query = current_query
            context.previous_results = results.copy()

            result = await self._execute_single_agent(collection_agent, context)
            results.append(result)

            # If successful and query was modified, use it
            if result.status == AgentExecutionStatus.SUCCESS and result.modified_query:
                current_query = result.modified_query
                logger.info(
                    "Query modified by %s: '%s' -> '%s'",
                    result.agent_name,
                    context.search_input.get("question", ""),
                    current_query,
                )

        logger.info("Pre-search stage completed: %d agents executed", len(results))
        return current_query, results

    async def execute_post_search_agents(
        self,
        collection_id: UUID4,
        context: AgentContext,
        query_results: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[AgentResult]]:
        """Execute post-search agents sequentially by priority.

        Post-search agents can modify, rerank, or filter the retrieved results.
        Each agent receives the modified results from the previous agent.

        Args:
            collection_id: Collection UUID
            context: Execution context
            query_results: Retrieved documents

        Returns:
            Tuple of (modified_results, list of results)
        """
        logger.info("Executing post-search agents for collection %s", collection_id)

        agents = self._get_collection_agents(collection_id, AgentStage.POST_SEARCH)
        results: list[AgentResult] = []
        current_results = query_results

        for collection_agent in agents:
            # Update context with current results
            context.query_results = current_results
            context.previous_results = results.copy()

            result = await self._execute_single_agent(collection_agent, context)
            results.append(result)

            # If successful and results were modified, use them
            if result.status == AgentExecutionStatus.SUCCESS and result.modified_results:
                current_results = result.modified_results
                logger.info(
                    "Results modified by %s: %d -> %d items",
                    result.agent_name,
                    len(query_results),
                    len(current_results),
                )

        logger.info("Post-search stage completed: %d agents executed", len(results))
        return current_results, results

    async def execute_response_agents(
        self,
        collection_id: UUID4,
        context: AgentContext,
    ) -> tuple[list[AgentArtifact], list[AgentResult]]:
        """Execute response agents in parallel.

        Response agents generate artifacts (PDFs, PowerPoints, charts, etc.)
        and run in parallel since they don't depend on each other.

        Args:
            collection_id: Collection UUID
            context: Execution context

        Returns:
            Tuple of (artifacts, list of results)
        """
        logger.info("Executing response agents for collection %s", collection_id)

        agents = self._get_collection_agents(collection_id, AgentStage.RESPONSE)

        if not agents:
            return [], []

        # Execute all response agents in parallel
        tasks = [self._execute_single_agent(agent, context) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_results: list[AgentResult] = []
        all_artifacts: list[AgentArtifact] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle exception from gather
                agent_config = agents[i].agent_config
                agent_results.append(
                    AgentResult(
                        agent_config_id=agent_config.id,
                        agent_name=agent_config.name,
                        agent_type=agent_config.agent_type,
                        stage=agent_config.stage,
                        status=AgentExecutionStatus.FAILED,
                        execution_time_ms=0.0,
                        error_message=str(result),
                    )
                )
            else:
                agent_results.append(result)
                if result.artifacts:
                    all_artifacts.extend(result.artifacts)

        logger.info(
            "Response stage completed: %d agents executed, %d artifacts generated",
            len(results),
            len(all_artifacts),
        )
        return all_artifacts, agent_results

    async def execute_all_stages(
        self,
        collection_id: UUID4,
        search_input: dict[str, Any],
        user_id: UUID4,
        initial_query: str,
        query_results: list[dict[str, Any]],
    ) -> AgentExecutionSummary:
        """Execute all agent stages for a search request.

        This is the main entry point for agent execution during search.
        It orchestrates the three stages and collects results.

        Args:
            collection_id: Collection UUID
            search_input: Original search request
            user_id: User UUID
            initial_query: Initial search query
            query_results: Retrieved documents (as dicts)

        Returns:
            Summary of all agent executions
        """
        logger.info("Starting agent execution for collection %s", collection_id)
        start_time = time.time()

        summary = AgentExecutionSummary()

        # Create initial context
        context = AgentContext(
            search_input=search_input,
            collection_id=collection_id,
            user_id=user_id,
            stage=SchemaAgentStage.PRE_SEARCH,
            query=initial_query,
        )

        # Stage 1: Pre-search agents
        try:
            modified_query, pre_results = await self.execute_pre_search_agents(
                collection_id, context.model_copy(deep=True)
            )
            summary.pre_search_results = pre_results
            context.query = modified_query

            # Update counts
            for result in pre_results:
                summary.total_agents += 1
                if result.status == AgentExecutionStatus.SUCCESS:
                    summary.successful += 1
                elif result.status in (AgentExecutionStatus.FAILED, AgentExecutionStatus.TIMEOUT):
                    summary.failed += 1
                else:
                    summary.skipped += 1

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Log but don't fail search
            logger.exception("Pre-search stage failed: %s", e)

        # Stage 2: Post-search agents
        try:
            context.stage = SchemaAgentStage.POST_SEARCH
            context.query_results = query_results

            modified_results, post_results = await self.execute_post_search_agents(
                collection_id, context.model_copy(deep=True), query_results
            )
            summary.post_search_results = post_results

            # Update counts
            for result in post_results:
                summary.total_agents += 1
                if result.status == AgentExecutionStatus.SUCCESS:
                    summary.successful += 1
                elif result.status in (AgentExecutionStatus.FAILED, AgentExecutionStatus.TIMEOUT):
                    summary.failed += 1
                else:
                    summary.skipped += 1

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Log but don't fail search
            logger.exception("Post-search stage failed: %s", e)

        # Stage 3: Response agents
        try:
            context.stage = SchemaAgentStage.RESPONSE

            artifacts, response_results = await self.execute_response_agents(
                collection_id, context.model_copy(deep=True)
            )
            summary.response_results = response_results
            summary.artifacts = artifacts

            # Update counts
            for result in response_results:
                summary.total_agents += 1
                if result.status == AgentExecutionStatus.SUCCESS:
                    summary.successful += 1
                elif result.status in (AgentExecutionStatus.FAILED, AgentExecutionStatus.TIMEOUT):
                    summary.failed += 1
                else:
                    summary.skipped += 1

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Log but don't fail search
            logger.exception("Response stage failed: %s", e)

        summary.total_execution_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Agent execution completed: %d total, %d successful, %d failed, %d skipped in %.2fms",
            summary.total_agents,
            summary.successful,
            summary.failed,
            summary.skipped,
            summary.total_execution_time_ms,
        )

        return summary

    def has_agents_for_collection(self, collection_id: UUID4) -> bool:
        """Check if a collection has any enabled agents.

        Args:
            collection_id: Collection UUID

        Returns:
            True if collection has enabled agents
        """
        count = (
            self.db.query(CollectionAgent)
            .filter(
                CollectionAgent.collection_id == collection_id,
                CollectionAgent.enabled.is_(True),
            )
            .count()
        )
        return count > 0

    def get_collection_agent_summary(self, collection_id: UUID4) -> dict[str, int]:
        """Get a summary of agents for a collection by stage.

        Args:
            collection_id: Collection UUID

        Returns:
            Dict with counts per stage
        """
        summary = {
            "pre_search": 0,
            "post_search": 0,
            "response": 0,
            "total": 0,
        }

        for stage in AgentStage:
            count = len(self._get_collection_agents(collection_id, stage))
            summary[stage.value] = count
            summary["total"] += count

        return summary
