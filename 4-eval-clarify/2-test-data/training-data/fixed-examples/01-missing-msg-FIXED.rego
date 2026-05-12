package kubernetes.admission

# FIXED VERSION OF EXAMPLE #1
# Fix: Add explicit msg assignment
# Why: Rego requires msg definition for violations to be reported

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := "Privileged containers are not allowed"  # ✅ FIXED: Added msg
}

# What changed: Added the msg assignment so violations are properly reported.
# Result: Policy now correctly blocks privileged containers with clear error message.
