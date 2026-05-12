package kubernetes.admission

# FAULTY EXAMPLE #7
# Common Mistake: Missing input validation
# Issue: Accessing nested fields without checking existence
# Severity: HIGH (policy crashes on nil pointer)

deny[msg] {
    input.request.kind.kind == "Pod"
    # BUG: Assumes securityContext exists - crashes if nil
    container := input.request.object.spec.containers[_]
    container.securityContext.runAsUser == 0
    msg := "Container runs as root"
}
