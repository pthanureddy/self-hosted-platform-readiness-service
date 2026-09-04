resource "kubernetes_namespace_v1" "readiness" {
  metadata {
    name = var.namespace
    labels = merge(
      {
        "app.kubernetes.io/part-of"    = "readiness-service"
        "app.kubernetes.io/managed-by" = "terraform"
      },
      var.labels
    )
  }
}

resource "kubernetes_resource_quota_v1" "readiness" {
  metadata {
    name      = "readiness-service"
    namespace = kubernetes_namespace_v1.readiness.metadata[0].name
  }
  spec {
    hard = {
      "requests.cpu"    = var.quota.cpu_requests
      "limits.cpu"      = var.quota.cpu_limits
      "requests.memory" = var.quota.memory_requests
      "limits.memory"   = var.quota.memory_limits
      pods              = tostring(var.quota.pods)
    }
  }
}

resource "kubernetes_limit_range_v1" "readiness" {
  metadata {
    name      = "readiness-service"
    namespace = kubernetes_namespace_v1.readiness.metadata[0].name
  }
  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "256Mi"
      }
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
    }
  }
}

