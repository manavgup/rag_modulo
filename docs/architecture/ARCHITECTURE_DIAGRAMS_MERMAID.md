# RAG Technique System - Architecture Diagrams (Mermaid)

## Overview

This document contains mermaid diagrams visualizing the RAG technique system architecture, organized by priority and complexity similar to the RAG techniques analysis.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    A[User Request<br/>SearchInput] --> B[SearchService<br/>EXISTING]
    B --> C{Technique<br/>Pipeline?}

    C -->|Yes - NEW| D[Pipeline Builder]
    C -->|No - Legacy| E[Direct Retrieval]

    D --> F[Technique Pipeline<br/>NEW]
    E --> F

    F --> G[Technique Context<br/>NEW]
    G --> H[Vector Retrieval<br/>Adapter NEW]
    G --> I[Hybrid Retrieval<br/>Adapter NEW]
    G --> J[LLM Reranking<br/>Adapter NEW]

    H --> K[VectorRetriever<br/>EXISTING]
    I --> L[HybridRetriever<br/>EXISTING]
    J --> M[LLMReranker<br/>EXISTING]

    K --> N[Vector Store<br/>Milvus/ES/etc.]
    L --> N
    L --> O[Keyword<br/>TF-IDF]
    M --> P[LLM Provider<br/>WatsonX/OpenAI]

    F --> Q[SearchOutput]
    Q --> R[Answer + Metrics<br/>+ Techniques Applied]

    classDef new fill:#fff4e1,stroke:#ffa500,stroke-width:2px
    classDef adapter fill:#f0fff4,stroke:#00aa00,stroke-width:2px
    classDef existing fill:#f5f5f5,stroke:#666,stroke-width:2px

    class D,F,G,R new
    class H,I,J adapter
    class B,E,K,L,M,N,O,P existing
```

**Color Legend:**
- 🟡 Yellow: NEW orchestration framework
- 🟢 Green: NEW adapter implementations
- ⚪ Gray: EXISTING reused components

---

## 2. Adapter Pattern - How Techniques Wrap Existing Components

```mermaid
flowchart LR
    subgraph NEW["NEW: Adapter Technique"]
        A[VectorRetrievalTechnique]
        A --> B[execute method]
    end

    subgraph Wrapping["Wrapping Logic"]
        B --> C{Has<br/>retriever?}
        C -->|No| D[Create from<br/>context.vector_store]
        C -->|Yes| E[Reuse instance]
        D --> F[Delegate to<br/>existing component]
        E --> F
    end

    subgraph EXISTING["EXISTING: Component"]
        F --> G[VectorRetriever.retrieve]
        G --> H[DocumentStore.vector_store]
        H --> I[Milvus/Elasticsearch/etc.]
    end

    subgraph Result["Result Wrapping"]
        I --> J[QueryResult<br/>EXISTING]
        J --> K[Wrap in<br/>TechniqueResult<br/>NEW]
        K --> L[Update Context<br/>NEW]
    end

    classDef new fill:#fff4e1,stroke:#ffa500,stroke-width:2px
    classDef existing fill:#f5f5f5,stroke:#666,stroke-width:2px

    class A,B,D,E,K,L new
    class G,H,I,J existing
```

---

## 3. Technique Execution Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant SI as SearchInput
    participant SS as SearchService
    participant PB as PipelineBuilder
    participant P as Pipeline
    participant C as Context
    participant VT as VectorTechnique
    participant VR as VectorRetriever
    participant VS as VectorStore
    participant RT as RerankTechnique
    participant RR as LLMReranker
    participant LLM as LLM Provider

    U->>SI: POST /search with techniques
    SI->>SS: search(input)

    Note over SS,PB: Step 1: Build Pipeline
    SS->>PB: build_pipeline(techniques)
    PB->>PB: validate + instantiate
    PB-->>SS: Pipeline ready

    Note over SS,C: Step 2: Create Context
    SS->>C: inject dependencies
    SS->>C: llm_provider, vector_store

    Note over SS,P: Step 3: Execute Pipeline
    SS->>P: execute(context)

    P->>VT: execute(context)
    VT->>VR: retrieve(query)
    VR->>VS: search vectors
    VS-->>VR: results
    VR-->>VT: QueryResult[]
    VT->>C: update documents
    VT-->>P: TechniqueResult

    P->>RT: execute(context)
    RT->>RR: rerank(query, docs)
    RR->>LLM: score documents
    LLM-->>RR: scores
    RR-->>RT: reranked results
    RT->>C: update documents
    RT-->>P: TechniqueResult

    P->>C: add metrics
    P-->>SS: updated context

    Note over SS,LLM: Step 4: Generate Answer
    SS->>LLM: generate(query, docs)
    LLM-->>SS: answer

    SS-->>SI: SearchOutput + metrics
    SI-->>U: response
```

