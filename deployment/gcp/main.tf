# Terraform Configuration for Knytt on GCP + Supabase
# Creates Cloud Run services for FastAPI backend and Celery workers

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # GCS backend for state - enables state persistence across CI/CD runs
  backend "gcs" {
    bucket = "knytt-backend-terraform-state"
    prefix = "prod/terraform/state"
  }
}

# =====================================================
# VARIABLES
# =====================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "supabase_url" {
  description = "Supabase Project URL"
  type        = string
  sensitive   = true
}

variable "supabase_service_key" {
  description = "Supabase Service Role Key"
  type        = string
  sensitive   = true
}

variable "supabase_anon_key" {
  description = "Supabase Anonymous Key"
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "PostgreSQL Database URL"
  type        = string
  sensitive   = true
}

variable "api_image" {
  description = "Docker image for FastAPI service"
  type        = string
  default     = "gcr.io/PROJECT_ID/knytt-api:latest"
}

variable "worker_image" {
  description = "Docker image for Celery worker"
  type        = string
  default     = "gcr.io/PROJECT_ID/knytt-worker:latest"
}

variable "redis_host" {
  description = "Redis host for Celery (Memorystore)"
  type        = string
  default     = ""
}

variable "redis_port" {
  description = "Redis port"
  type        = string
  default     = "6379"
}

# =====================================================
# PROVIDER CONFIGURATION
# =====================================================

provider "google" {
  project = var.project_id
  region  = var.region
}

# =====================================================
# ARTIFACT REGISTRY
# =====================================================
# Note: Artifact Registry repository is created manually before Terraform runs
# This is because the Docker build job needs to push images before Terraform deploys Cloud Run
# Repository name: knytt-${var.environment}
# Location: ${var.region}

# =====================================================
# MEMORYSTORE REDIS (for Celery broker)
# =====================================================

resource "google_redis_instance" "cache" {
  name           = "knytt-redis-${var.environment}"
  tier           = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.environment == "prod" ? 5 : 1
  region         = var.region

  redis_version     = "REDIS_7_0"
  display_name      = "Knytt Redis Cache"
  reserved_ip_range = "10.0.0.0/29"

  # Enable AUTH
  auth_enabled = true

  labels = {
    environment = var.environment
    application = "knytt"
  }
}

# =====================================================
# CLOUD STORAGE BUCKET (for FAISS indices)
# =====================================================

resource "google_storage_bucket" "ml_artifacts" {
  name          = "${var.project_id}-knytt-ml-${var.environment}"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = {
    environment = var.environment
    application = "knytt"
  }
}

# =====================================================
# SECRET MANAGER (for sensitive env vars)
# =====================================================

resource "google_secret_manager_secret" "supabase_url" {
  secret_id = "supabase-url-${var.environment}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "supabase_url" {
  secret = google_secret_manager_secret.supabase_url.id
  secret_data = var.supabase_url
}

resource "google_secret_manager_secret" "supabase_service_key" {
  secret_id = "supabase-service-key-${var.environment}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "supabase_service_key" {
  secret = google_secret_manager_secret.supabase_service_key.id
  secret_data = var.supabase_service_key
}

