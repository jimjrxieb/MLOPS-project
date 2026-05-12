package kubernetes.admission  # ✅ FIXED: Added package declaration

# FIXED VERSION OF EXAMPLE #4
# Fix: Add package declaration
# Why: Required for OPA to properly scope and load policy

deny[msg] {
    input.request.kind.kind == "Pod"
    not input.request.object.metadata.labels["app"]
    msg := "Pods must have 'app' label"
}
