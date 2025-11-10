# Import existing GCP resources into Terraform state
# This file handles importing resources that were created manually or in previous deployments
# Terraform will automatically import these on first run with the GCS backend

import {
  to = google_redis_instance.cache
  id = "projects/${var.project_id}/locations/${var.region}/instances/knytt-redis-${var.environment}"
}

import {
  to = google_storage_bucket.ml_artifacts
  id = "${var.project_id}-knytt-ml-${var.environment}"
}

import {
  to = google_secret_manager_secret.supabase_url
  id = "projects/${var.project_id}/secrets/supabase-url-${var.environment}"
}

import {
  to = google_secret_manager_secret.supabase_service_key
  id = "projects/${var.project_id}/secrets/supabase-service-key-${var.environment}"
}

import {
  to = google_secret_manager_secret.redis_auth
  id = "projects/${var.project_id}/secrets/redis-auth-${var.environment}"
}

import {
  to = google_secret_manager_secret_version.supabase_url
  id = "projects/${var.project_id}/secrets/supabase-url-${var.environment}/versions/1"
}

import {
  to = google_secret_manager_secret_version.supabase_service_key
  id = "projects/${var.project_id}/secrets/supabase-service-key-${var.environment}/versions/1"
}

import {
  to = google_secret_manager_secret_version.redis_auth
  id = "projects/${var.project_id}/secrets/redis-auth-${var.environment}/versions/2"
}

import {
  to = google_service_account.cloud_run_sa
  id = "projects/${var.project_id}/serviceAccounts/knytt-cloud-run-${var.environment}@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_vpc_access_connector.connector
  id = "projects/${var.project_id}/locations/${var.region}/connectors/knytt-vpc-connector-${var.environment}"
}

import {
  to = google_cloud_run_v2_service.worker
  id = "projects/${var.project_id}/locations/${var.region}/services/knytt-worker-${var.environment}"
}

import {
  to = google_cloud_scheduler_job.rebuild_faiss_index
  id = "projects/${var.project_id}/locations/${var.region}/jobs/knytt-rebuild-faiss-${var.environment}"
}

# Note: Secret versions and IAM bindings will be managed by Terraform after initial import
# Cloud Run API service is recreated fresh on each deployment
