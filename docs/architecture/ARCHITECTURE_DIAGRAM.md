# RAG Technique System - Architecture Diagrams

## Overview Architecture

```mermaid
graph TB
    subgraph "API Layer"
        A[SearchInput] --> |techniques config| B[SearchService]
        A --> |technique_preset| B
        A --> |config_metadata<br/>legacy| B
    end

    subgraph "Technique Orchestration Layer NEW"
        B --> C[TechniquePipelineBuilder]
        C --> D[TechniquePipeline]
        D --> E[TechniqueContext]
        E --> F1[Technique 1]
        E --> F2[Technique 2]
        E --> F3[Technique N]
    end

    subgraph "Adapter Layer NEW"
        F1 --> |wraps| G1[VectorRetrievalTechnique]
        F2 --> |wraps| G2[HybridRetrievalTechnique]
        F3 --> |wraps| G3[LLMRerankingTechnique]
    end

    subgraph "Existing Infrastructure REUSED"
        G1 --> |delegates to| H1[VectorRetriever]
        G2 --> |delegates to| H2[HybridRetriever]
        G3 --> |delegates to| H3[LLMReranker]

        H1 --> I1[Vector Store]
        H2 --> I1
        H2 --> I2[Keyword TF-IDF]
        H3 --> I3[LLM Provider]
    end

    subgraph "Services & Infrastructure EXISTING"
        I1 --> J1[Milvus/Elasticsearch/etc.]
        I3 --> J2[WatsonX/OpenAI/Anthropic]
    end

    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#fff4e1
    style E fill:#fff4e1
    style F1 fill:#fff4e1
    style F2 fill:#fff4e1
    style F3 fill:#fff4e1
    style G1 fill:#f0fff4
    style G2 fill:#f0fff4
    style G3 fill:#f0fff4
    style H1 fill:#f5f5f5
    style H2 fill:#f5f5f5
    style H3 fill:#f5f5f5
```

**Legend:**
- 🔵 Blue: API Layer (Entry Point)
- 🟡 Yellow: NEW - Technique Orchestration
- 🟢 Green: NEW - Adapter Techniques
- ⚪ Gray: EXISTING - Reused Infrastructure

---

## Detailed Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant API as SearchInput
    participant Service as SearchService
    participant Builder as PipelineBuilder
    participant Pipeline as TechniquePipeline
    participant Context as TechniqueContext
    participant VT as VectorTechnique<br/>(Adapter)
    participant VR as VectorRetriever<br/>(Existing)
    participant VS as Vector Store<br/>(Existing)
    participant RT as RerankingTechnique<br/>(Adapter)
    participant RR as LLMReranker<br/>(Existing)
    participant LLM as LLM Provider<br/>(Existing)

    User->>API: SearchInput(techniques=[...])
    API->>Service: search(search_input)

    Note over Service: Step 1: Build Pipeline
    Service->>Builder: build_pipeline(techniques)
    Builder->>Builder: Validate techniques
    Builder->>Builder: Instantiate adapters
    Builder-->>Service: TechniquePipeline

    Note over Service: Step 2: Create Context
    Service->>Context: Create with dependencies
    Service->>Context: Inject llm_provider
    Service->>Context: Inject vector_store
    Service->>Context: Inject db_session

    Note over Service: Step 3: Execute Pipeline
    Service->>Pipeline: execute(context)

    loop For each technique
        Pipeline->>VT: execute(context)

        Note over VT: Adapter wraps existing
        VT->>VR: Instantiate VectorRetriever
        VT->>VR: retrieve(collection, query)

        Note over VR: Existing implementation
        VR->>VS: retrieve_documents(query)
        VS-->>VR: QueryResult[]
        VR-->>VT: QueryResult[]

        VT->>Context: Update retrieved_documents
        VT-->>Pipeline: TechniqueResult

        Pipeline->>RT: execute(context)

        Note over RT: Adapter wraps existing
        RT->>RR: Instantiate LLMReranker
        RT->>RR: rerank(query, documents)

        Note over RR: Existing implementation
        RR->>LLM: generate_text(prompts)
        LLM-->>RR: Scores
        RR->>RR: Extract & normalize scores
        RR-->>RT: Reranked results

        RT->>Context: Update retrieved_documents
        RT-->>Pipeline: TechniqueResult
    end

    Pipeline->>Context: Add metrics
    Pipeline-->>Service: Updated Context

    Note over Service: Step 4: Generate Answer
    Service->>LLM: generate(query, documents)
    LLM-->>Service: Answer

    Service-->>API: SearchOutput + metrics
    API-->>User: Response with techniques_applied
