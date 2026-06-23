"""Memory.md ingestion pipeline — structured template recognition and context extraction.

Implements the full pipeline:
    file detection → parsing → entity matching → context extraction → dedup → ingest

Design Doc §3.1 Memory.md import pipeline with 4-chapter template recognition.
"""
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.integrations.memory_md_parser import parse_memory_md, scan_memory_directory
from app.services.ingestion_service import ingest_context
from app.pipelines.dedup_pipeline import dedup_check


def process_memory_file(
    db: Session,
    file_path: str,
    actor: str = "system:memory_md_importer",
) -> list:
    """Process a single Memory.md file through the full ingestion pipeline.

    Returns list of created ContextItems.
    """
    parsed = parse_memory_md(file_path)
    if parsed is None:
        return []

    results = []
    for section in parsed.get("sections", []):
        role = section["role"]
        content = section["content"]
        entities = section.get("entities", [])

        # Dedup check
        duplicate = dedup_check(db, content)
        if duplicate:
            continue

        # Determine context_subtype and structured_fields
        context_subtype = None
        structured_fields = None
        source_type = "memory_md"

        if role == "lesson_learned":
            context_subtype = "lesson_learned"
            source_type = "lesson_learned"
            # Extract table columns if present
            structured_fields = _extract_lesson_learned_fields(section["content"])

        # Generate context_id
        ctx_id = f"ctx_md_{uuid.uuid4().hex[:8]}"

        ctx = ingest_context(
            db=db,
            actor=actor,
            title=f"Memory.md: {parsed['title']} — {_role_label(role)}",
            content=content,
            context_id=ctx_id,
            source_system="memory_md",
            source_type=source_type,
            source_platform=file_path,
            context_subtype=context_subtype,
            context_role=role,
            structured_fields=structured_fields,
            entities=entities,
        )
        results.append(ctx)

    return results


def process_memory_directory(
    db: Session,
    directory: str,
    actor: str = "system:memory_md_importer",
) -> list:
    """Process all .md files in a directory."""
    files = scan_memory_directory(directory)
    all_results = []
    for f in files:
        all_results.extend(process_memory_file(db, f, actor))
    return all_results


def _role_label(role: str) -> str:
    labels = {
        "goal": "目标",
        "progress": "进度",
        "finding": "发现",
        "lesson_learned": "经验教训",
    }
    return labels.get(role, role)


def _extract_lesson_learned_fields(content: str) -> Optional[dict]:
    """Extract table columns from Lessons Learned section.

    Expected table format:
    | 错误/问题 | 尝试方案 | 最终解决方案 | 经验总结 |

    Returns structured_fields JSONB dict.
    """
    # Try to parse markdown tables
    import re
    lines = content.strip().split("\n")
    if len(lines) < 2:
        return None

    # Look for table rows (lines starting with |)
    table_rows = [line for line in lines if line.strip().startswith("|")]
    if len(table_rows) < 2:
        return None

    # Skip header row + separator, take first data row
    data_rows = [r for r in table_rows if not re.match(r"^\|[\s\-:]+\|", r)]
    if not data_rows:
        return None

    cells = [c.strip() for c in data_rows[0].split("|")[1:-1]]
    if len(cells) >= 4:
        return {
            "error": cells[0] if len(cells) > 0 else "",
            "attempt": cells[1] if len(cells) > 1 else "",
            "resolution": cells[2] if len(cells) > 2 else "",
            "summary": cells[3] if len(cells) > 3 else "",
        }
    return None
