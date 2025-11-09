/**
 * Artifact Registry Configuration
 *
 * Creates a Docker repository for storing container images.
 * More modern and recommended over Google Container Registry (GCR).
 */

resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for Knytt backend images"
  format        = "DOCKER"

  # Cleanup policy to remove old images
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "delete-old-images"
    action = "DELETE"

    condition {
      tag_state  = "UNTAGGED"
      older_than = "2592000s" # 30 days
    }
  }

  cleanup_policies {
    id     = "keep-recent-versions"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Output the repository URL for use in workflows
output "artifact_registry_repository" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}"
  description = "Artifact Registry repository URL"
}
