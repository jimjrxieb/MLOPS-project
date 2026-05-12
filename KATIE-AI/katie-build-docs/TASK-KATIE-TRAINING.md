# Task: Generate Katie 3B Training Data + New Eval Questions

## Context

Katie is a LLaMA 3.2-3B-Instruct model fine-tuned for Kubernetes platform engineering triage. She's been trained on 300k examples but her eval scores show gaps in deep understanding vs surface-level keyword matching.

**The problem:** Katie can parrot terms but doesn't truly understand HOW things work. When asked about pod connectivity, she should reason through DNS → Endpoints → NetworkPolicy → Ports → CNI. Not guess randomly.

**What we need:** Two types of output:
1. **Training data** → `../1-data-pipeline/01-raw-data-lake/` (JSONL, ChatML format)
2. **New eval questions** → `../4-eval-clarify/2-test-data/evaluation/` (JSONL, benchmark format)

IMPORTANT: Training data and eval questions MUST be different. Never put eval answers into training data (data leakage).

---

## Output Format

### Training Data (JSONL)
```json
{"messages": [
  {"role": "system", "content": "You are Katie, a CKS/CKA-certified Kubernetes platform engineer..."},
  {"role": "user", "content": "The actual question or scenario"},
  {"role": "assistant", "content": "Deep, detailed answer with exact commands, YAML, and reasoning"}
]}
```

### Eval Questions (JSONL)
```json
{"id": "unique-id", "category": "operational", "subcategory": "troubleshooting", "rank": "D", "question": "The question text", "expected_keywords": ["term1", "term2"], "expected_fix_contains": "key command or config", "grading": {"keywords_required": 3, "fix_required": false, "workflow_required": false}}
```

---

## Priority Areas (by weight)

### 1. CKS — Kubernetes Security (40% weight, currently 31.7%)

**What Katie gets wrong:** Uses paraphrases instead of canonical terms. Says "policy" instead of "NetworkPolicy". Knows concepts but doesn't name the exact resource kinds.

**Generate training data for:**
- NetworkPolicy scenarios (default-deny, egress DNS, multi-namespace, troubleshooting when traffic is blocked)
- Falco rules (detection patterns, FalcoRule YAML, tuning, MITRE ATT&CK mapping)
- Supply chain (Cosign signing, image digest pinning, ImagePolicyWebhook, multi-stage Dockerfiles)
- securityContext (full restricted PSS, AppArmor profiles, seccomp RuntimeDefault)
- AuditLog (kube-apiserver audit policy, StaticPod configuration)
- Pod Security Standards (PSA labels: enforce/audit/warn, restricted/baseline/privileged)

**MUST use these exact terms in every answer:** NetworkPolicy, FalcoRule, Falco, Cosign, digest, ImagePolicyWebhook, mTLS, StaticPod, AppArmor, securityContext, seccompProfile, AuditLog, Pod Security Standards, Sysdig

### 2. CKA — Kubernetes Administration (25% weight, currently 42.1%)

**What Katie gets wrong:** Doesn't know exact admin commands (kubeadm, etcdctl, journalctl).

**Generate training data for:**
- kubeadm cluster upgrades (full step-by-step: plan → apply → drain → kubelet → uncordon)
- etcd backup/restore (etcdctl snapshot save/restore with --cacert --cert --key flags)
- kubelet troubleshooting (journalctl -u kubelet, systemctl status, PLEG, certificate expiry)
- Node troubleshooting (NotReady, DiskPressure, drain/uncordon)
- Storage operations (PV/PVC, dynamic provisioning, StorageClass, volume expansion)
- CoreDNS troubleshooting (loop detection, ConfigMap, resolve.conf)
- Service debugging (empty endpoints, selector mismatch, port vs targetPort)

### 3. CNPA — Platform Engineering (25% weight, currently 54.5%)

**What Katie gets wrong:** Doesn't name specific tools (Sealed Secrets, External Secrets Operator, Crossplane XRDs).

