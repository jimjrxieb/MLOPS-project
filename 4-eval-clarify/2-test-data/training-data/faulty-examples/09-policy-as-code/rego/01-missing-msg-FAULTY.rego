package kubernetes.admission

# FAULTY EXAMPLE #1
# Common Mistake: Missing msg assignment in deny rule
# Issue: Policy fails silently or doesn't produce violation messages
# Severity: HIGH (policy won't work as expected)

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    # BUG: Missing msg assignment - this line should be here:
    # msg := "Privileged containers are not allowed"
}

# What happens: The deny rule will match privileged containers but won't
# output any violation message, causing silent failures or confusion.

# Impact: Security violations go undetected because no error is shown.