resource "google_secret_manager_secret" "redis_auth" {
  secret_id = "redis-auth-${var.environment}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_auth" {
  secret = google_secret_manager_secret.redis_auth.id
  secret_data = google_redis_instance.cache.auth_string
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url-${var.environment}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

# =====================================================
# SERVICE ACCOUNT (for Cloud Run services)
# =====================================================

resource "google_service_account" "cloud_run_sa" {
  account_id   = "knytt-cloud-run-${var.environment}"
  display_name = "Knytt Cloud Run Service Account"
  description  = "Service account for Knytt Cloud Run services"
}

# Grant permissions to access secrets
resource "google_secret_manager_secret_iam_member" "cloud_run_secrets" {
  for_each = tomap({
    "supabase-url"         = google_secret_manager_secret.supabase_url.id,
    "supabase-service-key" = google_secret_manager_secret.supabase_service_key.id,
    "redis-auth"           = google_secret_manager_secret.redis_auth.id,
    "database-url"         = google_secret_manager_secret.database_url.id,
  })

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Grant permissions to access storage bucket
resource "google_storage_bucket_iam_member" "cloud_run_storage" {
  bucket = google_storage_bucket.ml_artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# =====================================================
# VPC CONNECTOR (for accessing Memorystore)
# =====================================================

resource "google_vpc_access_connector" "connector" {
  name          = "knytt-vpc-connector-${var.environment}"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = "default"

  min_throughput = 200
  max_throughput = var.environment == "prod" ? 1000 : 300
}

# =====================================================
# CLOUD RUN: FastAPI Backend Service
# =====================================================

resource "google_cloud_run_v2_service" "api" {
  name     = "knytt-api-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run_sa.email

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = var.environment == "prod" ? 1 : 0
      max_instance_count = var.environment == "prod" ? 10 : 3
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }

        cpu_idle = true
        startup_cpu_boost = true
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Note: PORT is automatically set by Cloud Run

      env {
        name  = "API_CORS_ORIGINS"
        value = jsonencode([
          "https://knytt.xyz",
          "https://www.knytt.xyz",
          "http://localhost:3000",
          "http://localhost:8080"
        ])
      }

      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SUPABASE_SERVICE_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_service_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cache.host
      }

      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.cache.port)
      }

      env {
        name = "REDIS_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_auth.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.ml_artifacts.name
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
      }
    }
  }

  labels = {
    environment = var.environment
    application = "knytt"
    component   = "api"
  }
}

# Make the API service publicly accessible
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =====================================================
# CLOUD RUN: Celery Worker Service
# =====================================================

resource "google_cloud_run_v2_service" "worker" {
  name     = "knytt-worker-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.cloud_run_sa.email

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 0
      max_instance_count = var.environment == "prod" ? 5 : 2
    }

    containers {
      image = var.worker_image

      # Workers don't expose ports, but Cloud Run requires one
      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "4"  # More CPU for ML workloads
          memory = "8Gi"  # More memory for embeddings
        }

        cpu_idle = false  # Workers need consistent CPU
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "WORKER_TYPE"
        value = "celery"
      }

      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SUPABASE_SERVICE_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_service_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cache.host
      }

      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.cache.port)
      }

      env {
        name = "REDIS_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_auth.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.ml_artifacts.name
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  labels = {
    environment = var.environment
    application = "knytt"
    component   = "worker"
  }
}

# =====================================================
# CLOUD SCHEDULER: Trigger periodic tasks
# =====================================================

resource "google_cloud_scheduler_job" "generate_embeddings" {
  name             = "knytt-generate-embeddings-${var.environment}"
  description      = "Daily embedding generation for new products"
  schedule         = "0 2 * * *"  # 2 AM daily
  time_zone        = "America/Los_Angeles"
  attempt_deadline = "1800s"  # 30 minutes

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/admin/generate-embeddings"

    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }

  retry_config {
    retry_count = 3
  }
}

resource "google_cloud_scheduler_job" "rebuild_faiss_index" {
  name             = "knytt-rebuild-faiss-${var.environment}"
  description      = "Weekly FAISS index rebuild"
  schedule         = "0 3 * * 0"  # 3 AM every Sunday
  time_zone        = "America/Los_Angeles"
  attempt_deadline = "1800s"  # 30 minutes (maximum allowed by Cloud Scheduler)

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/admin/rebuild-index"

    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }

  retry_config {
    retry_count = 1
  }
}

# =====================================================
# OUTPUTS
# =====================================================

output "api_url" {
  description = "URL of the FastAPI service"
  value       = google_cloud_run_v2_service.api.uri
}

output "redis_host" {
  description = "Redis host address"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "Redis port"
  value       = google_redis_instance.cache.port
}

output "gcs_bucket" {
  description = "GCS bucket for ML artifacts"
  value       = google_storage_bucket.ml_artifacts.name
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.cloud_run_sa.email
}
