import hashlib
import io
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
import fitz  # PyMuPDF

logger = logging.getLogger("edunex.rag.extractor")


class PDFProcessingError(Exception):
    """Raised when PDF extraction or validation fails."""
    pass


class CorruptedPDFError(PDFProcessingError):
    """Raised when a PDF is corrupted, unreadable, or invalid."""
    pass


class EmptyPDFError(PDFProcessingError):
    """Raised when a PDF has 0 pages or contains no extractable text."""
    pass


@dataclass
class ExtractedDocument:
    filename: str
    file_size_bytes: int
    sha256_hash: str
    page_count: int
    total_characters: int
    pages: List[Tuple[int, str]]  # [(1, "page 1 text..."), (2, "page 2 text...")]
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFExtractor:
    """
    Validates, analyzes, and extracts text page-by-page from PDF files using PyMuPDF.
    """

    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

    @classmethod
    def compute_sha256(cls, content: bytes) -> str:
        """Compute SHA-256 hash of file bytes for duplicate detection."""
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def validate_pdf_bytes(cls, content: bytes, filename: str) -> None:
        """
        Validates PDF content:
        1. Checks size limits
        2. Validates PDF magic header (%PDF-)
        3. Catches empty files
        """
        if not content or len(content) == 0:
            raise EmptyPDFError(f"File '{filename}' is completely empty (0 bytes).")

        if len(content) > cls.MAX_FILE_SIZE_BYTES:
            raise PDFProcessingError(
                f"File '{filename}' exceeds maximum allowed size of {cls.MAX_FILE_SIZE_BYTES / (1024 * 1024):.1f} MB."
            )

        # PDF header magic check
        if not content.startswith(b"%PDF-"):
            raise CorruptedPDFError(
                f"File '{filename}' does not have a valid PDF header signature (%PDF-)."
            )

    @classmethod
    def extract_text(cls, content: bytes, filename: str) -> ExtractedDocument:
        """
        Extracts text from PDF bytes page by page.
        Raises CorruptedPDFError or EmptyPDFError on failures.
        """
        cls.validate_pdf_bytes(content, filename)
        sha256_hash = cls.compute_sha256(content)

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            logger.error("Failed to open PDF %s: %s", filename, str(e))
            raise CorruptedPDFError(f"Cannot parse PDF '{filename}': {str(e)}") from e

        with doc:
            page_count = len(doc)
            if page_count == 0:
                raise EmptyPDFError(f"PDF '{filename}' contains 0 pages.")

            extracted_pages: List[Tuple[int, str]] = []
            total_chars = 0

            for page_index in range(page_count):
                try:
                    page = doc.load_page(page_index)
                    text = page.get_text("text").strip()
                    page_number = page_index + 1  # 1-indexed for students & citations
                    extracted_pages.append((page_number, text))
                    total_chars += len(text)
                except Exception as e:
                    logger.warning("Error reading page %d of %s: %s", page_index + 1, filename, str(e))
                    extracted_pages.append((page_index + 1, ""))

            # Verify that the PDF is not entirely blank
            if total_chars == 0:
                raise EmptyPDFError(
                    f"PDF '{filename}' contains {page_count} page(s) but no extractable text was found."
                )

            # Metadata extraction
            doc_meta = doc.metadata or {}
            clean_metadata = {
                "title": doc_meta.get("title") or filename,
                "author": doc_meta.get("author") or "Unknown",
                "subject": doc_meta.get("subject") or "",
                "creator": doc_meta.get("creator") or "",
                "producer": doc_meta.get("producer") or "",
                "format": doc_meta.get("format") or "PDF",
                "page_count": page_count,
            }

            logger.info(
                "Extracted %s: %d pages, %d characters, hash=%s",
                filename,
                page_count,
                total_chars,
                sha256_hash[:12],
            )

            return ExtractedDocument(
                filename=filename,
                file_size_bytes=len(content),
                sha256_hash=sha256_hash,
                page_count=page_count,
                total_characters=total_chars,
                pages=extracted_pages,
                metadata=clean_metadata,
            )

