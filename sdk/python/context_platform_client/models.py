"""Data models for the Context Platform Python SDK."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Context:
    """Context item data model."""
    id: str
    context_id: str
    title: str
    content: str
    domain: str
    confidence_level: str
    confidence_score: float
    lifecycle_status: str
    created_by: str
    created_at: Optional[str] = None
    version: int = 1
    is_immutable: bool = False
    extra_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        return cls(
            id=data.get("id", ""),
            context_id=data.get("context_id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            domain=data.get("domain", ""),
            confidence_level=data.get("confidence_level", "L2"),
            confidence_score=data.get("confidence_score", 0.5),
            lifecycle_status=data.get("lifecycle_status", "pending_review"),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at"),
            version=data.get("version", 1),
            is_immutable=data.get("is_immutable", False),
            extra_data=data.get("extra_data", {}),
        )


@dataclass
class Entity:
    """Entity data model."""
    id: str
    name: str
    type: str
    domain: Optional[str] = None
    aliases: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            domain=data.get("domain"),
            aliases=data.get("aliases", []),
        )


@dataclass
class Relation:
    """Relation data model."""
    id: str
    source_id: str
    target_id: str
    type: str
    direction: str = "forward"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        return cls(
            id=data.get("id", ""),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            type=data.get("type", ""),
            direction=data.get("direction", "forward"),
        )


@dataclass
class SearchResult:
    """Search result item."""
    context_id: str
    title: str
    content: str
    score: float = 0.0
    domain: Optional[str] = None
    confidence_level: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        return cls(
            context_id=data.get("context_id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            domain=data.get("domain"),
            confidence_level=data.get("confidence_level"),
        )
