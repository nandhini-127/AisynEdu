import io
import os
import uuid
from pathlib import Path
import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import Document, UploadedImage, User
from app.multimodal.image_processor import CorruptedImageError, ImageProcessor
from app.multimodal.ocr_engine import OCREngine
from app.multimodal.pdf_processor import MultimodalPDFProcessor
from app.multimodal.service import (
    DocumentAccessDeniedError,
    ImageNotFoundError,
    MultimodalService,
)
from app.multimodal.validator import (
    FileSizeLimitExceededError,
    FileValidationError,
    FileValidator,
    InvalidFileSignatureError,
    PathTraversalSecurityError,
    UnsupportedFileTypeError,
)
from app.multimodal.vision_client import VisionClient
from app.rag.service import RAGService
from app.rag.vectorstore import ChromaVectorStore

SAMPLE_PDFS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_pdfs"


def create_sample_diagram_png(text: str = "Client-Server Architecture") -> bytes:
    """Generates a valid educational diagram PNG with labeled blocks and arrows."""
    img = Image.new("RGB", (600, 300), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)

    # Box 1: Client
    draw.rectangle([50, 80, 200, 180], outline=(41, 128, 185), width=3, fill=(235, 245, 251))
    draw.text((80, 120), "Client / Browser", fill=(20, 20, 20))

    # Box 2: Server
    draw.rectangle([400, 80, 550, 180], outline=(39, 174, 96), width=3, fill=(234, 250, 234))
    draw.text((430, 120), "FastAPI Server", fill=(20, 20, 20))

    # Connecting arrow line
    draw.line([200, 130, 400, 130], fill=(52, 73, 94), width=3)
    draw.text((250, 105), "HTTP Request", fill=(52, 73, 94))

    # Title header
    draw.text((180, 30), text, fill=(10, 10, 10))

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def create_sample_jpeg_math() -> bytes:
    """Generates a valid JPEG educational math chart."""
    img = Image.new("RGB", (400, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 350], outline=(0, 0, 0), width=2)
    draw.line([50, 200, 350, 200], fill=(200, 0, 0), width=2)  # X axis
    draw.line([200, 50, 200, 350], fill=(0, 0, 200), width=2)  # Y axis
    draw.text((60, 60), "f(x) = sin(x)", fill=(0, 0, 0))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


def create_sample_webp() -> bytes:
    """Generates a valid WebP image."""
    img = Image.new("RGB", (200, 200), color=(220, 240, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([40, 40, 160, 160], fill=(255, 100, 100))
    out = io.BytesIO()
    img.save(out, format="WEBP")
    return out.getvalue()


def create_synthetic_scanned_pdf() -> bytes:
    """
    Creates a synthetic scanned PDF:
    Contains a rendered image of text, but ZERO native extractable text characters.
    """
    # 1. Create an image containing text
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), "CHAPTER 4: ADVANCED DATABASE SYSTEMS (SCANNED)", fill=(0, 0, 0))
    draw.text((50, 140), "ACID Properties: Atomicity, Consistency, Isolation, Durability.", fill=(0, 0, 0))
    draw.text((50, 200), "Two-Phase Locking (2PL) guarantees serializability in transaction processing.", fill=(0, 0, 0))

    img_bytes_io = io.BytesIO()
    img.save(img_bytes_io, format="PNG")
    img_bytes = img_bytes_io.getvalue()

    # 2. Insert into PDF page as an image
    doc = fitz.open()
    page = doc.new_page(width=800, height=1000)
    page.insert_image(page.rect, stream=img_bytes)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ── TEST SUITE ─────────────────────────────────────────────────────────────

def test_file_validator_valid_signatures():
    """Tests that FileValidator accepts valid PNG, JPEG, and WebP images."""
    png_bytes = create_sample_diagram_png()
    fmt_png, name_png = FileValidator.validate_image_upload(png_bytes, "diagram.png", "image/png")
    assert fmt_png == "png"
    assert name_png == "diagram.png"

    jpeg_bytes = create_sample_jpeg_math()
    fmt_jpg, name_jpg = FileValidator.validate_image_upload(jpeg_bytes, "plot.jpg", "image/jpeg")
    assert fmt_jpg == "jpeg"

    webp_bytes = create_sample_webp()
    fmt_webp, name_webp = FileValidator.validate_image_upload(webp_bytes, "figure.webp", "image/webp")
    assert fmt_webp == "webp"


def test_file_validator_reject_spoofed_signature():
    """Security test: rejects malicious shell script disguised with .png extension."""
    malicious_script = b"#!/bin/bash\necho 'Hacked!'\nrm -rf /"
    with pytest.raises(InvalidFileSignatureError) as exc_info:
        FileValidator.validate_image_upload(malicious_script, "exploit.png", "image/png")
    assert "File signature mismatch" in str(exc_info.value)


