"""
Feedback Module
Handles user interaction events and updates embeddings in real-time.
"""

from .feedback_handler import (
    FeedbackHandler,
    InteractionEvent,
    InteractionType,
    FeedbackProcessor,
)

__all__ = [
    "FeedbackHandler",
    "InteractionEvent",
    "InteractionType",
    "FeedbackProcessor",
]
