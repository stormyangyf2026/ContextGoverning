"""Project knowledge base ingestion pipeline.

Syncs documents from IMA/Feishu Drive into the context platform.
"""
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.integrations.project_kb_client import ProjectKbClient
from app.services.ingestion_service import ingest_context
from app.pipelines.dedup_pipeline import dedup_check


def sync_kb_documents(
    db: Session,
    client: ProjectKbClient,
    space_id: Optional[str] = None,
    actor: str = "system:project_kb_sync",
) -> list:
    """Sync documents from a knowledge base to the context platform.

    Returns list of created ContextItems.
    """
    documents = client.list_documents(space_id)
    results = []

    for doc in documents:
        doc_id = doc.get("id") or doc.get("file_id")
        if not doc_id:
            continue

        # Get full document content
        full_doc = client.get_document(doc_id)
        if not full_doc:
            continue

        title = full_doc.get("title") or doc.get("name", "Unknown")
        content = full_doc.get("content") or full_doc.get("body", "")

        # Dedup
        duplicate = dedup_check(db, content)
        if duplicate:
            continue

        ctx_id = f"ctx_kb_{uuid.uuid4().hex[:8]}"

        ctx = ingest_context(
            db=db,
            actor=actor,
            title=title,
            content=content,
            context_id=ctx_id,
            source_system="project_kb",
            source_type="project_kb",
            source_platform=client.platform,
            source_url=full_doc.get("url"),
        )
        results.append(ctx)

    return results
