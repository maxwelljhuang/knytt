/**
 * Terraform Configuration for Knytt Backend Infrastructure
 *
 * This configuration sets up:
 * - Google Cloud Provider
 * - Backend state storage in GCS
 * - Required API services
 */

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Store Terraform state in Google Cloud Storage
  # Uncomment after creating the bucket manually:
  # backend "gcs" {
  #   bucket = "knytt-terraform-state"
  #   prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required Google Cloud APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",              # Cloud Run
    "artifactregistry.googleapis.com", # Artifact Registry
    "secretmanager.googleapis.com",    # Secret Manager
    "iam.googleapis.com",              # IAM
    "iamcredentials.googleapis.com",   # Workload Identity
    "cloudbuild.googleapis.com",       # Cloud Build (optional)
  ])

  service            = each.value
  disable_on_destroy = false
}
