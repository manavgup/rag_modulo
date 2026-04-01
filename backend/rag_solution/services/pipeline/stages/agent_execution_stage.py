"""
Agent execution stage for search pipeline.

This stage orchestrates the execution of configured agents at the appropriate
pipeline points. It integrates with the AgentExecutorService to run agents
at three stages:
- Pre-Search: Query enhancement agents (run before retrieval)
- Post-Search: Result enhancement agents (run after retrieval, before generation)
- Response: Artifact generation agents (run after generation)

Reference: GitHub Issue #697
"""

from typing import Any

from sqlalchemy.orm import Session

from core.config import Settings
from core.logging_utils import get_logger
from rag_solution.schemas.agent_config_schema import AgentStage
from rag_solution.services.agent_executor_service import AgentExecutorService
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.agent_execution")


class PreSearchAgentStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Execute pre-search agents for query enhancement.

    This stage runs agents that can modify the query before retrieval:
    - Query expanders
    - Language detectors/translators
    - Acronym resolvers
    - Intent classifiers

    Agents are executed sequentially by priority.
    """

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        """
        Initialize the pre-search agent stage.

        Args:
            db: Database session
            settings: Application settings
        """
        super().__init__("PreSearchAgents")
        self.db = db
        self.settings = settings
        self._executor: AgentExecutorService | None = None

    @property
    def executor(self) -> AgentExecutorService:
        """Lazy initialization of agent executor service."""
        if self._executor is None:
            self._executor = AgentExecutorService(self.db, self.settings)
        return self._executor

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute pre-search agents.

        Args:
            context: Current search context

        Returns:
            StageResult with potentially modified query
        """
        self._log_stage_start(context)

        try:
            # Check if collection has any pre-search agents
            if not self.executor.has_agents_for_collection(context.collection_id):
                logger.debug("No agents configured for collection %s", context.collection_id)
                return StageResult(success=True, context=context)

            # Build agent context
            agent_context_dict = {
                "search_input": context.search_input.model_dump(),
                "collection_id": context.collection_id,
                "user_id": context.user_id,
                "stage": AgentStage.PRE_SEARCH,
                "query": context.search_input.question,
                "query_results": [],
                "previous_results": [],
                "config": {},
                "metadata": context.metadata,
            }

            from rag_solution.schemas.agent_config_schema import AgentContext as SchemaAgentContext

            agent_context = SchemaAgentContext(**agent_context_dict)

            # Execute pre-search agents
            modified_query, results = await self.executor.execute_pre_search_agents(
                context.collection_id,
                agent_context,
            )

            # Update context with modified query if changed
            if modified_query and modified_query != context.search_input.question:
                context.rewritten_query = modified_query
                logger.info("Query modified by pre-search agents: '%s'", modified_query[:100])

            # Initialize or update execution summary
            if context.agent_execution_summary is None:
                from rag_solution.schemas.agent_config_schema import AgentExecutionSummary

                context.agent_execution_summary = AgentExecutionSummary()

            context.agent_execution_summary.pre_search_results = results

            # Update counts
            for result in results:
                context.agent_execution_summary.total_agents += 1
                if result.status.value == "success":
                    context.agent_execution_summary.successful += 1
                elif result.status.value in ("failed", "timeout"):
                    context.agent_execution_summary.failed += 1
                else:
                    context.agent_execution_summary.skipped += 1

            context.add_metadata(
                "pre_search_agents",
                {
                    "agents_executed": len(results),
                    "query_modified": modified_query != context.search_input.question,
                },
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Log but don't fail pipeline for agent errors
            logger.exception("Pre-search agent stage failed: %s", e)
            # Return success to allow pipeline to continue
            return StageResult(success=True, context=context, error=str(e))


class PostSearchAgentStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Execute post-search agents for result enhancement.

    This stage runs agents that can modify the retrieved results:
    - Re-rankers
    - Deduplicators
    - External enrichers
    - PII redactors

    Agents are executed sequentially by priority.
    """

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        """
        Initialize the post-search agent stage.

        Args:
            db: Database session
            settings: Application settings
        """
        super().__init__("PostSearchAgents")
        self.db = db
        self.settings = settings
        self._executor: AgentExecutorService | None = None

    @property
    def executor(self) -> AgentExecutorService:
        """Lazy initialization of agent executor service."""
        if self._executor is None:
            self._executor = AgentExecutorService(self.db, self.settings)
        return self._executor

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute post-search agents.

        Args:
            context: Current search context with query_results

        Returns:
            StageResult with potentially modified results
        """
        self._log_stage_start(context)

        try:
            # Check if collection has any post-search agents
            if not self.executor.has_agents_for_collection(context.collection_id):
                logger.debug("No agents configured for collection %s", context.collection_id)
                return StageResult(success=True, context=context)

            # Convert QueryResults to dicts for agent processing
            query_results_dicts = [
                {
                    "chunk_id": r.chunk.id if r.chunk else None,
                    "document_id": r.document_id,
                    "score": r.score,
                    "text": r.chunk.text if r.chunk else "",
                    "metadata": r.chunk.metadata if r.chunk else {},
                }
                for r in context.query_results
            ]

            # Build agent context
            agent_context_dict = {
                "search_input": context.search_input.model_dump(),
                "collection_id": context.collection_id,
                "user_id": context.user_id,
                "stage": AgentStage.POST_SEARCH,
                "query": context.rewritten_query or context.search_input.question,
                "query_results": query_results_dicts,
                "previous_results": [],
                "config": {},
                "metadata": context.metadata,
            }

            from rag_solution.schemas.agent_config_schema import AgentContext as SchemaAgentContext

            agent_context = SchemaAgentContext(**agent_context_dict)

            # Execute post-search agents
            modified_results, results = await self.executor.execute_post_search_agents(
                context.collection_id,
                agent_context,
                query_results_dicts,
            )

            # Note: Modified results would need conversion back to QueryResult objects
            # For now, agents can modify scores/order but not the structure
            # A future enhancement could allow full result modification

            # Initialize or update execution summary
            if context.agent_execution_summary is None:
                from rag_solution.schemas.agent_config_schema import AgentExecutionSummary

                context.agent_execution_summary = AgentExecutionSummary()

            context.agent_execution_summary.post_search_results = results

            # Update counts
            for result in results:
                context.agent_execution_summary.total_agents += 1
                if result.status.value == "success":
                    context.agent_execution_summary.successful += 1
                elif result.status.value in ("failed", "timeout"):
                    context.agent_execution_summary.failed += 1
                else:
                    context.agent_execution_summary.skipped += 1

            context.add_metadata(
                "post_search_agents",
                {
                    "agents_executed": len(results),
                    "results_modified": len(modified_results) != len(query_results_dicts),
                },
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Log but don't fail pipeline for agent errors
            logger.exception("Post-search agent stage failed: %s", e)
            return StageResult(success=True, context=context, error=str(e))


class ResponseAgentStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Execute response agents for artifact generation.

    This stage runs agents that generate artifacts from the search results:
    - PowerPoint generators
    - PDF report generators
    - Chart generators
    - Audio summary generators

    Agents are executed in parallel since they don't depend on each other.
    """

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        """
        Initialize the response agent stage.

        Args:
            db: Database session
            settings: Application settings
        """
        super().__init__("ResponseAgents")
        self.db = db
        self.settings = settings
        self._executor: AgentExecutorService | None = None

    @property
    def executor(self) -> AgentExecutorService:
        """Lazy initialization of agent executor service."""
        if self._executor is None:
            self._executor = AgentExecutorService(self.db, self.settings)
        return self._executor

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute response agents for artifact generation.

        Args:
            context: Current search context with generated answer

        Returns:
            StageResult with generated artifacts
        """
        self._log_stage_start(context)

        try:
            # Check if collection has any response agents
            if not self.executor.has_agents_for_collection(context.collection_id):
                logger.debug("No agents configured for collection %s", context.collection_id)
                return StageResult(success=True, context=context)

            # Convert QueryResults to dicts for agent processing
            query_results_dicts = [
                {
                    "chunk_id": r.chunk.id if r.chunk else None,
                    "document_id": r.document_id,
                    "score": r.score,
                    "text": r.chunk.text if r.chunk else "",
                    "metadata": r.chunk.metadata if r.chunk else {},
                }
                for r in context.query_results
            ]

            # Build agent context with full search data
            agent_context_dict = {
                "search_input": context.search_input.model_dump(),
                "collection_id": context.collection_id,
                "user_id": context.user_id,
                "stage": AgentStage.RESPONSE,
                "query": context.rewritten_query or context.search_input.question,
                "query_results": query_results_dicts,
                "previous_results": [],
                "config": {},
                "metadata": {
                    **context.metadata,
                    "generated_answer": context.generated_answer,
                    "document_count": len(context.document_metadata),
                },
            }

            from rag_solution.schemas.agent_config_schema import AgentContext as SchemaAgentContext

            agent_context = SchemaAgentContext(**agent_context_dict)

            # Execute response agents (in parallel)
            artifacts, results = await self.executor.execute_response_agents(
                context.collection_id,
                agent_context,
            )

            # Update context with artifacts
            context.agent_artifacts = artifacts

            # Initialize or update execution summary
            if context.agent_execution_summary is None:
                from rag_solution.schemas.agent_config_schema import AgentExecutionSummary

                context.agent_execution_summary = AgentExecutionSummary()

            context.agent_execution_summary.response_results = results
            context.agent_execution_summary.artifacts = artifacts

            # Update counts
            for result in results:
                context.agent_execution_summary.total_agents += 1
                if result.status.value == "success":
                    context.agent_execution_summary.successful += 1
                elif result.status.value in ("failed", "timeout"):
                    context.agent_execution_summary.failed += 1
                else:
                    context.agent_execution_summary.skipped += 1

            # Calculate total execution time
            if context.agent_execution_summary:
                total_time = sum(
                    r.execution_time_ms
                    for r in (
                        context.agent_execution_summary.pre_search_results
                        + context.agent_execution_summary.post_search_results
                        + context.agent_execution_summary.response_results
                    )
                )
                context.agent_execution_summary.total_execution_time_ms = total_time

            context.add_metadata(
                "response_agents",
                {
                    "agents_executed": len(results),
                    "artifacts_generated": len(artifacts),
                },
            )

            logger.info(
                "Response agents generated %d artifacts from %d agents",
                len(artifacts),
                len(results),
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Log but don't fail pipeline for agent errors
            logger.exception("Response agent stage failed: %s", e)
            return StageResult(success=True, context=context, error=str(e))
