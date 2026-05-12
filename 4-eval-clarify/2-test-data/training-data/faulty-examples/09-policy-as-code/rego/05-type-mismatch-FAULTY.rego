package kubernetes.admission

# FAULTY EXAMPLE #5
# Common Mistake: Using array instead of set for membership check
# Issue: Index errors, inefficient lookups
# Severity: MEDIUM (may fail with non-integer keys)

trusted_registries := ["docker.io", "gcr.io"]  # BUG: Array instead of set

deny[msg] {
    input.request.kind.kind == "Pod"
    image := input.request.object.spec.containers[_].image
    registry := split(image, "/")[0]
    not trusted_registries[registry]  # BUG: Array doesn't support string indexing
    msg := sprintf("Image '%s' from untrusted registry", [image])
}
