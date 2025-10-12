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
from typing import Any, ClassVar

from fastapi import BackgroundTasks, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import get_settings
from core.custom_exceptions import NotFoundError, PromptTemplateNotFoundError, ValidationError
from rag_solution.generation.audio.factory import AudioProviderFactory
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.repository.podcast_repository import PodcastRepository
from rag_solution.schemas.podcast_schema import (
    AudioFormat,
    PodcastAudioGenerationInput,
    PodcastDuration,
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastListResponse,
    PodcastScriptGenerationInput,
    PodcastScriptOutput,
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

    # Language code to full name mapping
    LANGUAGE_NAMES: ClassVar[dict[str, str]] = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "nl": "Dutch",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "ar": "Arabic",
        "ru": "Russian",
        "hi": "Hindi",
    }

    # Default podcast prompt template
    # pylint: disable=line-too-long
    PODCAST_SCRIPT_PROMPT = """You are a professional podcast script writer. Create an engaging podcast dialogue between a HOST and an EXPERT in {language} language.

IMPORTANT: Generate the ENTIRE script in {language} language. All dialogue must be in {language}.

Topic/Focus: {user_topic}

Content from documents:
{rag_results}

Duration: {duration_minutes} minutes (approximately {word_count} words at 150 words/minute)

**Podcast Style:** {podcast_style}
**Target Audience:** {complexity_level}
**Language:** {language} (ALL text must be in this language)

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

3. **Style Guidelines for {podcast_style}:**
   - conversational_interview: Use Q&A format with engaging, open-ended questions. HOST should ask follow-ups and show curiosity.
   - narrative: Use storytelling approach with smooth transitions. EXPERT should weave information into a compelling narrative arc.
   - educational: Use structured learning format. Break down concepts clearly with examples. Build from basics to advanced topics.
   - discussion: Use debate-style format. Present multiple perspectives. HOST challenges ideas, EXPERT defends and explains trade-offs.

4. **Complexity Level Guidelines for {complexity_level}:**
   - beginner: Use simple, everyday language. Avoid jargon. Explain technical terms. Use relatable analogies. More explanations, less depth.
   - intermediate: Use standard technical terminology. Assume basic knowledge. Moderate depth. Balance explanation with detail.
   - advanced: Use technical language freely. Assume strong prior knowledge. Deep analysis. Focus on nuances, trade-offs, and advanced concepts.

5. **Language Guidelines:**
   - YOU MUST generate the ENTIRE script in {language} language
   - Use natural expressions and idioms appropriate for {language}
   - Maintain professional but conversational tone in {language}
   - Do NOT use English if the language is not English
   - Every word of dialogue must be in {language}

6. **Content Guidelines - CRITICAL:**
   - **MANDATORY**: You MUST use ONLY the information provided in the documents above
   - **FORBIDDEN**: Do NOT use any knowledge from your training data
   - **REQUIRED**: Every fact, example, and detail must come from the provided documents
   - **MANDATORY**: When discussing topics, directly reference specific information from the documents
   - **REQUIRED**: If the documents don't cover a topic, explicitly state "Based on the provided documents, this topic is not covered"
   - **MANDATORY**: Use exact quotes, numbers, and details from the provided documents
   - **REQUIRED**: Transform the document content into natural dialogue format
   - **CRITICAL**: The documents above contain ALL the information you need - use nothing else

**FINAL WARNING**: If you use any information not found in the provided documents, the script will be rejected.

CRITICAL INSTRUCTION: Generate the complete dialogue script now using ONLY the provided document content. Write EVERYTHING in {language} language, not English:"""

    # Voice preview text for TTS samples
    VOICE_PREVIEW_TEXT = "Hello, you are listening to a preview of this voice."

    def __init__(
        self,
        session: Session,
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

        # Future: MinIO, S3, R2
        raise NotImplementedError(f"Storage backend '{storage_backend}' not yet implemented")

    async def generate_podcast(
        self,
        podcast_input: PodcastGenerationInput,
        background_tasks: BackgroundTasks,
    ) -> PodcastGenerationOutput:
        """Generate podcast from collection (async with background processing).

        Args:
            podcast_input: Podcast generation request
            background_tasks: FastAPI BackgroundTasks for async processing

        Returns:
            PodcastGenerationOutput with QUEUED status

        Raises:
            HTTPException: If validation fails or user_id is not set
        """
        # Validate user_id is set (should be auto-filled by router from auth)
        if not podcast_input.user_id:
            raise ValidationError("user_id is required for podcast generation", field="user_id")

        user_id: UUID4 = podcast_input.user_id  # Type assertion for mypy

        try:
            # 1. Validate request
            await self._validate_podcast_request(podcast_input)

            # 2. Create podcast record
            podcast = self.repository.create(
                user_id=user_id,
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
                user_id,
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
            ValidationError: If validation fails or access denied
        """
        # Check collection exists and retrieve it
        # get_collection() raises NotFoundError if collection doesn't exist
        try:
            collection = self.collection_service.get_collection(collection_id=podcast_input.collection_id)
        except NotFoundError as e:
            raise NotFoundError(
                resource_type="Collection",
                resource_id=str(podcast_input.collection_id),
                message=f"Collection {podcast_input.collection_id} not found",
            ) from e

        # Check collection has sufficient documents
        doc_count = len(collection.files) if collection.files else 0
        min_docs = self.settings.podcast_min_documents

        if doc_count < min_docs:
            raise ValidationError(
                f"Collection has {doc_count} documents, but {min_docs} required for podcast generation"
            )

        # Check user's active podcast limit
        active_count = self.repository.count_active_for_user(podcast_input.user_id)
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
        audio_stored = False  # Track if audio was stored for cleanup

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
            audio_stored = True  # Mark audio as stored for cleanup if needed

            # Step 6: Mark complete (100%)
            self.repository.mark_completed(
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

        except (NotFoundError, ValidationError) as e:
            # Resource/validation errors - provide clear error message
            error_msg = f"Validation error: {e}"
            logger.error("Podcast generation validation failed for %s: %s", podcast_id, error_msg)
            await self._cleanup_failed_podcast(podcast_id, podcast_input.user_id, audio_stored, error_msg)

        except Exception as e:
            # TODO: Use more specific exception types (e.g., LLMError, AudioGenerationError, StorageError)
            # and implement retry logic for transient failures. Sanitize error messages before
            # storing to avoid information leakage. See follow-up issue for exception hierarchy.

            # Unexpected errors - log full traceback and clean up
            error_msg = f"Generation failed: {e}"
            logger.exception("Podcast generation failed for %s: %s", podcast_id, e)
            await self._cleanup_failed_podcast(podcast_id, podcast_input.user_id, audio_stored, error_msg)

    async def _cleanup_failed_podcast(
        self,
        podcast_id: UUID4,
        user_id: UUID4,
        audio_stored: bool,
        error_message: str,
    ) -> None:
        """
        Clean up resources for a failed podcast generation.

        Args:
            podcast_id: Podcast ID
            user_id: User ID
            audio_stored: Whether audio file was stored
            error_message: Error description
        """
        try:
            # Clean up audio file if it was stored
            if audio_stored:
                try:
                    await self.audio_storage.delete_audio(
                        podcast_id=podcast_id,
                        user_id=user_id,
                    )
                    logger.info("Cleaned up audio file for failed podcast: %s", podcast_id)
                except Exception as cleanup_error:
                    logger.warning(
                        "Failed to clean up audio file for %s: %s",
                        podcast_id,
                        cleanup_error,
                    )

            # Mark podcast as failed in database
            self.repository.update_status(
                podcast_id=podcast_id,
                status=PodcastStatus.FAILED,
                error_message=error_message,
            )
            logger.info("Marked podcast as failed: %s", podcast_id)

        except Exception as e:
            # Even cleanup failed - log but don't raise
            logger.exception("Failed to clean up failed podcast %s: %s", podcast_id, e)

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

        # Note: Topic will be extracted from description and passed to specialized search

        # Create optimized query for podcast content retrieval
        if podcast_input.description:
            podcast_query = (
                f"Comprehensive information about {podcast_input.description}. "
                f"Include key concepts, examples, details, insights, and practical applications. "
                f"Cover all aspects of this topic for podcast content generation."
            )
        else:
            podcast_query = (
                "Provide comprehensive overview of all key topics, main insights, "
                "important concepts, and significant information from this collection. "
                "Include examples, details, and practical applications suitable for "
                "creating an educational podcast dialogue."
            )

        logger.info("Using optimized podcast search query: '%s'", podcast_query[:100] + "...")

        # Execute search with podcast-optimized parameters
        search_input = SearchInput(
            user_id=podcast_input.user_id,
            collection_id=podcast_input.collection_id,
            question=podcast_query,
            config_metadata={
                "top_k": top_k,
                "enable_reranking": False,  # Disable reranking for comprehensive content
                "enable_hierarchical": True,  # Enable hierarchical retrieval for better coverage
                "cot_enabled": False,  # Skip chain-of-thought for document retrieval
            },
        )

        search_result = await self.search_service.search(search_input)

        # Validate sufficient content retrieved
        num_retrieved = len(search_result.query_results) if search_result.query_results else 0

        # Require at least 20% of requested documents for SHORT, 30% for others
        min_threshold_pct = 0.2 if podcast_input.duration == PodcastDuration.SHORT else 0.3
        min_required = max(3, int(top_k * min_threshold_pct))  # At least 3 documents minimum

        if num_retrieved < min_required:
            raise ValidationError(
                f"Insufficient content retrieved: got {num_retrieved} documents, "
                f"need at least {min_required} (minimum {min_threshold_pct:.0%} of {top_k} requested) "
                f"for {podcast_input.duration.value} podcast",
                field="content_retrieval",
            )

        # Format results for prompt using query_results which contain the actual text
        formatted_results = "\n\n".join(
            [
                f"[Document {i + 1}]: {result.chunk.text if result.chunk else ''}"
                for i, result in enumerate(search_result.query_results)
                if result.chunk
            ]
        )

        logger.info(
            "Retrieved %d documents for podcast (top_k=%d, min_required=%d)",
            num_retrieved,
            top_k,
            min_required,
        )

        # Debug: Log sample of RAG content being passed to LLM
        logger.info("Podcast RAG content sample (first 500 chars): %s", formatted_results[:500])
        logger.info("Podcast RAG content total length: %d characters", len(formatted_results))
        logger.info(
            "Podcast search strategies used: %s",
            search_result.metadata.get("strategies_used", ["unknown"]) if search_result.metadata else ["unknown"],
        )

        return formatted_results

    async def _generate_script(self, podcast_input: PodcastGenerationInput, rag_results: str) -> str:
        """Generate podcast script via LLM using database template.

        Args:
            podcast_input: Podcast generation request input
            rag_results: Retrieved content from knowledge base

        Returns:
            Generated podcast script text

        Raises:
            ValidationError: If user_id is not set in podcast_input
        """
        # Validate user_id is set (should be auto-filled by router from auth)
        if not podcast_input.user_id:
            from rag_solution.core.exceptions import ValidationError

            raise ValidationError("user_id is required for podcast generation", field="user_id")

        user_id: UUID4 = podcast_input.user_id  # Type assertion after validation

        # Calculate target word count
        duration_minutes_map = {
            PodcastDuration.SHORT: 5,
            PodcastDuration.MEDIUM: 15,
            PodcastDuration.LONG: 30,
            PodcastDuration.EXTENDED: 60,
        }
        duration_minutes = duration_minutes_map[podcast_input.duration]
        word_count = duration_minutes * 150  # 150 words/minute

        # Calculate min/max word count (±15% tolerance)
        min_word_count = int(word_count * 0.85)
        max_word_count = int(word_count * 1.15)

        # Get podcast template from database
        from rag_solution.schemas.prompt_template_schema import (
            PromptTemplateInput,
            PromptTemplateOutput,
            PromptTemplateType,
        )
        from rag_solution.services.prompt_template_service import PromptTemplateService

        template_service = PromptTemplateService(self.session)

        podcast_template: PromptTemplateOutput | PromptTemplateInput
        try:
            loaded_template = template_service.get_by_type(user_id, PromptTemplateType.PODCAST_GENERATION)
            if loaded_template is None:
                # No template found - use fallback
                logger.info("No podcast template found for user %s, using fallback", user_id)
                podcast_template = PromptTemplateInput(
                    name="podcast_fallback",
                    user_id=user_id,
                    template_type=PromptTemplateType.PODCAST_GENERATION,
                    system_prompt="You are a professional podcast script writer.",
                    template_format=self.PODCAST_SCRIPT_PROMPT,
                    input_variables={
                        "user_topic": "Topic or focus area for the podcast",
                        "rag_results": "Content from documents to be discussed",
                        "duration_minutes": "Target duration in minutes",
                        "word_count": "Target word count",
                        "min_word_count": "Minimum word count",
                        "max_word_count": "Maximum word count",
                        "podcast_style": "Style of podcast (conversational_interview, narrative, educational, discussion)",
                        "language": "Language for the podcast (en, es, fr, de, etc.)",
                        "complexity_level": "Target audience complexity (beginner, intermediate, advanced)",
                    },
                )
            else:
                podcast_template = loaded_template  # Type: PromptTemplateOutput
        except (NotFoundError, PromptTemplateNotFoundError):
            # Template service errors - use fallback
            logger.info("Template service error, using fallback template")
            podcast_template = PromptTemplateInput(
                name="podcast_fallback",
                user_id=user_id,
                template_type=PromptTemplateType.PODCAST_GENERATION,
                system_prompt="You are a professional podcast script writer.",
                template_format=self.PODCAST_SCRIPT_PROMPT,
                input_variables={
                    "user_topic": "Topic or focus area for the podcast",
                    "rag_results": "Content from documents to be discussed",
                    "duration_minutes": "Target duration in minutes",
                    "word_count": "Target word count",
                    "min_word_count": "Minimum word count",
                    "max_word_count": "Maximum word count",
                    "podcast_style": "Style of podcast (conversational_interview, narrative, educational, discussion)",
                    "language": "Language for the podcast (en, es, fr, de, etc.)",
                    "complexity_level": "Target audience complexity (beginner, intermediate, advanced)",
                },
            )

        # For non-English languages, use a simpler, more direct prompt
        # Use consistent template system for ALL languages
        # Set variables for template system
        variables = {
            "user_topic": podcast_input.description or "General overview of the content",
            "rag_results": rag_results,  # RAG content is included for ALL languages
            "duration_minutes": duration_minutes,
            "word_count": word_count,
            "min_word_count": min_word_count,
            "max_word_count": max_word_count,
            # New advanced options
            "podcast_style": podcast_input.podcast_style,
            "language": podcast_input.language,
            "complexity_level": podcast_input.complexity_level,
        }

        # Continue with template system for all languages
        factory = LLMProviderFactory(self.session)
        llm_provider = factory.get_provider(self.settings.llm_provider)

        # Override LLM parameters for podcast generation
        # We need much higher token limits for long-form content
        from rag_solution.schemas.llm_parameters_schema import LLMParametersInput

        # Calculate max_new_tokens for podcast generation
        # Target word count * 1.5 (tokens per word) * 2 (buffer for formatting/structure)
        desired_tokens = max_word_count * 3  # Conservative estimate for long-form content

        # Don't cap - let WatsonX API handle its own limits
        # Granite 3.3 8B context window: 128K (can read lots of RAG content)
        # Granite 3.3 8B max_new_tokens: Set by API, we'll let it fail if too high
        max_tokens = desired_tokens

        logger.info(
            "Token calculation: desired=%d, max_allowed=%d, word_count=%d, duration=%d minutes",
            desired_tokens,
            max_tokens,
            max_word_count,
            duration_minutes,
        )

        podcast_params = LLMParametersInput(
            user_id=user_id,  # Required field
            name="podcast_generation_params",
            description="Parameters optimized for podcast script generation",
            max_new_tokens=max_tokens,  # Capped at model limits
            temperature=0.7,
            top_k=50,
            top_p=0.95,
            repetition_penalty=1.1,
            is_default=False,
        )

        script_text = llm_provider.generate_text(
            user_id=user_id,
            prompt="",  # Empty - template contains full prompt
            template=podcast_template,
            variables=variables,
            model_parameters=podcast_params,
        )

        logger.info(
            "Generated script: %d characters, target %d words (range: %d-%d)",
            len(script_text) if isinstance(script_text, str) else sum(len(s) for s in script_text),
            word_count,
            min_word_count,
            max_word_count,
        )

        # Ensure we return a single string (some providers may return list)
        if isinstance(script_text, list):
            return "\n\n".join(script_text)
        return script_text

    async def _generate_audio(
        self,
        _podcast_id: UUID4,
        podcast_script: Any,  # PodcastScript - keeping as Any for now as type is complex
        podcast_input: PodcastGenerationInput,
    ) -> bytes:
        """
        Generate audio from parsed script with progress tracking.

        Args:
            _podcast_id: Podcast ID for progress updates (currently unused, reserved for future)
            podcast_script: Parsed PodcastScript
            podcast_input: Original request

        Returns:
            Audio file bytes
        """
        # Create audio provider
        # Default to openai if not configured
        audio_provider_type = getattr(self.settings, "podcast_audio_provider", "openai")
        logger.info("Creating audio provider: type=%s", audio_provider_type)

        audio_provider = AudioProviderFactory.create_provider(
            provider_type=audio_provider_type,
            settings=self.settings,
        )

        logger.info("Audio provider created successfully: %s", audio_provider.__class__.__name__)

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
        self.repository.update_progress(
            podcast_id=podcast_id,
            progress_percentage=progress,
            current_step=step,
            step_details=step_details,
        )

        if status:
            self.repository.update_status(
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
        podcast = self.repository.get_by_id(podcast_id)

        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")

        # user_id comes from get_current_user() as UUID object
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
        # user_id comes from get_current_user() as UUID object
        podcasts = self.repository.get_by_user(user_id=user_id, limit=limit, offset=offset)

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
        podcast = self.repository.get_by_id(podcast_id)

        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")

        # user_id comes from get_current_user() as UUID object
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
        return self.repository.delete(podcast_id)

    async def generate_voice_preview(self, voice_id: str) -> bytes:
        """
        Generate a short audio preview for a specific voice.

        Args:
            voice_id: The ID of the voice to preview.

        Returns:
            The audio data as bytes.
        """
        try:
            logger.info("Generating voice preview for voice_id: %s", voice_id)

            # Create audio provider
            audio_provider = AudioProviderFactory.create_provider(
                provider_type=self.settings.podcast_audio_provider,
                settings=self.settings,
            )

            # Generate a short, generic audio preview
            # Note: generate_single_turn_audio is implemented in concrete audio providers but not in base class
            audio_bytes = await audio_provider.generate_single_turn_audio(  # type: ignore[attr-defined]
                text=self.VOICE_PREVIEW_TEXT,
                voice_id=voice_id,
                audio_format=AudioFormat.MP3,
            )

            return bytes(audio_bytes)  # Ensure return type is bytes

        except Exception as e:
            logger.exception("Failed to generate voice preview for voice_id: %s", voice_id)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate voice preview: {e}",
            ) from e

    async def generate_script_only(
        self,
        script_input: "PodcastScriptGenerationInput",
    ) -> "PodcastScriptOutput":
        """
        Generate podcast script without audio synthesis.

        This endpoint is useful for:
        - Script quality validation
        - Faster iteration (30s vs 90s)
        - Cost savings (no TTS API calls)
        - Script editing workflows

        Args:
            script_input: Script generation request

        Returns:
            PodcastScriptOutput with generated script and metadata

        Raises:
            ValidationError: If input validation fails
            NotFoundError: If collection not found
        """
        from uuid import uuid4

        from rag_solution.schemas.podcast_schema import PodcastScriptOutput

        logger.info("Starting script-only generation for collection %s", script_input.collection_id)

        # Validate collection exists
        collection = self.collection_service.get_collection(script_input.collection_id)
        if not collection:
            raise NotFoundError(f"Collection {script_input.collection_id} not found")

        # Convert to full podcast input for internal processing
        podcast_input = PodcastGenerationInput(
            collection_id=script_input.collection_id,
            user_id=script_input.user_id,
            duration=script_input.duration,
            title=script_input.title or f"Script for {collection.name}",
            description=script_input.description,
            audio_format=AudioFormat.MP3,
            voice_settings=script_input.voice_settings
            or {
                "voice_id": "nova",
                "gender": "female",
                "speed": 1.0,
                "pitch": 1.0,
                "language": "en-US",
                "name": "Nova",
            },
        )

        # Step 1: Fetch RAG results
        logger.info("Fetching RAG results for script generation")
        rag_results = await self._retrieve_content(podcast_input)

        # Step 2: Generate script
        logger.info("Generating script via LLM")
        script_text = await self._generate_script(podcast_input, rag_results)

        # Calculate metadata
        word_count = len(script_text.split())
        duration_minutes = podcast_input.duration if isinstance(podcast_input.duration, int) else 15
        target_word_count = duration_minutes * 150  # 150 words/minute
        estimated_duration = word_count / 150.0  # Actual duration based on word count

        # Check format
        has_host = "HOST:" in script_text or "Host:" in script_text
        has_expert = "EXPERT:" in script_text or "Expert:" in script_text
        has_proper_format = has_host and has_expert

        logger.info(
            "Script generated: %d words (target: %d), estimated duration: %.1f minutes",
            word_count,
            target_word_count,
            estimated_duration,
        )

        return PodcastScriptOutput(
            script_id=uuid4(),
            collection_id=script_input.collection_id,
            user_id=script_input.user_id,
            title=podcast_input.title,
            script_text=script_text,
            word_count=word_count,
            target_word_count=target_word_count,
            duration_minutes=duration_minutes,
            estimated_duration_minutes=estimated_duration,
            has_proper_format=has_proper_format,
            metadata={
                "has_host": has_host,
                "has_expert": has_expert,
                "rag_results_length": len(rag_results),
                "collection_name": collection.name,
            },
        )

    async def generate_audio_from_script(
        self,
        audio_input: "PodcastAudioGenerationInput",
        background_tasks: BackgroundTasks,
    ) -> PodcastGenerationOutput:
        """
        Generate podcast audio from an existing script (skip LLM script generation).

        This method is useful for:
        - Converting previously generated scripts to audio
        - Converting user-edited scripts to audio
        - Re-generating audio with different voices
        - Faster/cheaper processing (TTS only, no LLM)

        Workflow:
        1. Validate user has access to collection
        2. Create podcast record (status: QUEUED)
        3. Schedule background task for audio generation
        4. Background task: parse script → generate audio → store → update status

        Cost: ~$0.05-0.80 (TTS only, 60% cheaper than full generation)
        Time: ~30-90 seconds (depending on duration)

        Args:
            audio_input: Audio generation request with script
            background_tasks: FastAPI background tasks

        Returns:
            PodcastGenerationOutput with QUEUED status

        Raises:
            ValidationError: If user_id not set or script format invalid
            NotFoundError: If collection not found
            HTTPException: For validation/permission errors
        """
        from uuid import uuid4

        # Validate user_id is set (should be auto-filled by router from auth)
        if not audio_input.user_id:
            raise ValidationError("user_id is required for podcast generation", field="user_id")

        user_id: UUID4 = audio_input.user_id

        # Validate collection exists and user has access
        collection = self.collection_service.get_collection(audio_input.collection_id)
        if not collection:
            raise NotFoundError(f"Collection {audio_input.collection_id} not found")

        logger.info(
            "Starting audio generation from script for collection %s (user %s)", audio_input.collection_id, user_id
        )

        # Create podcast record
        podcast_id = uuid4()
        podcast_record = self.repository.create(
            podcast_id=podcast_id,
            user_id=user_id,
            collection_id=audio_input.collection_id,
            title=audio_input.title,
            description=audio_input.description,
            duration=audio_input.duration,
            status=PodcastStatus.QUEUED,
            audio_format=audio_input.audio_format,
        )

        # Schedule background processing
        background_tasks.add_task(
            self._process_audio_from_script,
            podcast_id,
            audio_input,
        )

        logger.info("Podcast %s queued for audio generation (script-to-audio)", podcast_id)

        return PodcastGenerationOutput.model_validate(podcast_record)

    async def _process_audio_from_script(
        self,
        podcast_id: UUID4,
        audio_input: "PodcastAudioGenerationInput",
    ) -> None:
        """
        Background task: Generate audio from script.

        Steps:
        1. Update status to GENERATING
        2. Parse script into turns
        3. Generate multi-voice audio
        4. Store audio file
        5. Update status to COMPLETED

        Args:
            podcast_id: Podcast record ID
            audio_input: Audio generation request
        """
        try:
            logger.info("Processing audio generation for podcast %s", podcast_id)

            # Step 1: Update status
            await self._update_progress(
                podcast_id,
                PodcastStatus.GENERATING,
                progress_percentage=0,
                current_step="parsing_script",
            )

            # Step 2: Parse script
            logger.info("Parsing script into dialogue turns")
            parser = PodcastScriptParser()
            parsed_script = parser.parse_script(audio_input.script_text)

            await self._update_progress(
                podcast_id,
                PodcastStatus.GENERATING,
                progress_percentage=30,
                current_step="generating_audio",
            )

            # Step 3: Generate audio
            logger.info("Generating multi-voice audio")
            audio_bytes = await self._generate_audio(
                script=parsed_script.script,
                host_voice=audio_input.host_voice,
                expert_voice=audio_input.expert_voice,
                audio_format=audio_input.audio_format,
            )

            await self._update_progress(
                podcast_id,
                PodcastStatus.GENERATING,
                progress_percentage=80,
                current_step="storing_audio",
            )

            # Step 4: Store audio
            logger.info("Storing audio file")
            audio_url = await self._store_audio(
                podcast_id=podcast_id,
                audio_bytes=audio_bytes,
                audio_format=audio_input.audio_format,
            )

            # Step 5: Mark completed
            self.repository.update(
                podcast_id=podcast_id,
                status=PodcastStatus.COMPLETED,
                audio_url=audio_url,
                progress_percentage=100,
                current_step="completed",
            )

            logger.info("Audio generation completed for podcast %s", podcast_id)

        except Exception as e:
            logger.exception("Audio generation failed for podcast %s", podcast_id)
            await self._cleanup_failed_podcast(podcast_id, str(e))
            raise
