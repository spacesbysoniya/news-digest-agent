terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Secret Manager for Google API Key
resource "google_secret_manager_secret" "api_key" {
  secret_id = "GOOGLE_API_KEY"
  replication {
    auto {}
  }
}

# 2. Artifact Registry for Container Storage
resource "google_artifact_registry_repository" "agent_repo" {
  location      = var.region
  repository_id = "news-digest-agent-repo"
  description   = "Container repository for the News Digest Agent"
  format        = "DOCKER"
}

# 3. Cloud Run Service (v2) for Container Deployment
resource "google_cloud_run_v2_service" "agent_service" {
  name     = "news-digest-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_repo.repository_id}/agent:latest"

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.api_key.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }
    }
  }
}
