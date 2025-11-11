/**
 * Secret Manager Configuration
 *
 * Stores all sensitive environment variables securely.
 * Secrets are referenced by Cloud Run instead of being stored as env vars.
 */

# Define all secrets that need to be created
locals {
  secrets = {
    database-url = {
      value       = var.database_url
      description = "PostgreSQL database connection string"
    }
    supabase-url = {
      value       = var.supabase_url
      description = "Supabase project URL"
    }
    supabase-anon-key = {
      value       = var.supabase_anon_key
      description = "Supabase anonymous key"
    }
    supabase-service-key = {
      value       = var.supabase_service_key
      description = "Supabase service role key"
    }
    jwt-secret-key = {
      value       = var.jwt_secret_key
      description = "JWT secret key for authentication"
    }
    jwt-algorithm = {
      value       = var.jwt_algorithm
      description = "JWT signing algorithm"
    }
    cors-origins = {
      value       = var.cors_origins
      description = "Allowed CORS origins (JSON array)"
    }
    clip-model = {
      value       = var.clip_model
      description = "CLIP model version"
    }
    embedding-dimension = {
      value       = var.embedding_dimension
      description = "Embedding vector dimension"
    }
    environment = {
      value       = var.environment
      description = "Environment name"
    }
    hf-token = {
      value       = var.hf_token
      description = "Hugging Face API token for model downloads"
    }
  }
}

# Create secrets in Secret Manager
resource "google_secret_manager_secret" "app_secrets" {
  for_each = local.secrets

  secret_id = each.key
  labels = {
    app = var.service_name
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# Add secret versions with actual values
resource "google_secret_manager_secret_version" "app_secret_versions" {
  for_each = local.secrets

  secret      = google_secret_manager_secret.app_secrets[each.key].id
  secret_data = each.value.value
}