```

---

## Adapter Pattern Detail

```mermaid
graph LR
    subgraph "Technique Adapter NEW"
        A[VectorRetrievalTechnique<br/>BaseTechnique]
        A --> |implements| B[execute method]
    end

    subgraph "Adapter Implementation"
        B --> C{Has retriever?}
        C -->|No| D[Create VectorRetriever<br/>from context.vector_store]
        C -->|Yes| E[Reuse existing instance]
        D --> F[Call retriever.retrieve]
        E --> F
    end

    subgraph "Existing Component REUSED"
        F --> G[VectorRetriever.retrieve<br/>EXISTING CODE]
        G --> H[document_store.vector_store<br/>EXISTING CODE]
        H --> I[Milvus/Elasticsearch/etc.<br/>EXISTING INFRASTRUCTURE]
    end

    subgraph "Result Wrapping"
        I --> J[QueryResult EXISTING]
        J --> K[Wrap in TechniqueResult<br/>NEW]
        K --> L[Update Context<br/>NEW]
    end

    style A fill:#f0fff4
    style B fill:#f0fff4
    style C fill:#f0fff4
    style D fill:#f0fff4
    style E fill:#f0fff4
    style F fill:#f0fff4
    style G fill:#f5f5f5
    style H fill:#f5f5f5
    style I fill:#f5f5f5
    style J fill:#f5f5f5
    style K fill:#fff4e1
    style L fill:#fff4e1
```

---

## Technique Context Data Flow

```mermaid
graph TB
    subgraph "Context Input"
        A[TechniqueContext Created]
        A --> B[user_id: UUID]
        A --> C[collection_id: UUID]
        A --> D[original_query: str]
    end

    subgraph "Injected Dependencies EXISTING"
        A --> E[llm_provider: LLMBase<br/>from LLMProviderService]
        A --> F[vector_store: VectorStore<br/>from CollectionService]
        A --> G[db_session: Session<br/>from FastAPI dependency]
    end

    subgraph "Pipeline State MUTABLE"
        A --> H[current_query: str<br/>can be transformed]
        A --> I[retrieved_documents: list<br/>updated by techniques]
        A --> J[intermediate_results: dict<br/>technique outputs]
    end

    subgraph "Observability"
        A --> K[metrics: dict<br/>performance data]
        A --> L[execution_trace: list<br/>technique IDs]
    end

    subgraph "Technique 1: Query Transform"
        H --> M[Transform query]
        M --> N[Update current_query]
        N --> O[Store in intermediate_results]
    end

    subgraph "Technique 2: Vector Retrieval"
        N --> P[Use current_query]
        F --> P
        P --> Q[VectorRetriever.retrieve]
        Q --> R[Update retrieved_documents]
    end

    subgraph "Technique 3: Reranking"
        R --> S[Use retrieved_documents]
        E --> S
        S --> T[LLMReranker.rerank]
        T --> U[Update retrieved_documents]
    end

    U --> V[Final Context State]
    K --> V
    L --> V

    style E fill:#f5f5f5
    style F fill:#f5f5f5
    style G fill:#f5f5f5
    style Q fill:#f5f5f5
    style T fill:#f5f5f5
