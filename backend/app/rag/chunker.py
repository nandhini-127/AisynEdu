import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger("edunex.rag.chunker")


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    user_id: str
    page_number: int
    chunk_index: int
    text: str
    char_length: int
    metadata: Dict[str, Any]


class DocumentChunker:
    """
    Splits document pages into semantically cohesive chunks using recursive character
    text splitting, preserving page numbers, document IDs, and citation metadata.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "; ", ", ", " ", ""]

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def split_pages(
        self,
        pages: List[tuple[int, str]],  # [(page_number, text), ...]
        doc_id: UUID,
        user_id: UUID,
        filename: str,
        subject: str,
    ) -> List[DocumentChunk]:
        """
        Splits list of (page_num, text) into DocumentChunks with full tracking metadata.
        """
        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page_num, page_text in pages:
            if not page_text or not page_text.strip():
                continue

            raw_chunks = self._splitter.split_text(page_text)

            for raw_chunk in raw_chunks:
                clean_chunk = raw_chunk.strip()
                if not clean_chunk:
                    continue

                chunk_id = f"{doc_id}_p{page_num}_c{global_chunk_idx}"
                meta = {
                    "doc_id": str(doc_id),
                    "user_id": str(user_id),
                    "filename": filename,
                    "subject": subject,
                    "page": page_num,
                    "chunk_index": global_chunk_idx,
                }

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=str(doc_id),
                        user_id=str(user_id),
                        page_number=page_num,
                        chunk_index=global_chunk_idx,
                        text=clean_chunk,
                        char_length=len(clean_chunk),
                        metadata=meta,
                    )
                )
                global_chunk_idx += 1

        logger.info(
            "Chunked document %s (%s) into %d chunks (chunk_size=%d, overlap=%d)",
            filename,
            str(doc_id)[:8],
            len(chunks),
            self.chunk_size,
            self.chunk_overlap,
        )
        return chunks

