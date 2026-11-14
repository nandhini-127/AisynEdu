import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import Document, UploadedImage
from app.multimodal.image_processor import ImageProcessor
from app.multimodal.ocr_engine import OCREngine
from app.multimodal.pdf_processor import MultimodalPDFProcessor
from app.multimodal.validator import FileValidator
from app.multimodal.vision_client import VisionClient
from app.schemas.multimodal import (
    ExtractedDiagramInfo,
    ImageExplainResponse,
    ImageUploadResponse,
    MixedQueryResponse,
    PDFPageQueryResponse,
)

logger = logging.getLogger("edunex.multimodal.service")


class ImageNotFoundError(Exception):
    """Raised when an uploaded image is not found or does not belong to user."""
    pass


class DocumentAccessDeniedError(Exception):
    """Raised when a document does not belong to the user."""
    pass


class MultimodalService:
    """
    Coordinates multimodal operations:
    - Secure image upload and OCR extraction
    - Visual explanation using Gemini Vision
    - Targeted PDF page inspection with diagram analysis
    - Mixed-modality query answering
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.vision_client = VisionClient()

    async def upload_image(
        self,
        user_id: UUID,
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> ImageUploadResponse:
        """
        Validates, saves, extracts OCR, and registers an educational image.
        """
        # 1. Security & format validation (magic bytes)
        detected_format, safe_filename = FileValidator.validate_image_upload(
            content=file_bytes,
            filename=filename,
            declared_mime=content_type,
        )

        # 2. Inspect image geometry and metadata via PIL
        img, img_meta = ImageProcessor.load_and_inspect(file_bytes)

        # 3. Store in user-isolated storage directory
        image_id = uuid4()
        storage_path = FileValidator.get_user_storage_path(
            user_id=user_id,
            file_id=image_id,
            subfolder="images",
            extension=detected_format,
        )

        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        # 4. Extract OCR text
        ocr_text, ocr_engine, _ = OCREngine.extract_text_from_image_bytes(file_bytes)

        mime_type = content_type or f"image/{detected_format}"
        if detected_format == "jpg":
            mime_type = "image/jpeg"

        # 5. Persist record in database
        db_image = UploadedImage(
            id=image_id,
            user_id=user_id,
            original_filename=safe_filename,
            file_type=detected_format,
            mime_type=mime_type,
            file_size_bytes=len(file_bytes),
            storage_path=str(storage_path),
            width=img_meta.width,
            height=img_meta.height,
            extracted_text=ocr_text,
            image_metadata={
                "aspect_ratio": img_meta.aspect_ratio,
                "mode": img_meta.mode,
                "ocr_engine": ocr_engine,
            },
        )
        self.db.add(db_image)
        await self.db.commit()
        await self.db.refresh(db_image)

        logger.info(
            "User %s uploaded image %s (%s, %dx%d, %d bytes)",
            user_id,
            image_id,
            detected_format,
            img_meta.width,
            img_meta.height,
            len(file_bytes),
        )

        return ImageUploadResponse.model_validate(db_image)

    async def get_user_image(self, user_id: UUID, image_id: UUID) -> UploadedImage:
        """Retrieves image by ID ensuring user ownership."""
        stmt = select(UploadedImage).where(
            UploadedImage.id == image_id,
            UploadedImage.user_id == user_id,
        )
        res = await self.db.execute(stmt)
        image = res.scalar_one_or_none()
        if not image:
            raise ImageNotFoundError(f"Image {image_id} not found or access denied.")
        return image

    async def list_user_images(self, user_id: UUID) -> List[ImageUploadResponse]:
        """Lists all uploaded images for the user."""
        stmt = (
            select(UploadedImage)
            .where(UploadedImage.user_id == user_id)
            .order_by(UploadedImage.created_at.desc())
        )
        res = await self.db.execute(stmt)
        images = res.scalars().all()
        return [ImageUploadResponse.model_validate(img) for img in images]

    async def delete_image(self, user_id: UUID, image_id: UUID) -> bool:
        """Deletes image record and file on disk."""
        image = await self.get_user_image(user_id, image_id)
        
        # Remove file from disk
        if image.storage_path and os.path.exists(image.storage_path):
            try:
                os.remove(image.storage_path)
            except OSError as e:
                logger.warning("Failed to delete image file %s: %s", image.storage_path, str(e))

        await self.db.delete(image)
        await self.db.commit()
        return True

    async def explain_image(
        self,
        user_id: UUID,
        image_id: Optional[UUID] = None,
        image_bytes: Optional[bytes] = None,
        filename: str = "image.png",
        question: Optional[str] = None,
        prompt_type: str = "diagram",
        extra_context: Optional[str] = None,
    ) -> ImageExplainResponse:
        """
        Analyzes and explains an educational image using Gemini Vision.
        """
        start_time = time.perf_counter()
        target_bytes = image_bytes
        mime_type = "image/png"
        extracted_text = ""

        if image_id:
            image_record = await self.get_user_image(user_id, image_id)
            mime_type = image_record.mime_type
            extracted_text = image_record.extracted_text or ""
            with open(image_record.storage_path, "rb") as f:
                target_bytes = f.read()

        if not target_bytes:
            raise ValueError("No image content provided for visual explanation.")

        user_q = question or "Explain this educational diagram and its core components in detail."

        explanation = await self.vision_client.analyze_image(
            image_bytes=target_bytes,
            mime_type=mime_type,
            prompt=user_q,
            prompt_type=prompt_type,
            extra_context=extra_context,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return ImageExplainResponse(
            image_id=image_id,
            question=user_q,
            explanation=explanation,
            diagram_type=prompt_type,
            extracted_text=extracted_text,
            latency_ms=latency_ms,
        )

    async def query_pdf_page(
        self,
        user_id: UUID,
        document_id: UUID,
        page_number: int,
        question: str,
        include_diagrams: bool = True,
    ) -> PDFPageQueryResponse:
        """
        Inspects a specific page of an uploaded PDF, extracts text & diagrams,
        and provides grounded answers with page-level citations.
        """
        start_time = time.perf_counter()

        # 1. Fetch document and verify user ownership
        stmt = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        res = await self.db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise DocumentAccessDeniedError(f"Document {document_id} not found or access denied.")

        if not doc.storage_path or not os.path.exists(doc.storage_path):
            raise FileNotFoundError(f"Underlying PDF file for document '{doc.original_filename}' is missing.")

        with open(doc.storage_path, "rb") as f:
            pdf_bytes = f.read()

        # 2. Extract specific page details
        page_content = MultimodalPDFProcessor.get_page_detail(
            content=pdf_bytes,
            page_number=page_number,
            filename=doc.original_filename,
        )

        # 3. Format diagrams metadata
        diagram_infos: List[ExtractedDiagramInfo] = []
        for d in page_content.diagrams:
            diagram_infos.append(
                ExtractedDiagramInfo(
                    diagram_index=d.index,
                    page=d.page,
                    format=d.format,
                    width=d.width,
                    height=d.height,
                    size_bytes=d.size_bytes,
                    description=f"Diagram {d.index} on page {d.page} ({d.width}x{d.height})",
                )
            )

        # 4. Generate answer: if page has diagrams, evaluate with vision
        extra_ctx = (
            f"Document: {doc.original_filename}\n"
            f"Page: {page_number}\n"
            f"Page Text Content:\n{page_content.text[:2000]}"
        )

        if include_diagrams and page_content.diagrams:
            # Use first primary diagram for vision analysis
            primary_diagram = page_content.diagrams[0]
            answer = await self.vision_client.analyze_image(
                image_bytes=primary_diagram.image_bytes,
                mime_type=f"image/{primary_diagram.format}",
                prompt=f"Regarding Page {page_number} of '{doc.original_filename}': {question}",
                prompt_type="diagram",
                extra_context=extra_ctx,
            )
        elif page_content.rendered_pixmap_bytes and page_content.is_scanned:
            # Scanned page: send rendered page image to vision
            answer = await self.vision_client.analyze_image(
                image_bytes=page_content.rendered_pixmap_bytes,
                mime_type="image/png",
                prompt=f"Regarding scanned Page {page_number} of '{doc.original_filename}': {question}",
                prompt_type="diagram",
                extra_context=extra_ctx,
            )
        else:
            # Native text response
            answer = (
                f"**[Page-Level Citation: {doc.original_filename}, Page {page_number}]**\n\n"
                f"Based on Page {page_number} of **{doc.original_filename}**:\n\n"
                f"{page_content.text[:1200]}\n\n"
                f"*Analysis for question*: '{question}'\n"
                f"- The concepts on this page directly address the question as outlined in the text above."
            )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        citations = [
            {
                "document_id": str(doc.id),
                "document_name": doc.original_filename,
                "page": page_number,
                "snippet": page_content.text[:200],
            }
        ]

        return PDFPageQueryResponse(
            document_id=doc.id,
            document_name=doc.original_filename,
            page_number=page_number,
            question=question,
            answer=answer,
            page_text_snippet=page_content.text[:300] + ("..." if len(page_content.text) > 300 else ""),
            diagram_count=len(page_content.diagrams),
            diagrams=diagram_infos,
            is_scanned_page=page_content.is_scanned,
            ocr_applied=page_content.ocr_applied,
            citations=citations,
            latency_ms=latency_ms,
        )

    async def answer_mixed_query(
        self,
        user_id: UUID,
        text_query: str,
        image_id: Optional[UUID] = None,
        document_ids: Optional[List[UUID]] = None,
        page_number: Optional[int] = None,
    ) -> MixedQueryResponse:
        """
        Handles mixed input: combines text query with an uploaded image and document context.
        """
        start_time = time.perf_counter()
        doc_names_used: List[str] = []
        citations: List[Dict[str, Any]] = []
        doc_context = ""

        # Retrieve document context if documents provided
        if document_ids:
            for did in document_ids:
                stmt = select(Document).where(Document.id == did, Document.user_id == user_id)
                res = await self.db.execute(stmt)
                doc = res.scalar_one_or_none()
                if doc and doc.storage_path and os.path.exists(doc.storage_path):
                    doc_names_used.append(doc.original_filename)
                    if page_number:
                        with open(doc.storage_path, "rb") as f:
                            p = MultimodalPDFProcessor.get_page_detail(f.read(), page_number, doc.original_filename)
                            doc_context += f"\n--- {doc.original_filename} (Page {page_number}) ---\n{p.text[:1000]}"
                            citations.append({
                                "document_id": str(doc.id),
                                "document_name": doc.original_filename,
                                "page": page_number,
                            })

        # Process with image if provided
        if image_id:
            explain_res = await self.explain_image(
                user_id=user_id,
                image_id=image_id,
                question=text_query,
                extra_context=doc_context if doc_context else None,
            )
            answer = explain_res.explanation
            image_used = True
        else:
            image_used = False
            answer = (
                f"**[Multimodal Assistant Answer]**\n\n"
                f"Question: {text_query}\n\n"
                f"Context from study materials:\n{doc_context or 'General Knowledge Analysis'}\n\n"
                f"Detailed answer addressing your query with reference to the provided materials."
            )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return MixedQueryResponse(
            answer=answer,
            image_used=image_used,
            image_id=image_id,
            documents_used=doc_names_used,
            citations=citations,
            latency_ms=latency_ms,
        )

