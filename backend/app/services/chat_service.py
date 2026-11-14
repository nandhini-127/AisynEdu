from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Message, Session, User
from app.schemas.base import MessageCreate, SessionCreate


class ChatService:
    @staticmethod
    async def get_session_by_id(db: AsyncSession, session_id: UUID) -> Optional[Session]:
        result = await db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_session(db: AsyncSession, user_id: UUID, data: SessionCreate) -> Session:
        doc_ids_serialized = [str(did) for did in data.document_ids]
        session = Session(
            user_id=user_id,
            subject=data.subject,
            title=data.title or f"{data.subject} Discussion",
            document_ids=doc_ids_serialized,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def list_user_sessions(db: AsyncSession, user_id: UUID) -> List[Session]:
        result = await db.execute(
            select(Session).where(Session.user_id == user_id).order_by(Session.updated_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_message(
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        intent: str = "qa",
        sources: list = None,
        token_count: int = 0,
        latency_ms: int = 0,
        llm_provider: Optional[str] = None,
    ) -> Message:
        msg = Message(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            intent=intent,
            sources=sources or [],
            token_count=token_count,
            latency_ms=latency_ms,
            llm_provider=llm_provider,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def get_session_messages(db: AsyncSession, session_id: UUID) -> List[Message]:
        result = await db.execute(
            select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
