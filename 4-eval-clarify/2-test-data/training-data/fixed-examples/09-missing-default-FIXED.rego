package kubernetes.admission

# FIXED VERSION OF EXAMPLE #9
# Fix: Add explicit default allow rule
# Why: Makes policy behavior predictable and clear

# ✅ FIXED: Explicit default - allow if no denials
default allow := true

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := "Privileged containers are not allowed"
}

# Clear logic: If deny rules produce messages, request is denied
# Otherwise, default allow applies
allow {
    count(deny) == 0
}
