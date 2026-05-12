package kubernetes.admission

# FAULTY EXAMPLE #2
# Common Mistake: Inverted logic - checks for presence instead of absence
# Issue: Policy allows what it should deny and vice versa
# Severity: CRITICAL (complete logic inversion)

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.resources.limits.cpu  # BUG: Positive check instead of negative
    msg := sprintf("Container '%s' must define CPU limits", [container.name])
}

# What happens: This denies pods that HAVE CPU limits (opposite of intent)
# Correct behavior: Should deny pods WITHOUT CPU limits

# Impact: Security policy is completely inverted - allows unsafe pods, blocks safe ones
