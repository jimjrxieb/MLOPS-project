package kubernetes.admission

# FAULTY EXAMPLE #3
# Common Mistake: Using 'some i' unnecessarily
# Issue: Inefficient, verbose code
# Severity: LOW (works but suboptimal)

deny[msg] {
    input.request.kind.kind == "Pod"
    volumes := input.request.object.spec.volumes
    some i  # BUG: Unnecessary variable declaration
    volumes[i].hostPath
    msg := "hostPath volumes are not allowed"
}
