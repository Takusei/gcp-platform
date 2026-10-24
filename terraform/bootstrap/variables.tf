variable "project_id" {
  type    = string
  default = "dev-projects-476011"
}

variable "region" {
  type    = string
  default = "asia-northeast1"
}

variable "github_owner_id" {
  description = "Numeric GitHub user ID for Takusei; obtain with gh api users/Takusei --jq .id"
  type        = string
  validation {
    condition     = can(regex("^[0-9]+$", var.github_owner_id))
    error_message = "Use the numeric GitHub owner ID."
  }
}

variable "runtime_service_accounts" {
  description = "Exact runtime service account emails from the live Cloud Run inventory"
  type        = set(string)
  validation {
    condition     = length(var.runtime_service_accounts) > 0 && alltrue([for email in var.runtime_service_accounts : can(regex("^[^@]+@[^@]+\\.gserviceaccount\\.com$", email))])
    error_message = "Supply the runtime identities used by your existing services and jobs."
  }
}
