"""
SQLAlchemy ORM Models
Database table definitions using SQLAlchemy ORM.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, TIMESTAMP,
    ForeignKey, Numeric, Text, Index, text
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    # Fallback for type hints
    Vector = ARRAY

Base = declarative_base()


class User(Base):
    """
    User model.

    Stores user information and preferences.
    """
    __tablename__ = 'users'

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    external_id = Column(String(255), unique=True, index=True, nullable=True,
                        comment='External user ID from client system')
    email = Column(String(255), unique=True, index=True, nullable=False,
                  comment='User email address (required for authentication)')

    # Authentication fields
    password_hash = Column(String(255), nullable=False,
                          comment='Bcrypt hashed password')
    is_active = Column(Boolean, nullable=False, server_default='true',
                      comment='Whether user account is active')
    email_verified = Column(Boolean, nullable=False, server_default='false',
                           comment='Whether email has been verified')
    last_login = Column(TIMESTAMP, nullable=True,
                       comment='Timestamp of last successful login')
    onboarded = Column(Boolean, nullable=False, server_default='false',
                      comment='Whether user has completed onboarding')

    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    last_active = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # Preferences (JSONB for flexible schema)
    brand_affinities = Column(JSONB, nullable=False, server_default='{}',
                             comment='Brand preferences: {brand_id: affinity_score}')
    price_band_min = Column(Numeric(10, 2), nullable=True)
    price_band_max = Column(Numeric(10, 2), nullable=True)
    preferred_categories = Column(JSONB, nullable=False, server_default='[]',
                                 comment='List of preferred category IDs')
    style_preferences = Column(JSONB, nullable=False, server_default='{}',
                              comment='Style tags and preferences')

    # Stats
    total_interactions = Column(Integer, nullable=False, server_default='0',
                               comment='Total number of user interactions')

    # Relationships
    embeddings = relationship("UserEmbedding", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship("UserInteraction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, external_id={self.external_id})>"


class UserEmbedding(Base):
    """
    User embedding model.

    Stores user taste profile embeddings for personalized recommendations.
    Supports both long-term (persistent taste) and session (current intent) embeddings.
    """
    __tablename__ = 'user_embeddings'

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Embedding type (for backward compatibility, though we now have dedicated columns)
    embedding_type = Column(String(50), nullable=False, index=True,
                           comment='Type: long_term, session, cold_start, etc.')

    # Legacy embedding column (ARRAY format for backward compatibility)
    embedding = Column(ARRAY(Float, dimensions=1), nullable=True,
                      comment='Legacy embedding array (deprecated, use specific columns)')

    # pgvector embeddings (512-dimensional for CLIP ViT-B-32)
    long_term_embedding = Column(Vector(512) if PGVECTOR_AVAILABLE else ARRAY(Float), nullable=True,
                                comment='Long-term user taste profile (EWMA of interactions)')
    session_embedding = Column(Vector(512) if PGVECTOR_AVAILABLE else ARRAY(Float), nullable=True,
                              comment='Current session intent (rolling average)')

    # Metadata
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    last_interaction_at = Column(TIMESTAMP, nullable=True,
                                comment='Timestamp of last user interaction')

    # Stats
    interaction_count = Column(Integer, nullable=False, server_default='0',
                              comment='Number of interactions used to build this embedding')
    confidence_score = Column(Float, nullable=False, server_default='0.5',
                            comment='Confidence in embedding quality (0-1)')

    # Relationships
    user = relationship("User", back_populates="embeddings")

    # Unique constraint: one embedding per user per type
    __table_args__ = (
        Index('idx_user_embeddings_user_type', 'user_id', 'embedding_type', unique=True),
    )

    def __repr__(self):
        return f"<UserEmbedding(id={self.id}, user_id={self.user_id}, type={self.embedding_type})>"


class UserInteraction(Base):
    """
    User interaction model.

    Stores all user-product interactions for:
    - Building user embeddings
    - Analytics and metrics
    - Personalization feedback loop
    """
    __tablename__ = 'user_interactions'

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))

    # User and product
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'),
                    nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'),
                       nullable=False, index=True)

    # Interaction details
    interaction_type = Column(String(50), nullable=False, index=True,
                             comment='Type: view, click, add_to_cart, purchase, like, share, rating')
    rating = Column(Float, nullable=True, comment='Rating value (0-5) for rating interactions')

    # Session and context
    session_id = Column(String(128), nullable=True, index=True,
                       comment='Session ID for grouping interactions')
    context = Column(String(64), nullable=True, index=True,
                    comment='Context: search, feed, similar, recommendation, etc.')
    query = Column(String(500), nullable=True,
                  comment='Search query that led to this interaction')
    position = Column(Integer, nullable=True,
                     comment='Position of product in results (for CTR analysis)')

    # Additional metadata (using interaction_metadata to avoid SQLAlchemy reserved name)
    interaction_metadata = Column('metadata', JSONB, nullable=True, server_default='{}',
                                 comment='Additional metadata: page, referrer, device, etc.')

    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)

    # Processing flags
    processed_for_embedding = Column(Boolean, nullable=False, server_default='false',
                                    comment='Whether this interaction was used to update embeddings')
    processed_at = Column(TIMESTAMP, nullable=True,
                         comment='When this interaction was processed for embeddings')

    # Relationships
    user = relationship("User", back_populates="interactions")
    product = relationship("Product", back_populates="interactions")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_interactions_user_created', 'user_id', 'created_at'),
        Index('idx_user_interactions_session', 'session_id', 'created_at'),
        Index('idx_user_interactions_type_created', 'interaction_type', 'created_at'),
        Index('idx_user_interactions_unprocessed', 'processed_for_embedding',
              postgresql_where=text('processed_for_embedding = false')),
    )

    def __repr__(self):
        return f"<UserInteraction(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, type={self.interaction_type})>"


class Product(Base):
    """
    Product model.

    Stores product catalog information.
    """
    __tablename__ = 'products'

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))

    # Merchant identifiers
    merchant_product_id = Column(String(255), nullable=False)
    merchant_id = Column(Integer, nullable=False, index=True)
    merchant_name = Column(String(255), nullable=True)
    aw_product_id = Column(String(255), nullable=True)

    # Core product info
    product_name = Column(Text, nullable=False)
    brand_name = Column(String(255), nullable=True, index=True)
    brand_id = Column(Integer, nullable=True, index=True)
    description = Column(Text, nullable=True)
    product_short_description = Column(Text, nullable=True)

    # Categories
    category_name = Column(String(255), nullable=True)
    category_id = Column(Integer, nullable=True, index=True)
    merchant_category = Column(String(255), nullable=True)

    # Pricing
    search_price = Column(Numeric(10, 2), nullable=True, index=True)
    store_price = Column(Numeric(10, 2), nullable=True)
    rrp_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), nullable=False, server_default='GBP')
    delivery_cost = Column(Numeric(10, 2), nullable=True)

    # Images
    merchant_image_url = Column(Text, nullable=True)
    aw_image_url = Column(Text, nullable=True)
    large_image = Column(Text, nullable=True)
    alternate_images = Column(JSONB, nullable=False, server_default='[]')

    # Fashion attributes
    fashion_suitable_for = Column(String(100), nullable=True)
    fashion_category = Column(String(100), nullable=True)
    fashion_size = Column(Text, nullable=True)
    fashion_material = Column(Text, nullable=True)
    fashion_pattern = Column(String(100), nullable=True)
    colour = Column(String(100), nullable=True)

    # Stock
    in_stock = Column(Boolean, nullable=False, server_default='true')
    stock_quantity = Column(Integer, nullable=True)
    stock_status = Column(String(50), nullable=True)

    # Links
    aw_deep_link = Column(Text, nullable=True)
    merchant_deep_link = Column(Text, nullable=True)

    # Embeddings (denormalized for performance)
    image_embedding = Column(Vector(512) if PGVECTOR_AVAILABLE else ARRAY(Float), nullable=True,
                            comment='CLIP image embedding (512-dim)')
    text_embedding = Column(Vector(512) if PGVECTOR_AVAILABLE else ARRAY(Float), nullable=True,
                           comment='CLIP text embedding (512-dim)')
    embedding = Column(Vector(512) if PGVECTOR_AVAILABLE else ARRAY(Float), nullable=True,
                      comment='Fused multimodal embedding (512-dim)')
    embedding_model_version = Column(String(50), nullable=True)
    embedding_generated_at = Column(TIMESTAMP, nullable=True)

    # Metadata
    last_updated = Column(TIMESTAMP, nullable=True)
    ingested_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Quality
    is_active = Column(Boolean, nullable=False, server_default='true', index=True)
    is_nsfw = Column(Boolean, nullable=False, server_default='false')
    quality_score = Column(Float, nullable=False, server_default='0.0')

    # Deduplication
    product_hash = Column(String(64), nullable=True, index=True)
    canonical_product_id = Column(PGUUID(as_uuid=True), ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    is_duplicate = Column(Boolean, nullable=False, server_default='false')

    # Relationships
    interactions = relationship("UserInteraction", back_populates="product", cascade="all, delete-orphan")
    embeddings_rel = relationship("ProductEmbedding", back_populates="product", cascade="all, delete-orphan")

    # Unique constraint
    __table_args__ = (
        Index('idx_products_merchant_unique', 'merchant_id', 'merchant_product_id', unique=True),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.product_name[:30]})>"


class ProductEmbedding(Base):
    """
    Product embedding model (normalized table).

    Stores product embeddings separately for:
    - Version control
    - Multiple embedding types
    - Historical tracking
    """
    __tablename__ = 'product_embeddings'

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    product_id = Column(PGUUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'),
                       nullable=False)

    # Embedding type
    embedding_type = Column(String(50), nullable=False, index=True,
                           comment='Type: text, image, multimodal')

    # Legacy embedding (ARRAY format)
    embedding = Column(ARRAY(Float, dimensions=1), nullable=True,
                      comment='Legacy embedding array')

    # pgvector embedding
    embedding_vector = Column(Vector(512) if PGVECTOR_AVAILABLE else ARRAY(Float), nullable=True,
                             comment='pgvector embedding (512-dim)')

    # Metadata
    model_version = Column(String(50), nullable=False, server_default='ViT-B/32')
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="embeddings_rel")

    # Unique constraint
    __table_args__ = (
        Index('idx_product_embeddings_product_type', 'product_id', 'embedding_type', unique=True),
    )

    def __repr__(self):
        return f"<ProductEmbedding(id={self.id}, product_id={self.product_id}, type={self.embedding_type})>"


class TaskExecution(Base):
    """
    Task execution tracking model.

    Tracks Celery task executions for monitoring and auditing.
    Stores task metadata, progress, results, and errors.
    """
    __tablename__ = 'task_executions'

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    task_id = Column(String(255), unique=True, index=True, nullable=False,
                    comment='Celery task ID (UUID)')
    task_name = Column(String(255), nullable=False, index=True,
                      comment='Task function name (e.g., tasks.generate_product_embeddings)')
    task_type = Column(String(100), nullable=False, index=True,
                      comment='Task category: embedding, ingestion, maintenance')

    # Status tracking
    status = Column(String(50), nullable=False, index=True, server_default='PENDING',
                   comment='Task status: PENDING, STARTED, PROGRESS, SUCCESS, FAILURE, REVOKED, RETRY')
    progress_percent = Column(Integer, nullable=True,
                             comment='Task progress percentage (0-100)')
    progress_current = Column(Integer, nullable=True,
                             comment='Current item being processed')
    progress_total = Column(Integer, nullable=True,
                           comment='Total items to process')
    progress_message = Column(Text, nullable=True,
                             comment='Human-readable progress message')

    # Task metadata
    args = Column(JSONB, nullable=True,
                 comment='Task positional arguments')
    kwargs = Column(JSONB, nullable=True,
                   comment='Task keyword arguments')
    task_metadata = Column(JSONB, nullable=True,
                     comment='Additional task metadata')

    # Execution details
    worker_name = Column(String(255), nullable=True,
                        comment='Celery worker that executed the task')
    queue_name = Column(String(100), nullable=True,
                       comment='Queue the task was sent to')
    retries = Column(Integer, nullable=False, server_default='0',
                    comment='Number of retry attempts')
    max_retries = Column(Integer, nullable=True,
                        comment='Maximum number of retries allowed')

    # Timing
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(),
                       comment='When task was created/dispatched')
    started_at = Column(TIMESTAMP, nullable=True,
                       comment='When task started executing')
    completed_at = Column(TIMESTAMP, nullable=True,
                         comment='When task finished (success or failure)')

    # Results and errors
    result = Column(JSONB, nullable=True,
                   comment='Task result data')
    error = Column(Text, nullable=True,
                  comment='Error message if task failed')
    traceback = Column(Text, nullable=True,
                      comment='Full error traceback')

    # User association (optional, for user-triggered tasks)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'),
                    nullable=True, index=True,
                    comment='User who triggered the task (if applicable)')

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # Indexes for common queries
    __table_args__ = (
        Index('idx_task_executions_status_created', 'status', 'created_at'),
        Index('idx_task_executions_type_status', 'task_type', 'status'),
        Index('idx_task_executions_name_created', 'task_name', 'created_at'),
    )

    def __repr__(self):
        return f"<TaskExecution(id={self.id}, task_id={self.task_id}, status={self.status})>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_finished(self) -> bool:
        """Check if task has finished (success, failure, or revoked)."""
        return self.status in ('SUCCESS', 'FAILURE', 'REVOKED')

    @property
    def is_active(self) -> bool:
        """Check if task is currently active (started or in progress)."""
        return self.status in ('STARTED', 'PROGRESS')
