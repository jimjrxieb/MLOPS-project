package kubernetes.admission

# FAULTY EXAMPLE #10
# Common Mistake: Incorrect negation with membership checks
# Issue: Using != instead of proper negation pattern
# Severity: HIGH (logic error - may not deny what you expect)

trusted_images := {
    "nginx:1.21",
    "redis:6.2",
    "postgres:13"
}

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    image := container.image
    # BUG: != doesn't work with sets - always false
    image != trusted_images[_]
    msg := sprintf("Image '%s' not in trusted list", [image])
}
