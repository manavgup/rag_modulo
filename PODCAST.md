# 🎙️ Issue #240: Podcast Generation and AI Evaluation Feature - Implementation Plan

## 📋 Overview
This document outlines the comprehensive implementation plan for adding podcast generation capabilities with real-time interactive Q&A and AI-powered evaluation features to the RAG Modulo platform.

---

## 🏗️ Architecture Overview

### Core Innovation: Real-Time Interactive Podcasts
- **During podcast playback**, users can ask questions at any moment
- **Immediate RAG search** using existing SearchService and ChainOfThoughtService
- **Dynamic audio insertion** with seamless transitions
- **Version control** for evolving podcast content
- **WebSocket-based** real-time updates

---

## 🔄 Integration with Existing Services

### 1. **Document Processing Pipeline Integration**
The podcast generation will leverage the existing document processing infrastructure:

```python
class PodcastGenerationService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        # Leverage existing services
        self.search_service = SearchService(db, settings)
        self.chain_of_thought_service = ChainOfThoughtService(db, settings)
        self.conversation_service = ConversationService(db, settings)
        self.file_service = FileManagementService(settings)

    async def generate_podcast_content(self, podcast_input: PodcastCreationInput):
        """Generate podcast content from selected documents"""

        # 1. Use existing document retrieval from collection
        documents = await self.file_service.get_collection_documents(
            podcast_input.collection_id,
            podcast_input.selected_document_ids
        )

        # 2. Process documents through existing pipeline
        processed_content = []
        for doc in documents:
            # Use existing document processing pipeline
            doc_content = await self.file_service.extract_document_content(doc.id)
            processed_content.append(doc_content)

        # 3. Generate podcast script using Chain of Thought
        podcast_script = await self._generate_script_with_cot(
            processed_content,
            podcast_input.duration_minutes
        )

        return podcast_script

    async def _generate_script_with_cot(self, content: List[str], duration_minutes: int):
        """Use Chain of Thought to create coherent podcast narrative"""

        # Leverage existing CoT for content organization
        cot_request = {
            "question": f"Create a {duration_minutes}-minute podcast script from these documents",
            "context": content,
            "config_metadata": {
                "cot_enabled": True,
                "output_format": "podcast_script",
                "target_duration": duration_minutes
            }
        }

        # Use existing CoT service for intelligent content structuring
        script = await self.chain_of_thought_service.process_with_reasoning(cot_request)

        return script
```

### 2. **SearchService Integration for Real-Time Q&A**
```python
class InteractivePodcastService:
    async def process_real_time_question(
        self,
        playback_session_id: UUID,
        question: str,
        current_timestamp: float
    ):
        """Process user question using existing RAG infrastructure"""

        session = await self.get_playback_session(playback_session_id)
        podcast = session.podcast

        # Use existing SearchService with automatic pipeline resolution
        search_input = SearchInput(
            question=question,
            collection_id=podcast.collection_id,
            user_id=session.user_id,
            config_metadata={
                "context_type": "podcast_interaction",
                "timestamp": current_timestamp,
                "cot_enabled": True,  # Enable CoT for complex questions
                "show_cot_steps": False  # Don't show steps in audio
            }
        )

        # Leverage existing search with CoT enhancement
        search_result = await self.search_service.search(search_input)

        # Format for audio response
        audio_response = await self._format_for_audio(search_result)

        return audio_response
```

### 3. **Chain of Thought Service for Content Quality**
```python
async def enhance_podcast_with_cot(self, podcast_content: str, interactions: List[Interaction]):
    """Use CoT to ensure coherent narrative with Q&A insertions"""

    # Analyze narrative flow
    flow_analysis = await self.chain_of_thought_service.analyze_content_flow(
        main_content=podcast_content,
        insertions=interactions,
        objective="maintain_narrative_coherence"
    )

    # Generate transition segments
    transitions = await self.chain_of_thought_service.generate_transitions(
        flow_analysis,
        voice_style="conversational"
    )

    return transitions
```

---

## 🎯 Multi-Modal Model for Audio Generation

### Exclusive Multi-Modal Approach

We will use **only multi-modal models** for all audio generation, leveraging the advanced capabilities of modern LLMs:

