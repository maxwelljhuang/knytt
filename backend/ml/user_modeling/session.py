"""
Session Embedding Tracker
Tracks short-term user intent within a session.
"""

import logging
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import deque

from ..config import get_ml_config

logger = logging.getLogger(__name__)


class SessionEmbedding:
    """
    Tracks user's current session intent.

    Uses rolling average of last N interactions:
    session_embedding = mean(last_N_interactions)

    Represents what user is looking for RIGHT NOW,
    separate from their long-term taste profile.
    """

    def __init__(self, window_size: Optional[int] = None):
        """
        Initialize session embedding tracker.

        Args:
            window_size: Number of recent interactions to track
        """
        self.config = get_ml_config()
        self.window_size = window_size or self.config.user_modeling.session_window_size

        # Interaction history (fixed-size queue)
        self.interactions = deque(maxlen=self.window_size)
        self.last_activity = None

    def add_interaction(
        self,
        product_embedding: np.ndarray,
        interaction_type: str = "view",
        timestamp: Optional[datetime] = None,
    ):
        """
        Add an interaction to the session.

        Args:
            product_embedding: Embedding of interacted product
            interaction_type: Type of interaction
            timestamp: When it happened (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.interactions.append(
            {
                "embedding": product_embedding,
                "type": interaction_type,
                "timestamp": timestamp,
            }
        )

        self.last_activity = timestamp

    def get_session_embedding(self) -> Optional[np.ndarray]:
        """
        Compute current session embedding.

        Returns:
            Session embedding (mean of recent interactions) or None if no interactions
        """
        if not self.interactions:
            return None

        # Get all embeddings
        embeddings = [interaction["embedding"] for interaction in self.interactions]

        # Compute rolling average
        session_emb = np.mean(embeddings, axis=0)

        # Normalize
        if self.config.embedding.normalize_embeddings:
            session_emb = session_emb / np.linalg.norm(session_emb)

        return session_emb

    def is_active(self, timeout_minutes: Optional[int] = None) -> bool:
        """
        Check if session is still active.

        Args:
            timeout_minutes: Session timeout (default: from config)

        Returns:
            True if session is active
        """
        if self.last_activity is None:
            return False

        if timeout_minutes is None:
            timeout_minutes = self.config.user_modeling.session_timeout_minutes

        timeout = timedelta(minutes=timeout_minutes)
        elapsed = datetime.now() - self.last_activity

        return elapsed < timeout

    def clear(self):
        """Clear session history."""
        self.interactions.clear()
        self.last_activity = None

    def get_interaction_count(self) -> int:
        """Get number of interactions in session."""
        return len(self.interactions)

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        if not self.interactions:
            return {
                "interaction_count": 0,
                "is_active": False,
                "has_embedding": False,
            }

        # Count interaction types
        type_counts = {}
        for interaction in self.interactions:
            itype = interaction["type"]
            type_counts[itype] = type_counts.get(itype, 0) + 1

        return {
            "interaction_count": len(self.interactions),
            "is_active": self.is_active(),
            "has_embedding": True,
            "last_activity": self.last_activity,
            "interaction_types": type_counts,
            "window_size": self.window_size,
        }


class SessionManager:
    """
    Manages sessions for multiple users.

    Stores session embeddings in memory (Redis in production).
    """

    def __init__(self):
        """Initialize session manager."""
        self.config = get_ml_config()
        self.sessions = {}  # user_id -> SessionEmbedding

    def get_session(self, user_id: str) -> SessionEmbedding:
        """
        Get or create session for user.

        Args:
            user_id: User ID

        Returns:
            SessionEmbedding for this user
        """
        if user_id not in self.sessions:
            self.sessions[user_id] = SessionEmbedding()
        elif not self.sessions[user_id].is_active():
            # Session timed out, create new one
            logger.info(f"Session timed out for user {user_id}, creating new session")
            self.sessions[user_id] = SessionEmbedding()

        return self.sessions[user_id]

    def add_interaction(
        self, user_id: str, product_embedding: np.ndarray, interaction_type: str = "view"
    ):
        """
        Add interaction to user's session.

        Args:
            user_id: User ID
            product_embedding: Product embedding
            interaction_type: Interaction type
        """
        session = self.get_session(user_id)
        session.add_interaction(product_embedding, interaction_type)

    def get_session_embedding(self, user_id: str) -> Optional[np.ndarray]:
        """
        Get session embedding for user.

        Args:
            user_id: User ID

        Returns:
            Session embedding or None
        """
        session = self.get_session(user_id)
        return session.get_session_embedding()

    def clear_session(self, user_id: str):
        """Clear session for user."""
        if user_id in self.sessions:
            self.sessions[user_id].clear()

    def cleanup_inactive_sessions(self):
        """Remove inactive sessions to free memory."""
        inactive_users = [
            user_id for user_id, session in self.sessions.items() if not session.is_active()
        ]

        for user_id in inactive_users:
            del self.sessions[user_id]

        if inactive_users:
            logger.info(f"Cleaned up {len(inactive_users)} inactive sessions")

    def get_active_session_count(self) -> int:
        """Get number of active sessions."""
        return sum(1 for session in self.sessions.values() if session.is_active())


# Global session manager
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
