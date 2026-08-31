output "service_uri" {
  value       = google_cloud_run_v2_service.agent_service.uri
  description = "The Cloud Run service URL"
}

output "artifact_registry_uri" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_repo.repository_id}"
  description = "Artifact Registry Docker repository URI"
}
