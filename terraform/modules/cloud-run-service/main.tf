# For new services or a reviewed import of existing services. This module is
# deliberately NOT instantiated by bootstrap; importing incomplete runtime
# configuration could otherwise erase existing environment/secret bindings.
resource "google_cloud_run_v2_service" "this" {
  project             = var.project_id
  name                = var.name
  location            = var.region
  deletion_protection = true

  template {
    service_account                  = var.runtime_service_account
    timeout                          = var.timeout
    max_instance_request_concurrency = var.concurrency
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    containers {
      image = var.initial_image
      ports {
        container_port = var.port
      }
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

  lifecycle {
    # Application release workflows own the image; Terraform owns runtime config.
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }
}