**Generate training data for:**
- GitOps (ArgoCD, Flux, reconciliation, drift detection, pull-based)
- Secrets management (Sealed Secrets, External Secrets Operator, SOPS, KMS)
- Service mesh (Istio mTLS STRICT, VirtualService, DestinationRule, circuit breaking with outlierDetection)
- Observability (OpenTelemetry, OTLP, Collector, auto-instrumentation, PromQL, ServiceMonitor)
- Platform engineering (IDP, Backstage, golden paths, self-service namespace provisioning)
- Crossplane (XRD, Composition, Claim, provider)
- Admission controllers (Kyverno vs OPA Gatekeeper vs ValidatingAdmissionPolicy comparison)

### 4. AWS/Cloud (10% weight, currently 30%)

**Generate training data for:**
- IAM (least privilege, instance profiles, credential-report, cross-account assume role)
- VPC (public/private/database subnets, NAT Gateway, NACLs vs Security Groups)
- EKS specifics (shared responsibility model, what AWS manages vs what you manage)
- AWS CLI commands (aws iam, aws ec2, aws s3api, aws rds)

### 5. Operational/Real-World (NEW — currently not tested)

**This is the most important section.** Katie's actual job is triage and routing.

**Generate training data for:**
- ArgoCD ownership checking (ALWAYS check app.kubernetes.io/instance label before fixing)
- Drift wars (kubectl patch on ArgoCD-managed resource → ArgoCD reverts → fix in git instead)
- Finding deduplication (3 scanners find same issue = 1 fix, not 3)
- Rank assignment with context (hostNetwork on kube-proxy = suppress, hostNetwork on app pod = fix)
- Troubleshooting mental models (pod-to-pod = DNS→Endpoints→NetworkPolicy, NOT storage)
- Recent K8s changes (Gateway API replacing Ingress-NGINX March 2026, ValidatingAdmissionPolicy GA, PSA replacing PSP)

---

## Hard Rules

1. **Every training answer MUST use exact canonical Kubernetes resource kind names** (NetworkPolicy not "network policy", StaticPod not "static pod")
2. **Every YAML block must be syntactically valid** — run through a YAML parser before including
3. **Every kubectl command must be complete** — include namespace, flags, full resource path
4. **Never generate generic "best practices" lists** — every answer must be a specific scenario with specific commands
5. **ArgoCD rule:** Any fix on an ArgoCD-managed resource MUST say "fix in git, push, let ArgoCD sync. Never kubectl patch."
6. **Include the WHY** — not just "use runAsNonRoot: true" but WHY (root in container = potential escape to host via kernel exploit)
7. **Training data and eval questions MUST be completely different** — no overlap

## Quantity Targets

| Area | Training Examples | New Eval Questions |
|------|------------------|--------------------|
| CKS | 200-300 | 30 |
| CKA | 100-150 | 20 |
| CNPA | 100-150 | 20 |
| AWS | 50-80 | 10 |
| Operational | 100-150 | 30 |
| **Total** | **550-830** | **110** |

## File Naming

Training data:
```
../1-data-pipeline/01-raw-data-lake/gemini_cks_training.jsonl
../1-data-pipeline/01-raw-data-lake/gemini_cka_training.jsonl
../1-data-pipeline/01-raw-data-lake/gemini_cnpa_training.jsonl
../1-data-pipeline/01-raw-data-lake/gemini_aws_training.jsonl
../1-data-pipeline/01-raw-data-lake/gemini_operational_training.jsonl
```

Eval questions:
```
../4-eval-clarify/2-test-data/evaluation/11-gemini-cks-benchmark/cks-new-questions.jsonl
../4-eval-clarify/2-test-data/evaluation/12-gemini-cka-benchmark/cka-new-questions.jsonl
../4-eval-clarify/2-test-data/evaluation/13-gemini-cnpa-benchmark/cnpa-new-questions.jsonl
../4-eval-clarify/2-test-data/evaluation/14-gemini-aws-benchmark/aws-new-questions.jsonl
../4-eval-clarify/2-test-data/evaluation/15-gemini-operational-benchmark/operational-new-questions.jsonl
```
