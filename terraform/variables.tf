/**
 * Terraform Variables
 *
 * Define all input variables for the infrastructure.
 * Set actual values in terraform.tfvars (not committed to git).
 */

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "knytt-backend"
}

variable "repository_id" {
  description = "Artifact Registry repository ID"
  type        = string
  default     = "knytt-backend"
}

variable "github_repo" {
  description = "GitHub repository in format 'owner/repo'"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to trigger deployments"
  type        = string
  default     = "main"
}

# Environment variables for the application
# These will be stored in Secret Manager

variable "database_url" {
  description = "PostgreSQL database connection string"
  type        = string
  sensitive   = true
}

variable "supabase_url" {
  description = "Supabase project URL"
  type        = string
}

variable "supabase_anon_key" {
  description = "Supabase anonymous key"
  type        = string
  sensitive   = true
}

variable "supabase_service_key" {
  description = "Supabase service role key"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key for authentication"
  type        = string
  sensitive   = true
}

variable "jwt_algorithm" {
  description = "JWT algorithm"
  type        = string
  default     = "HS256"
}

variable "cors_origins" {
  description = "List of allowed CORS origins (as JSON array string)"
  type        = string
}

variable "clip_model" {
  description = "CLIP model version"
  type        = string
  default     = "ViT-B/32"
}

variable "embedding_dimension" {
  description = "Embedding dimension"
  type        = string
  default     = "512"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  type        = string
  default     = "production"
}

variable "hf_token" {
  description = "Hugging Face API token for downloading models"
  type        = string
  sensitive   = true
}
