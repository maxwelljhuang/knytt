"""
User Modeling Package
User embedding generation and management.
"""

from .cold_start import (
    ColdStartEmbedding,
    get_cold_start_generator,
    create_user_from_quiz,
)

from .warm_user import (
    WarmUserEmbedding,
    get_warm_user_updater,
    update_user_from_interaction,
)

from .session import (
    SessionEmbedding,
    SessionManager,
    get_session_manager,
)

from .blending import (
    UserEmbeddingBlender,
    get_user_blender,
    blend_user_embeddings,
)

from .embedding_builder import (
    UserEmbeddingBuilder,
    get_embedding_builder,
)

__all__ = [
    # Cold start
    "ColdStartEmbedding",
    "get_cold_start_generator",
    "create_user_from_quiz",
    # Warm user
    "WarmUserEmbedding",
    "get_warm_user_updater",
    "update_user_from_interaction",
    # Session
    "SessionEmbedding",
    "SessionManager",
    "get_session_manager",
    # Blending
    "UserEmbeddingBlender",
    "get_user_blender",
    "blend_user_embeddings",
    # Embedding builder
    "UserEmbeddingBuilder",
    "get_embedding_builder",
]