---

## 4. Technique Context Data Flow

```mermaid
flowchart TD
    subgraph Input["Context Inputs"]
        A[user_id]
        B[collection_id]
        C[original_query]
    end

    subgraph Dependencies["Injected Dependencies EXISTING"]
        D[llm_provider<br/>from LLMProviderService]
        E[vector_store<br/>from CollectionService]
        F[db_session<br/>from FastAPI]
    end

    subgraph State["Mutable Pipeline State"]
        G[current_query<br/>can be transformed]
        H[retrieved_documents<br/>updated by techniques]
        I[intermediate_results<br/>technique outputs]
    end

    subgraph Observability["Metrics & Tracing"]
        J[metrics dict]
        K[execution_trace list]
    end

    A & B & C --> L[TechniqueContext]
    D & E & F --> L
    L --> G & H & I
    L --> J & K

    G --> M[Technique 1<br/>Query Transform]
    M --> N[Update current_query]

    N --> O[Technique 2<br/>Vector Retrieval]
    E --> O
    O --> P[Update retrieved_documents]

    P --> Q[Technique 3<br/>Reranking]
    D --> Q
    Q --> R[Update retrieved_documents]

    R --> S[Final Context]
    J --> S
    K --> S

    classDef input fill:#e1f5ff,stroke:#0080ff,stroke-width:2px
    classDef existing fill:#f5f5f5,stroke:#666,stroke-width:2px
    classDef state fill:#fff4e1,stroke:#ffa500,stroke-width:2px

    class A,B,C input
    class D,E,F existing
    class G,H,I,J,K,L,M,N,O,P,Q,R,S state
```

---

## 5. Technique Registry & Validation

```mermaid
flowchart TD
    subgraph Registration["Technique Registration"]
        A[@register_technique<br/>decorator]
        A --> B[VectorRetrievalTechnique]
        A --> C[HybridRetrievalTechnique]
        A --> D[LLMRerankingTechnique]
    end

    B & C & D --> E[TechniqueRegistry.register]

    subgraph Storage["Registry Storage"]
        E --> F[techniques dict<br/>id -> class]
        E --> G[metadata_cache dict<br/>id -> metadata]
        E --> H[instances dict<br/>id -> singleton]
    end

    subgraph Discovery["Pipeline Validation"]
        I[User Request] --> J[technique_ids list]
        J --> K{All<br/>registered?}
        K -->|No| L[Error: Unknown]
        K -->|Yes| M[Get metadata]
        M --> N{Valid<br/>stage order?}
        N -->|No| O[Error: Invalid order]
        N -->|Yes| P{Compatible?}
        P -->|No| Q[Error: Incompatible]
        P -->|Yes| R[Valid Pipeline]
    end

    R --> S{Singleton?}
    S -->|Yes| T[Return cached]
    S -->|No| U[Create new]
    T & U --> V[Technique Pipeline]

    classDef reg fill:#fff4e1,stroke:#ffa500,stroke-width:2px
    classDef validate fill:#f0fff4,stroke:#00aa00,stroke-width:2px
    classDef error fill:#ffe6e6,stroke:#ff0000,stroke-width:2px

    class A,E,F,G,H reg
    class I,J,K,M,N,P,R,S,T,U,V validate
    class L,O,Q error
```

---

## 6. Complete System Integration

```mermaid
flowchart TD
    A[POST /search<br/>SearchInput] --> B[FastAPI Router]
    B --> C[SearchService.search<br/>EXISTING]

    C --> D{Uses<br/>techniques?}
    D -->|Yes| E[Build pipeline<br/>NEW]
    D -->|No| F[Default retrieval<br/>EXISTING]

    E & F --> G[Create Context<br/>NEW]

    subgraph Services["Service Dependencies EXISTING"]
        H[LLMProviderService]
        I[CollectionService]
        J[Database Session]
    end

    H --> K[llm_provider]
    I --> L[vector_store]
    J --> M[db_session]
    K & L & M --> G

    G --> N[Pipeline.execute<br/>NEW]

    subgraph Pipeline["Technique Adapters NEW"]
        N --> O[VectorRetrievalTechnique]
        N --> P[RerankingTechnique]
        N --> Q[Other Techniques]
    end

    subgraph Existing["Existing Components REUSED"]
        O --> R[VectorRetriever]
        P --> S[LLMReranker]
        Q --> T[Other Components]
    end

    subgraph Infrastructure["Existing Infrastructure"]
        R --> U[Vector Store<br/>Milvus/ES]
        S --> V[LLM Provider<br/>WatsonX/OpenAI]
        T --> W[Services<br/>CoT/Attribution]
    end

    N --> X[Updated Context]
    X --> Y[Generate Answer<br/>EXISTING]
    Y --> Z[SearchOutput]

    Z --> AA[answer]
    Z --> AB[documents]
    Z --> AC[techniques_applied<br/>NEW]
    Z --> AD[technique_metrics<br/>NEW]

    AD --> AE[Response to User]

    classDef new fill:#fff4e1,stroke:#ffa500,stroke-width:2px
    classDef adapter fill:#f0fff4,stroke:#00aa00,stroke-width:2px
    classDef existing fill:#f5f5f5,stroke:#666,stroke-width:2px

    class E,G,N,AC,AD new
    class O,P,Q adapter
    class C,D,F,H,I,J,R,S,T,U,V,W,Y existing
```

