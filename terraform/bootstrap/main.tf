terraform {
  required_version = ">= 1.6.0, < 2.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # Configure a private GCS state bucket with `terraform init -backend-config=...`.
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  repositories = toset([
    "Takusei/api-collections", "Takusei/knowledge-search",
    "Takusei/line-webhook", "Takusei/line-poster",
    "Takusei/marp-ppt-agent", "Takusei/marp-ppt-api",
    "Takusei/pdm-agent-backend", "Takusei/realEstate",
  ])
  registries = toset([
    "fastapi-repo", "knowledge-search", "line-webhook", "line-poster",
    "marp-ppt-agent", "marp-ppt-api", "pdf-agent-backend",
    "rec-agent", "realestate-repo", "rec-embed",
  ])
}

# Dedicated identity: do not modify/reuse the existing github-pool implicitly.
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "portfolio-github"
  display_name              = "Portfolio GitHub deployments"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-main"
  display_name                       = "Portfolio GitHub main"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository_owner_id == '${var.github_owner_id}' && assertion.repository in ${jsonencode(sort(tolist(local.repositories)))} && assertion.ref == 'refs/heads/main' && assertion.event_name == 'workflow_dispatch'"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  account_id   = "portfolio-github-deployer"
  display_name = "GitHub portfolio container deployer"
}

resource "google_service_account_iam_member" "github" {
  for_each           = local.repositories
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${each.key}"
}

# This identity can update Cloud Run workloads in this personal GCP project.
# It cannot change project IAM or access application secret values.
resource "google_project_iam_member" "run_deployer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Existing registries are referenced, never recreated or imported by bootstrap.
resource "google_artifact_registry_repository_iam_member" "writer" {
  for_each   = local.registries
  project    = var.project_id
  location   = var.region
  repository = each.key
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "runtime_user" {
  for_each           = var.runtime_service_accounts
  service_account_id = "projects/${var.project_id}/serviceAccounts/${each.key}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}