### 1. **Unified Architecture**
```python
class MultiModalAudioService:
    def __init__(self, settings: Settings):
        self.settings = settings
        # Use existing LLM provider infrastructure
        self.llm_service = LLMProviderService(settings)

    async def generate_audio_from_text(
        self,
        text: str,
        voice_parameters: dict = None
    ) -> bytes:
        """Generate audio using multi-modal models"""

        provider = self.llm_service.get_user_provider()

        if provider.supports_audio_generation():
            # Use native multi-modal capabilities
            audio_response = await provider.generate_audio(
                text=text,
                voice_settings=voice_parameters,
                output_format="mp3"
            )
        else:
            # Require multi-modal support for audio generation
            raise ValueError(f"Provider {provider} does not support audio generation. Please use a provider with multi-modal capabilities.")

        return audio_response
```

### 2. **Provider-Specific Multi-Modal Implementation**

#### **OpenAI Integration**
```python
class OpenAIMultiModalProvider(LLMProvider):
    async def generate_audio(self, text: str, voice_settings: dict):
        """Use OpenAI's multi-modal capabilities"""
        # OpenAI's new models support audio generation
        response = await self.client.audio.speech.create(
            model="tts-1-hd",
            voice=voice_settings.get("voice", "alloy"),
            input=text,
            response_format="mp3"
        )
        return response.content
```

#### **Anthropic Integration**
```python
class AnthropicMultiModalProvider(LLMProvider):
    async def generate_audio(self, text: str, voice_settings: dict):
        """Use Anthropic's multi-modal capabilities when available"""
        # Anthropic's Claude can process audio (future capability)
        # For now, use their text generation with audio markup
        pass
```

#### **WatsonX Integration**
```python
class WatsonXMultiModalProvider(LLMProvider):
    async def generate_audio(self, text: str, voice_settings: dict):
        """Use IBM WatsonX multi-modal capabilities"""
        # WatsonX multi-modal audio generation
        audio_response = await self.client.generate_multi_modal(
            text=text,
            mode="audio",
            voice=voice_settings.get("voice", "professional"),
            format="mp3"
        )

        return audio_response.content
```

### 3. **Advantages of Multi-Modal Approach**

- **Context Awareness**: Multi-modal models understand document context for appropriate emphasis and pacing
- **Emotion & Tone**: Automatic tone adjustment based on content type and narrative flow
- **Question Handling**: Native understanding of Q&A interactions for seamless integration
- **Cost Efficiency**: Single API call for both text and audio generation
- **Consistency**: Unified voice and style across all podcast content
- **Future-Proof**: Evolving capabilities as multi-modal models advance

### 4. **Enhanced Implementation with Multi-Modal**
```python
class EnhancedPodcastGenerationService:
    async def generate_interactive_podcast(
        self,
        collection_id: UUID,
        user_id: UUID,
        duration_minutes: int
    ):
        """Generate podcast using multi-modal capabilities"""

        # 1. Generate content using existing RAG pipeline
        content = await self.search_service.get_collection_summary(collection_id)

        # 2. Use multi-modal model for script AND audio generation
        provider = self.llm_service.get_user_provider(user_id)

        if provider.supports_multi_modal():
            # Single call for script + audio
            podcast_response = await provider.generate_multi_modal(
                prompt=f"Create a {duration_minutes}-minute podcast about: {content}",
                output_formats=["text", "audio"],
                audio_settings={
                    "voice": "professional",
                    "pace": "moderate",
                    "style": "educational"
                }
            )

            return {
                "script": podcast_response.text,
                "audio": podcast_response.audio,
                "metadata": podcast_response.metadata
            }
        else:
            # Multi-modal support required
            raise ValueError(f"Provider must support multi-modal generation for podcast creation")
```

---

## 📊 Database Schema

### 1. **Podcast Model** (`rag_solution/models/podcast.py`)
```python
class Podcast(Base):
    __tablename__ = "podcasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Generation Configuration
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    voice_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    selected_document_ids: Mapped[list] = mapped_column(JSON, default=list)
    generation_model: Mapped[str] = mapped_column(String(100), nullable=True)  # Which multi-modal model used

    # Processing Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    generation_progress: Mapped[int] = mapped_column(Integer, default=0)

    # Audio File Information
    audio_file_path: Mapped[str] = mapped_column(String, nullable=True)
    audio_format: Mapped[str] = mapped_column(String(10), default="mp3")
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)

    # Script and Metadata
    podcast_script: Mapped[str] = mapped_column(Text, nullable=True)  # Generated script
    generation_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="podcasts")
    collection = relationship("Collection", back_populates="podcasts")
    playback_sessions = relationship("PodcastPlaybackSession", back_populates="podcast", cascade="all, delete-orphan")
    interactions = relationship("PodcastInteraction", back_populates="podcast", cascade="all, delete-orphan")
    versions = relationship("PodcastVersion", back_populates="podcast", cascade="all, delete-orphan")
```

