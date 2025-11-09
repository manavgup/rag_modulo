# Document Processing

This document describes RAG Modulo's document processing capabilities, including file upload, content extraction, chunking strategies, embedding generation, and the integration with IBM Docling for advanced format support.

## Overview

RAG Modulo provides comprehensive document processing with support for multiple file formats:

- **Multi-Format Support**: PDF, DOCX, PPTX, XLSX, HTML, TXT, Images
- **IBM Docling Integration**: Advanced document understanding
- **Hierarchical Chunking**: Context-aware text segmentation
- **Batch Processing**: Efficient handling of multiple files
- **Background Processing**: Non-blocking document ingestion
- **OCR Support**: Text extraction from images and scanned PDFs
- **Table Extraction**: Structured data from tables and spreadsheets

## Processing Pipeline

### Document Upload Flow

```
┌─────────────┐
│  1. Upload  │ ← User uploads file via API/UI
└──────┬──────┘
       ↓
┌─────────────┐
│  2. Validate│ ← Check file type, size, format
└──────┬──────┘
       ↓
┌─────────────┐
│  3. Store   │ ← Save to MinIO object storage
└──────┬──────┘
       ↓
┌─────────────┐
│  4. Process │ ← Extract content, generate chunks
└──────┬──────┘
       ↓
┌─────────────┐
│  5. Embed   │ ← Generate vector embeddings
└──────┬──────┘
       ↓
┌─────────────┐
│  6. Index   │ ← Store in vector database
└──────┬──────┘
       ↓
┌─────────────┐
│  7. Complete│ ← Update status, notify user
└─────────────┘
```

## File Upload

### API Endpoint

**POST /api/files/upload**

```python
from fastapi import UploadFile, File, Depends
from uuid import UUID

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    collection_id: UUID = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload and process document file"""
    # Validate file type
    allowed_extensions = [
        ".pdf", ".docx", ".pptx", ".xlsx",
        ".txt", ".html", ".png", ".jpg"
    ]

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}"
        )

    # Validate file size (max 100MB)
    max_size = 100 * 1024 * 1024  # 100MB
    file_size = 0
    content = b""

    for chunk in file.file:
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail="File size exceeds 100MB limit"
            )
        content += chunk

    # Store file in MinIO
    file_id = await file_service.store_file(
        file_content=content,
        filename=file.filename,
        collection_id=collection_id,
        user_id=current_user["uuid"]
    )

    # Process document in background
    background_tasks.add_task(
        process_document_task,
        file_id=file_id,
        collection_id=collection_id,
        user_id=current_user["uuid"]
    )

    return {
        "file_id": file_id,
        "status": "processing",
        "message": "File uploaded successfully, processing in background"
    }
```

### Frontend Upload

**React component with drag-and-drop**:

```typescript
// frontend/src/components/collections/FileUpload.tsx
import { useState } from 'react';
import { FileUploaderDropContainer } from '@carbon/react';

const FileUpload: React.FC = () => {
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async (files: FileList) => {
    setUploading(true);

    const formData = new FormData();
    formData.append('file', files[0]);
    formData.append('collection_id', collectionId);

    try {
      const response = await apiClient.post('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      console.log('File uploaded:', response.data);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <FileUploaderDropContainer
      labelText="Drag and drop files here or click to upload"
      accept={['.pdf', '.docx', '.pptx', '.xlsx', '.txt', '.html']}
      onAddFiles={(evt, { addedFiles }) => handleFileUpload(addedFiles)}
      disabled={uploading}
    />
  );
};
```

## Document Processors

### Processor Selection

**Factory pattern** for processor selection:

