/**
 * IAM Configuration
 *
 * Creates service accounts and configures permissions:
 * 1. Cloud Run service account - runs the backend service
 * 2. GitHub Actions service account - deploys from CI/CD
 * 3. Workload Identity Federation - secure GitHub authentication
 */

# Service account for Cloud Run to use
resource "google_service_account" "cloud_run" {
  account_id   = "cloud-run-${var.service_name}"
  display_name = "Cloud Run Service Account for ${var.service_name}"
  description  = "Service account used by Cloud Run to access GCP resources"
}

# Grant Cloud Run service account access to Secret Manager
resource "google_secret_manager_secret_iam_member" "cloud_run_secrets" {
  for_each = google_secret_manager_secret.app_secrets

  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Service account for GitHub Actions
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-${var.service_name}"
  display_name = "GitHub Actions Service Account"
  description  = "Service account for GitHub Actions to deploy to Cloud Run"
}

# Grant GitHub Actions permissions
resource "google_project_iam_member" "github_actions_permissions" {
  for_each = toset([
    "roles/run.admin",               # Deploy to Cloud Run
    "roles/iam.serviceAccountUser",  # Act as Cloud Run service account
    "roles/artifactregistry.writer", # Push Docker images
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Workload Identity Pool for GitHub Actions
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions"
}

# Workload Identity Provider for GitHub
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  description                        = "OIDC provider for GitHub Actions"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow GitHub Actions from specific repo to use the service account
resource "google_service_account_iam_member" "github_actions_workload_identity" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
