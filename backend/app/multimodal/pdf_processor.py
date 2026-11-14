import io
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF

from app.multimodal.ocr_engine import OCREngine
from app.rag.extractor import CorruptedPDFError, EmptyPDFError, PDFExtractor

logger = logging.getLogger("edunex.multimodal.pdf")


@dataclass
class ExtractedDiagram:
    index: int
    page: int
    xref: int
    width: int
    height: int
    format: str
    image_bytes: bytes
    size_bytes: int


@dataclass
class MultimodalPageContent:
    page_number: int
    text: str
    character_count: int
    diagrams: List[ExtractedDiagram] = field(default_factory=list)
    is_scanned: bool = False
    ocr_applied: bool = False
    rendered_pixmap_bytes: Optional[bytes] = None


@dataclass
class MultimodalPDFDocument:
    filename: str
    page_count: int
    total_characters: int
    total_diagrams: int
    pages: List[MultimodalPageContent]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultimodalPDFProcessor:
    """
    Advanced PDF processor capable of extracting text, preserving page numbers,
    detecting scanned pages for OCR, and extracting embedded diagrams & charts.
    """

    MIN_TEXT_CHARS_FOR_NATIVE_PAGE = 30  # Pages with fewer chars are evaluated for scanned OCR

    @classmethod
    def process_pdf(
        cls,
        content: bytes,
        filename: str,
        extract_diagrams: bool = True,
        enable_ocr: bool = True,
    ) -> MultimodalPDFDocument:
        """
        Processes a PDF completely, extracting text, diagrams, and applying OCR on scanned pages.
        """
        PDFExtractor.validate_pdf_bytes(content, filename)

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            logger.error("Failed to open PDF %s: %s", filename, str(e))
            raise CorruptedPDFError(f"Cannot parse PDF '{filename}': {str(e)}") from e

        with doc:
            page_count = len(doc)
            if page_count == 0:
                raise EmptyPDFError(f"PDF '{filename}' contains 0 pages.")

            pages: List[MultimodalPageContent] = []
            total_chars = 0
            total_diagrams = 0

            for page_index in range(page_count):
                page_num = page_index + 1
                try:
                    page = doc.load_page(page_index)
                    native_text = page.get_text("text").strip()
                    diagrams: List[ExtractedDiagram] = []

                    # 1. Extract embedded diagrams/images
                    if extract_diagrams:
                        diagrams = cls._extract_page_diagrams(doc, page, page_num)
                        total_diagrams += len(diagrams)

                    # 2. Check if page is scanned (no native text or very few characters)
                    is_scanned = len(native_text) < cls.MIN_TEXT_CHARS_FOR_NATIVE_PAGE
                    ocr_applied = False
                    final_text = native_text

                    if is_scanned and enable_ocr:
                        try:
                            # Render page to image pixmap for OCR
                            pix = page.get_pixmap(dpi=150)
                            pix_bytes = pix.tobytes("png")
                            ocr_text = OCREngine.ocr_scanned_pdf_page(pix_bytes, page_num)
                            if ocr_text:
                                final_text = f"{native_text}\n{ocr_text}".strip()
                                ocr_applied = True
                        except Exception as ocr_err:
                            logger.warning("OCR failed on page %d of %s: %s", page_num, filename, str(ocr_err))

                    total_chars += len(final_text)
                    pages.append(
                        MultimodalPageContent(
                            page_number=page_num,
                            text=final_text,
                            character_count=len(final_text),
                            diagrams=diagrams,
                            is_scanned=is_scanned,
                            ocr_applied=ocr_applied,
                        )
                    )
                except Exception as e:
                    logger.warning("Error processing page %d of %s: %s", page_num, filename, str(e))
                    pages.append(
                        MultimodalPageContent(
                            page_number=page_num,
                            text="",
                            character_count=0,
                            diagrams=[],
                            is_scanned=False,
                            ocr_applied=False,
                        )
                    )

            meta = doc.metadata or {}
            clean_metadata = {
                "title": meta.get("title") or filename,
                "author": meta.get("author") or "Unknown",
                "subject": meta.get("subject") or "",
                "format": "PDF",
                "page_count": page_count,
            }

            return MultimodalPDFDocument(
                filename=filename,
                page_count=page_count,
                total_characters=total_chars,
                total_diagrams=total_diagrams,
                pages=pages,
                metadata=clean_metadata,
            )

    @classmethod
    def get_page_detail(
        cls,
        content: bytes,
        page_number: int,
        filename: str = "document.pdf",
    ) -> MultimodalPageContent:
        """
        Extracts high-resolution detail for a specific 1-indexed page number:
        text, diagrams, and rendered preview pixmap.
        """
        PDFExtractor.validate_pdf_bytes(content, filename)

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise CorruptedPDFError(f"Cannot parse PDF '{filename}': {str(e)}") from e

        with doc:
            if page_number < 1 or page_number > len(doc):
                raise ValueError(
                    f"Invalid page number {page_number}. Document '{filename}' has {len(doc)} pages."
                )

            page = doc.load_page(page_number - 1)
            native_text = page.get_text("text").strip()
            diagrams = cls._extract_page_diagrams(doc, page, page_number)

            # Render page preview
            pix = page.get_pixmap(dpi=150)
            rendered_bytes = pix.tobytes("png")

            is_scanned = len(native_text) < cls.MIN_TEXT_CHARS_FOR_NATIVE_PAGE
            ocr_applied = False
            final_text = native_text

            if is_scanned:
                try:
                    ocr_text = OCREngine.ocr_scanned_pdf_page(rendered_bytes, page_number)
                    if ocr_text:
                        final_text = f"{native_text}\n{ocr_text}".strip()
                        ocr_applied = True
                except Exception as ocr_err:
                    logger.warning("OCR failed on page %d: %s", page_number, str(ocr_err))

            return MultimodalPageContent(
                page_number=page_number,
                text=final_text,
                character_count=len(final_text),
                diagrams=diagrams,
                is_scanned=is_scanned,
                ocr_applied=ocr_applied,
                rendered_pixmap_bytes=rendered_bytes,
            )

    @classmethod
    def _extract_page_diagrams(
        cls,
        doc: fitz.Document,
        page: fitz.Page,
        page_num: int,
    ) -> List[ExtractedDiagram]:
        """Extracts embedded images and diagrams from a single PDF page."""
        diagrams: List[ExtractedDiagram] = []
        try:
            image_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                image_bytes = base_image.get("image", b"")
                # Filter out tiny icon-sized artifacts (< 40x40 or < 1KB)
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)
                if width < 40 or height < 40 or len(image_bytes) < 1024:
                    continue

                ext = base_image.get("ext", "png").lower()
                diagrams.append(
                    ExtractedDiagram(
                        index=img_idx + 1,
                        page=page_num,
                        xref=xref,
                        width=width,
                        height=height,
                        format=ext,
                        image_bytes=image_bytes,
                        size_bytes=len(image_bytes),
                    )
                )
        except Exception as e:
            logger.debug("Diagram extraction skipped on page %d: %s", page_num, str(e))

        return diagrams

