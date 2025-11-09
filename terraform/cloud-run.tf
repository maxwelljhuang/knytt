/**
 * Cloud Run Service Configuration
 *
 * Deploys the backend application to Cloud Run with:
 * - Secrets from Secret Manager
 * - Auto-scaling configuration
 * - Public access (or configure IAM as needed)
 */

resource "google_cloud_run_v2_service" "backend" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = 0 # Scale to zero when not in use
      max_instance_count = 10
    }

    containers {
      # Image will be updated by GitHub Actions on each deployment
      # This is just the initial/default image
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/backend:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      # Environment variables from Secret Manager
      dynamic "env" {
        for_each = {
          DATABASE_URL          = "database-url"
          SUPABASE_URL          = "supabase-url"
          SUPABASE_ANON_KEY     = "supabase-anon-key"
          SUPABASE_SERVICE_KEY  = "supabase-service-key"
          JWT_SECRET_KEY        = "jwt-secret-key"
          JWT_ALGORITHM         = "jwt-algorithm"
          API_CORS_ORIGINS      = "cors-origins"
          CLIP_MODEL            = "clip-model"
          EMBEDDING_DIMENSION   = "embedding-dimension"
          ENVIRONMENT           = "environment"
        }

        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app_secrets[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      # Additional non-secret environment variables
      env {
        name  = "API_HOST"
        value = "0.0.0.0"
      }

      env {
        name  = "API_PORT"
        value = "8080"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCP_REGION"
        value = var.region
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_iam_member.cloud_run_secrets,
  ]

  lifecycle {
    ignore_changes = [
      # Image will be updated by CI/CD
      template[0].containers[0].image,
    ]
  }
}

# Allow unauthenticated access to the service
# Remove this if you want to require authentication
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.backend.name
  location = google_cloud_run_v2_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
