import hashlib
import logging
import os
import uuid
from typing import List, Dict, Any, Optional, Iterable
import re
import multiprocessing
import concurrent.futures
from multiprocessing.managers import SyncManager
import pymupdf
import aiofiles

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.base_processor import BaseProcessor
from rag_solution.data_ingestion.chunking import get_chunking_method
from rag_solution.doc_utils import clean_text
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from vectordbs.utils.watsonx import get_embeddings

logger = logging.getLogger(__name__)

class PdfProcessor(BaseProcessor):
    def __init__(self, manager: Optional[SyncManager] = None) -> None:
        super().__init__()
        if manager is None:
            manager = multiprocessing.Manager()
        self.saved_image_hashes = set(manager.list())

    async def process(self, file_path: str) -> Iterable[Document]:
        output_folder: str = os.path.join(os.path.dirname(file_path), "extracted_images")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        try:
            with pymupdf.open(file_path) as doc:
                metadata: Dict[str, Any] = await self.extract_metadata(doc)
                logger.info(f"Extracted metadata from {file_path}: {metadata}")

                document_id = str(uuid.uuid4())

                async with concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
                    future_to_page = {executor.submit(self.process_page, page_num, file_path, output_folder, document_id): page_num 
                                      for page_num in range(len(doc))}
                    
                    for future in concurrent.futures.as_completed(future_to_page):
                        page_num = future_to_page[future]
                        try:
                            chunks = future.result()
                            if chunks:
                                yield Document(
                                    name=os.path.basename(file_path),
                                    document_id=document_id,
                                    chunks=chunks,
                                    path=file_path,
                                    metadata=DocumentChunkMetadata(**metadata, page_number=page_num+1)
                                )
                        except Exception as e:
                            logger.error(f"Error processing page {page_num} of {file_path}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing PDF file {file_path}") from e

    async def process_page(self, page_number: int, file_path: str, output_folder: str, document_id: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        chunking_method = get_chunking_method()

        with pymupdf.open(file_path) as doc:
            page: pymupdf.Page = doc.load_page(page_number)
            page_content: List[Dict[str, Any]] = self.extract_text_from_page(page)
            tables: List[List[List[str]]] = self.extract_tables_from_page(page)

            text_blocks: List[str] = [block["content"] for block in page_content if block["type"] == "text"]
            full_text: str = "\n".join(text_blocks)

            page_metadata = {
                'page_number': page_number + 1,
                'source': Source.PDF
            }

            # Process main text
            text_chunks = chunking_method(full_text)
            for chunk_text in text_chunks:
                chunk_embedding = get_embeddings(chunk_text)
                chunk_metadata = {
                    **page_metadata,
                    'content_type': 'text',
                }
                chunks.append(self.create_document_chunk(chunk_text, chunk_embedding, chunk_metadata, document_id))

            # Process tables
            if tables:
                for table_index, table in enumerate(tables):
                    table_text = "\n".join([" | ".join(row) for row in table])
                    table_chunks = chunking_method(table_text)
                    for table_chunk in table_chunks:
                        table_embedding = get_embeddings(table_chunk)
                        chunk_metadata = {
                            **page_metadata,
                            'content_type': 'table',
                            'table_index': table_index
                        }
                        chunks.append(self.create_document_chunk(table_chunk, table_embedding, chunk_metadata, document_id))

            # Process images
            images: List[str] = self.extract_images_from_page(page, output_folder)
            for img_index, img in enumerate(images):
                chunk_metadata = {
                    **page_metadata,
                    'content_type': 'image',
                    'image_index': img_index
                }
                image_text = f"Image: {img}"
                image_embedding = get_embeddings(image_text)
                chunks.append(self.create_document_chunk(image_text, image_embedding, chunk_metadata, document_id))

        return chunks

    # Other methods remain the same...
