package kubernetes.admission

# FIXED VERSION OF EXAMPLE #7
# Fix: Check if securityContext exists before accessing
# Why: Prevents crashes on missing fields

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    # ✅ FIXED: Validate existence first
    sc := container.securityContext
    sc.runAsUser == 0
    msg := sprintf("Container '%s' runs as root", [container.name])
}
