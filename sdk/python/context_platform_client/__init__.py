"""Context Platform Python SDK.

Provides a Python client for interacting with the Context Platform API.
"""
from .client import ContextPlatformClient
from .models import Context, Entity, Relation, SearchResult
from .events import EventHandler

__version__ = "1.0.0"
__all__ = ["ContextPlatformClient", "Context", "Entity", "Relation", "SearchResult", "EventHandler"]
