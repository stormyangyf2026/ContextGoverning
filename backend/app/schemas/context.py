"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ---- Context ----

class ContextCreate(BaseModel):
    title: str = Field(..., max_length=512)
    content: str
    context_id: Optional[str] = None
    domain: str = "operations"
    source_system: Optional[str] = None
    confidence_source_type: Optional[str] = None
    context_subtype: Optional[str] = None
    context_role: Optional[str] = None
    structured_fields: Optional[dict] = None
    tags: Optional[List[str]] = None
    entities: Optional[List[dict]] = None


class ContextUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=512)
    content: Optional[str] = None
    domain: Optional[str] = None
    sub_category: Optional[str] = None
    tags: Optional[List[str]] = None


class ContextResponse(BaseModel):
    id: str
    context_id: str
    title: str
    content: str
    domain: str
    sub_category: Optional[str] = None
    tags: List[str] = []
    confidence_level: str
    confidence_score: float
    confidence_source_type: Optional[str] = None
    context_subtype: Optional[str] = None
    context_role: Optional[str] = None
    structured_fields: Optional[dict] = None
    lifecycle_status: str
    version: int
    is_immutable: bool
    source_system: Optional[str] = None
    source_platform: Optional[str] = None
    created_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContextListResponse(BaseModel):
    items: List[ContextResponse]
    total: int
    page: int
    page_size: int


# ---- Entity ----

class EntityCreate(BaseModel):
    name: str = Field(..., max_length=256)
    type: str = Field(..., max_length=32)
    domain: Optional[str] = None
    aliases: List[str] = []
    metadata: dict = {}


class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    domain: Optional[str] = None
    aliases: List[str] = []
    metadata: dict = {}
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Relation ----

class RelationCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    direction: str = "forward"
    metadata: dict = {}


class RelationResponse(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: str
    direction: str
    created_by: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- User ----

class UserCreate(BaseModel):
    username: str = Field(..., max_length=128)
    email: str = Field(..., max_length=256)
    display_name: Optional[str] = None
    password: str = Field(..., min_length=8)
    role: str = "consultant"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Search ----

class SearchRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # keyword/semantic/graph/hybrid
    domain: Optional[str] = None
    confidence_level: Optional[str] = None
    limit: int = 20
    offset: int = 0


class SearchResult(BaseModel):
    context: ContextResponse
    score: float
    mode: str


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    mode: str


# ---- Auth ----

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str


# ---- Config ----

class ConfigUpdateRequest(BaseModel):
    section: str
    key: str
    value: object
    reason: str = ""