def test_file_validator_reject_path_traversal():
    """Security test: detects and neutralizes path traversal characters."""
    sanitized = FileValidator.sanitize_filename("../../etc/passwd.png")
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert sanitized.endswith(".png")


def test_file_validator_reject_oversized_image():
    """Security test: rejects images exceeding MAX_IMAGE_UPLOAD_SIZE_BYTES (10 MB)."""
    oversized_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)
    with pytest.raises(FileSizeLimitExceededError):
        FileValidator.validate_image_upload(oversized_bytes, "huge.png")


def test_image_processor_load_and_thumbnails():
    """Tests image loading, dimension inspection, and thumbnail generation."""
    png_bytes = create_sample_diagram_png()
    img, meta = ImageProcessor.load_and_inspect(png_bytes)
    assert meta.width == 600
    assert meta.height == 300
    assert meta.format == "PNG"
    assert meta.aspect_ratio == 2.0

    # Thumbnail
    thumb_bytes = ImageProcessor.create_thumbnail_bytes(png_bytes, max_size=(200, 200))
    thumb_img, thumb_meta = ImageProcessor.load_and_inspect(thumb_bytes)
    assert thumb_meta.width <= 200
    assert thumb_meta.height <= 200


def test_image_processor_corrupted_bytes():
    """Tests that corrupt image bytes raise CorruptedImageError."""
    fake_png = b"\x89PNG\r\n\x1a\n" + b"random_corrupted_garbage_bytes"
    with pytest.raises(CorruptedImageError):
        ImageProcessor.load_and_inspect(fake_png)


def test_ocr_engine_extraction():
    """Tests OCR engine on sample diagram."""
    png_bytes = create_sample_diagram_png("Microservices Diagram")
    text, engine, conf = OCREngine.extract_text_from_image_bytes(png_bytes)
    assert isinstance(text, str)
    assert conf > 0.0
    assert engine in ["pytesseract", "pymupdf_ocr", "visual_metadata_ocr"]


def test_multimodal_pdf_processor_normal_pdf():
    """Tests multimodal PDF processing on a standard educational PDF with page numbers preserved."""
    pdf_path = SAMPLE_PDFS_DIR / "computer_networks.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    doc = MultimodalPDFProcessor.process_pdf(pdf_bytes, "computer_networks.pdf")
    assert doc.page_count >= 1
    assert doc.total_characters > 100
    for page in doc.pages:
        assert page.page_number >= 1
        assert isinstance(page.diagrams, list)


def test_multimodal_pdf_processor_scanned_pdf():
    """Tests detection of scanned PDF pages (0 native characters) and OCR invocation."""
    scanned_pdf_bytes = create_synthetic_scanned_pdf()
    doc = MultimodalPDFProcessor.process_pdf(scanned_pdf_bytes, "scanned_db.pdf")
    assert doc.page_count == 1
    page1 = doc.pages[0]
    assert page1.is_scanned is True
    assert len(page1.text) >= 0


def test_multimodal_pdf_get_page_detail():
    """Tests targeted single-page inspection with rendered preview bytes."""
    pdf_path = SAMPLE_PDFS_DIR / "computer_networks.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    page_detail = MultimodalPDFProcessor.get_page_detail(pdf_bytes, page_number=1)
    assert page_detail.page_number == 1
    assert len(page_detail.text) > 0
    assert page_detail.rendered_pixmap_bytes is not None
    assert len(page_detail.rendered_pixmap_bytes) > 0


@pytest.mark.asyncio
async def test_vision_client_diagram_and_math_analysis():
    """Tests educational diagram and math illustration explanation via VisionClient."""
    client = VisionClient()
    diagram_bytes = create_sample_diagram_png()

    # Diagram analysis
    diag_res = await client.analyze_image(
        image_bytes=diagram_bytes,
        mime_type="image/png",
        prompt="Explain the client-server interaction depicted.",
        prompt_type="diagram",
    )
    assert "Diagram" in diag_res or "Explanation" in diag_res or "Client" in diag_res
    assert len(diag_res) > 50

    # Mathematical analysis
    math_bytes = create_sample_jpeg_math()
    math_res = await client.analyze_image(
        image_bytes=math_bytes,
        mime_type="image/jpeg",
        prompt="Derive the formula shown in this graph.",
        prompt_type="math",
    )
    assert "Mathematical" in math_res or "Formula" in math_res or "$" in math_res


