/**
 * API request and response type definitions.
 * Based on backend/api/routers/* endpoint schemas.
 */

import { InteractionType, RecommendationContext, HealthStatus } from "./enums";
import { ProductResult, FilterParams } from "./product";

// Re-export product types for convenience
export type { ProductResult, FilterParams };

// ============================================================================
// SEARCH ENDPOINT: POST /api/v1/search
// ============================================================================

/**
 * Request body for product search.
 */
export interface SearchRequest {
  query: string; // Required, 1-500 characters
  user_id?: string; // Optional, for personalization (UUID)
  filters?: FilterParams;
  offset?: number; // Default: 0
  limit?: number; // Default: 20, max: 100
  use_ranking?: boolean; // Default: true
  enable_diversity?: boolean; // Default: true
}

/**
 * Response from product search.
 */
export interface SearchResponse {
  results: ProductResult[];
  total: number; // Total matching products
  offset: number;
  limit: number;
  page: number; // Current page (1-indexed)
  query: string; // Echo of search query
  user_id?: string;
  search_time_ms: number; // Time spent on vector search
  total_time_ms: number; // Total request time
  personalized: boolean; // Whether user personalization was applied
  cached: boolean; // Whether results came from cache
  filters_applied: boolean;
  ranking_applied: boolean;
}

// ============================================================================
// RECOMMEND ENDPOINT: POST /api/v1/recommend
// ============================================================================

/**
 * Request body for personalized recommendations.
 */
export interface RecommendRequest {
  user_id: string; // Required (UUID)
  context?: RecommendationContext; // Default: "feed"

  // Context-specific parameters (required based on context)
  product_id?: string; // Required if context="similar"
  category_id?: number; // Required if context="category"
  search_query?: string; // Required if context="search"

  // Filtering & pagination
  filters?: FilterParams;
  offset?: number; // Default: 0
  limit?: number; // Default: 20, max: 100

  // Personalization options
  use_session_context?: boolean; // Default: true, blend session + long-term
  enable_diversity?: boolean; // Default: true
  diversity_lambda?: number; // 0-1, default: 0.5
}

/**
 * Response from personalized recommendations.
 */
export interface RecommendResponse {
  results: ProductResult[];
  total: number;
  offset: number;
  limit: number;
  page: number;
  user_id: string;
  context: string; // Recommendation context used
  recommendation_time_ms: number;
  total_time_ms: number;
  personalized: boolean;
  cached: boolean;
  filters_applied: boolean;
  diversity_applied: boolean;

  // User context metadata
  has_long_term_profile: boolean;
  has_session_context: boolean;
  blend_weights?: {
    long_term?: number;
    session?: number;
    query?: number;
    product?: number;
  };
}

// ============================================================================
// FEEDBACK ENDPOINT: POST /api/v1/feedback
// ============================================================================

/**
 * Request body for user interaction feedback.
 */
export interface FeedbackRequest {
  user_id: string; // Required (UUID)
  product_id: string; // Required
  interaction_type: InteractionType; // Required

  // Optional metadata
  rating?: number; // 0-5, required if interaction_type="rating"
  session_id?: string; // Session identifier
  context?: string; // Where interaction happened (e.g., "search", "feed", "product_detail")
  query?: string; // Search query if from search results
  position?: number; // Position in results (for CTR analysis)
  metadata?: Record<string, any>; // Additional tracking data

  // Update preferences
  update_embeddings?: boolean; // Default: true
  update_session?: boolean; // Default: true
}

/**
 * Response from feedback submission.
 */
export interface FeedbackResponse {
  success: boolean;
  message: string;
  interaction_id?: number;
  user_id: string;
  product_id: string;
  interaction_type: string;
  embeddings_updated: boolean;
  session_updated: boolean;
  cache_invalidated: boolean;
  recorded_at: string; // ISO 8601 timestamp
  processing_time_ms: number;
}

// ============================================================================
// HEALTH & STATUS ENDPOINTS
// ============================================================================

/**
 * Response from GET /health endpoint.
 */
export interface HealthResponse {
  status: HealthStatus;
  timestamp: string; // ISO 8601 timestamp
}

/**
 * Component health status.
 */
export interface ComponentStatus {
  status: HealthStatus;
  latency_ms?: number;
  message?: string;
}

/**
 * Response from GET /status endpoint (detailed health check).
 */
export interface StatusResponse {
  status: HealthStatus;
  timestamp: string;
  version: string;
  components: {
    database: ComponentStatus;
    redis: ComponentStatus;
    faiss_index: ComponentStatus;
  };
  performance: {
    request_count: number;
    latency_p50_ms: number;
    latency_p95_ms: number;
    latency_p99_ms: number;
    target_p95_ms: number; // Performance target (e.g., 150ms)
    meets_target: boolean;
  };
  cache: {
    cached_products: number;
    cached_users: number;
    hot_products: number;
  };
}

/**
 * Response from GET /metrics endpoint.
 */
export interface MetricsResponse {
  requests: {
    total: number;
  };
  latency: {
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    mean_ms: number;
    min_ms: number;
    max_ms: number;
  };
  timestamp: string;
}

// ============================================================================
// COMMON TYPES
// ============================================================================

/**
 * Pagination parameters for list requests.
 */
export interface PaginationParams {
  offset?: number; // Default: 0
  limit?: number; // Default: 20
}

/**
 * Standard API error response.
 */
export interface ApiError {
  error: string;
  message: string;
  status_code: number;
  details?: Record<string, any>;
  timestamp?: string;
}

/**
 * Generic API response wrapper.
 */
export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
  meta?: {
    request_id?: string;
    timestamp: string;
  };
}

/**
 * Onboarding request (custom endpoint to be created).
 */
export interface OnboardingRequest {
  user_id: number;
  selected_product_ids: string[]; // 3-5 products from moodboard
}

/**
 * Onboarding response.
 */
export interface OnboardingResponse {
  success: boolean;
  user_id: number;
  user_embedding_created: boolean;
  selected_products: number;
  message: string;
}

// ============================================================================
// USER ENDPOINTS: /api/v1/users/*
// ============================================================================

/**
 * User preferences update request.
 */
export interface UserPreferencesUpdate {
  preferred_categories?: string[];
  price_band_min?: number;
  price_band_max?: number;
  style_preferences?: Record<string, any>;
  brand_affinities?: Record<string, number>;
}

/**
 * User statistics response.
 */
export interface UserStatsResponse {
  total_interactions: number;
  total_views: number;
  total_clicks: number;
  total_likes: number;
  total_cart_adds: number;
  total_purchases: number;
  favorite_categories: Array<{ category: string; count: number }>;
  favorite_brands: Array<{ brand: string; count: number }>;
  avg_price_point: number | null;
  account_age_days: number;
  last_active: string | null; // ISO 8601 timestamp
}

/**
 * Single interaction history item.
 */
export interface InteractionHistoryItem {
  interaction_id: number;
  product_id: string;
  product_title: string | null;
  product_image_url: string | null;
  product_price: number | null;
  interaction_type: string;
  created_at: string; // ISO 8601 timestamp
  context: string | null;
  query: string | null;
}

/**
 * Interaction history response.
 */
export interface InteractionHistoryResponse {
  interactions: InteractionHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}

/**
 * Favorite product with metadata.
 */
export interface FavoriteProduct {
  product_id: string;
  title: string;
  price: number;
  currency: string;
  image_url: string | null;
  brand: string | null;
  in_stock: boolean;
  liked_at: string; // ISO 8601 timestamp
}

/**
 * Favorites response.
 */
export interface FavoritesResponse {
  favorites: FavoriteProduct[];
  total: number;
}
