variable "namespace" {
  description = "Namespace to bootstrap for the readiness service."
  type        = string
  default     = "readiness-service"
  validation {
    condition     = can(regex("^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", var.namespace)) && length(var.namespace) <= 63
    error_message = "namespace must be a valid Kubernetes DNS label"
  }
}

variable "labels" {
  description = "Additional namespace labels."
  type        = map(string)
  default     = {}
}

variable "quota" {
  description = "Namespace resource quota."
  type = object({
    cpu_requests    = string
    cpu_limits      = string
    memory_requests = string
    memory_limits   = string
    pods            = number
  })
  default = {
    cpu_requests    = "2"
    cpu_limits      = "4"
    memory_requests = "2Gi"
    memory_limits   = "4Gi"
    pods            = 10
  }
}

