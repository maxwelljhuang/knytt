-- Initial Schema Migration for Knytt
-- E-commerce product discovery platform with ML embeddings

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text matching
CREATE EXTENSION IF NOT EXISTS "vector";   -- For pgvector

-- =====================================================
-- PRODUCTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Basic product info
    title TEXT NOT NULL,
    description TEXT,
    brand TEXT,
    category TEXT,
    subcategory TEXT,

    -- Pricing
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',

    -- Availability
    in_stock BOOLEAN DEFAULT true,
    stock_quantity INTEGER,

    -- Media
    image_url TEXT,
    additional_images TEXT[],

    -- External links
    product_url TEXT,
    source_platform TEXT,  -- e.g., 'shopify', 'etsy', etc.
    external_id TEXT,

    -- Quality metrics
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),
    is_duplicate BOOLEAN DEFAULT false,
    duplicate_of UUID REFERENCES products(id),

    -- ML embeddings
    embedding vector(512),  -- CLIP embeddings (512 dimensions)

    -- Metadata
    tags TEXT[],
    color TEXT,
    size TEXT,
    material TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_ingestion_date TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT positive_price CHECK (price >= 0),
    CONSTRAINT positive_stock CHECK (stock_quantity >= 0)
);

-- Indexes for products
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_in_stock ON products(in_stock);
CREATE INDEX IF NOT EXISTS idx_products_quality ON products(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_products_title_trgm ON products USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_tags ON products USING gin (tags);

-- Vector similarity index (IVFFlat for large datasets)
-- Adjust lists parameter based on number of products (sqrt of total products is a good heuristic)
CREATE INDEX IF NOT EXISTS idx_products_embedding ON products
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =====================================================
-- USERS TABLE (extends auth.users)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Profile info
    username TEXT UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    bio TEXT,

    -- Preferences
    preferred_categories TEXT[],
    price_range_min DECIMAL(10,2),
    price_range_max DECIMAL(10,2),

    -- Privacy settings
    is_public BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- USER EMBEDDINGS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS user_embeddings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Long-term taste profile (EWMA of interactions)
    long_term_embedding vector(512),
    long_term_weight FLOAT DEFAULT 0.0,
    long_term_updated_at TIMESTAMPTZ,

    -- Short-term session intent (rolling average)
    session_embedding vector(512),
    session_weight FLOAT DEFAULT 0.0,
    session_started_at TIMESTAMPTZ,
    session_updated_at TIMESTAMPTZ,

    -- Metadata
    total_interactions INTEGER DEFAULT 0,
    last_active_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for active users
CREATE INDEX IF NOT EXISTS idx_user_embeddings_last_active ON user_embeddings(last_active_at DESC);

-- =====================================================
-- USER INTERACTIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Interaction types
    interaction_type VARCHAR(50) NOT NULL, -- 'view', 'click', 'like', 'favorite', 'purchase', 'share'

    -- Context
    context VARCHAR(50), -- 'feed', 'search', 'similar', 'category'
    search_query TEXT,
    session_id UUID,

    -- Engagement metrics
    duration_seconds INTEGER, -- Time spent viewing
    scroll_depth FLOAT, -- How far they scrolled

    -- Implicit feedback
    implicit_rating FLOAT CHECK (implicit_rating >= 0 AND implicit_rating <= 1),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for interactions
CREATE INDEX IF NOT EXISTS idx_interactions_user ON user_interactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_product ON user_interactions(product_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_session ON user_interactions(session_id);

-- =====================================================
-- USER FAVORITES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS user_favorites (
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_favorites(user_id, created_at DESC);

-- =====================================================
-- INGESTION LOGS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ingestion metadata
    file_name TEXT NOT NULL,
    file_size_bytes BIGINT,
    source_url TEXT,

    -- Processing stats
    total_rows INTEGER,
    valid_rows INTEGER,
    invalid_rows INTEGER,
    duplicate_rows INTEGER,
    processed_rows INTEGER,

    -- Status
    status VARCHAR(50) NOT NULL, -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,

    -- Performance metrics
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_logs_status ON ingestion_logs(status, created_at DESC);

-- =====================================================
-- SEARCH QUERIES TABLE (for analytics)
-- =====================================================
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Query details
    query_text TEXT NOT NULL,
    filters JSONB, -- Store filter parameters as JSON

    -- Results
    results_count INTEGER,
    results_clicked INTEGER DEFAULT 0,

    -- Performance
    response_time_ms INTEGER,

    -- Context
    session_id UUID,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_queries_user ON search_queries(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_queries_text ON search_queries USING gin (to_tsvector('english', query_text));
CREATE INDEX IF NOT EXISTS idx_search_queries_created_at ON search_queries(created_at DESC);

-- =====================================================
-- UPDATED_AT TRIGGER FUNCTION
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at
-- Drop existing triggers first to make migration idempotent
DROP TRIGGER IF EXISTS update_products_updated_at ON products;
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_embeddings_updated_at ON user_embeddings;
CREATE TRIGGER update_user_embeddings_updated_at BEFORE UPDATE ON user_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;

-- Products are public (read-only for users)
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Products are viewable by everyone" ON products;
CREATE POLICY "Products are viewable by everyone" ON products
    FOR SELECT USING (true);

-- User profiles
DROP POLICY IF EXISTS "Users can view public profiles" ON user_profiles;
CREATE POLICY "Users can view public profiles" ON user_profiles
    FOR SELECT USING (is_public = true OR auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- User embeddings (private)
DROP POLICY IF EXISTS "Users can view own embeddings" ON user_embeddings;
CREATE POLICY "Users can view own embeddings" ON user_embeddings
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own embeddings" ON user_embeddings;
CREATE POLICY "Users can update own embeddings" ON user_embeddings
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own embeddings" ON user_embeddings;
CREATE POLICY "Users can insert own embeddings" ON user_embeddings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- User interactions
DROP POLICY IF EXISTS "Users can view own interactions" ON user_interactions;
CREATE POLICY "Users can view own interactions" ON user_interactions
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own interactions" ON user_interactions;
CREATE POLICY "Users can insert own interactions" ON user_interactions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- User favorites
DROP POLICY IF EXISTS "Users can view own favorites" ON user_favorites;
CREATE POLICY "Users can view own favorites" ON user_favorites
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage own favorites" ON user_favorites;
CREATE POLICY "Users can manage own favorites" ON user_favorites
    FOR ALL USING (auth.uid() = user_id);

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================
COMMENT ON TABLE products IS 'Product catalog with ML embeddings for semantic search';
COMMENT ON TABLE user_profiles IS 'Extended user profile information';
COMMENT ON TABLE user_embeddings IS 'User taste profiles as embeddings (long-term + session)';
COMMENT ON TABLE user_interactions IS 'Track all user interactions with products';
COMMENT ON TABLE user_favorites IS 'User favorite/saved products';
COMMENT ON TABLE ingestion_logs IS 'CSV ingestion tracking and monitoring';
COMMENT ON TABLE search_queries IS 'Search analytics and query logging';
