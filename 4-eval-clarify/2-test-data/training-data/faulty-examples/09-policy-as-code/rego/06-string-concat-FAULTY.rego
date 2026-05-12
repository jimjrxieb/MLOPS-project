package kubernetes.admission

# FAULTY EXAMPLE #6
# Common Mistake: Incorrect string concatenation
# Issue: Using + instead of sprintf for dynamic messages
# Severity: HIGH (syntax error in Rego)

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.cpu
    # BUG: Cannot use + operator for string concatenation in Rego
    msg := "Container " + container.name + " missing CPU limit"
}
