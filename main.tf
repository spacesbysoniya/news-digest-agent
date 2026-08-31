# Infrastructure as Code (IaC) for deploying the News Digest Agent
terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.80.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type        = string
  description = "The GCP project ID to deploy resources"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Region to deploy regional services"
}

# Secret Manager for Secure API Key Storage
resource "google_secret_manager_secret" "api_key" {
  secret_id = "GOOGLE_API_KEY"
  replication {
    automatic = true
  }
}

# Artifact Registry to store Docker image of the Agent
resource "google_artifact_registry_repository" "agent_repo" {
  location      = var.region
  repository_id = "news-digest-agent-repo"
  description   = "Docker repository for the News Digest Agent"
  format        = "DOCKER"
}

# Cloud Run service to deploy the containerized Agent securely
resource "google_cloud_run_service" "agent_service" {
  name     = "news-digest-agent-service"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_repo.repository_id}/news-digest-agent:latest"
        
        env {
          name = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        env {
          name = "GOOGLE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.api_key.secret_id
              key  = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}