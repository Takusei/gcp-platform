# Opt-in module for new jobs or reviewed imports, not part of bootstrap.
resource "google_cloud_run_v2_job" "this" {
  project             = var.project_id
  name                = var.name
  location            = var.region
  deletion_protection = true
  template {
    task_count  = var.task_count
    parallelism = var.parallelism
    template {
      service_account = var.runtime_service_account
      timeout         = var.timeout
      max_retries     = var.max_retries
      containers {
        image = var.initial_image
        resources {
          limits = { cpu = var.cpu, memory = var.memory }
        }
        dynamic "env" {
          for_each = var.environment
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret
                version = env.value.version
              }
            }
          }
        }
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }
}
