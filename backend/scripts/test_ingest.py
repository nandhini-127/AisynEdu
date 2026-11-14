import asyncio
import os
import sys
import uuid
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.database import Base
from app.models.entities import User
from app.rag.service import RAGService
from app.rag.vectorstore import ChromaVectorStore

async def main():
    print("1. Creating in-memory SQLite engine...", flush=True)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        print("2. Creating sample user...", flush=True)
        user = User(
            id=uuid.uuid4(),
            email="test@edunex.ai",
            name="Test User",
            hashed_password="hash",
            role="student",
        )
        db.add(user)
        await db.commit()

        pdf_path = Path("backend/data/sample_pdfs/operating_systems.pdf")
        print(f"3. Reading PDF bytes from {pdf_path} (exists={pdf_path.exists()})...", flush=True)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        print(f"Read {len(pdf_bytes)} bytes", flush=True)

        print("4. Initializing ChromaVectorStore and RAGService...", flush=True)
        vs = ChromaVectorStore(persist_dir="./temp_chroma")
        service = RAGService(db_session=db, vector_store=vs)

        print("5. Calling ingest_document...", flush=True)
        doc = await service.ingest_document(
            user_id=user.id,
            file_bytes=pdf_bytes,
            filename="operating_systems.pdf",
            subject="Computer Science",
        )
        print("6. Ingestion SUCCESS! Status:", doc.status, "Chunks:", doc.chunk_count, flush=True)

        print("7. Testing query...", flush=True)
        resp = await service.query(
            user_id=user.id,
            query_text="What are Coffman's four deadlock conditions?",
        )
        print("8. Query SUCCESS! Answer:", resp.answer[:100], "Citations:", len(resp.citations), flush=True)

    await engine.dispose()
    print("ALL DONE!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
