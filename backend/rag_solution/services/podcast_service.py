"""
Podcast generation service.

Orchestrates podcast generation from document collections:
1. Validates request (collection exists, sufficient documents, concurrency limits)
2. Creates podcast record in database (status: QUEUED)
3. Schedules background processing (FastAPI BackgroundTasks)
4. Background task:
   - Retrieves content via RAG pipeline
   - Generates Q&A dialogue script via LLM
   - Parses script into turns
   - Generates multi-voice audio via TTS
   - Stores audio file
   - Updates podcast status (COMPLETED/FAILED)
"""

import logging

from core.config import get_settings
from core.custom_exceptions import NotFoundError, ValidationError
from fastapi import BackgroundTasks, HTTPException
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from rag_solution.generation.audio.factory import AudioProviderFactory
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.repository.podcast_repository import PodcastRepository
from rag_solution.schemas.podcast_schema import (
    AudioFormat,
    PodcastDuration,
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastListResponse,
    PodcastStatus,
)
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.search_service import SearchService
from rag_solution.services.storage.audio_storage import AudioStorageBase, LocalFileStorage
from rag_solution.utils.script_parser import PodcastScriptParser

logger = logging.getLogger(__name__)


class PodcastService:
    """Service for podcast generation and management."""

    # Default podcast prompt template
    PODCAST_SCRIPT_PROMPT = """You are a professional podcast script writer. Create an engaging podcast dialogue between a HOST and an EXPERT discussing the following content.

Content from documents:
{rag_results}

Duration: {duration_minutes} minutes (approximately {word_count} words at 150 words/minute)

Format your script as a natural conversation with these guidelines:

1. **Structure:**
   - HOST asks insightful questions to guide the conversation
   - EXPERT provides detailed, engaging answers with examples
   - Include natural transitions and follow-up questions
   - Start with a brief introduction from HOST
   - End with a conclusion from HOST

2. **Script Format (IMPORTANT):**
   Use this exact format for each turn:

   HOST: [Question or introduction]
   EXPERT: [Detailed answer with examples]
   HOST: [Follow-up or transition]
   EXPERT: [Further explanation]

3. **Content Guidelines:**
   - Make it conversational and engaging
   - Use examples and analogies to clarify complex topics
   - Keep language accessible but informative
   - Include natural pauses and transitions

Generate the complete dialogue script now:"""

    def __init__(
        self,
        session: AsyncSession,
        collection_service: CollectionService,
        search_service: SearchService,
    ):
        """
        Initialize podcast service.

        Args:
            session: Database session
            collection_service: Collection service for validation
            search_service: Search service for RAG content retrieval
        """
        self.session = session
        self.collection_service = collection_service
        self.search_service = search_service
        self.repository = PodcastRepository(session)
        self.settings = get_settings()

        # Initialize script parser
        self.script_parser = PodcastScriptParser(average_wpm=150)

        # Initialize audio storage
        self.audio_storage = self._create_audio_storage()

        logger.info("PodcastService initialized")

    def _create_audio_storage(self) -> AudioStorageBase:
        """Create audio storage backend based on configuration."""
        storage_backend = self.settings.podcast_storage_backend

        if storage_backend == "local":
            storage_path = self.settings.podcast_local_storage_path
            logger.info("Using local file storage: %s", storage_path)
            return LocalFileStorage(base_path=storage_path)
        else:
            # Future: MinIO, S3, R2
            raise NotImplementedError(f"Storage backend '{storage_backend}' not yet implemented")

    async def generate_podcast(
        self,
        podcast_input: PodcastGenerationInput,
        background_tasks: BackgroundTasks,
    ) -> PodcastGenerationOutput:
        """
        Generate podcast from collection (async with background processing).

        Args:
            podcast_input: Podcast generation request
            background_tasks: FastAPI BackgroundTasks for async processing

        Returns:
            PodcastGenerationOutput with QUEUED status

        Raises:
            HTTPException: If validation fails
        """
        try:
            # 1. Validate request
            await self._validate_podcast_request(podcast_input)

            # 2. Create podcast record
            podcast = await self.repository.create(
                user_id=podcast_input.user_id,
                collection_id=podcast_input.collection_id,
                duration=podcast_input.duration.value,
                voice_settings=podcast_input.voice_settings.model_dump(),
                host_voice=podcast_input.host_voice,
                expert_voice=podcast_input.expert_voice,
                audio_format=podcast_input.format.value,
                title=podcast_input.title,
            )

            # 3. Schedule background processing
            background_tasks.add_task(
                self._process_podcast_generation,
                podcast_id=podcast.podcast_id,
                podcast_input=podcast_input,
            )

            logger.info(
                "Queued podcast generation: id=%s, user=%s, collection=%s",
                podcast.podcast_id,
                podcast_input.user_id,
                podcast_input.collection_id,
            )

            # 4. Return immediate response
            return self.repository.to_schema(podcast)

        except (NotFoundError, ValidationError) as e:
            logger.error("Validation failed: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.exception("Failed to queue podcast generation: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue podcast generation: {e}",
            ) from e

    async def _validate_podcast_request(self, podcast_input: PodcastGenerationInput) -> None:
        """
        Validate podcast generation request.

        Args:
            podcast_input: Request to validate

        Raises:
            NotFoundError: If collection not found
            ValidationError: If validation fails
        """
        # Check collection exists and user has access
        collection = await self.collection_service.get_by_id(  # type: ignore[attr-defined]
            collection_id=podcast_input.collection_id,
            user_id=podcast_input.user_id,
        )

        if not collection:
            raise NotFoundError(  # type: ignore[call-arg]
                f"Collection {podcast_input.collection_id} not found or not accessible"
            )

        # Check collection has sufficient documents
        doc_count = await self.collection_service.count_documents(  # type: ignore[attr-defined]
            podcast_input.collection_id
        )
        min_docs = self.settings.podcast_min_documents

        if doc_count < min_docs:
            raise ValidationError(
                f"Collection has {doc_count} documents, but {min_docs} required for podcast generation"
            )

        # Check user's active podcast limit
        active_count = await self.repository.count_active_for_user(podcast_input.user_id)
        max_concurrent = self.settings.podcast_max_concurrent_per_user

        if active_count >= max_concurrent:
            raise ValidationError(
                f"User has {active_count} active podcasts, maximum {max_concurrent} allowed. "
                "Please wait for current podcasts to complete."
            )

        logger.debug(
            "Validation passed: collection=%s, documents=%d, active_podcasts=%d",
            podcast_input.collection_id,
            doc_count,
            active_count,
        )

    async def _process_podcast_generation(
        self,
        podcast_id: UUID4,
        podcast_input: PodcastGenerationInput,
    ) -> None:
        """
        Background task for podcast generation.

        Args:
            podcast_id: Podcast database ID
            podcast_input: Original request input
        """
        try:
            logger.info("Starting podcast generation: %s", podcast_id)

            # Step 1: Retrieve content via RAG (10-30%)
            await self._update_progress(
                podcast_id,
                status=PodcastStatus.GENERATING,
                progress=10,
                step="retrieving_content",
            )
            rag_results = await self._retrieve_content(podcast_input)

            # Step 2: Generate script via LLM (30-40%)
            await self._update_progress(podcast_id, progress=30, step="generating_script")
            script_text = await self._generate_script(podcast_input, rag_results)

            # Step 3: Parse script into turns (40-50%)
            await self._update_progress(podcast_id, progress=40, step="parsing_turns")
            parsing_result = self.script_parser.parse(script_text)
            podcast_script = parsing_result.script

            if parsing_result.parsing_warnings:
                logger.warning(
                    "Script parsing warnings for %s: %s",
                    podcast_id,
                    parsing_result.parsing_warnings,
                )

            # Step 4: Generate audio (50-90% with per-turn tracking)
            await self._update_progress(
                podcast_id,
                progress=50,
                step="generating_audio",
                step_details={
                    "total_turns": len(podcast_script.turns),
                    "completed_turns": 0,
                },
            )
            audio_bytes = await self._generate_audio(podcast_id, podcast_script, podcast_input)

            # Step 5: Store audio (90-95%)
            await self._update_progress(podcast_id, progress=90, step="storing_audio")
            audio_url = await self._store_audio(podcast_id, podcast_input.user_id, audio_bytes, podcast_input.format)

            # Step 6: Mark complete (100%)
            await self.repository.mark_completed(
                podcast_id=podcast_id,
                audio_url=audio_url,
                transcript=script_text,
                audio_size_bytes=len(audio_bytes),
            )

            logger.info(
                "Completed podcast generation: %s, size=%d bytes, duration=%.1fs",
                podcast_id,
                len(audio_bytes),
                podcast_script.total_duration,
            )

        except Exception as e:
            logger.exception("Podcast generation failed for %s: %s", podcast_id, e)
            await self.repository.update_status(
                podcast_id=podcast_id,
                status=PodcastStatus.FAILED,
                error_message=str(e),
            )

    async def _retrieve_content(self, podcast_input: PodcastGenerationInput) -> str:
        """
        Retrieve content from collection via RAG pipeline.

        Args:
            podcast_input: Podcast request

        Returns:
            Formatted RAG results as string
        """
        # Determine top_k based on duration
        top_k_map = {
            PodcastDuration.SHORT: self.settings.podcast_retrieval_top_k_short,
            PodcastDuration.MEDIUM: self.settings.podcast_retrieval_top_k_medium,
            PodcastDuration.LONG: self.settings.podcast_retrieval_top_k_long,
            PodcastDuration.EXTENDED: self.settings.podcast_retrieval_top_k_extended,
        }
        top_k = top_k_map[podcast_input.duration]

        # Create synthetic query for comprehensive content
        synthetic_query = (
            "Provide a comprehensive overview of all key topics, main insights, "
            "important concepts, and significant information from this collection "
            "suitable for creating an educational podcast dialogue."
        )

        # Execute search
        search_input = SearchInput(
            user_id=podcast_input.user_id,
            collection_id=podcast_input.collection_id,
            question=synthetic_query,
            config_metadata={
                "top_k": top_k,
                "enable_reranking": True,
                "enable_hierarchical": True,
                "cot_enabled": False,  # Skip chain-of-thought for retrieval
            },
        )

        search_result = await self.search_service.search(search_input)

        # Format results for prompt
        formatted_results = "\n\n".join(
            [f"[Document {i+1}]: {doc.chunk_text}" for i, doc in enumerate(search_result.documents)]
        )

        logger.info(
            "Retrieved %d documents for podcast (top_k=%d)",
            len(search_result.documents),
            top_k,
        )

        return formatted_results

    async def _generate_script(self, podcast_input: PodcastGenerationInput, rag_results: str) -> str:
        """
        Generate podcast script via LLM.

        Args:
            podcast_input: Podcast request
            rag_results: Retrieved content

        Returns:
            Generated script text
        """
        # Calculate target word count
        duration_minutes_map = {
            PodcastDuration.SHORT: 5,
            PodcastDuration.MEDIUM: 15,
            PodcastDuration.LONG: 30,
            PodcastDuration.EXTENDED: 60,
        }
        duration_minutes = duration_minutes_map[podcast_input.duration]
        word_count = duration_minutes * 150  # 150 words/minute

        # Format prompt
        prompt = self.PODCAST_SCRIPT_PROMPT.format(
            rag_results=rag_results,
            duration_minutes=duration_minutes,
            word_count=word_count,
        )

        # Generate via LLM
        # TODO: Get LLM provider from user preferences
        # For now, use default provider
        llm_provider = LLMProviderFactory.create_provider(  # type: ignore[attr-defined]
            provider_name="watsonx",  # or from user config
            session=self.session,
        )

        script_text = llm_provider.generate_text(
            user_id=podcast_input.user_id,
            prompt=prompt,
        )

        logger.info(
            "Generated script: %d characters, target %d words",
            len(script_text),
            word_count,
        )

        return script_text

    async def _generate_audio(
        self,
        _podcast_id: UUID4,
        podcast_script,
        podcast_input: PodcastGenerationInput,
    ) -> bytes:
        """
        Generate audio from parsed script with progress tracking.

        Args:
            _podcast_id: Podcast ID for progress updates (reserved for future use)
            podcast_script: Parsed PodcastScript
            podcast_input: Original request

        Returns:
            Audio file bytes
        """
        # Create audio provider
        audio_provider = AudioProviderFactory.create_provider(
            provider_type=self.settings.podcast_audio_provider,
            settings=self.settings,
        )

        # Generate audio with turn-by-turn progress
        # Note: OpenAIAudioProvider handles turn iteration internally
        # We could add progress callback for more granular tracking
        audio_bytes = await audio_provider.generate_dialogue_audio(
            script=podcast_script,
            host_voice=podcast_input.host_voice,
            expert_voice=podcast_input.expert_voice,
            audio_format=podcast_input.format,
        )

        return audio_bytes

    async def _store_audio(
        self,
        podcast_id: UUID4,
        user_id: UUID4,
        audio_bytes: bytes,
        audio_format: AudioFormat,
    ) -> str:
        """
        Store audio file and return URL.

        Args:
            podcast_id: Podcast ID
            user_id: User ID
            audio_bytes: Audio file bytes
            audio_format: Audio format

        Returns:
            Audio access URL
        """
        audio_url = await self.audio_storage.store_audio(
            podcast_id=podcast_id,
            user_id=user_id,
            audio_data=audio_bytes,
            audio_format=audio_format.value,
        )

        return audio_url

    async def _update_progress(
        self,
        podcast_id: UUID4,
        progress: int,
        step: str,
        status: PodcastStatus | None = None,
        step_details: dict | None = None,
    ) -> None:
        """
        Update podcast generation progress.

        Args:
            podcast_id: Podcast ID
            progress: Progress percentage (0-100)
            step: Current step name
            status: Optional status update
            step_details: Optional step details
        """
        await self.repository.update_progress(
            podcast_id=podcast_id,
            progress_percentage=progress,
            current_step=step,
            step_details=step_details,
        )

        if status:
            await self.repository.update_status(
                podcast_id=podcast_id,
                status=status,
            )

    async def get_podcast(self, podcast_id: UUID4, user_id: UUID4) -> PodcastGenerationOutput:
        """
        Get podcast by ID with access control.

        Args:
            podcast_id: Podcast ID
            user_id: Requesting user ID

        Returns:
            PodcastGenerationOutput

        Raises:
            HTTPException: If not found or access denied
        """
        podcast = await self.repository.get_by_id(podcast_id)

        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")

        if podcast.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return self.repository.to_schema(podcast)

    async def list_user_podcasts(self, user_id: UUID4, limit: int = 100, offset: int = 0) -> PodcastListResponse:
        """
        List podcasts for user.

        Args:
            user_id: User ID
            limit: Maximum results
            offset: Pagination offset

        Returns:
            PodcastListResponse
        """
        podcasts = await self.repository.get_by_user(user_id=user_id, limit=limit, offset=offset)

        return PodcastListResponse(
            podcasts=[self.repository.to_schema(p) for p in podcasts],
            total_count=len(podcasts),
        )

    async def delete_podcast(self, podcast_id: UUID4, user_id: UUID4) -> bool:
        """
        Delete podcast with access control.

        Args:
            podcast_id: Podcast ID
            user_id: Requesting user ID

        Returns:
            True if deleted

        Raises:
            HTTPException: If not found or access denied
        """
        # Verify ownership
        podcast = await self.repository.get_by_id(podcast_id)

        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")

        if podcast.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete audio file if exists
        if podcast.audio_url:
            try:
                await self.audio_storage.delete_audio(
                    podcast_id=podcast_id,
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning("Failed to delete audio file: %s", e)

        # Delete database record
        return await self.repository.delete(podcast_id)