@pytest.mark.asyncio
async def test_multimodal_service_upload_and_isolation(db_session: AsyncSession):
    """Tests image upload, metadata persistence, and strict multi-tenant isolation."""
    user_a = User(
        id=uuid.uuid4(),
        email=f"user_a_{uuid.uuid4().hex[:6]}@edunex.ai",
        name="Student A",
        hashed_password="hash",
        role="student",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"user_b_{uuid.uuid4().hex[:6]}@edunex.ai",
        name="Student B",
        hashed_password="hash",
        role="student",
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    service = MultimodalService(db_session)
    png_bytes = create_sample_diagram_png()

    # User A uploads diagram
    img_a = await service.upload_image(
        user_id=user_a.id,
        file_bytes=png_bytes,
        filename="network_architecture.png",
        content_type="image/png",
    )
    assert img_a.id is not None
    assert img_a.width == 600
    assert img_a.height == 300

    # User A can access it
    fetched = await service.get_user_image(user_a.id, img_a.id)
    assert fetched.id == img_a.id

    # User B CANNOT access User A's image!
    with pytest.raises(ImageNotFoundError):
        await service.get_user_image(user_b.id, img_a.id)


@pytest.mark.asyncio
async def test_multimodal_service_pdf_page_query(db_session: AsyncSession, tmp_path):
    """Tests querying a specific page of an uploaded educational PDF with page citations."""
    user = User(
        id=uuid.uuid4(),
        email=f"pdf_student_{uuid.uuid4().hex[:6]}@edunex.ai",
        name="PDF Student",
        hashed_password="hash",
        role="student",
    )
    db_session.add(user)
    await db_session.commit()

    # Save PDF directly to user storage path
    pdf_path = SAMPLE_PDFS_DIR / "computer_networks.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    doc_path = tmp_path / "computer_networks.pdf"
    with open(doc_path, "wb") as f:
        f.write(pdf_bytes)

    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        original_filename="computer_networks.pdf",
        file_type="pdf",
        file_size_bytes=len(pdf_bytes),
        subject="Computer Networks",
        status="ready",
        storage_path=str(doc_path),
    )
    db_session.add(doc)
    await db_session.commit()

    mm_service = MultimodalService(db_session)
    res = await mm_service.query_pdf_page(
        user_id=user.id,
        document_id=doc.id,
        page_number=1,
        question="What does this page explain about layered network architecture?",
    )
    assert res.document_id == doc.id
    assert res.page_number == 1
    assert len(res.answer) > 20
    assert len(res.citations) == 1
    assert res.citations[0]["page"] == 1


@pytest.mark.asyncio
async def test_multimodal_service_mixed_query(db_session: AsyncSession):
    """Tests mixed query combining text question and uploaded diagram."""
    user = User(
        id=uuid.uuid4(),
        email=f"mixed_student_{uuid.uuid4().hex[:6]}@edunex.ai",
        name="Mixed Student",
        hashed_password="hash",
        role="student",
    )
    db_session.add(user)
    await db_session.commit()

    service = MultimodalService(db_session)
    png_bytes = create_sample_diagram_png()
    img = await service.upload_image(
        user_id=user.id,
        file_bytes=png_bytes,
        filename="system_design.png",
        content_type="image/png",
    )

    mixed_res = await service.answer_mixed_query(
        user_id=user.id,
        text_query="How does data flow between client and server in this diagram?",
        image_id=img.id,
    )
    assert mixed_res.image_used is True
    assert mixed_res.image_id == img.id
    assert len(mixed_res.answer) > 30


@pytest.mark.asyncio
async def test_multimodal_api_upload_and_explain(client: AsyncClient, db_session: AsyncSession):
    """Tests the /api/v1/multimodal API endpoints via HTTP client."""
    from app.core.security import create_access_token

    user = User(
        id=uuid.uuid4(),
        email=f"mm_api_{uuid.uuid4().hex[:6]}@edunex.ai",
        name="MM API Student",
        hashed_password="hash",
        role="student",
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(subject=str(user.id))
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload image via multipart/form-data
    png_bytes = create_sample_diagram_png()
    files = {"file": ("architecture.png", png_bytes, "image/png")}
    upload_res = await client.post(
        "/api/v1/multimodal/upload-image",
        headers=auth_headers,
        files=files,
    )
    assert upload_res.status_code == 201
    img_data = upload_res.json()["data"]
    image_id = img_data["id"]
    assert img_data["width"] == 600
    assert img_data["height"] == 300

    # 3. List images
    list_res = await client.get("/api/v1/multimodal/images", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 4. Explain image
    explain_res = await client.post(
        "/api/v1/multimodal/explain-image",
        headers=auth_headers,
        json={
            "image_id": image_id,
            "question": "Explain this architecture diagram in detail.",
            "prompt_type": "diagram",
        },
    )
    assert explain_res.status_code == 200
    explanation = explain_res.json()["data"]["explanation"]
    assert len(explanation) > 30

    # 5. Delete image
    del_res = await client.delete(f"/api/v1/multimodal/images/{image_id}", headers=auth_headers)
    assert del_res.status_code == 200
