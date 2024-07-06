import hashlib
import logging
import os
import uuid
from typing import AsyncIterable, List, Set

import pymupdf  # PyMuPDF

from exceptions import DocumentProcessingError
from rag_solution.doc_utils import clean_text, get_document
from vectordbs.data_types import Document

from .base_processor import BaseProcessor
from .chunking import semantic_chunking, semantic_chunking_for_tables

logger = logging.getLogger(__name__)


class PdfProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self.saved_image_hashes: Set[str] = set()

    async def process(self, file_path: str) -> AsyncIterable[Document]:
        output_folder = os.path.join(os.path.dirname(file_path), "extracted_images")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        try:
            with pymupdf.open(file_path) as doc:
                for page in doc:
                    text = self.extract_text_from_page(page)
                    for chunk in semantic_chunking(
                        text,
                        self.min_chunk_size,
                        self.max_chunk_size,
                        self.semantic_threshold,
                    ):
                        yield get_document(
                            name=file_path, document_id=str(uuid.uuid4()), text=chunk
                        )

                    tables = self.extract_tables_from_page(page)
                    for table_chunk in semantic_chunking_for_tables(
                        tables,
                        self.min_chunk_size,
                        self.max_chunk_size,
                        self.semantic_threshold,
                    ):
                        yield get_document(
                            name=file_path,
                            document_id=str(uuid.uuid4()),
                            text=table_chunk,
                        )

                    self.extract_images_from_page(
                        page,
                        output_folder,
                        self.saved_image_hashes,
                        raise_on_error=True,
                    )
        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}", exc_info=True)
            raise DocumentProcessingError(
                f"Error processing PDF file {file_path}"
            ) from e

    def extract_text_from_page(self, page: pymupdf.Page) -> str:
        return page.get_text("text")

    def extract_tables_from_page(self, page: pymupdf.Page) -> List[List[List[str]]]:
        """
        Extract tables from a PDF page.

        Args:
            page (pymupdf.Page): The PDF page object.

        Returns:
            List[List[List[str]]]: A list of extracted tables, where each table is a list of rows,
            and each row is a list of cell values.
        """
        tables = page.find_tables()
        extracted_tables: List[List[List[str]]] = []

        for table in tables:
            extracted_table = table.extract()
            cleaned_table = [
                [clean_text(cell) if cell is not None else "" for cell in row]
                for row in extracted_table
            ]
            if any(
                cell for row in cleaned_table for cell in row
            ):  # Check if table has any non-empty cells
                extracted_tables.append(cleaned_table)

        return extracted_tables

    def extract_images_from_page(
        self,
        page: pymupdf.Page,
        output_folder: str,
        saved_image_hashes: Set[str],
        raise_on_error: bool = False,
    ) -> List[str]:
        """
        Extract images from a PDF page and save them to the output folder.

        Args:
            page (pymupdf.Page): The PDF page object.
            output_folder (str): The folder to save extracted images.
            saved_image_hashes (Set[str]): A set of hashes of already saved images to avoid duplicates.
            raise_on_error (bool): Whether to raise an error if an exception occurs.

        Returns:
            List[str]: A list of paths to the saved image files.
        """
        image_list = page.get_images(full=True)
        images: List[str] = []

        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            try:
                base_image = page.parent.extract_image(xref)
                if base_image:
                    image_bytes = base_image["image"]
                    image_hash = hashlib.md5(image_bytes).hexdigest()
                    logger.info(
                        f"Processing image on page {page.number + 1}, index {img_index}, hash: {image_hash}"
                    )

                    if image_hash not in saved_image_hashes:
                        image_extension = base_image["ext"]
                        image_filename = f"{output_folder}/image_{page.number + 1}_{img_index}.{image_extension}"
                        with open(image_filename, "wb") as img_file:
                            img_file.write(image_bytes)
                        images.append(image_filename)
                        saved_image_hashes.add(image_hash)
                        logger.info(f"Saved new image: {image_filename}")
                    else:
                        logger.info(
                            f"Skipped duplicate image on page {page.number + 1}, image index {img_index}"
                        )
                else:
                    logger.warning(
                        f"Failed to extract image {xref} from page {page.number + 1}"
                    )
            except Exception as e:
                logger.error(
                    f"Error extracting image {xref} from page {page.number + 1}: {e}"
                )
                if raise_on_error:
                    raise DocumentProcessingError(
                        f"Error extracting image {xref} from page {page.number + 1}"
                    ) from e

        return images
