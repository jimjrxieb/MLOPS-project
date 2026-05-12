package kubernetes.admission

# FIXED VERSION OF EXAMPLE #8
# Fix: Use configurable set of trusted registries
# Why: Allows runtime configuration without policy redeployment

# ✅ FIXED: Define as configurable set
trusted_registries := {
    "docker.io",
    "gcr.io",
    "quay.io"
}

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    image := container.image
    registry := split(image, "/")[0]
    not trusted_registries[registry]
    msg := sprintf("Image '%s' from untrusted registry '%s'", [image, registry])
}