```python
# backend/data_ingestion/document_processor.py
class DocumentProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings

        # Docling processor for advanced formats
        docling_processor = DoclingProcessor(settings)

        # Legacy processors for fallback
        legacy_pdf = PdfProcessor(settings)
        legacy_docx = WordProcessor(settings)

        # Processor mapping
        if settings.enable_docling:
            self.processors = {
                ".pdf": docling_processor,
                ".docx": docling_processor,
                ".pptx": docling_processor,
                ".html": docling_processor,
                ".png": docling_processor,  # OCR
                ".jpg": docling_processor,  # OCR
                ".txt": TxtProcessor(settings),
                ".xlsx": ExcelProcessor(settings),
            }
        else:
            self.processors = {
                ".pdf": legacy_pdf,
                ".docx": legacy_docx,
                ".txt": TxtProcessor(settings),
            }

    def get_processor(self, file_extension: str) -> BaseProcessor:
        """Get appropriate processor for file type"""
        processor = self.processors.get(file_extension.lower())

        if not processor:
            raise ValueError(f"No processor for {file_extension}")

        return processor
```

### IBM Docling Processor

**Advanced document understanding** with IBM Docling:

```python
# backend/data_ingestion/processors/docling_processor.py
from docling.document_converter import DocumentConverter

class DoclingProcessor(BaseProcessor):
    """Advanced document processor using IBM Docling"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.converter = DocumentConverter()

    async def process(
        self,
        file_path: str,
        document_id: str
    ) -> AsyncIterator[Document]:
        """Process document with Docling"""
        # Convert document to intermediate format
        result = self.converter.convert(file_path)

        # Extract structured content
        for element in result.document.elements:
            if isinstance(element, Table):
                # Convert table to markdown
                content = self._table_to_markdown(element)
                yield Document(
                    content=content,
                    metadata={
                        "document_id": document_id,
                        "type": "table",
                        "page": element.page_number
                    }
                )

            elif isinstance(element, Image):
                # OCR image content
                content = await self._process_image(element)
                if content:
                    yield Document(
                        content=content,
                        metadata={
                            "document_id": document_id,
                            "type": "image",
                            "page": element.page_number
                        }
                    )

            elif isinstance(element, Paragraph):
                yield Document(
                    content=element.text,
                    metadata={
                        "document_id": document_id,
                        "type": "paragraph",
                        "page": element.page_number
                    }
                )

    def _table_to_markdown(self, table: Table) -> str:
        """Convert table to markdown format"""
        markdown = []

        # Header row
        if table.header:
            markdown.append("| " + " | ".join(table.header) + " |")
            markdown.append("| " + " | ".join(["---"] * len(table.header)) + " |")

        # Data rows
        for row in table.rows:
            markdown.append("| " + " | ".join(str(cell) for cell in row) + " |")

        return "\n".join(markdown)

    async def _process_image(self, image: Image) -> str | None:
        """Extract text from image using OCR"""
        try:
            # Use Docling's built-in OCR
            text = image.ocr_text
            return text if text else None
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return None
```

### PDF Processor

**PDF text extraction** with fallback to OCR:

```python
# backend/data_ingestion/processors/pdf_processor.py
import PyPDF2
from PIL import Image
import pytesseract

class PdfProcessor(BaseProcessor):
    """PDF document processor with OCR fallback"""

    async def process(
        self,
        file_path: str,
        document_id: str
    ) -> AsyncIterator[Document]:
        """Extract text from PDF"""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            for page_num, page in enumerate(pdf_reader.pages):
                # Extract text
                text = page.extract_text()

                # If no text found, try OCR
                if not text.strip():
                    text = await self._ocr_page(page)

                if text.strip():
                    yield Document(
                        content=text,
                        metadata={
                            "document_id": document_id,
                            "page": page_num + 1,
                            "type": "pdf"
                        }
                    )

    async def _ocr_page(self, page) -> str:
        """OCR page if no text found"""
        try:
            # Convert page to image
            image = page.to_image()

            # OCR image
            text = pytesseract.image_to_string(image)

            return text
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""
```

### Word Processor

**DOCX document extraction**:

```python
# backend/data_ingestion/processors/word_processor.py
from docx import Document as DocxDocument

class WordProcessor(BaseProcessor):
    """Microsoft Word document processor"""

    async def process(
        self,
        file_path: str,
        document_id: str
    ) -> AsyncIterator[Document]:
        """Extract text from DOCX"""
        doc = DocxDocument(file_path)

        for i, paragraph in enumerate(doc.paragraphs):
            if paragraph.text.strip():
                yield Document(
                    content=paragraph.text,
                    metadata={
                        "document_id": document_id,
                        "paragraph": i + 1,
                        "type": "docx"
                    }
                )

        # Extract tables
        for table_num, table in enumerate(doc.tables):
            table_text = self._extract_table(table)
            yield Document(
                content=table_text,
                metadata={
                    "document_id": document_id,
                    "table": table_num + 1,
                    "type": "table"
                }
            )

    def _extract_table(self, table) -> str:
        """Extract table as markdown"""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join(rows)
```

## Chunking Strategies

### Hierarchical Chunking

**Maintain context** across document chunks:

```python
# backend/data_ingestion/chunking/hierarchical_chunker.py
class HierarchicalChunker:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self,
        document: str,
        metadata: dict
    ) -> list[Chunk]:
        """Create hierarchical chunks with context"""
        chunks = []

        # 1. Split into sections (by headers/paragraphs)
        sections = self._split_into_sections(document)

        # 2. Create chunks within sections
        for section in sections:
            # Keep section title for context
            section_context = f"Section: {section.title}\n\n"

            # Chunk section content
            section_chunks = self._chunk_text(
                text=section.content,
                chunk_size=self.chunk_size - len(section_context),
                overlap=self.chunk_overlap
            )

            # Add section context to each chunk
            for i, chunk_text in enumerate(section_chunks):
                full_chunk = section_context + chunk_text

                chunks.append(Chunk(
                    content=full_chunk,
                    metadata={
                        **metadata,
                        "section": section.title,
                        "section_id": section.id,
                        "chunk_index": i,
                        "total_chunks": len(section_chunks)
                    }
                ))

        return chunks

    def _split_into_sections(self, document: str) -> list[Section]:
        """Split document into sections by headers"""
        sections = []
        current_section = None

        for line in document.split("\n"):
            # Detect headers (lines ending with colon or all caps)
            if self._is_header(line):
                if current_section:
                    sections.append(current_section)

                current_section = Section(
                    title=line.strip(),
                    content="",
                    id=len(sections)
                )
            elif current_section:
                current_section.content += line + "\n"

        if current_section:
            sections.append(current_section)

        return sections

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> list[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0

        while start < len(text):
            # Get chunk
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(".")
                if last_period > chunk_size * 0.5:
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())

            # Move start with overlap
            start = end - overlap

        return chunks
```

### Semantic Chunking

**Split by semantic boundaries**:

```python
class SemanticChunker:
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model

    async def chunk_document(
        self,
        document: str,
        similarity_threshold: float = 0.7
    ) -> list[Chunk]:
        """Split by semantic similarity"""
        # Split into sentences
        sentences = self._split_sentences(document)

        # Generate embeddings for sentences
        embeddings = await self.embedding_model.encode_batch(sentences)

        # Group by similarity
        chunks = []
        current_chunk = [sentences[0]]
        current_embedding = embeddings[0]

        for i in range(1, len(sentences)):
            # Calculate similarity with current chunk
            similarity = self._cosine_similarity(
                current_embedding,
                embeddings[i]
            )

            if similarity >= similarity_threshold:
                # Add to current chunk
                current_chunk.append(sentences[i])
                # Update chunk embedding (average)
                current_embedding = np.mean(
                    [current_embedding, embeddings[i]],
                    axis=0
                )
            else:
                # Start new chunk
                chunks.append(Chunk(
                    content=" ".join(current_chunk),
                    metadata={"chunk_index": len(chunks)}
                ))
                current_chunk = [sentences[i]]
                current_embedding = embeddings[i]

        # Add final chunk
        if current_chunk:
            chunks.append(Chunk(
                content=" ".join(current_chunk),
                metadata={"chunk_index": len(chunks)}
            ))

        return chunks
```

## Embedding Generation

### Batch Embedding

**Generate embeddings** for document chunks:

```python
# backend/rag_solution/services/embedding_service.py
class EmbeddingService:
    def __init__(self, settings: Settings):
        self.model = SentenceTransformer(
            settings.embedding_model_name
        )

    async def embed_chunks(
        self,
        chunks: list[Chunk],
        batch_size: int = 100
    ) -> list[Chunk]:
        """Generate embeddings for chunks in batches"""
        # Extract text content
        texts = [chunk.content for chunk in chunks]

        # Generate embeddings in batches
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            batch_embeddings = self.model.encode(
                batch,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            embeddings.extend(batch_embeddings)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()

        return chunks
```

### Embedding Models

**Supported embedding models**:

```python
# Configuration
EMBEDDING_MODELS = {
    "default": "sentence-transformers/all-MiniLM-L6-v2",
    "large": "sentence-transformers/all-mpnet-base-v2",
    "multilingual": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
}

# .env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

## Vector Storage

### Milvus Integration

**Store embeddings** in Milvus vector database:

```python
async def store_chunks(
    chunks: list[Chunk],
    collection_name: str
):
    """Store chunks in vector database"""
    # Prepare data for insertion
    data = [
        {
            "id": i,
            "embedding": chunk.embedding,
            "content": chunk.content,
            "metadata": json.dumps(chunk.metadata)
        }
        for i, chunk in enumerate(chunks)
    ]

    # Insert into Milvus
    self.collection.insert(data)

    # Flush to ensure data is written
    self.collection.flush()
```

## Background Processing

### Celery Task Queue

**Process documents** asynchronously:

```python
# backend/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "rag_modulo",
    broker="redis://redis:6379/0"
)

@celery_app.task(bind=True, max_retries=3)
def process_document_task(
    self,
    file_id: str,
    collection_id: str,
    user_id: str
):
    """Background task for document processing"""
    try:
        # 1. Load file from storage
        file_content = file_service.load_file(file_id)

        # 2. Process document
        processor = document_processor.get_processor(file_extension)
        chunks = await processor.process(file_content)

        # 3. Generate embeddings
        chunks = await embedding_service.embed_chunks(chunks)

        # 4. Store in vector database
        await vector_store.store_chunks(chunks, collection_id)

        # 5. Update file status
        await file_service.update_status(
            file_id,
            status="COMPLETED"
        )

        return {"status": "success", "chunks": len(chunks)}

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries)
        )
```

## CLI Usage

### Upload Documents

```bash
# Upload single file
./rag-cli files upload \
  --collection-id "col_123abc" \
  --file "document.pdf"

# Upload multiple files
./rag-cli files upload-batch \
  --collection-id "col_123abc" \
  --directory "./documents/"

# Check processing status
./rag-cli files status --file-id "file_456def"
```

## Configuration

### Environment Variables

```bash
# Docling
ENABLE_DOCLING=true
DOCLING_FALLBACK_ENABLED=true

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50
CHUNKING_STRATEGY=hierarchical  # or "semantic"

# Embedding
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=100

# Processing
MAX_FILE_SIZE_MB=100
ALLOWED_FILE_TYPES=.pdf,.docx,.pptx,.xlsx,.txt,.html,.png,.jpg

# Background Processing
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_WORKER_CONCURRENCY=4
```

## Best Practices

### File Upload

1. **Validate file types** - Check extensions before processing
2. **Limit file size** - Prevent memory exhaustion
3. **Use background processing** - Don't block API requests
4. **Provide status updates** - Keep users informed

### Chunking

1. **Maintain context** - Use hierarchical chunking
2. **Optimal chunk size** - Balance between context and precision
3. **Add overlap** - Prevent information loss at boundaries
4. **Include metadata** - Track source and location

### Performance

1. **Batch embeddings** - Process multiple chunks together
2. **Use Celery** - Offload heavy processing
3. **Cache results** - Avoid reprocessing identical files
4. **Monitor queue** - Track processing backlog

## Related Documentation

- [Search and Retrieval](search-retrieval.md) - Use processed documents
- [LLM Integration](llm-integration.md) - Provider configuration
- [Architecture - Components](../architecture/components.md) - System design
- [Troubleshooting - Document Processing](../troubleshooting/debugging.md) - Debug issues