---

## 7. Technique Preset Configuration

```mermaid
flowchart LR
    A[User Selects<br/>technique_preset=accurate] --> B{Preset<br/>exists?}

    B -->|No| C[Error: Unknown preset]
    B -->|Yes| D[TECHNIQUE_PRESETS<br/>accurate]

    D --> E[List of<br/>TechniqueConfig]

    subgraph Preset["Preset: 'accurate'"]
        E --> F[1. query_transformation]
        E --> G[2. hyde]
        E --> H[3. fusion_retrieval]
        E --> I[4. reranking]
        E --> J[5. contextual_compression]
    end

    F & G & H & I & J --> K[PipelineBuilder]

    K --> L[Validate ordering]
    L --> M[Instantiate techniques]
    M --> N[TechniquePipeline]

    N --> O[Execute in sequence]
    O --> P[Each wraps<br/>existing component]

    classDef preset fill:#e1f5ff,stroke:#0080ff,stroke-width:2px
    classDef builder fill:#fff4e1,stroke:#ffa500,stroke-width:2px
    classDef adapter fill:#f0fff4,stroke:#00aa00,stroke-width:2px

    class A,D,E preset
    class K,L,M,N builder
    class P adapter
```

---

## 8. Technique Pipeline Stages

```mermaid
flowchart LR
    A[QUERY_PREPROCESSING] --> B[QUERY_TRANSFORMATION]
    B --> C[RETRIEVAL]
    C --> D[POST_RETRIEVAL]
    D --> E[RERANKING]
    E --> F[COMPRESSION]
    F --> G[GENERATION]

    subgraph Stage1["Stage 1"]
        A
    end

    subgraph Stage2["Stage 2"]
        B
    end

    subgraph Stage3["Stage 3"]
        C
    end

    subgraph Stage4["Stage 4"]
        D
    end

    subgraph Stage5["Stage 5"]
        E
    end

    subgraph Stage6["Stage 6"]
        F
    end

    subgraph Stage7["Stage 7"]
        G
    end

    classDef stage1 fill:#ffe6e6,stroke:#ff6666,stroke-width:2px
    classDef stage2 fill:#fff0e6,stroke:#ff9966,stroke-width:2px
    classDef stage3 fill:#ffffcc,stroke:#ffcc66,stroke-width:2px
    classDef stage4 fill:#e6ffe6,stroke:#66ff66,stroke-width:2px
    classDef stage5 fill:#e6f2ff,stroke:#6699ff,stroke-width:2px
    classDef stage6 fill:#f0e6ff,stroke:#9966ff,stroke-width:2px
    classDef stage7 fill:#ffe6f0,stroke:#ff66cc,stroke-width:2px

    class A stage1
    class B stage2
    class C stage3
    class D stage4
    class E stage5
    class F stage6
    class G stage7
```

---

## 9. Technique Priority Roadmap

```mermaid
flowchart TD
    subgraph HIGH["🔥 HIGH Priority - Quick Wins 2-3 weeks"]
        A1[HyDE<br/>2-3 days]
        A2[Contextual Compression<br/>2-3 days]
        A3[Query Transformations<br/>3-5 days]
        A4[Fusion Retrieval<br/>3-4 days]
    end

    subgraph MEDIUM["⚡ MEDIUM Priority - Core Enhancements 3-4 weeks"]
        B1[Semantic Chunking<br/>4-6 days]
        B2[Adaptive Retrieval<br/>4-5 days]
        B3[Multi-faceted Filtering<br/>3-4 days]
        B4[Contextual Headers<br/>2-3 days]
    end

    subgraph ADVANCED["💡 ADVANCED Priority - Advanced Features 3-4 weeks"]
        C1[Proposition Chunking<br/>5-7 days]
        C2[HyPE<br/>4-5 days]
        C3[RSE<br/>3-4 days]
        C4[Explainable Retrieval<br/>2-3 days]
    end

    subgraph FEEDBACK["🔁 FEEDBACK Priority - Iteration 2-3 weeks"]
        D1[Feedback Loops<br/>6-8 days]
        D2[Document Augmentation<br/>3-4 days]
    end

    HIGH --> MEDIUM
    MEDIUM --> ADVANCED
    ADVANCED --> FEEDBACK

    classDef high fill:#ffe6e6,stroke:#ff0000,stroke-width:3px
    classDef med fill:#fff4e1,stroke:#ffa500,stroke-width:2px
    classDef adv fill:#e6f2ff,stroke:#0080ff,stroke-width:2px
    classDef feed fill:#f0fff4,stroke:#00aa00,stroke-width:2px

    class A1,A2,A3,A4 high
    class B1,B2,B3,B4 med
    class C1,C2,C3,C4 adv
    class D1,D2 feed
```

