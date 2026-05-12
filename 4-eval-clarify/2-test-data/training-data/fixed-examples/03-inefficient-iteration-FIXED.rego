package kubernetes.admission

# FIXED VERSION OF EXAMPLE #3
# Fix: Use wildcard _ for iteration
# Why: More idiomatic, cleaner, faster in Rego

deny[msg] {
    input.request.kind.kind == "Pod"
    volume := input.request.object.spec.volumes[_]  # ✅ FIXED: Direct iteration
    volume.hostPath
    msg := "hostPath volumes are not allowed"
}
