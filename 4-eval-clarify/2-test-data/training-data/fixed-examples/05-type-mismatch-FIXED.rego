package kubernetes.admission

# FIXED VERSION OF EXAMPLE #5
# Fix: Use set for membership checks
# Why: Sets support efficient membership checks with any key type

trusted_registries := {"docker.io", "gcr.io"}  # ✅ FIXED: Set instead of array

deny[msg] {
    input.request.kind.kind == "Pod"
    image := input.request.object.spec.containers[_].image
    registry := split(image, "/")[0]
    not trusted_registries[registry]  # ✅ Now works correctly
    msg := sprintf("Image '%s' from untrusted registry", [image])
}