### 2. **PodcastInteraction Model** (`rag_solution/models/podcast_interaction.py`)
```python
class PodcastInteraction(Base):
    __tablename__ = "podcast_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    podcast_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("podcasts.id"), nullable=False)
    playback_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("podcast_playback_sessions.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Interaction Details
    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=True)

    # RAG Integration
    search_results: Mapped[dict] = mapped_column(JSON, default=dict)  # SearchService results
    cot_reasoning: Mapped[dict] = mapped_column(JSON, default=dict)  # ChainOfThought reasoning steps
    source_documents: Mapped[list] = mapped_column(JSON, default=list)  # Document references

    # Audio Generation
    audio_response_path: Mapped[str] = mapped_column(String, nullable=True)
    audio_duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    generation_model: Mapped[str] = mapped_column(String(100), nullable=True)  # Multi-modal model used

    # Processing Status
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    podcast = relationship("Podcast", back_populates="interactions")
```

### 3. **MediaUpload Model** (`rag_solution/models/media_upload.py`)
```python
class MediaUpload(Base):
    __tablename__ = "media_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # File Information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Multi-Modal Evaluation
    evaluation_model: Mapped[str] = mapped_column(String(100), nullable=True)
    evaluation_results: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluation_score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="media_uploads")
```

---

## 🌐 API Endpoints

### Podcast Generation & Management
```python
# POST /api/podcasts - Create new podcast
# GET /api/podcasts/{id} - Get podcast details
# PUT /api/podcasts/{id} - Update podcast
# DELETE /api/podcasts/{id} - Delete podcast
# GET /api/podcasts - List user podcasts

# POST /api/podcasts/{id}/generate - Start generation
# GET /api/podcasts/{id}/status - Get generation status
# GET /api/podcasts/{id}/stream - Stream audio

# Real-time Q&A
# POST /api/podcasts/{id}/interactions - Ask question during playback
# GET /api/podcasts/interactions/{id}/audio - Get Q&A audio
# WebSocket /api/podcasts/{id}/live-interactions - Real-time updates
```

---

## ⚛️ Frontend Components

```
frontend/src/components/podcast/
├── PodcastGenerationModal.tsx       # Creation interface
├── InteractivePodcastPlayer.tsx     # Player with Q&A capability
├── QuestionModal.tsx                 # Real-time question interface
├── InteractionSidebar.tsx           # Q&A responses display
└── PodcastLibrary.tsx               # User's podcast collection

frontend/src/components/evaluation/
├── MediaUploadModal.tsx             # Upload interface
├── EvaluationResults.tsx            # AI feedback display
└── EvaluationReport.tsx             # Detailed analysis
```

---

## 📊 Implementation Phases

| **Phase** | **Duration** | **Key Features** | **Services Used** |
|-----------|-------------|------------------|-------------------|
| **Phase 1** | 4 weeks | Core podcast generation | SearchService, CoT, Multi-modal |
| **Phase 2** | 3 weeks | Real-time Q&A system | SearchService, WebSocket |
| **Phase 3** | 4 weeks | AI pitch evaluation | Multi-modal evaluation |
| **Phase 4** | 2 weeks | Polish & optimization | All services |

---

## 🚀 Key Benefits of This Approach

1. **Leverages Existing Infrastructure**
   - Uses existing SearchService with automatic pipeline resolution
   - Integrates ChainOfThoughtService for content quality
   - Reuses document processing pipeline
   - Extends ConversationService patterns

2. **Multi-Modal Model Excellence**
   - Single API for text + audio generation
   - Context-aware voice synthesis with document understanding
   - Consistent quality and voice across all content
   - Future-proof as multi-modal capabilities advance

3. **Real-Time Interactivity**
   - WebSocket infrastructure already in place
   - RAG search provides accurate answers
   - CoT ensures coherent responses
   - Dynamic content updates

4. **Cost Optimization**
   - Unified billing through existing LLM providers
   - Single API call for both text and audio
   - Efficient resource utilization

---

## 🎯 Next Steps

1. **Prototype multi-modal audio generation** with existing providers
2. **Extend SearchService** for podcast-specific queries
3. **Implement WebSocket handlers** for real-time Q&A
4. **Create database migrations** for new models
5. **Build frontend components** incrementally

This implementation fully leverages the existing RAG infrastructure while adding revolutionary interactive podcast capabilities powered exclusively by multi-modal models.
