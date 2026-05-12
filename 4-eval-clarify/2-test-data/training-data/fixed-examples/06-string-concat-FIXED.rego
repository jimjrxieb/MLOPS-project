package kubernetes.admission

# FIXED VERSION OF EXAMPLE #6
# Fix: Use sprintf for string formatting
# Why: Rego doesn't support + operator for strings

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.cpu
    msg := sprintf("Container '%s' missing CPU limit", [container.name])  # ✅ FIXED: Use sprintf
}
