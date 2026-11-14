import logging
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entities import User
from app.rag.extractor import (
    CorruptedPDFError,
    EmptyPDFError,
    PDFProcessingError,
)
from app.rag.service import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    RAGService,
)
from app.schemas.base import ApiResponse
from app.schemas.rag import (
    DocumentQueryRequest,
    DocumentQueryResponse,
    DocumentRead,
    DocumentUploadResponse,
)

logger = logging.getLogger("edunex.api.documents")

router = APIRouter(prefix="/documents", tags=["Educational Documents & RAG"])


@router.post(
    "/upload",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest educational PDF",
)
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form("general"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads a study material PDF, validates it, extracts text page-by-page,
    splits text into chunks, generates vector embeddings, and stores them in ChromaDB.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents (.pdf) are supported.",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    rag_service = RAGService(db_session=db)

    try:
        doc = await rag_service.ingest_document(
            user_id=current_user.id,
            file_bytes=content,
            filename=file.filename,
            subject=subject.strip(),
        )
        doc_read = DocumentRead.model_validate(doc)
        return ApiResponse(
            success=True,
            message="Document uploaded, indexed, and ready for study queries.",
            data=DocumentUploadResponse(
                document=doc_read,
                chunk_count=doc.chunk_count,
                message=f"Successfully extracted {doc.chunk_count} chunk(s).",
            ).model_dump(),
        )
    except EmptyPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except CorruptedPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except PDFProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Unhandled error ingesting document %s: %s", file.filename, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process educational document: {str(e)}",
        )


@router.get(
    "",
    response_model=ApiResponse,
    summary="List all study materials uploaded by user",
)
async def list_documents(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all educational documents owned by the authenticated student.
    Zero cross-user data exposure.
    """
    rag_service = RAGService(db_session=db)
    docs = await rag_service.list_user_documents(user_id=current_user.id, subject=subject)
    data = [DocumentRead.model_validate(d).model_dump() for d in docs]
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data)} document(s).",
        data=data,
    )


@router.get(
    "/{document_id}",
    response_model=ApiResponse,
    summary="Get single document status and metadata",
)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Gets details of a single document owned by the authenticated student.
    """
    rag_service = RAGService(db_session=db)
    try:
        doc = await rag_service.get_document(user_id=current_user.id, doc_id=document_id)
        return ApiResponse(
            success=True,
            data=DocumentRead.model_validate(doc).model_dump(),
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or access denied.",
        )


@router.delete(
    "/{document_id}",
    response_model=ApiResponse,
    summary="Delete document and remove all vector embeddings",
)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a document from the database and removes all its vector chunks from ChromaDB.
    """
    rag_service = RAGService(db_session=db)
    try:
        await rag_service.delete_document(user_id=current_user.id, doc_id=document_id)
        return ApiResponse(
            success=True,
            message=f"Document {document_id} and all associated vector embeddings have been deleted.",
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or access denied.",
        )


@router.post(
    "/query",
    response_model=ApiResponse,
    summary="Ask question over uploaded study materials (RAG QA)",
)
async def query_documents(
    req: DocumentQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Performs grounded semantic retrieval and LLM question answering over the student's study materials.
    Returns answer, source document citations with page numbers, and retrieval latency.
    """
    rag_service = RAGService(db_session=db)
    try:
        result: DocumentQueryResponse = await rag_service.query(
            user_id=current_user.id,
            query_text=req.query,
            doc_ids=req.document_ids,
            subject=req.subject,
            top_k=req.top_k or 4,
            similarity_threshold=req.similarity_threshold,
        )
        return ApiResponse(
            success=True,
            message="RAG query answered successfully.",
            data=result.model_dump(),
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Error executing RAG query: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute RAG query: {str(e)}",
        )

