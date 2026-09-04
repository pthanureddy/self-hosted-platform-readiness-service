output "namespace" {
  description = "Bootstrapped namespace."
  value       = kubernetes_namespace_v1.readiness.metadata[0].name
}

