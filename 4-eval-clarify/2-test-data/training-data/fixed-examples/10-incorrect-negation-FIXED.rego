package kubernetes.admission

# FIXED VERSION OF EXAMPLE #10
# Fix: Use 'not' with set membership check
# Why: Proper way to check if element is NOT in set

trusted_images := {
    "nginx:1.21",
    "redis:6.2",
    "postgres:13"
}

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    image := container.image
    # ✅ FIXED: Use 'not' with set membership
    not trusted_images[image]
    msg := sprintf("Image '%s' not in trusted list", [image])
}
