output "github_secrets" {
  description = "Set these two repository secrets in each of the eight application repositories."
  value = {
    GCP_WORKLOAD_IDENTITY_PROVIDER = google_iam_workload_identity_pool_provider.github.name
    GCP_SERVICE_ACCOUNT          = google_service_account.deployer.email
  }
}
