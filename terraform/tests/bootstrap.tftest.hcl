mock_provider "kubernetes" {}

run "default_bootstrap" {
  command = plan

  assert {
    condition     = kubernetes_namespace_v1.readiness.metadata[0].name == "readiness-service"
    error_message = "default namespace changed unexpectedly"
  }

  assert {
    condition     = kubernetes_resource_quota_v1.readiness.spec[0].hard["pods"] == "10"
    error_message = "pod quota must remain bounded"
  }

  assert {
    condition     = kubernetes_limit_range_v1.readiness.spec[0].limit[0].default_request["memory"] == "128Mi"
    error_message = "default memory request changed unexpectedly"
  }
}

run "custom_namespace" {
  command = plan
  variables {
    namespace = "readiness-dedicated"
  }
  assert {
    condition     = output.namespace == "readiness-dedicated"
    error_message = "custom namespace was not propagated"
  }
}

