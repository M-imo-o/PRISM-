"""Deciders sub-package: segmenters, routers, and card writers."""
from .fakes import FakeCardWriter, KeywordRouter, KeywordSegmenter
from .interfaces import CardWriter, Router, SegmentDecision, Segmenter
from .laya_decider import (
    LayaRouter,
    LayaSegmenter,
    format_topic_card,
    get_shared_router,
    reset_shared_router,
)
from .llm import GeminiCardWriter, LLMCardWriter, TopicCardOutput
from .rag import (
    ChunkResult,
    GoogleProvider,
    L4Config,
    L4Error,
    LocalRAG,
    ProviderError,
    RetrievalError,
    SourceDocumentError,
)

__all__ = [
    "SegmentDecision",
    "Segmenter",
    "Router",
    "CardWriter",
    "LayaSegmenter",
    "LayaRouter",
    "format_topic_card",
    "get_shared_router",
    "reset_shared_router",
    "LLMCardWriter",
    "GeminiCardWriter",
    "TopicCardOutput",
    "KeywordSegmenter",
    "KeywordRouter",
    "FakeCardWriter",
    "ChunkResult",
    "GoogleProvider",
    "L4Config",
    "L4Error",
    "LocalRAG",
    "ProviderError",
    "RetrievalError",
    "SourceDocumentError",
]
