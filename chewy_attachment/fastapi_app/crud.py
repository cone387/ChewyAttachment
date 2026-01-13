"""CRUD operations for ChewyAttachment FastAPI app"""

from typing import Optional

from sqlmodel import Session, select

from ..core.utils import generate_uuid
from .models import Attachment, AttachmentCreate


def create_attachment(session: Session, data: AttachmentCreate) -> Attachment:
    """
    Create a new attachment record.

    Args:
        session: Database session
        data: Attachment creation data

    Returns:
        Created Attachment instance
    """
    attachment = Attachment(
        id=generate_uuid(),
        original_name=data.original_name,
        storage_path=data.storage_path,
        mime_type=data.mime_type,
        size=data.size,
        owner_id=data.owner_id,
        is_public=data.is_public,
    )
    session.add(attachment)
    session.commit()
    session.refresh(attachment)
    return attachment


def get_attachment(session: Session, attachment_id: str) -> Optional[Attachment]:
    """
    Get attachment by ID.

    Args:
        session: Database session
        attachment_id: Attachment ID

    Returns:
        Attachment instance or None
    """
    statement = select(Attachment).where(Attachment.id == attachment_id)
    return session.exec(statement).first()


def get_attachments_by_owner(
    session: Session,
    owner_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[Attachment]:
    """
    Get attachments by owner ID.

    Args:
        session: Database session
        owner_id: Owner ID
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of Attachment instances
    """
    statement = (
        select(Attachment)
        .where(Attachment.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
        .order_by(Attachment.created_at.desc())
    )
    return list(session.exec(statement).all())


def delete_attachment(session: Session, attachment: Attachment) -> bool:
    """
    Delete attachment record.

    Args:
        session: Database session
        attachment: Attachment instance to delete

    Returns:
        True if deleted
    """
    session.delete(attachment)
    session.commit()
    return True
