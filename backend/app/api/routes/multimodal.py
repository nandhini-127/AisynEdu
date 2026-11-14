import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entities import User
from app.multimodal.image_processor import CorruptedImageError
from app.multimodal.service import (
    DocumentAccessDeniedError,
    ImageNotFoundError,
    MultimodalService,
)
from app.multimodal.validator import (
    FileSizeLimitExceededError,
    FileValidationError,
    InvalidFileSignatureError,
    PathTraversalSecurityError,
    UnsupportedFileTypeError,
)
from app.schemas.base import ApiResponse
from app.schemas.multimodal import (
    ImageExplainRequest,
    ImageExplainResponse,
    ImageUploadResponse,
    MixedQueryRequest,
    MixedQueryResponse,
    PDFPageQueryRequest,
    PDFPageQueryResponse,
)

logger = logging.getLogger("edunex.api.multimodal")

router = APIRouter(prefix="/multimodal", tags=["Multimodal Educational Assistant"])


@router.post(
    "/upload-image",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an educational diagram or image",
)
async def upload_image(
    file: UploadFile = File(..., description="Educational image (PNG, JPEG, WebP)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads, validates, and runs initial OCR on an educational image.
    Enforces binary magic byte validation, maximum 10MB file limit, and user directory isolation.
    """
    try:
        content = await file.read()
        service = MultimodalService(db)
        image_response = await service.upload_image(
            user_id=current_user.id,
            file_bytes=content,
            filename=file.filename or "upload.png",
            content_type=file.content_type,
        )
        return ApiResponse(
            success=True,
            message="Educational image uploaded and processed successfully",
            data=image_response,
        )
    except FileSizeLimitExceededError as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
    except (InvalidFileSignatureError, UnsupportedFileTypeError, PathTraversalSecurityError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (FileValidationError, CorruptedImageError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error("Failed to upload image: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the image: {str(e)}",
        )


@router.post(
    "/explain-image",
    response_model=ApiResponse,
    summary="Ask questions and explain an educational diagram using Gemini Vision",
)
async def explain_image(
    payload: ImageExplainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Explains an educational image, diagram, chart, or math illustration using Gemini Vision.
    """
    try:
        service = MultimodalService(db)
        res = await service.explain_image(
            user_id=current_user.id,
            image_id=payload.image_id,
            question=payload.question,
            prompt_type=payload.prompt_type,
        )
        return ApiResponse(
            success=True,
            data=res,
        )
    except ImageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to explain image: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision explanation failed: {str(e)}",
        )


@router.post(
    "/pdf-page-query",
    response_model=ApiResponse,
    summary="Ask questions about a specific PDF page with diagram analysis",
)
async def query_pdf_page(
    payload: PDFPageQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Performs targeted analysis of a specific PDF page, extracting page text,
    diagrams, and generating grounded explanations.
    """
    try:
        service = MultimodalService(db)
        res = await service.query_pdf_page(
            user_id=current_user.id,
            document_id=payload.document_id,
            page_number=payload.page_number,
            question=payload.question,
            include_diagrams=payload.include_diagrams,
        )
        return ApiResponse(
            success=True,
            data=res,
        )
    except DocumentAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to query PDF page: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF page query failed: {str(e)}",
        )


@router.post(
    "/mixed-query",
    response_model=ApiResponse,
    summary="Ask questions using mixed input (text + image + documents)",
)
async def answer_mixed_query(
    payload: MixedQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts student questions combined with an uploaded image and document references.
    """
    try:
        service = MultimodalService(db)
        res = await service.answer_mixed_query(
            user_id=current_user.id,
            text_query=payload.text_query,
            image_id=payload.image_id,
            document_ids=payload.document_ids,
            page_number=payload.page_number,
        )
        return ApiResponse(
            success=True,
            data=res,
        )
    except ImageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to process mixed query: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mixed query processing failed: {str(e)}",
        )


@router.get(
    "/images",
    response_model=ApiResponse,
    summary="List student's uploaded educational images",
)
async def list_images(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all uploaded images belonging to the authenticated student."""
    service = MultimodalService(db)
    images = await service.list_user_images(current_user.id)
    return ApiResponse(
        success=True,
        data=images,
    )


@router.get(
    "/images/{image_id}",
    response_model=ApiResponse,
    summary="Get image metadata by ID",
)
async def get_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves metadata of a specific image."""
    try:
        service = MultimodalService(db)
        image = await service.get_user_image(current_user.id, image_id)
        return ApiResponse(
            success=True,
            data=ImageUploadResponse.model_validate(image),
        )
    except ImageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/images/{image_id}",
    response_model=ApiResponse,
    summary="Delete an uploaded image",
)
async def delete_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes an image record and removes its underlying file from disk."""
    try:
        service = MultimodalService(db)
        await service.delete_image(current_user.id, image_id)
        return ApiResponse(
            success=True,
            message="Image successfully deleted",
        )
    except ImageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

