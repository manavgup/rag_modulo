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
from enum import Enum
from typing import Any, ClassVar

from fastapi import BackgroundTasks, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import get_settings
from core.custom_exceptions import NotFoundError, PromptTemplateNotFoundError, ValidationError
from core.identity_service import IdentityService
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


class SupportedLanguage(str, Enum):
    """Supported languages for podcast generation with display names."""

    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE = "zh"
    ARABIC = "ar"
    RUSSIAN = "ru"
    HINDI = "hi"

    @property
    def display_name(self) -> str:
        """Get human-readable language name."""
        names = {
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
        return names.get(self.value, self.value)


class PodcastService:
    """Service for podcast generation and management."""

    # Legacy dict for backward compatibility - use SupportedLanguage enum instead
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

    # Default podcast prompt template with XML tag structure to prevent leakage
    # pylint: disable=line-too-long
    PODCAST_SCRIPT_PROMPT = """You are a professional podcast script writer. Create an engaging podcast dialogue between a HOST and an EXPERT in {language} language.

CRITICAL OUTPUT FORMAT:
You MUST structure your response using these XML tags:
1. <thinking> - Internal reasoning, planning, and notes (NOT part of the final script)
2. <script> - The actual podcast dialogue script (this is what gets published)

Example structure:
<thinking>
Let me plan the podcast structure... I'll start with an introduction...
[Your internal planning and reasoning go here]
</thinking>

<script>
HOST: Welcome to today's show!
EXPERT: Thanks for having me!
[The actual podcast dialogue goes here]
</script>

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
   - CRITICAL: DO NOT use placeholders like [HOST NAME] or [EXPERT NAME]
   - CRITICAL: The speakers should refer to each other naturally without using placeholder names
   - CRITICAL: Use direct address or simply continue the dialogue without inserting name placeholders

2. **Script Format (IMPORTANT):**
   Use this exact format for each turn INSIDE the <script> tags:

   HOST: [Question or introduction]
   EXPERT: [Detailed answer with examples]
   HOST: [Follow-up or transition]
   EXPERT: [Further explanation]

   CRITICAL: Do NOT include any placeholders like [HOST NAME], [EXPERT NAME], or [INSERT NAME]. Write natural dialogue without placeholder names.

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

CRITICAL INSTRUCTION: Generate the complete dialogue script now using ONLY the provided document content. Write EVERYTHING in {language} language, not English.

REMEMBER: Use <thinking> tags for your internal reasoning and <script> tags for the actual podcast dialogue!"""

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

            # Step 5.5: Generate chapters (95-98%)
            await self._update_progress(podcast_id, progress=95, step="generating_chapters")
            chapters = self._generate_chapters_from_script(podcast_script)

            # Step 6: Mark complete (100%)
            self.repository.mark_completed(
                podcast_id=podcast_id,
                audio_url=audio_url,
                transcript=script_text,
                audio_size_bytes=len(audio_bytes),
                chapters=chapters,
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
                "Provide a comprehensive overview of all key topics, main insights, "
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
        factory = LLMProviderFactory(self.session, self.settings)
        llm_provider = factory.get_provider(self.settings.llm_provider)

        # Override LLM parameters for podcast generation
        # We need much higher token limits for long-form content
        from rag_solution.schemas.llm_parameters_schema import LLMParametersInput

        # Calculate max_new_tokens for podcast generation
        # Target word count * 1.5 (tokens per word) * 2 (buffer for formatting/structure)
        desired_tokens = max_word_count * 3  # Conservative estimate for long-form content

        # Add reasonable upper bound to prevent runaway token usage
        # While model may support up to 128K context, generation is limited
        # Set upper bound to 200K tokens (~133K words) which should handle even 60-minute podcasts
        max_token_upper_bound = 200_000

        # Cap at reasonable upper bound for safety
        max_tokens = min(desired_tokens, max_token_upper_bound)

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
            temperature=self.settings.temperature,
            top_k=self.settings.top_k,
            top_p=self.settings.top_p,
            repetition_penalty=self.settings.repetition_penalty,
            is_default=False,
        )

        # Retry logic with quality threshold (similar to Issue #461 CoT hardening)
        max_retries = 3
        quality_threshold = 0.6  # Minimum acceptable quality score
        best_script = None
        best_quality = 0.0
        best_method = "none"

        for attempt in range(1, max_retries + 1):
            logger.info("Script generation attempt %d/%d", attempt, max_retries)

            # Generate script
            raw_script = llm_provider.generate_text(
                user_id=user_id,
                prompt="",  # Empty - template contains full prompt
                template=podcast_template,
                variables=variables,
                model_parameters=podcast_params,
            )

            # Ensure we have a single string
            if isinstance(raw_script, list):
                raw_script = "\n\n".join(raw_script)

            logger.info("Generated raw script: %d characters (attempt %d)", len(raw_script), attempt)

            # Parse with hardening
            parsed_script, parsing_quality, parsing_method = self._parse_script_with_hardening(raw_script)

            # Assess overall quality
            quality_score = self._assess_script_quality(parsed_script, word_count, parsing_method)

            logger.info(
                "Attempt %d: quality=%.2f, parsing_quality=%.2f, method=%s, length=%d chars",
                attempt,
                quality_score,
                parsing_quality,
                parsing_method,
                len(parsed_script),
            )

            # Track best result
            if quality_score > best_quality:
                best_script = parsed_script
                best_quality = quality_score
                best_method = parsing_method

            # Check if quality meets threshold
            if quality_score >= quality_threshold:
                logger.info(
                    "✅ Quality threshold met (%.2f >= %.2f) on attempt %d", quality_score, quality_threshold, attempt
                )
                script_text = parsed_script
                break

            # Log retry reason
            if attempt < max_retries:
                logger.warning(
                    "⚠️ Quality below threshold (%.2f < %.2f), retrying (%d/%d)",
                    quality_score,
                    quality_threshold,
                    attempt,
                    max_retries,
                )

        else:
            # All retries exhausted - use best result
            logger.warning(
                "⚠️ Max retries reached. Using best result: quality=%.2f, method=%s", best_quality, best_method
            )
            script_text = best_script if best_script else raw_script

        # Final cleanup
        script_text = self._clean_llm_script(script_text)

        logger.info(
            "Final script: %d characters, target %d words (range: %d-%d), quality=%.2f",
            len(script_text),
            word_count,
            min_word_count,
            max_word_count,
            best_quality,
        )

        return script_text

    def _clean_llm_script(self, script_text: str) -> str:
        """
        Clean LLM-generated script by removing meta-commentary and duplicates.

        LLMs often add unwanted content like:
        - Meta-commentary: "This script adheres to..."
        - Duplicated content
        - Instructions/wrapping markers

        Args:
            script_text: Raw LLM output

        Returns:
            Cleaned script with only dialogue content
        """
        # Common end markers that indicate meta-commentary starts
        end_markers = [
            "**End of script.**",
            "** End of script **",
            "[End of Response]",
            "[End of Script]",
            "[Instruction's wrapping]",
            "Please note that this script",
            "---\n\n**Podcast Script:**",  # Duplication marker
            "***End of Script***",
        ]

        # Find the first occurrence of any end marker
        first_marker_pos = len(script_text)
        for marker in end_markers:
            pos = script_text.find(marker)
            if pos != -1 and pos < first_marker_pos:
                first_marker_pos = pos

        # Strip everything after the first marker
        if first_marker_pos < len(script_text):
            logger.info(
                "Cleaning script: found end marker at position %d, stripping %d chars",
                first_marker_pos,
                len(script_text) - first_marker_pos,
            )
            script_text = script_text[:first_marker_pos]

        # Remove leading/trailing whitespace and separator lines
        script_text = script_text.strip()
        script_text = script_text.strip("-")
        script_text = script_text.strip()

        return script_text

    def _parse_script_with_hardening(self, raw_response: str) -> tuple[str, float, str]:
        """
        Parse LLM response using multi-layer fallback strategy to extract script and prevent leakage.

        Implements 5 parsing strategies (similar to Issue #461 CoT hardening):
        1. XML tag parsing (<script>...</script>)
        2. Regex-based tag extraction
        3. Heuristic-based extraction (look for HOST/EXPERT markers)
        4. Fallback to full response (if it looks like a valid script)
        5. Error state (if no valid script found)

        Args:
            raw_response: Raw LLM response with potential XML tags

        Returns:
            Tuple of (parsed_script, quality_score, parsing_method_used)
        """
        import re

        logger.info("Parsing script with hardening (input length: %d chars)", len(raw_response))

        # Strategy 1: XML tag parsing (highest priority)
        script_match = re.search(r"<script>\s*(.*?)\s*</script>", raw_response, re.DOTALL | re.IGNORECASE)
        if script_match:
            script_content = script_match.group(1).strip()
            if self._validate_script_format(script_content):
                logger.info("✅ Strategy 1: XML tag parsing successful (%d chars)", len(script_content))
                return script_content, 0.95, "xml_tags"

        # Strategy 2: Regex-based tag extraction (case-insensitive, flexible whitespace)
        script_match_flexible = re.search(
            r"<\s*script\s*>(.*?)<\s*/\s*script\s*>", raw_response, re.DOTALL | re.IGNORECASE
        )
        if script_match_flexible:
            script_content = script_match_flexible.group(1).strip()
            if self._validate_script_format(script_content):
                logger.info("✅ Strategy 2: Flexible regex parsing successful (%d chars)", len(script_content))
                return script_content, 0.90, "flexible_regex"

        # Strategy 3: Heuristic extraction - find content between thinking and end
        # Remove thinking section if present
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", raw_response, flags=re.DOTALL | re.IGNORECASE)
        cleaned = cleaned.strip()

        # Check if remaining content is a valid script
        if self._validate_script_format(cleaned):
            logger.info("✅ Strategy 3: Heuristic extraction successful (%d chars)", len(cleaned))
            return cleaned, 0.80, "heuristic"

        # Strategy 4: Look for HOST/EXPERT dialogue even without tags
        # Extract everything that looks like dialogue
        dialogue_lines = []
        for line in raw_response.split("\n"):
            if line.strip().startswith(("HOST:", "EXPERT:", "Host:", "Expert:")):
                dialogue_lines.append(line)

        if len(dialogue_lines) >= 4:  # At least 2 exchanges
            dialogue_script = "\n".join(dialogue_lines)
            if self._validate_script_format(dialogue_script):
                logger.info("✅ Strategy 4: Dialogue extraction successful (%d lines)", len(dialogue_lines))
                return dialogue_script, 0.70, "dialogue_extraction"

        # Strategy 5: Fallback - check if full response is a valid script
        if self._validate_script_format(raw_response):
            logger.warning("⚠️ Strategy 5: Using full response as script (may contain artifacts)")
            return raw_response, 0.50, "full_response"

        # No valid script found
        logger.error("❌ All parsing strategies failed - no valid script found")
        return raw_response, 0.0, "parsing_failed"

    def _validate_script_format(self, script_text: str) -> bool:
        """
        Validate that script has proper HOST/EXPERT dialogue format.

        Args:
            script_text: Script text to validate

        Returns:
            True if script has valid format, False otherwise
        """
        if not script_text or len(script_text) < 50:
            return False

        # Check for HOST and EXPERT markers
        has_host = bool(re.search(r"\bHOST\s*:", script_text, re.IGNORECASE))
        has_expert = bool(re.search(r"\bEXPERT\s*:", script_text, re.IGNORECASE))

        # Count dialogue turns
        host_count = len(re.findall(r"\bHOST\s*:", script_text, re.IGNORECASE))
        expert_count = len(re.findall(r"\bEXPERT\s*:", script_text, re.IGNORECASE))

        # Valid script should have both speakers and at least 2 turns each
        is_valid = has_host and has_expert and host_count >= 2 and expert_count >= 2

        if not is_valid:
            logger.debug(
                "Script validation failed: has_host=%s, has_expert=%s, host_count=%d, expert_count=%d",
                has_host,
                has_expert,
                host_count,
                expert_count,
            )

        return is_valid

    def _assess_script_quality(self, script_text: str, target_word_count: int, parsing_method: str) -> float:
        """
        Assess script quality using multiple criteria.

        Quality Score (0.0-1.0):
        - 1.0: Perfect script (ideal length, format, no artifacts)
        - 0.8-0.9: Good script (minor issues)
        - 0.6-0.7: Acceptable script (some issues but usable)
        - 0.4-0.5: Poor script (significant issues)
        - 0.0-0.3: Failed script (unusable)

        Args:
            script_text: Parsed script text
            target_word_count: Target word count for the script
            parsing_method: Method used to parse the script

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 1.0

        # Factor 1: Parsing method quality (higher is better)
        parsing_quality = {
            "xml_tags": 1.0,
            "flexible_regex": 0.95,
            "heuristic": 0.85,
            "dialogue_extraction": 0.75,
            "full_response": 0.60,
            "parsing_failed": 0.0,
        }
        score *= parsing_quality.get(parsing_method, 0.5)

        # Factor 2: Script format validation
        if not self._validate_script_format(script_text):
            score *= 0.5
            logger.warning("Quality penalty: Invalid script format detected")

        # Factor 3: Word count accuracy (±20% tolerance)
        word_count = len(script_text.split())
        target_min = int(target_word_count * 0.80)
        target_max = int(target_word_count * 1.20)

        if word_count < target_min:
            # Too short - penalize proportionally
            shortage_ratio = word_count / target_min
            score *= max(0.6, shortage_ratio)
            logger.warning(
                "Quality penalty: Script too short (%d words, target: %d-%d)", word_count, target_min, target_max
            )
        elif word_count > target_max:
            # Too long - minor penalty
            score *= 0.95
            logger.warning(
                "Quality penalty: Script too long (%d words, target: %d-%d)", word_count, target_min, target_max
            )

        # Factor 4: Check for artifacts/leakage indicators
        artifacts = [
            "<thinking>",
            "</thinking>",
            "Let me plan",
            "I will create",
            "Here is the script",
            "[INSERT",
            "[HOST NAME]",
            "[EXPERT NAME]",
        ]

        artifact_count = sum(1 for artifact in artifacts if artifact.lower() in script_text.lower())
        if artifact_count > 0:
            score *= max(0.5, 1.0 - (artifact_count * 0.1))
            logger.warning("Quality penalty: Found %d artifact indicators", artifact_count)

        # Factor 5: Dialogue balance (HOST vs EXPERT turns)
        import re

        host_count = len(re.findall(r"\bHOST\s*:", script_text, re.IGNORECASE))
        expert_count = len(re.findall(r"\bEXPERT\s*:", script_text, re.IGNORECASE))

        if host_count > 0 and expert_count > 0:
            balance_ratio = min(host_count, expert_count) / max(host_count, expert_count)
            if balance_ratio < 0.5:
                score *= 0.90
                logger.warning("Quality penalty: Imbalanced dialogue (HOST=%d, EXPERT=%d)", host_count, expert_count)
        else:
            score *= 0.3
            logger.error("Quality penalty: Missing speaker turns (HOST=%d, EXPERT=%d)", host_count, expert_count)

        # Ensure score is in valid range
        final_score = max(0.0, min(1.0, score))

        logger.info(
            "Script quality assessment: score=%.2f, method=%s, words=%d (target: %d), artifacts=%d",
            final_score,
            parsing_method,
            word_count,
            target_word_count,
            artifact_count,
        )

        return final_score

    def _generate_chapters_from_script(self, podcast_script: Any) -> list[dict[str, Any]]:
        """
        Generate dynamic chapter markers from podcast script.

        Extracts questions/topics from HOST dialogue and calculates timestamps
        based on word count and turn structure.

        Args:
            podcast_script: Parsed PodcastScript with turns

        Returns:
            List of chapter dictionaries with title, start_time, duration, speaker
        """
        import re

        from rag_solution.schemas.podcast_schema import PodcastChapter, Speaker

        chapters: list[dict[str, Any]] = []
        current_time = 0.0  # Running timestamp in seconds

        logger.info("Generating chapters from %d turns", len(podcast_script.turns))

        for i, turn in enumerate(podcast_script.turns):
            # Only create chapters for HOST turns (questions/introductions)
            if turn.speaker == Speaker.HOST:
                # Extract question/topic from turn text
                turn_text = turn.text.strip()

                # Clean up the text to get a nice chapter title
                # Remove filler words and get first sentence
                chapter_title = turn_text.split(".")[0].strip() if "." in turn_text else turn_text[:100]

                # Further clean the title
                chapter_title = re.sub(r"\s+", " ", chapter_title)  # Normalize whitespace
                if len(chapter_title) > 80:
                    chapter_title = chapter_title[:77] + "..."

                # Calculate duration for this chapter (until next HOST turn or end)
                chapter_duration = turn.estimated_duration

                # Look ahead to find next HOST turn for better duration estimate
                for j in range(i + 1, len(podcast_script.turns)):
                    if podcast_script.turns[j].speaker == Speaker.HOST:
                        # Found next HOST turn - duration is from current to next
                        break
                    # Add EXPERT turn duration to this chapter
                    chapter_duration += podcast_script.turns[j].estimated_duration

                # Create chapter
                chapter = PodcastChapter(
                    title=chapter_title,
                    start_time=current_time,
                    duration=chapter_duration,
                    speaker="HOST",
                )

                chapters.append(chapter.model_dump())
                logger.debug(
                    "Chapter %d: '%s' at %.1fs (duration: %.1fs)",
                    len(chapters),
                    chapter_title,
                    current_time,
                    chapter_duration,
                )

            # Update running timestamp
            current_time += turn.estimated_duration

        logger.info("Generated %d chapters from script", len(chapters))

        # If no chapters found, create a single chapter for the whole podcast
        if not chapters:
            logger.warning("No HOST turns found, creating single chapter")
            chapters = [
                PodcastChapter(
                    title="Podcast Content",
                    start_time=0.0,
                    duration=podcast_script.total_duration,
                    speaker="HOST",
                ).model_dump()
            ]

        return chapters

    async def _resolve_voice_id(self, voice_id: str, user_id: UUID4) -> tuple[str, str | None]:
        """
        Resolve voice ID to provider-specific voice ID.

        If voice_id is a UUID (custom voice), look it up in database and return:
        - provider_voice_id: The actual voice ID in the TTS provider's system
        - provider_name: The TTS provider name (elevenlabs, playht, resemble)

        If voice_id is not a UUID (predefined voice), return it as-is with None provider.

        Args:
            voice_id: Voice ID (either UUID for custom voice or provider voice name)
            user_id: User ID for custom voice lookup

        Returns:
            Tuple of (resolved_voice_id, provider_name)

        Raises:
            ValidationError: If custom voice not found or not ready
        """
        from uuid import UUID

        # Check if voice_id is a UUID (custom voice)
        try:
            voice_uuid = UUID(voice_id)
            # It's a custom voice - look it up in database
            from rag_solution.repository.voice_repository import VoiceRepository

            voice_repo = VoiceRepository(self.session)
            custom_voice = voice_repo.get_by_id(voice_uuid)

            if not custom_voice:
                raise ValidationError(f"Custom voice '{voice_id}' not found", field="voice_id")

            # Check voice ownership
            if custom_voice.user_id != user_id:
                raise ValidationError(
                    f"Custom voice '{voice_id}' does not belong to user",
                    field="voice_id",
                )

            # Check voice is ready
            if custom_voice.status != "ready":
                raise ValidationError(
                    f"Custom voice '{voice_id}' is not ready (status: {custom_voice.status})",
                    field="voice_id",
                )

            # Check provider voice ID exists
            if not custom_voice.provider_voice_id:
                raise ValidationError(
                    f"Custom voice '{voice_id}' has no provider voice ID",
                    field="voice_id",
                )

            logger.info(
                "Resolved custom voice %s to provider voice ID: %s (provider: %s)",
                voice_id,
                custom_voice.provider_voice_id,
                custom_voice.provider_name,
            )

            return custom_voice.provider_voice_id, custom_voice.provider_name

        except ValueError:
            # Not a UUID - it's a predefined provider voice name
            logger.debug("Voice ID '%s' is a predefined provider voice", voice_id)
            return voice_id, None

    async def _generate_audio(
        self,
        _podcast_id: UUID4,
        podcast_script: Any,  # PodcastScript - keeping as Any for now as type is complex
        podcast_input: PodcastGenerationInput,
    ) -> bytes:
        """
        Generate audio from parsed script with multi-provider support.

        This implements per-turn provider selection, allowing mixing of voices
        from different providers (e.g., custom ElevenLabs voice for host,
        OpenAI voice for expert).

        Strategy:
        1. For each turn, resolve voice ID and determine its provider
        2. Create provider instance if needed (cached to avoid recreation)
        3. Generate audio segment using the appropriate provider
        4. Combine all segments with pauses into final audio

        Args:
            _podcast_id: Podcast ID for progress updates (currently unused)
            podcast_script: Parsed PodcastScript with turns
            podcast_input: Original podcast generation input with voice settings

        Returns:
            Audio bytes (MP3, WAV, etc.)

        Raises:
            AudioGenerationError: If audio generation fails
            ValidationError: If voices are invalid
        """
        import io

        from pydub import AudioSegment

        from rag_solution.schemas.podcast_schema import Speaker

        logger.info(
            "Generating audio with multi-provider support for %d turns (host=%s, expert=%s)",
            len(podcast_script.turns),
            podcast_input.host_voice,
            podcast_input.expert_voice,
        )

        # Resolve both voices upfront to validate and determine providers
        host_voice_id, host_provider = await self._resolve_voice_id(
            podcast_input.host_voice,
            podcast_input.user_id,
        )
        expert_voice_id, expert_provider = await self._resolve_voice_id(
            podcast_input.expert_voice,
            podcast_input.user_id,
        )

        # Determine provider for each role
        # If voice has a provider, use it; otherwise use default from settings
        default_provider = getattr(self.settings, "podcast_audio_provider", "openai")
        host_provider_type = host_provider or default_provider
        expert_provider_type = expert_provider or default_provider

        logger.info(
            "Voice configuration: HOST(voice=%s, provider=%s), EXPERT(voice=%s, provider=%s)",
            host_voice_id,
            host_provider_type,
            expert_voice_id,
            expert_provider_type,
        )

        # Cache provider instances to avoid recreating them for each turn
        from rag_solution.generation.audio.base import AudioProviderBase

        provider_cache: dict[str, AudioProviderBase] = {}

        def get_provider(provider_type: str) -> AudioProviderBase:
            """Get or create audio provider instance."""
            if provider_type not in provider_cache:
                logger.debug("Creating %s audio provider", provider_type)
                provider_cache[provider_type] = AudioProviderFactory.create_provider(
                    provider_type=provider_type,
                    settings=self.settings,
                )
            return provider_cache[provider_type]

        # Generate audio segments for each turn
        audio_segments = []
        pause_duration_ms = 500  # Default pause between speakers

        for idx, turn in enumerate(podcast_script.turns):
            # Determine voice and provider for this turn
            if turn.speaker == Speaker.HOST:
                voice_id = host_voice_id
                provider_type = host_provider_type
            else:
                voice_id = expert_voice_id
                provider_type = expert_provider_type

            # Get provider instance
            provider = get_provider(provider_type)

            # Generate audio for this turn
            try:
                logger.debug(
                    "Generating turn %d/%d: speaker=%s, provider=%s, voice=%s, text_len=%d",
                    idx + 1,
                    len(podcast_script.turns),
                    turn.speaker.value,
                    provider_type,
                    voice_id,
                    len(turn.text),
                )

                # Call provider's internal turn generation method
                # pylint: disable=protected-access  # Intentional use of internal method for per-turn generation
                segment = await provider._generate_turn_audio(
                    text=turn.text,
                    voice_id=voice_id,
                    audio_format=podcast_input.format,
                )

                audio_segments.append(segment)

                logger.debug(
                    "Generated turn %d/%d successfully (%s, %d chars, %.1f sec)",
                    idx + 1,
                    len(podcast_script.turns),
                    turn.speaker.value,
                    len(turn.text),
                    len(segment) / 1000.0,
                )

            except Exception as e:
                from rag_solution.generation.audio.base import AudioGenerationError

                logger.error(
                    "Failed to generate audio for turn %d/%d (speaker=%s, provider=%s): %s",
                    idx + 1,
                    len(podcast_script.turns),
                    turn.speaker.value,
                    provider_type,
                    e,
                )
                raise AudioGenerationError(
                    provider=provider_type,
                    error_type="turn_generation_failed",
                    message=f"Failed to generate audio for turn {idx + 1}: {e}",
                    original_error=e,
                ) from e

            # Add pause after turn (except last one)
            if idx < len(podcast_script.turns) - 1:
                pause = AudioSegment.silent(duration=pause_duration_ms)
                audio_segments.append(pause)

        # Combine all segments into final audio
        logger.info("Combining %d audio segments into final podcast", len(audio_segments))

        if not audio_segments:
            raise ValueError("No audio segments generated")

        combined = AudioSegment.empty()
        for segment in audio_segments:
            combined += segment

        # Export to bytes
        buffer = io.BytesIO()
        combined.export(buffer, format=podcast_input.format.value)
        audio_bytes = buffer.getvalue()

        logger.info(
            "Generated complete podcast: %d turns, %d bytes, %.1f seconds, providers_used=%s",
            len(podcast_script.turns),
            len(audio_bytes),
            len(combined) / 1000.0,
            list(provider_cache.keys()),
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
        from rag_solution.schemas.podcast_schema import PodcastScriptOutput

        logger.info(
            "Starting script-only generation for collection %s",
            script_input.collection_id,
        )

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
            script_id=IdentityService.generate_id(),
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

        # Validate user_id is set (should be auto-filled by router from auth)
        if not audio_input.user_id:
            raise ValidationError("user_id is required for podcast generation", field="user_id")

        user_id: UUID4 = audio_input.user_id

        # Validate collection exists and user has access
        collection = self.collection_service.get_collection(audio_input.collection_id)
        if not collection:
            raise NotFoundError(f"Collection {audio_input.collection_id} not found")

        logger.info(
            "Starting audio generation from script for collection %s (user %s)",
            audio_input.collection_id,
            user_id,
        )

        # Create podcast record
        podcast_record = self.repository.create(
            user_id=user_id,
            collection_id=audio_input.collection_id,
            duration=audio_input.duration.value
            if isinstance(audio_input.duration, PodcastDuration)
            else audio_input.duration,
            voice_settings={},  # Empty dict - voices handled separately
            host_voice=audio_input.host_voice,
            expert_voice=audio_input.expert_voice,
            audio_format=audio_input.audio_format.value
            if isinstance(audio_input.audio_format, AudioFormat)
            else audio_input.audio_format,
            title=audio_input.title,
        )

        # Schedule background processing with the actual podcast ID from database
        background_tasks.add_task(
            self._process_audio_from_script,
            podcast_record.podcast_id,
            audio_input,
        )

        logger.info(
            "Podcast %s queued for audio generation (script-to-audio)",
            podcast_record.podcast_id,
        )

        return self.repository.to_schema(podcast_record)

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
                status=PodcastStatus.GENERATING,
                progress=0,
                step="parsing_script",
            )

            # Step 2: Parse script
            logger.info("Parsing script into dialogue turns")
            parsing_result = self.script_parser.parse(audio_input.script_text)
            podcast_script = parsing_result.script

            if parsing_result.parsing_warnings:
                logger.warning(
                    "Script parsing warnings for %s: %s",
                    podcast_id,
                    parsing_result.parsing_warnings,
                )

            await self._update_progress(
                podcast_id,
                progress=30,
                step="generating_audio",
            )

            # Step 3: Generate audio
            # Convert audio_input to PodcastGenerationInput for _generate_audio compatibility
            logger.info("Generating multi-voice audio")
            podcast_input_for_audio = PodcastGenerationInput(
                user_id=audio_input.user_id,
                collection_id=audio_input.collection_id,
                duration=audio_input.duration,
                voice_settings={"voice_id": audio_input.host_voice},  # Minimal voice settings
                host_voice=audio_input.host_voice,
                expert_voice=audio_input.expert_voice,
                format=audio_input.audio_format,
                title=audio_input.title,
            )

            audio_bytes = await self._generate_audio(
                podcast_id,
                podcast_script,
                podcast_input_for_audio,
            )

            await self._update_progress(
                podcast_id,
                progress=80,
                step="storing_audio",
            )

            # Step 4: Store audio
            logger.info("Storing audio file")
            audio_url = await self._store_audio(
                podcast_id=podcast_id,
                user_id=audio_input.user_id,
                audio_bytes=audio_bytes,
                audio_format=audio_input.audio_format,
            )

            # Step 5: Mark completed
            self.repository.mark_completed(
                podcast_id=podcast_id,
                audio_url=audio_url,
                transcript=audio_input.script_text,
                audio_size_bytes=len(audio_bytes),
            )

            logger.info("Audio generation completed for podcast %s", podcast_id)

        except Exception as e:
            logger.exception("Audio generation failed for podcast %s", podcast_id)
            await self._cleanup_failed_podcast(
                podcast_id=podcast_id,
                user_id=audio_input.user_id,
                audio_stored=False,
                error_message=str(e),
            )
            raise
