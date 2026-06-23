"""Memory.md file parser — reads and parses Memory.md files for context extraction.

Supports:
    - Single file mode: parse one .md file
    - Directory mode: scan all .md files in a directory
    - Workspace mode: integrate with .codebuddy/memory/ daily logs
"""
import os
import re
from typing import Optional, List, Dict


def parse_memory_md(file_path: str) -> Optional[Dict]:
    """Parse a single Memory.md file and extract structured information.

    Returns:
        Dict with keys: title, sections (list of {role, content, entities}),
        or None if file not found/unreadable.
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Extract title (first # heading)
    title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else os.path.basename(file_path)

    # Extract structured sections
    sections = _extract_sections(raw)

    return {
        "file_path": file_path,
        "title": title,
        "sections": sections,
        "raw": raw,
    }


def _extract_sections(content: str) -> List[Dict]:
    """Extract sections from Memory.md content based on the recommended template."""
    sections = []

    # Section patterns matching the 4-chapter template
    patterns = [
        ("goal", r"##\s+\d*\.?\s*(?:目标|Goal)\s*\n(.*?)(?=\n##\s|\Z)"),
        ("progress", r"##\s+\d*\.?\s*(?:进度与阶段|Phases.*?Progress|Phase)\s*\n(.*?)(?=\n##\s|\Z)"),
        ("finding", r"##\s+\d*\.?\s*(?:关键发现与知识|Findings.*?Knowledge)\s*\n(.*?)(?=\n##\s|\Z)"),
        ("lesson_learned", r"##\s+\d*\.?\s*(?:经验教训|Lessons.*?Learned)\s*\n(.*?)(?=\n##\s|\Z)"),
    ]

    for role, pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            section_text = match.group(1).strip()
            if section_text:
                sections.append({
                    "role": role,
                    "content": section_text,
                    "entities": _extract_entities(section_text),
                })

    # Fallback: if no structured sections found, treat entire content as finding
    if not sections:
        sections.append({
            "role": "finding",
            "content": content.strip(),
            "entities": _extract_entities(content),
        })

    return sections


def _extract_entities(text: str) -> List[Dict]:
    """Extract entity names from text (project/customer names)."""
    entities = []
    # Pattern: project names like "XX集团" or "YY科技有限公司"
    project_pattern = re.findall(r"((?:[A-Z]+|[A-Z][a-z]+)?[\u4e00-\u9fff]{2,}(?:集团|科技|公司|有限|技术|系统))", text)
    for name in set(project_pattern):
        entities.append({"name": name, "type": "project"})
    return entities


def scan_memory_directory(directory: str) -> List[str]:
    """Scan directory for all .md files.

    Args:
        directory: Path to scan for memory files.

    Returns:
        List of .md file paths.
    """
    md_files = []
    if not os.path.isdir(directory):
        return md_files

    for root, _, files in os.walk(directory):
        for f in sorted(files):
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))

    return md_files
