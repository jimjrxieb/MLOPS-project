package kubernetes.admission

# FAULTY EXAMPLE #9
# Common Mistake: Missing default allow behavior
# Issue: Implicit allow can be confusing and may not work in all OPA configurations
# Severity: MEDIUM (works but can be unpredictable)

# BUG: No explicit default allow rule

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := "Privileged containers are not allowed"
}

# BUG: What happens if no deny rules match?
# Unclear if request is allowed or denied
