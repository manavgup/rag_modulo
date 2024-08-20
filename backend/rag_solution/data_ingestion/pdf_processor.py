import hashlib
import logging
import os
import uuid
from typing import Iterable, List, Set, Dict, Any, Generator, Optional
import re
import multiprocessing

import pymupdf
from tqdm import tqdm

from backend.core.custom_exceptions import DocumentProcessingError
from backend.rag_solution.data_ingestion.base_processor import BaseProcessor
from backend.rag_solution.data_ingestion.chunking import semantic_chunking, semantic_chunking_for_tables, get_chunking_method
from backend.rag_solution.doc_utils import clean_text, get_document
from backend.vectordbs.data_types import Document
from backend.core.config import settings

logger = logging.getLogger(__name__)

def process_page_wrapper(args: tuple) -> List[Document]:
    processor, page_number, metadata, file_path, output_folder = args
    return processor.process_page(page_number, metadata, file_path, output_folder)

class PdfProcessor(BaseProcessor):
    def __init__(self, manager: multiprocessing.Manager) -> None:
        super().__init__()
        # Use a manager's list and wrap it in a set to manage image hashes
        self.saved_image_hashes = set(manager.list())

    def process(self, file_path: str) -> Generator[Document, None, None]:
        """
        Process the PDF file and yield Document instances.

        Args:
            file_path (str): The path to the PDF file to be processed.

        Yields:
            Document: An instance of Document containing the processed data.

        Raises:
            DocumentProcessingError: If there is an error processing the PDF file.
        """
        output_folder: str = os.path.join(os.path.dirname(file_path), "extracted_images")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        try:
            with pymupdf.open(file_path) as doc:
                metadata: Dict[str, Any] = self.extract_metadata(doc)
                logger.info(f"Extracted metadata from {file_path}: {metadata}")

                # Prepare arguments for multiprocessing
                args: List[tuple] = [(self, page.number, metadata, file_path, output_folder) for page in doc]

                # Process pages in parallel
                with multiprocessing.Pool() as pool:
                    results: List[List[Document]] = list(
                        tqdm(pool.map(process_page_wrapper, args), total=len(doc), desc="Processing pages")
                    )

                for result in results:
                    yield from result

        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(f"Error processing PDF file {file_path}") from e
    
    def process_page(
        self, 
        page_number: int, 
        metadata: Dict[str, Any], 
        file_path: str, 
        output_folder: str
    ) -> List[Document]:
        documents: List[Document] = []

        # Reinitialize chunking method for each process to ensure consistency
        chunking_method = get_chunking_method()

        with pymupdf.open(file_path) as doc:
            page: pymupdf.Page = doc.load_page(page_number)

            # Extract text and tables
            page_content: List[Dict[str, Any]] = self.extract_text_from_page(page)
            tables: List[List[List[str]]] = self.extract_tables_from_page(page)

            # Process text blocks
            text_blocks: List[str] = [block["content"] for block in page_content if block["type"] == "text"]
            full_text: str = "\n".join(text_blocks)

            # Add page_number to metadata
            page_metadata = {**metadata, 'page_number': page_number + 1}

            for chunk in chunking_method(full_text):
                documents.append(get_document(
                    name=metadata['title'],
                    document_id=str(uuid.uuid4()),
                    text=chunk,
                    metadata=page_metadata
                ))

            # Process tables
            if tables:
                for table in tables:
                    for table_chunk in semantic_chunking_for_tables([table], settings.min_chunk_size, settings.max_chunk_size, settings.semantic_threshold):
                        documents.append(get_document(
                            name=metadata['title'],
                            document_id=str(uuid.uuid4()),
                            text=table_chunk,
                            metadata={**page_metadata, 'content_type': 'table'}
                        ))


            # Process images
            images: List[str] = self.extract_images_from_page(page, output_folder)
            for img in images:
                documents.append(get_document(
                    name=metadata['title'],
                    document_id=str(uuid.uuid4()),
                    text=f"Image: {img}",
                    metadata={**page_metadata, 'content_type': 'image'}
                ))

        return documents
    
    def extract_text_from_page(self, page: pymupdf.Page) -> List[Dict[str, Any]]:
        """
        Extract text from a PDF page, preserving structure and layout information.
        
        Args:
            page (pymupdf.Page): The PDF page object.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a text block with its properties.
        """
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
                            "flags": span["flags"],  # Bold, italic, etc.
                            "color": span["color"],
                            "bbox": span["bbox"]  # Bounding box: (x0, y0, x1, y1)
                        })
                
                # Combine all text in the block
                full_text: str = " ".join([span["text"] for span in block_text])
                
                # Get the bounding box for the entire block
                block_bbox: List[float] = block["bbox"]
                
                page_text.append({
                    "type": "text",
                    "content": full_text,
                    "font": block_text[0]["font"],  # Assuming font is consistent in a block
                    "size": block_text[0]["size"],  # Assuming size is consistent in a block
                    "bbox": block_bbox,
                    "spans": block_text  # Keep detailed span information if needed
                })
            elif block["type"] == 1:  # Type 1 is image
                page_text.append({
                    "type": "image",
                    "bbox": block["bbox"],
                    "image_data": block.get("image", None)
                })

        return page_text
    
    def extract_tables_from_page(self, page: pymupdf.Page) -> List[List[List[str]]]:
        """
        Extract tables from a PDF page using multiple methods.
        
        Args:
            page (pymupdf.Page): The PDF page object.
        
        Returns:
            List[List[List[str]]]: A list of extracted tables, where each table is a list of rows,
            and each row is a list of cell values.
        """
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
        """
        Extract images from a PDF page and save them to the output folder.

        Args:
            page (pymupdf.Page): The PDF page object.
            output_folder (str): The folder to save extracted images.

        Returns:
            List[str]: A list of paths to the saved image files.
        """
        image_list: List[tuple] = page.get_images(full=True)
        images: List[str] = []

        for img_index, img in enumerate(image_list, start=1):
            xref: int = img[0]
            try:
                base_image: Optional[Dict[str, Any]] = page.parent.extract_image(xref)
                if base_image:
                    image_bytes: bytes = base_image["image"]
                    image_hash: str = hashlib.md5(image_bytes).hexdigest()

                    # Use manager's list to manage image hashes safely across processes
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
        """
        Extract metadata from the PDF document.

        Args:
            doc (pymupdf.Document): The PDF document object.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted metadata.
        """
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
            'total_pages': len(doc)
        }

# Example usage with a multiprocessing manager
if __name__ == "__main__":
    with multiprocessing.Manager() as manager:
        processor = PdfProcessor(manager)
        # Example call to processor.process() with a PDF file path
