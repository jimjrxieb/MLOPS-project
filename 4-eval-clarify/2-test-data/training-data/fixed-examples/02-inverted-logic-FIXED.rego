package kubernetes.admission

# FIXED VERSION OF EXAMPLE #2
# Fix: Add 'not' to check for absence of CPU limits
# Why: We want to deny when limits are MISSING, not when they exist

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.cpu  # ✅ FIXED: Added 'not' for negation
    msg := sprintf("Container '%s' must define CPU limits", [container.name])
}

# What changed: Added 'not' to properly check for missing CPU limits
# Result: Policy now correctly denies pods without resource limits