```

---

## Technique Registry & Discovery

```mermaid
graph TB
    subgraph "Technique Registration"
        A[@register_technique decorator]
        A --> B[VectorRetrievalTechnique]
        A --> C[HybridRetrievalTechnique]
        A --> D[LLMRerankingTechnique]

        B --> E[TechniqueRegistry.register]
        C --> E
        D --> E
    end

    subgraph "Registry Storage"
        E --> F[_techniques: dict<br/>technique_id -> class]
        E --> G[_metadata_cache: dict<br/>technique_id -> metadata]
        E --> H[_instances: dict<br/>technique_id -> singleton]
    end

    subgraph "Discovery & Validation"
        I[User Request] --> J[technique_ids: list]
        J --> K{Registered?}
        K -->|Yes| L[Get metadata]
        K -->|No| M[Error: Unknown technique]

        L --> N[Validate pipeline]
        N --> O{Valid stages?}
        O -->|Yes| P{Compatible?}
        O -->|No| Q[Error: Invalid ordering]

        P -->|Yes| R[Build pipeline]
        P -->|No| S[Error: Incompatible]
    end

    subgraph "Instantiation"
        R --> T{Singleton?}
        T -->|Yes| U[Return cached instance]
        T -->|No| V[Create new instance]

        U --> W[TechniquePipeline]
        V --> W
    end

    style A fill:#fff4e1
    style E fill:#fff4e1
    style F fill:#fff4e1
    style G fill:#fff4e1
    style H fill:#fff4e1
```

---

## Complete System Integration

```mermaid
graph TB
    subgraph "User Request"
        A[POST /search<br/>SearchInput]
    end

    subgraph "FastAPI Router"
        A --> B[search_endpoint<br/>router.py]
    end

    subgraph "SearchService EXISTING"
        B --> C[SearchService.search]
        C --> D{Uses techniques?}

        D -->|Yes| E[Build technique pipeline]
        D -->|No| F[Use default retrieval]

        E --> G[Create TechniqueContext]
        F --> G
    end

    subgraph "Service Dependencies EXISTING"
        G --> H[LLMProviderService<br/>get_provider user_id]
        G --> I[CollectionService<br/>get_vector_store collection_id]
        G --> J[Database Session<br/>SQLAlchemy]
    end

    subgraph "Technique Pipeline NEW"
        H --> K[TechniqueContext]
        I --> K
        J --> K

        K --> L[Pipeline.execute]

        L --> M[VectorRetrievalTechnique]
        L --> N[RerankingTechnique]
        L --> O[...other techniques]
    end

    subgraph "Existing Retrievers REUSED"
        M --> P[VectorRetriever<br/>EXISTING]
        N --> Q[LLMReranker<br/>EXISTING]
        O --> R[Other components<br/>EXISTING]
    end

    subgraph "Existing Infrastructure REUSED"
        P --> S[Vector Store<br/>Milvus/ES/etc.]
        Q --> T[LLM Provider<br/>WatsonX/OpenAI]
        R --> U[Services<br/>CoT/Attribution/etc.]
    end

    subgraph "Result Assembly"
        L --> V[Updated Context]
        V --> W[Generate answer<br/>EXISTING]
        W --> X[SearchOutput]

        X --> Y[answer: str]
        X --> Z[documents: list]
        X --> AA[techniques_applied: list NEW]
        X --> AB[technique_metrics: dict NEW]
    end

    AB --> AC[Response to user]

    style C fill:#f5f5f5
    style D fill:#f5f5f5
    style F fill:#f5f5f5
    style H fill:#f5f5f5
    style I fill:#f5f5f5
    style J fill:#f5f5f5
    style P fill:#f5f5f5
    style Q fill:#f5f5f5
    style R fill:#f5f5f5
    style S fill:#f5f5f5
    style T fill:#f5f5f5
    style U fill:#f5f5f5
    style W fill:#f5f5f5

    style E fill:#fff4e1
    style G fill:#fff4e1
    style K fill:#fff4e1
    style L fill:#fff4e1
    style M fill:#f0fff4
    style N fill:#f0fff4
    style O fill:#f0fff4
    style AA fill:#fff4e1
    style AB fill:#fff4e1
```

---

## Preset Configuration Flow

```mermaid
graph LR
    subgraph "User Selects Preset"
        A[SearchInput<br/>technique_preset='accurate']
    end

    subgraph "Preset Resolution"
        A --> B{Preset exists?}
        B -->|Yes| C[TECHNIQUE_PRESETS<br/>'accurate']
        B -->|No| D[Error: Unknown preset]

        C --> E[List of TechniqueConfig]
    end

    subgraph "Preset Definition"
        E --> F[TechniqueConfig<br/>query_transformation]
        E --> G[TechniqueConfig<br/>hyde]
        E --> H[TechniqueConfig<br/>fusion_retrieval]
        E --> I[TechniqueConfig<br/>reranking]
        E --> J[TechniqueConfig<br/>contextual_compression]
    end

    subgraph "Pipeline Building"
        F --> K[PipelineBuilder]
        G --> K
        H --> K
        I --> K
        J --> K

        K --> L[Validate ordering]
        L --> M[Instantiate techniques]
        M --> N[TechniquePipeline]
    end

    subgraph "Execution"
        N --> O[Execute in sequence]
        O --> P[Each technique wraps<br/>existing component]
    end

    style A fill:#e1f5ff
    style C fill:#fff4e1
    style K fill:#fff4e1
    style N fill:#fff4e1
    style P fill:#f0fff4
