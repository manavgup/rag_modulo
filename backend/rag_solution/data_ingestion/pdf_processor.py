import hashlib
import logging
import os
import uuid
from typing import List, Dict, Any, Optional, Iterable, AsyncIterable
import re
import multiprocessing
import concurrent.futures
from multiprocessing.managers import SyncManager
import pymupdf
import aiofiles
import asyncio

from core.custom_exceptions import DocumentProcessingError
from rag_solution.data_ingestion.base_processor import BaseProcessor
from rag_solution.data_ingestion.chunking import get_chunking_method
from rag_solution.doc_utils import clean_text
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from vectordbs.utils.watsonx import get_embeddings, _get_embeddings_client, sublist

logger = logging.getLogger(__name__)


class PdfProcessor(BaseProcessor):
    def __init__(self, manager: Optional[SyncManager] = None) -> None:
        super().__init__()
        if manager is None:
            manager = multiprocessing.Manager()
        self.saved_image_hashes = set(manager.list())

    async def process(self, file_path: str) -> AsyncIterable[Document]:
        logger.info(f"PdfProcessor: Attempting to process file: {file_path}")
        logger.info(f"File exists: {os.path.exists(file_path)}")
        # logger.info(f"Current working directory: {os.getcwd()}")
        # logger.info(f"Directory contents: {os.listdir(os.path.dirname(file_path))}")

        output_folder: str = os.path.join(os.path.dirname(file_path), "extracted_images")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        try:
            with pymupdf.open(file_path) as doc:
                metadata: Dict[str, Any] = await self.extract_metadata(doc)
                logger.info(f"Extracted metadata from {file_path}: {metadata}")

                document_id = str(uuid.uuid4())

                with concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
                    futures = [executor.submit(self.process_page, page_num, file_path, output_folder, document_id)
                               for page_num in range(len(doc))]

                    for future in concurrent.futures.as_completed(futures):
                        page_num = futures.index(future)
                        try:
                            chunks = future.result()
                            if chunks:
                                yield Document(
                                    name=os.path.basename(file_path),
                                    document_id=document_id,
                                    chunks=chunks,
                                    path=file_path,
                                    metadata=DocumentChunkMetadata(**metadata, page_number=page_num + 1)
                                )
                        except Exception as e:
                            logger.error(f"Error processing page {page_num} of {file_path}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing PDF file {file_path}") from e

    def process_page(self, page_number: int, file_path: str, output_folder: str, document_id: str) -> List[
        DocumentChunk]:
        chunks: List[DocumentChunk] = []
        chunking_method = get_chunking_method()

        try:
            with pymupdf.open(file_path) as doc:
                page: pymupdf.Page = doc.load_page(page_number)
                # Check if the page contains text
                if not page.get_text("text"):
                    logger.warning(f"Skipping page {page.number + 1}: not a text page.")
                    return chunks

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
                embed_client = _get_embeddings_client()
                for subset_chunks in sublist(inputs=text_chunks, n=5):
                    chunk_embeddings = get_embeddings(texts=subset_chunks, embed_client=embed_client)
                    for ix, chunk_text in enumerate(subset_chunks):
                        chunk_metadata = {
                            **page_metadata,
                            'content_type': 'text',
                        }
                        chunks.append(
                            self.create_document_chunk(chunk_text, chunk_embeddings[ix], chunk_metadata, document_id))

                # Process tables
                if tables:
                    for table_index, table in enumerate(tables):
                        table_text = "\n".join([" | ".join(row) for row in table])
                        table_chunks = chunking_method(table_text)
                        for table_chunk in table_chunks:
                            table_embedding = get_embeddings(texts=table_chunk, embed_client=embed_client)
                            chunk_metadata = {
                                **page_metadata,
                                'content_type': 'table',
                                'table_index': table_index
                            }
                            chunks.append(self.create_document_chunk(table_chunk, table_embedding[0], chunk_metadata,
                                                                     document_id))

                # Process images
                images: List[str] = self.extract_images_from_page(page, output_folder)
                for img_index, img in enumerate(images):
                    chunk_metadata = {
                        **page_metadata,
                        'content_type': 'image',
                        'image_index': img_index
                    }
                    image_text = f"Image: {img}"
                    image_embedding = get_embeddings(texts=image_text, embed_client=embed_client)
                    chunks.append(
                        self.create_document_chunk(image_text, image_embedding[0], chunk_metadata, document_id))

        except Exception as e:
            logger.error(f"Error processing page {page_number} of {file_path}: {e}", exc_info=True)
        return chunks

    def create_document_chunk(self, chunk_text: str, chunk_embedding: List[float], metadata: Dict[str, Any],
                              document_id: str) -> DocumentChunk:
        chunk_id = str(uuid.uuid4())
        return DocumentChunk(
            chunk_id=chunk_id,
            text=chunk_text,
            vectors=chunk_embedding,
            metadata=DocumentChunkMetadata(**metadata),
            document_id=document_id
        )

    def extract_text_from_page(self, page: pymupdf.Page) -> List[Dict[str, Any]]:
        try:
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
        except Exception as e:
            logger.error(f"Error extracting text from page {page.number}: {e}", exc_info=True)
            return []

    def extract_tables_from_page(self, page: pymupdf.Page) -> List[List[List[str]]]:
        tables: List[List[List[str]]] = []
        
        try:
            # First check if the page has any text content at all
            page_text = page.get_text("text").strip()
            if not page_text:
                logger.warning(f"Skipping page {page.number + 1}: no text content found.")
                return tables

            # Method 1: Use PyMuPDF's built-in table extraction with proper exception handling
            try:
                built_in_tables = page.find_tables()
                for table in built_in_tables:
                    extracted_table = table.extract()
                    cleaned_table: List[List[str]] = [
                        [clean_text(cell) if cell is not None else "" for cell in row]
                        for row in extracted_table
                    ]
                    if any(cell for row in cleaned_table for cell in row):  # Only add non-empty tables
                        tables.append(cleaned_table)
                if tables:
                    logger.info(f"Successfully extracted {len(tables)} tables using PyMuPDF's built-in method")
                    return tables
            except ValueError as ve:
                if "not a textpage of this page" in str(ve):
                    logger.info(f"Page {page.number + 1} doesn't support textpage extraction, falling back to alternative methods")
                else:
                    logger.warning(f"Unexpected ValueError during table extraction on page {page.number + 1}: {ve}")
            except Exception as e:
                logger.warning(f"Error during built-in table extraction on page {page.number + 1}: {e}")

            # Method 2: Use text blocks to identify potential tables
            try:
                text_blocks: List[Dict[str, Any]] = self.extract_text_from_page(page)
                potential_table: List[List[str]] = []
                current_y_position = None
                tolerance = 5  # Pixels tolerance for considering text blocks as part of the same row

                for block in text_blocks:
                    if block["type"] == "text":
                        # Get the y-position of this block
                        block_y = block["bbox"][1]  # y-coordinate of top of block
                        
                        # If this is a new row (y-position differs significantly from previous)
                        if current_y_position is None or abs(block_y - current_y_position) > tolerance:
                            if potential_table:  # Save the previous row if it exists
                                if len(potential_table[-1]) > 1:  # Only if it has multiple cells
                                    current_y_position = block_y
                                else:
                                    potential_table.pop()  # Remove single-cell rows
                            
                            # Start a new row
                            cells = [cell.strip() for cell in re.split(r'\s{3,}', block["content"].strip())]
                            if len(cells) > 1:
                                potential_table.append(cells)
                                current_y_position = block_y
                        else:
                            # Add to the current row
                            if potential_table:
                                potential_table[-1].extend(
                                    cell.strip() for cell in re.split(r'\s{3,}', block["content"].strip())
                                )

                # Add the last table if it meets our criteria
                if len(potential_table) > 1 and all(len(row) > 1 for row in potential_table):
                    tables.append(potential_table)
                    logger.info(f"Successfully extracted table using text block analysis")
                    return tables
            except Exception as e:
                logger.warning(f"Error during text block table extraction on page {page.number + 1}: {e}")

            # Method 3: Look for grid-like structures
            try:
                words: List[tuple] = page.get_text("words")
                grid: Dict[float, Dict[float, List[str]]] = {}
                
                # Improved grid detection with floating-point tolerance
                for word in words:
                    x, y = float(word[0]), float(word[1])
                    
                    # Find or create appropriate row (with tolerance)
                    row_key = None
                    for existing_y in grid.keys():
                        if abs(existing_y - y) < 5:  # 5 pixel tolerance for row alignment
                            row_key = existing_y
                            break
                    if row_key is None:
                        row_key = y
                        grid[row_key] = {}
                    
                    # Find or create appropriate column (with tolerance)
                    col_key = None
                    for existing_x in grid[row_key].keys():
                        if abs(existing_x - x) < 5:  # 5 pixel tolerance for column alignment
                            col_key = existing_x
                            break
                    if col_key is None:
                        col_key = x
                        grid[row_key][col_key] = []
                    
                    grid[row_key][col_key].append(word[4])

                # Convert grid to table format
                if len(grid) > 1:
                    table: List[List[str]] = []
                    for y in sorted(grid.keys()):
                        row: List[str] = [
                            " ".join(grid[y][x]).strip() 
                            for x in sorted(grid[y].keys())
                        ]
                        if len(row) > 1 and any(cell.strip() for cell in row):  # Only add non-empty rows
                            table.append(row)
                    
                    if len(table) > 1 and self._is_likely_table(table):
                        tables.append(table)
                        logger.info(f"Successfully extracted table using grid analysis")
                        return tables
            except Exception as e:
                logger.warning(f"Error during grid-based table extraction on page {page.number + 1}: {e}")

            # Log if no tables were found by any method
            if not tables:
                logger.info(f"No tables found on page {page.number + 1} using any extraction method")
            
            return tables

        except Exception as e:
            logger.error(f"Error in table extraction process for page {page.number + 1}: {e}", exc_info=True)
            return tables

    def _is_likely_table(self, table: List[List[str]]) -> bool:
        """
        Helper method to determine if a potential table structure is likely to be a real table.
        
        Args:
            table: The potential table structure to evaluate
            
        Returns:
            bool: True if the structure appears to be a real table, False otherwise
        """
        if not table or len(table) < 2:  # Need at least 2 rows
            return False
            
        # Check for consistent number of columns
        col_count = len(table[0])
        if col_count < 2:  # Need at least 2 columns
            return False
            
        if not all(len(row) == col_count for row in table):
            return False
            
        # Check if there's enough non-empty content
        non_empty_cells = sum(
            1 for row in table 
            for cell in row 
            if cell.strip()
        )
        total_cells = len(table) * col_count
        if non_empty_cells / total_cells < 0.25:  # At least 25% of cells should have content
            return False
            
        return True

    def extract_images_from_page(self, page: pymupdf.Page, output_folder: str) -> List[str]:
        images: List[str] = []

        try:
            image_list: List[tuple] = page.get_images(full=True)

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

        except Exception as e:
            logger.error(f"Error extracting images from page {page.number}: {e}", exc_info=True)

        return images

    async def extract_metadata(self, doc: pymupdf.Document) -> Dict[str, Any]:
        try:
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
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}", exc_info=True)
            return {
                'title': 'Unknown',
                'author': 'Unknown',
                'subject': '',
                'keywords': '',
                'creator': '',
                'producer': '',
                'creationDate': '',
                'modDate': '',
                'total_pages': 0,
                'source': Source.PDF
            }
