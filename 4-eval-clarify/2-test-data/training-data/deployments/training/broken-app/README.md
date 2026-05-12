# Broken App - JADE Training Honeypot

**WARNING: This deployment is INTENTIONALLY VULNERABLE. DO NOT deploy to production.**

## Purpose

This deployment contains 15+ security anti-patterns for training JADE to:
1. Detect security issues via scanners
2. Generate appropriate fixes
3. Classify findings by rank (E/D/C/B/S)

## Vulnerabilities Included

### Pod Security Violations

| # | Vulnerability | Scanner | Expected Fix |
|---|--------------|---------|--------------|
| 1 | No resource limits | Polaris, Checkov | Add resources.limits |
| 2 | No probes | Polaris | Add liveness/readiness probes |
| 3 | Running as root | Trivy, Checkov | runAsNonRoot: true |
| 4 | Privileged container | All scanners | privileged: false |
| 5 | :latest tag | Trivy, Polaris | Pin image version |
| 6 | Hardcoded secrets | Trivy, Checkov | Use Secrets or external vault |
| 7 | hostPath mount | Checkov, Polaris | Remove or use PVC |
| 8 | Writable root FS | Trivy | readOnlyRootFilesystem: true |
| 9 | Default SA | Kubescape | Create dedicated SA |
| 10 | Privilege escalation | All | allowPrivilegeEscalation: false |
| 11 | No seccomp | Trivy | Add seccompProfile |
| 12 | hostNetwork | Checkov | hostNetwork: false |
| 13 | hostPID | Checkov | hostPID: false |
| 14 | Capabilities not dropped | Trivy | drop: ["ALL"] |
| 15 | Dangerous capabilities | Checkov | Remove SYS_ADMIN, etc |

### ConfigMap/Secret Issues

| # | Vulnerability | Scanner | Expected Fix |
|---|--------------|---------|--------------|
| 16 | Secrets in ConfigMap | Trivy, Checkov | Move to Secret + encrypt |
| 17 | Hardcoded credentials | Gitleaks | Use external secrets |
| 18 | Private keys exposed | Trivy | Use sealed-secrets |

### Service/Network Issues

| # | Vulnerability | Scanner | Expected Fix |
|---|--------------|---------|--------------|
| 19 | No NetworkPolicy | Polaris | Create NetworkPolicy |
| 20 | LoadBalancer exposed | Checkov | Add source ranges |
| 21 | NodePort service | Polaris | Use ClusterIP + Ingress |

## Expected Scanner Findings

```bash
# Run scanners to generate findings
checkov -d deployments/training/broken-app/  # Expect ~30 findings
trivy config deployments/training/broken-app/  # Expect ~20 findings
polaris audit --audit-path deployments/training/broken-app/  # Expect ~15 findings
kubescape scan framework nsa deployments/training/broken-app/  # Expect ~25 findings
```

## Rank Classification

Based on Iron Legion ranking:

- **E-rank (auto-fix)**: Missing labels, missing probes
- **D-rank (auto-fix with logging)**: Resource limits, readOnlyRootFilesystem
- **C-rank (needs approval)**: Privileged containers, hostPath
- **B-rank (human decision)**: Network policies, RBAC changes
- **S-rank (human only)**: Production secrets, compliance decisions

## Usage

```bash
# Deploy to Kind cluster
kubectl apply -f deployments/training/broken-app/

# Let jsa-infrasec scan and fix
# All fix attempts logged to ~/GP-Copilot/training-data/fix-attempts.jsonl

# Verify fixes
kubectl get pods -n broken-app
```

## Data Collection

Each fix attempt by jsa-infrasec logs:
- Finding details (scanner, rule_id, severity)
- Action taken (patch, apply, skip, escalate)
- Result (FIXED, FAILED, PARTIAL, ESCALATED)
- Verification status

This data feeds into JADE LoRA fine-tuning.
