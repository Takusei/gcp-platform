variable "project_id" { type = string }
variable "name" { type = string }
variable "region" {
  type    = string
  default = "asia-northeast1"
}
variable "runtime_service_account" { type = string }
variable "initial_image" { type = string }
variable "environment" {
  type    = map(string)
  default = {}
}
variable "secrets" {
  type = map(object({
    secret  = string
    version = optional(string, "latest")
  }))
  default = {}
}
variable "cpu" {
  type    = string
  default = "1"
}
variable "memory" {
  type    = string
  default = "1Gi"
}
variable "port" {
  type    = number
  default = 8080
}
variable "timeout" {
  type    = string
  default = "900s"
}
variable "concurrency" {
  type    = number
  default = 80
}
variable "min_instances" {
  type    = number
  default = 0
}
variable "max_instances" {
  type    = number
  default = 10
}