---

## 10. Code Structure & File Organization

```mermaid
flowchart TD
    subgraph Backend["backend/rag_solution/"]
        A[techniques/<br/>NEW]
        B[retrieval/<br/>EXISTING]
        C[services/<br/>EXISTING]
        D[schemas/<br/>UPDATED]
    end

    subgraph Techniques["techniques/ NEW"]
        A --> E[__init__.py]
        A --> F[base.py<br/>BaseTechnique, Context]
        A --> G[registry.py<br/>TechniqueRegistry]
        A --> H[pipeline.py<br/>Builder, Pipeline]
        A --> I[implementations/]
    end

    subgraph Implementations["implementations/"]
        I --> J[__init__.py<br/>auto-registration]
        I --> K[adapters.py<br/>wraps existing]
    end

    subgraph Retrieval["retrieval/ EXISTING"]
        B --> L[retriever.py<br/>Vector, Hybrid]
        B --> M[reranker.py<br/>LLMReranker]
    end

    subgraph Integration["Integration"]
        K -.wraps.-> L
        K -.wraps.-> M
    end

    subgraph Schemas["schemas/ UPDATED"]
        D --> N[search_schema.py]
        N --> O[+ techniques field]
        N --> P[+ technique_preset]
        N --> Q[+ techniques_applied]
        N --> R[+ technique_metrics]
    end

    classDef new fill:#fff4e1,stroke:#ffa500,stroke-width:2px
    classDef adapter fill:#f0fff4,stroke:#00aa00,stroke-width:2px
    classDef existing fill:#f5f5f5,stroke:#666,stroke-width:2px
    classDef updated fill:#e1f5ff,stroke:#0080ff,stroke-width:2px

    class A,E,F,G,H,I,J new
    class K adapter
    class B,C,L,M existing
    class D,N,O,P,Q,R updated
```

---

## Testing on mermaid.live

To test these diagrams:

1. Go to https://mermaid.live
2. Copy any diagram code block (between the ```mermaid markers)
3. Paste into the editor
4. The diagram should render instantly

**All diagrams above have been validated for mermaid.live compatibility.**

---

## Diagram Index

| # | Diagram | Purpose | Complexity |
|---|---------|---------|------------|
| 1 | High-Level System Architecture | Overall system flow | Simple |
| 2 | Adapter Pattern | How techniques wrap existing code | Medium |
| 3 | Execution Sequence | Step-by-step execution flow | Medium |
| 4 | Context Data Flow | State management | Medium |
| 5 | Registry & Validation | Registration and validation | Complex |
| 6 | Complete Integration | Full system integration | Complex |
| 7 | Preset Configuration | How presets work | Simple |
| 8 | Pipeline Stages | Seven pipeline stages | Simple |
| 9 | Priority Roadmap | Implementation timeline | Simple |
| 10 | Code Structure | File organization | Medium |

---

## Color Legend

### By Layer
- 🔵 **Blue** (#e1f5ff): API Layer / User Input
- 🟡 **Yellow** (#fff4e1): NEW - Orchestration Framework
- 🟢 **Green** (#f0fff4): NEW - Adapter Implementations
- ⚪ **Gray** (#f5f5f5): EXISTING - Reused Components

### By Priority
- 🔴 **Red** (#ffe6e6): HIGH Priority (Quick Wins)
- 🟠 **Orange** (#fff4e1): MEDIUM Priority (Core Enhancements)
- 🔵 **Blue** (#e6f2ff): ADVANCED Priority (Advanced Features)
- 🟢 **Green** (#f0fff4): FEEDBACK Priority (Iteration)

---

**Document Version**: 2.0
**Last Updated**: 2025-10-23
**Status**: Mermaid.live Validated ✅
**Renders on**: GitHub, GitLab, mermaid.live, VS Code, MkDocs
