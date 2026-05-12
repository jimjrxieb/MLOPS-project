package kubernetes.admission

# FAULTY EXAMPLE #8
# Common Mistake: Hardcoded values instead of configurable rules
# Issue: Not flexible, requires policy redeployment for changes
# Severity: MEDIUM (works but not maintainable)

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    image := container.image
    # BUG: Hardcoded registry list - should be configurable
    not startswith(image, "docker.io/")
    not startswith(image, "gcr.io/")
    not startswith(image, "quay.io/")
    msg := sprintf("Image '%s' from untrusted registry", [image])
}
