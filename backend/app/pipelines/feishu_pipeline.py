"""Feishu data ingestion pipeline — collects documents and group messages from Feishu."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.integrations.feishu_client import FeishuClient
from app.services.ingestion_service import ingest_context
from app.pipelines.dedup_pipeline import dedup_check


def sync_feishu_documents(
    db: Session,
    client: FeishuClient,
    folder_token: Optional[str] = None,
    actor: str = "system:feishu_sync",
) -> list:
    """Sync Feishu documents into the context platform."""
    documents = client.list_documents(folder_token)
    results = []

    for doc in documents:
        doc_token = doc.get("token")
        title = doc.get("name", "Unknown")
        if not doc_token:
            continue

        content = client.get_document_content(doc_token)
        if not content:
            continue

        duplicate = dedup_check(db, content)
        if duplicate:
            continue

        ctx_id = f"ctx_fs_{uuid.uuid4().hex[:8]}"
        ctx = ingest_context(
            db=db, actor=actor, title=title, content=content,
            context_id=ctx_id, source_system="feishu",
            source_type="meeting_minutes",
            source_platform="feishu_drive",
        )
        results.append(ctx)
    return results


def sync_feishu_group_messages(
    db: Session,
    client: FeishuClient,
    chat_id: str,
    actor: str = "system:feishu_sync",
) -> list:
    """Sync Feishu group messages into the context platform."""
    messages = client.list_group_messages(chat_id)
    results = []

    for msg in messages:
        msg_id = msg.get("message_id")
        if not msg_id:
            continue

        content = client.get_message_content(msg_id)
        if not content:
            continue

        duplicate = dedup_check(db, content)
        if duplicate:
            continue

        ctx_id = f"ctx_fs_msg_{uuid.uuid4().hex[:8]}"
        ctx = ingest_context(
            db=db, actor=actor,
            title=f"飞书群消息 — {chat_id}",
            content=content, context_id=ctx_id,
            source_system="feishu", source_type="verbal",
            source_platform="feishu_group",
        )
        results.append(ctx)
    return results
