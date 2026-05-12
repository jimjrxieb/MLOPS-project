# FAULTY EXAMPLE #4
# Common Mistake: Missing package declaration
# Issue: OPA cannot organize/evaluate policy
# Severity: HIGH (policy won't load)

# BUG: Missing 'package kubernetes.admission'

deny[msg] {
    input.request.kind.kind == "Pod"
    not input.request.object.metadata.labels["app"]
    msg := "Pods must have 'app' label"
}