```

---

## Technique Compatibility Matrix

```mermaid
graph TB
    subgraph "Technique Stages Pipeline"
        A[QUERY_PREPROCESSING] --> B[QUERY_TRANSFORMATION]
        B --> C[RETRIEVAL]
        C --> D[POST_RETRIEVAL]
        D --> E[RERANKING]
        E --> F[COMPRESSION]
        F --> G[GENERATION]
    end

    subgraph "Available Techniques by Stage"
        H[Query Transform<br/>HyDE<br/>Step-back] -.-> B
        I[Vector Retrieval<br/>Hybrid Retrieval<br/>Fusion Retrieval] -.-> C
        J[Filtering<br/>Deduplication] -.-> D
        K[LLM Reranking<br/>Score-based] -.-> E
        L[Contextual Compression<br/>Summarization] -.-> F
        M[Answer Generation<br/>CoT] -.-> G
    end

    subgraph "Validation Rules"
        N[Stage ordering enforced]
        O[Compatible techniques checked]
        P[Required dependencies verified]
    end

    style A fill:#ffe6e6
    style B fill:#fff0e6
    style C fill:#ffffcc
    style D fill:#e6ffe6
    style E fill:#e6f2ff
    style F fill:#f0e6ff
    style G fill:#ffe6f0
```

---

## Code Structure Overview

```mermaid
graph TB
    subgraph "backend/rag_solution/"
        A[techniques/]
        B[retrieval/]
        C[services/]
        D[schemas/]
    end

    subgraph "techniques/ NEW"
        A --> E[__init__.py<br/>Package exports]
        A --> F[base.py<br/>BaseTechnique, Context, Result]
        A --> G[registry.py<br/>TechniqueRegistry]
        A --> H[pipeline.py<br/>Builder, Pipeline, Presets]
        A --> I[implementations/<br/>Concrete techniques]
    end

    subgraph "implementations/ NEW"
        I --> J[__init__.py<br/>Auto-registration]
        I --> K[adapters.py<br/>Wrap existing components]
    end

    subgraph "retrieval/ EXISTING REUSED"
        B --> L[retriever.py<br/>VectorRetriever, HybridRetriever]
        B --> M[reranker.py<br/>LLMReranker]
    end

    subgraph "Integration"
        K -.wraps.-> L
        K -.wraps.-> M

        D --> N[search_schema.py<br/>SearchInput, SearchOutput]
        N --> O[+ techniques field<br/>+ technique_preset field]
        N --> P[+ techniques_applied<br/>+ technique_metrics]
    end

    style E fill:#fff4e1
    style F fill:#fff4e1
    style G fill:#fff4e1
    style H fill:#fff4e1
    style I fill:#fff4e1
    style J fill:#f0fff4
    style K fill:#f0fff4
    style L fill:#f5f5f5
    style M fill:#f5f5f5
    style O fill:#e1f5ff
    style P fill:#e1f5ff
```

---

## Legend

### Colors
- 🔵 **Blue** (#e1f5ff): API Layer / User-facing
- 🟡 **Yellow** (#fff4e1): NEW - Orchestration & Framework
- 🟢 **Green** (#f0fff4): NEW - Adapter Implementations
- ⚪ **Gray** (#f5f5f5): EXISTING - Reused Components

### Arrows
- **Solid arrows** (→): Direct dependency or data flow
- **Dashed arrows** (-.->): Conceptual relationship or wrapping

### Key Principles
1. **Thin orchestration layer**: Pipeline & context management
2. **Adapter pattern**: Techniques wrap existing components
3. **100% reuse**: No duplicate retrieval/reranking logic
4. **Dependency injection**: Services provided via context
5. **Backward compatible**: Legacy API still works

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Architecture Visualization ✅
