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

    def process(self, file_path: str) -> Iterable[Document]:
        output_folder: str = os.path.join(os.path.dirname(file_path), "extracted_images")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        try:
            with pymupdf.open(file_path) as doc:
                metadata: Dict[str, Any] = self.extract_metadata(doc)
                logger.info(f"Extracted metadata from {file_path}: {metadata}")

                document_id = str(uuid.uuid4())

                with concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
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

    def process_page(self, page_number: int, file_path: str, output_folder: str, document_id: str) -> List[DocumentChunk]:
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

    def create_document_chunk(self, chunk_text: str, chunk_embedding: List[float], metadata: Dict[str, Any], document_id: str) -> DocumentChunk:
        chunk_id = str(uuid.uuid4())
        return DocumentChunk(
            chunk_id=chunk_id,
            text=chunk_text,
            vectors=chunk_embedding,
            metadata=DocumentChunkMetadata(**metadata),
            document_id=document_id
        )

    def extract_text_from_page(self, page: pymupdf.Page) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = page.get_text("dict")["blocks"]
        page_text: List[Dict[str, Any]] = []

        for block in blocks:
            if block["type"] == 0:  # Type 0 is text
                block_text: List[Dict[str, Any]] = []
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text.append({
                            "text": span["text"],
                            "font": span["font"],
                            "size": span["size"],
                            "flags": span["flags"],
                            "color": span["color"],
                            "bbox": span["bbox"]
                        })
                
                full_text: str = " ".join([span["text"] for span in block_text])
                block_bbox: List[float] = block["bbox"]
                
                page_text.append({
                    "type": "text",
                    "content": full_text,
                    "font": block_text[0]["font"],
                    "size": block_text[0]["size"],
                    "bbox": block_bbox,
                    "spans": block_text
                })
            elif block["type"] == 1:  # Type 1 is image
                page_text.append({
                    "type": "image",
                    "bbox": block["bbox"],
                    "image_data": block.get("image", None)
                })

        return page_text

    def extract_tables_from_page(self, page: pymupdf.Page) -> List[List[List[str]]]:
        tables: List[List[List[str]]] = []

        # Method 1: Use PyMuPDF's built-in table extraction
        built_in_tables = page.find_tables()
        for table in built_in_tables:
            extracted_table = table.extract()
            cleaned_table: List[List[str]] = [
                [clean_text(cell) if cell is not None else "" for cell in row]
                for row in extracted_table
            ]
            if any(cell for row in cleaned_table for cell in row):
                tables.append(cleaned_table)

        # Method 2: Use text blocks to identify potential tables
        if not tables:
            text_blocks: List[Dict[str, Any]] = self.extract_text_from_page(page)
            potential_table: List[List[str]] = []
            for block in text_blocks:
                if block["type"] == "text":
                    lines: List[str] = block["content"].split("\n")
                    for line in lines:
                        cells: List[str] = re.split(r'\s{2,}', line.strip())
                        if len(cells) > 1:
                            potential_table.append(cells)
                        elif potential_table:
                            if len(potential_table) > 1 and len(potential_table[0]) > 1:
                                tables.append(potential_table)
                            potential_table = []
            if len(potential_table) > 1 and len(potential_table[0]) > 1:
                tables.append(potential_table)

        # Method 3: Look for grid-like structures
        if not tables:
            words: List[tuple] = page.get_text("words")
            grid: Dict[int, Dict[int, str]] = {}
            for word in words:
                x, y = int(word[0]), int(word[1])
                if y not in grid:
                    grid[y] = {}
                if x not in grid[y]:
                    grid[y][x] = ""
                grid[y][x] += word[4] + " "

            if len(grid) > 1:
                table: List[List[str]] = []
                for y in sorted(grid.keys()):
                    row: List[str] = [grid[y][x].strip() for x in sorted(grid[y].keys())]
                    if len(row) > 1:  # Only add rows with more than one cell
                        table.append(row)
                if len(table) > 1:  # Only add tables with more than one row
                    tables.append(table)

        logger.info(f"Extracted {len(tables)} tables from page {page.number + 1}")
        for i, table in enumerate(tables):
            logger.info(f"Table {i+1} dimensions: {len(table)}x{len(table[0]) if table else 0}")
            logger.info(f"Table {i+1} sample content: {' | '.join(table[0][:5]) if table and table[0] else 'Empty'}")

        return tables

    def extract_images_from_page(self, page: pymupdf.Page, output_folder: str) -> List[str]:
        image_list: List[tuple] = page.get_images(full=True)
        images: List[str] = []

        for img_index, img in enumerate(image_list, start=1):
            xref: int = img[0]
            try:
                base_image: Optional[Dict[str, Any]] = page.parent.extract_image(xref)
                if base_image:
                    image_bytes: bytes = base_image["image"]
                    image_hash: str = hashlib.md5(image_bytes).hexdigest()

                    if image_hash not in self.saved_image_hashes:
                        image_extension: str = base_image["ext"]
                        image_filename: str = f"{output_folder}/image_{page.number + 1}_{img_index}.{image_extension}"
                        with open(image_filename, "wb") as img_file:
                            img_file.write(image_bytes)
                        images.append(image_filename)
                        self.saved_image_hashes.add(image_hash)
                        logger.info(f"Saved new image: {image_filename}")
                    else:
                        logger.info(f"Skipped duplicate image on page {page.number + 1}, image index {img_index}")
                else:
                    logger.warning(f"Failed to extract image {xref} from page {page.number + 1}")
            except Exception as e:
                logger.error(f"Error extracting image {xref} from page {page.number + 1}: {e}")

        return images

    def extract_metadata(self, doc: pymupdf.Document) -> Dict[str, Any]:
        metadata: Dict[str, Optional[str]] = doc.metadata
        return {
            'title': metadata.get('title', 'Unknown'),
            'author': metadata.get('author', 'Unknown'),
            'subject': metadata.get('subject', ''),
            'keywords': metadata.get('keywords', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creationDate': metadata.get('creationDate', ''),
            'modDate': metadata.get('modDate', ''),
            'total_pages': len(doc),
            'source': Source.PDF
        }

# Example usage
if __name__ == "__main__":
    with multiprocessing.Manager() as manager:
        processor = PdfProcessor(manager)
        # Example call to processor.process() with a PDF file path