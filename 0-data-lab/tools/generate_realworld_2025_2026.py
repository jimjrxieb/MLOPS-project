#!/usr/bin/env python3
"""
Real-World 2025-2026 Training Data + Operational Eval Benchmark
================================================================
Sources: CNCF blog, Kubernetes release notes, CVE feeds, CKA/CKS exam updates,
production postmortems, Gateway API migration guides.

Generates:
1. Training data — real-world scenarios from 2025-2026
2. Operational benchmark — eval questions testing Katie's ACTUAL job

Output:
  - 01-raw-data-lake/realworld_2025_2026.jsonl (training)
  - 4-eval-clarify/2-test-data/evaluation/10-operational-benchmark/ (eval)
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "4-eval-clarify" / "2-test-data" / "evaluation" / "10-operational-benchmark"

SYSTEM = "You are Katie, a Kubernetes platform engineering triage engine. You route findings, check ownership, deduplicate, and prioritize. You know current Kubernetes versions (1.32-1.35), recent CVEs, Gateway API migration, and real-world production failure patterns."


def msg(user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}


def generate_recent_cves():
    """Real CVEs from 2025 that Katie should know."""
    return [
        msg("CVE-2025-1974 scored CVSS 9.8 on the Ingress-NGINX controller. What is it and what's the fix?",
            """**CVE-2025-1974 (IngressNightmare) — CRITICAL, CVSS 9.8**

Disclosed March 24, 2025. Unauthenticated remote code execution via the Ingress-NGINX admission controller. An attacker on the pod network can send crafted admission review requests to execute arbitrary code in the ingress-nginx-controller pod, which typically has access to all cluster Secrets.

**Impact:**
- Unauthenticated RCE from within the pod network
- Access to all Secrets across all namespaces (Ingress-NGINX reads TLS secrets)
- Full cluster compromise if the controller has broad RBAC

**Related CVEs in the same disclosure:**
- CVE-2025-1097 (High) — annotation injection
- CVE-2025-1098 (High) — annotation injection
- CVE-2025-24514 (High) — auth-url injection
- CVE-2025-24513 (Medium) — path sanitization

**Fix:**
```bash
# Upgrade to patched versions
helm upgrade ingress-nginx ingress-nginx/ingress-nginx --set controller.image.tag=v1.11.5
# Or v1.12.1 for the 1.12 track

# If you can't upgrade immediately, disable the admission webhook:
kubectl delete validatingwebhookconfiguration ingress-nginx-admission
```

**Long-term:** Ingress-NGINX is being retired March 31, 2026. Migrate to Gateway API:
```bash
# Install a Gateway API controller (e.g., Envoy Gateway, Cilium, Traefik)
# Use ingress2gateway tool to convert existing Ingress resources
ingress2gateway print --input-file ingress.yaml
```

**Rank:** S — cluster-wide secret exposure, immediate patching required."""),

        msg("Three critical runc CVEs were disclosed in November 2025. What are they and what do they mean for our containers?",
            """**runc CVEs — November 2025 (Container Escape)**

- **CVE-2025-31133** — mount operation race condition
- **CVE-2025-52565** — file protection bypass during container creation
- **CVE-2025-52881** — mount namespace escape

**What runc is:** runc is the low-level container runtime that actually creates containers. It's used by containerd (which is used by Kubernetes). When you `kubectl run` a pod, the chain is: kubelet → containerd → runc → Linux namespaces/cgroups.

**Impact:** These CVEs exploit weaknesses in runc's mount operations during container creation. An attacker can:
1. Break container isolation during the creation window
2. Gain root access on the host system
3. Access all other containers on that node

**Fix:**
```bash
# Check your runc version
crictl info | grep runcVersion
# Or
runc --version

# Upgrade containerd (which bundles runc)
sudo apt-get update && sudo apt-get install -y containerd.io
sudo systemctl restart containerd
sudo systemctl restart kubelet

# Verify
crictl info | grep runcVersion
```

**Mitigations (defense in depth):**
- `securityContext.seccompProfile: RuntimeDefault` — limits syscalls available during exploitation
- `capabilities.drop: ALL` — reduces what an escaped process can do on the host
- gVisor or Kata Containers for high-security workloads (they don't use runc)
- Keep nodes patched — this is a node-level vulnerability, not a Kubernetes API vulnerability

**Rank:** S — container escape to host, affects all containers on the node."""),
    ]


def generate_gateway_api():
    """Gateway API replacing Ingress — active migration happening now."""
    return [
        msg("Ingress-NGINX is being retired March 2026. What is Gateway API and how do we migrate?",
            """**Ingress-NGINX retirement: March 31, 2026.** No more bug fixes, security patches, or updates after that.

**Important distinction:** The Kubernetes Ingress API itself is NOT deprecated. You can still create Ingress resources. What's retired is the NGINX-based controller that implements the Ingress API.

**Gateway API is the successor:**

```
Old: Ingress (one resource = load balancer + routing rules combined)
New: Gateway API (separated by role)
  ├── GatewayClass — infrastructure provider (admin)
  ├── Gateway — where traffic enters (ops team)
  └── HTTPRoute — how traffic is routed (app developer)
```

**Why it's better:**
- Role-oriented: cluster admin manages Gateway, app team manages HTTPRoute
- More expressive: header-based routing, request mirroring, traffic splitting
- Multi-tenant safe: Gateway and HTTPRoute are in different namespaces
- Portable: same API works across controllers (Envoy, Cilium, Traefik, Istio)

**Migration example:**
```yaml
# OLD: Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80

# NEW: Gateway API
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web
spec:
  parentRefs:
  - name: main-gateway
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: api-service
      port: 80
```

**Migration steps:**
1. Install a Gateway API controller (Envoy Gateway, Cilium, kGateway)
2. Run `ingress2gateway print --input-file ingress.yaml` to auto-convert
3. Deploy Gateway + HTTPRoute alongside existing Ingress (different external IPs)
4. Test, validate, shift traffic
5. Decommission Ingress-NGINX before March 2026

**Rank:** C — requires planning, JADE should assess blast radius per application."""),
    ]


def generate_k8s_recent_features():
    """K8s 1.32-1.35 features Katie should know about."""
    return [
        msg("What security features graduated to stable in Kubernetes 1.32 through 1.35?",
            """Key security features that graduated to GA (stable) in 2025:

**Kubernetes 1.32-1.33:**
- **Structured Authentication Config** (GA) — configurable authentication via file, not just API server flags
- **Bound Service Account Token Volumes** — tokens are audience-bound and time-limited by default

**Kubernetes 1.34:**
- **Pod Security Admission (PSA)** fully stable — replaces deprecated PodSecurityPolicy
- **ValidatingAdmissionPolicy** (GA) — CEL-based admission without webhooks
- **External JWT Signer for ServiceAccount Tokens** (Beta) — external signing service

**Kubernetes 1.35 (December 2025):**
- **Fine-grained Supplemental Groups Control** (GA) — `supplementalGroupsPolicy` field in Pod spec. Allows precise control over which supplemental groups a container gets. Prevents unintended file access via GID.
- **Dynamic Resource Allocation** (GA) — standardized GPU/hardware allocation
- **StatefulSet PVC Cleanup** — automatic PVC deletion when no longer needed
- **Memory Manager** (GA from 1.32) — NUMA-aware memory allocation

**What this means for security hardening:**
- Use PSA namespace labels (not PodSecurityPolicy — it's gone)
- Use `supplementalGroupsPolicy: Merge` or `Strict` for volume security
- ValidatingAdmissionPolicy can replace simple OPA/Kyverno rules with CEL expressions (faster, no webhook)
- ServiceAccount tokens are now short-lived by default — old long-lived tokens are a finding

**CKS exam now tests:** PSA/PSS (not PSP), SBOM generation, Cilium network policies, Kubernetes v1.34 environment."""),

        msg("What is ValidatingAdmissionPolicy and how does it compare to OPA Gatekeeper and Kyverno?",
            """**ValidatingAdmissionPolicy (VAP)** is a built-in Kubernetes admission control feature that uses CEL (Common Expression Language) — no external webhooks needed.

**Comparison:**

| Feature | VAP (built-in) | OPA Gatekeeper | Kyverno |
|---------|---------------|----------------|---------|
| Language | CEL | Rego | YAML patterns |
| External webhook | No (in-process) | Yes | Yes |
| Performance | Fastest (no network hop) | Slower (webhook call) | Slower (webhook call) |
| Complexity | Simple expressions | Complex logic possible | Medium |
| Mutation | No (validation only) | Yes (via assign) | Yes (built-in) |
| Generate resources | No | No | Yes |
| Image verification | No | No | Yes (Cosign) |

**Example — deny privileged containers with VAP:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: deny-privileged
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE", "UPDATE"]
      resources: ["pods"]
  validations:
  - expression: "!object.spec.containers.exists(c, c.securityContext.privileged == true)"
    message: "Privileged containers are not allowed"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: deny-privileged-binding
spec:
  policyName: deny-privileged
  validationActions:
  - Deny
```

**When to use each:**
- **VAP:** Simple validation rules (deny privileged, require labels, check resource limits). Fastest, no dependency.
- **OPA Gatekeeper:** Complex cross-resource logic, non-Kubernetes policies (Terraform, CI/CD). Rego is powerful but steep learning curve.
- **Kyverno:** Need mutation (auto-add labels), resource generation (auto-create NetworkPolicy), or image verification (Cosign). YAML-native, easiest for K8s teams.

**For most platform teams:** Use Kyverno for mutation/generation + VAP for simple validation. This gives you the best of both: fast built-in validation + powerful Kyverno features where needed."""),
    ]


def generate_production_failure_patterns():
    """The actual things that break in production K8s."""
    return [
        msg("What are the top 10 Kubernetes misconfigurations that cause production outages?",
            """Based on real-world incidents and industry data — 80% of Kubernetes outages are misconfigurations, not software bugs:

**1. Missing or wrong resource limits**
- No limits → one pod uses all node CPU/memory → other pods starve
- Limits too low → OOMKilled, CrashLoopBackOff
- Fix: Set requests AND limits. Use LimitRange as namespace default.

**2. Missing readiness probes**
- No readiness probe → pod gets traffic before app is ready → 502 errors
- Fix: Always set readinessProbe. Set initialDelaySeconds appropriately.

**3. Liveness probe too aggressive**
- `timeoutSeconds: 1` + `failureThreshold: 1` → one slow response kills the pod
- Fix: Generous timeouts (5-10s), failureThreshold 3+, initialDelaySeconds > app startup time

**4. Single replica Deployments**
- `replicas: 1` → pod restart = downtime
- Fix: Minimum 2 replicas + PodDisruptionBudget

**5. No PodDisruptionBudget**
- Node drain evicts all pods simultaneously → downtime during maintenance
- Fix: `minAvailable: 1` or `maxUnavailable: 1`

**6. Wrong Service selector**
- Label typo → Service has zero endpoints → connection refused
- Fix: `kubectl get endpoints` is your best friend

**7. Default-deny NetworkPolicy without DNS egress**
- Blocks all egress → pods can't resolve DNS → nothing works
- Fix: Always include UDP port 53 to kube-system in egress rules

**8. Ingress/Gateway misconfiguration**
- Wrong path, wrong port, missing TLS secret, wrong IngressClass
- Fix: Test with `curl -v` directly, check controller logs

**9. RBAC too permissive (cluster-admin everywhere)**
- Default ServiceAccount has cluster-admin → pod compromise = cluster compromise
- Fix: Dedicated ServiceAccounts with minimal verbs, `automountServiceAccountToken: false`

**10. No resource quotas per namespace**
- One team deploys 500 pods → starves other teams
- Fix: ResourceQuota per namespace, LimitRange for defaults

**The pattern:** Most outages come from MISSING things (limits, probes, PDBs, NetworkPolicy DNS rules) rather than wrong things. A good platform team makes these defaults via Kyverno generate rules or Backstage templates."""),

        msg("A team reports their app is getting OOMKilled. Walk through the diagnosis.",
            """**OOMKilled diagnosis — systematic approach:**

**Step 1: Confirm OOMKilled**
```bash
kubectl describe pod <pod> -n <ns> | grep -A3 "Last State"
# Look for: Reason: OOMKilled, Exit Code: 137

kubectl get events -n <ns> --field-selector reason=OOMKilled
```

**Step 2: Check current limits vs actual usage**
```bash
# What are the limits?
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[0].resources}'

# What is actual usage?
kubectl top pod <pod> -n <ns>

# Or with metrics-server:
kubectl top pods -n <ns> --sort-by=memory
```

**Step 3: Determine the cause**

| Scenario | Evidence | Fix |
|----------|----------|-----|
| Limit too low for normal operation | Usage consistently near limit | Increase limits.memory |
| Memory leak in application | Usage grows steadily over time | Fix the app, not the limit |
| JVM not respecting container limits | JVM allocates based on node memory | Set `-Xmx` to ~75% of limit |
| Sidecar memory not accounted for | Istio sidecar uses 128Mi+ | Include sidecar in limit calculation |

**Step 4: Fix**
```yaml
resources:
  requests:
    memory: 256Mi   # What the scheduler reserves
  limits:
    memory: 512Mi   # Hard OOM kill threshold
```

**Rules of thumb:**
- `requests` = what your app normally uses (p95)
- `limits` = 1.5-2x requests (headroom for spikes)
- Never set limits without requests (creates BestEffort QoS → evicted first)
- For JVMs: set `-Xmx` to 75% of limit, leave 25% for non-heap

**QoS classes matter for eviction order:**
- Guaranteed (requests == limits) → evicted last
- Burstable (requests < limits) → evicted second
- BestEffort (no requests/limits) → evicted first under pressure

**Rank:** D — deterministic fix (adjust resource limits). Check ArgoCD ownership before patching."""),
    ]


def generate_operational_eval_benchmark():
    """Eval questions that test Katie's ACTUAL job — triage, routing, ownership, dedup."""
    questions = []

    # Triage questions
    triage = [
        {"id": "ops-triage-001", "category": "operational", "subcategory": "triage", "rank": "D",
         "question": "Kubescape finding C-0013: container running as root on Deployment/web-app in namespace 'portfolio'. The Deployment has label app.kubernetes.io/instance=portfolio. What rank, what action?",
         "expected_keywords": ["B-rank", "ArgoCD", "git", "push", "Helm", "never kubectl", "securityContext", "runAsNonRoot"],
         "expected_fix_contains": "git",
         "grading": {"keywords_required": 4, "fix_required": True, "workflow_required": False}},

        {"id": "ops-triage-002", "category": "operational", "subcategory": "triage", "rank": "E",
         "question": "Gatekeeper audit shows a pod in namespace 'monitoring' violating the require-nonroot constraint. The monitoring namespace has no app.kubernetes.io/instance label. What rank, what action?",
         "expected_keywords": ["D-rank", "E-rank", "kubectl", "not ArgoCD", "patch", "securityContext", "runAsNonRoot"],
         "expected_fix_contains": "kubectl",
         "grading": {"keywords_required": 3, "fix_required": True, "workflow_required": False}},

        {"id": "ops-triage-003", "category": "operational", "subcategory": "triage", "rank": "C",
         "question": "Trivy found CVE-2025-1974 (CVSS 9.8) in the ingress-nginx-controller. Classify and route.",
         "expected_keywords": ["S-rank", "critical", "human", "immediate", "RCE", "patch", "upgrade", "secrets"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},

        {"id": "ops-triage-004", "category": "operational", "subcategory": "triage", "rank": "D",
         "question": "Bandit found B102 (use of exec) in a Python file in the client repo. Rank and route.",
         "expected_keywords": ["E-rank", "deterministic", "auto-fix", "sast", "ast.literal_eval"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 3, "fix_required": False, "workflow_required": False}},

        {"id": "ops-triage-005", "category": "operational", "subcategory": "triage", "rank": "C",
         "question": "Gitleaks found an AWS access key committed to a client repository. Rank and route.",
         "expected_keywords": ["S-rank", "human", "revoke", "rotate", "git history", "immediate", "credential"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},
    ]

    # Ownership questions
    ownership = [
        {"id": "ops-own-001", "category": "operational", "subcategory": "ownership", "rank": "D",
         "question": "How do you check if a Kubernetes Deployment is managed by ArgoCD before applying a security fix?",
         "expected_keywords": ["app.kubernetes.io/instance", "jsonpath", "kubectl get", "ArgoCD", "git", "label"],
         "expected_fix_contains": "jsonpath",
         "grading": {"keywords_required": 4, "fix_required": True, "workflow_required": False}},

        {"id": "ops-own-002", "category": "operational", "subcategory": "ownership", "rank": "C",
         "question": "You kubectl patched a Deployment to add securityContext but the changes keep reverting. What's happening and how do you fix it correctly?",
         "expected_keywords": ["ArgoCD", "drift", "revert", "sync", "git", "Helm", "never kubectl patch"],
         "expected_fix_contains": "git",
         "grading": {"keywords_required": 4, "fix_required": True, "workflow_required": False}},

        {"id": "ops-own-003", "category": "operational", "subcategory": "ownership", "rank": "D",
         "question": "Which resources are typically safe to fix with kubectl without worrying about GitOps drift?",
         "expected_keywords": ["Gatekeeper", "ClusterRoleBinding", "LimitRange", "ResourceQuota", "NetworkPolicy", "not ArgoCD"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},
    ]

    # Dedup questions
    dedup = [
        {"id": "ops-dedup-001", "category": "operational", "subcategory": "dedup", "rank": "D",
         "question": "Kubescape C-0013, Polaris run-as-root, and Checkov CKV_K8S_6 all flagged the same Deployment for 'container running as root'. How many fixes do you create?",
         "expected_keywords": ["one fix", "deduplicate", "same resource", "same finding", "fingerprint"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 3, "fix_required": False, "workflow_required": False}},

        {"id": "ops-dedup-002", "category": "operational", "subcategory": "dedup", "rank": "C",
         "question": "A scan returns 50 findings. 30 are on ArgoCD-managed Deployments and 20 are on Gatekeeper constraints. How do you batch the remediation?",
         "expected_keywords": ["split", "ArgoCD", "git", "kubectl", "group", "ownership", "B-rank", "D-rank"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},
    ]

    # Troubleshooting routing
    troubleshoot = [
        {"id": "ops-ts-001", "category": "operational", "subcategory": "troubleshooting", "rank": "D",
         "question": "A pod can't connect to another pod via its Service name. What do you check first?",
         "expected_keywords": ["DNS", "nslookup", "endpoints", "selector", "NetworkPolicy", "CoreDNS"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},

        {"id": "ops-ts-002", "category": "operational", "subcategory": "troubleshooting", "rank": "D",
         "question": "A pod is OOMKilled with exit code 137. What is the most likely cause and fix?",
         "expected_keywords": ["memory limit", "exceeded", "limits.memory", "increase", "resources", "OOM"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 3, "fix_required": False, "workflow_required": False}},

        {"id": "ops-ts-003", "category": "operational", "subcategory": "troubleshooting", "rank": "C",
         "question": "After applying a default-deny NetworkPolicy, all pods in the namespace lost DNS resolution. Why?",
         "expected_keywords": ["egress", "DNS", "port 53", "UDP", "kube-system", "CoreDNS", "NetworkPolicy"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},

        {"id": "ops-ts-004", "category": "operational", "subcategory": "troubleshooting", "rank": "D",
         "question": "A Service has no endpoints. What are the most likely causes?",
         "expected_keywords": ["selector", "labels", "mismatch", "readiness probe", "not Ready", "endpoints"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 3, "fix_required": False, "workflow_required": False}},

        {"id": "ops-ts-005", "category": "operational", "subcategory": "troubleshooting", "rank": "C",
         "question": "Pods are stuck in Pending after a node was drained. What should you check?",
         "expected_keywords": ["Insufficient", "cpu", "memory", "taint", "uncordon", "describe pod", "scheduler"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},
    ]

    # Recent K8s knowledge
    recent = [
        {"id": "ops-recent-001", "category": "operational", "subcategory": "recent-changes", "rank": "C",
         "question": "Ingress-NGINX is being retired in March 2026. What is the recommended migration path?",
         "expected_keywords": ["Gateway API", "HTTPRoute", "Gateway", "ingress2gateway", "retire", "controller"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},

        {"id": "ops-recent-002", "category": "operational", "subcategory": "recent-changes", "rank": "C",
         "question": "What is ValidatingAdmissionPolicy and when should you use it instead of OPA Gatekeeper or Kyverno?",
         "expected_keywords": ["CEL", "built-in", "no webhook", "faster", "validation", "Kubernetes native"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 3, "fix_required": False, "workflow_required": False}},

        {"id": "ops-recent-003", "category": "operational", "subcategory": "recent-changes", "rank": "D",
         "question": "PodSecurityPolicy was removed. What replaced it and how do you enforce it?",
         "expected_keywords": ["Pod Security Admission", "PSA", "Pod Security Standards", "restricted", "baseline", "namespace label", "enforce"],
         "expected_fix_contains": None,
         "grading": {"keywords_required": 4, "fix_required": False, "workflow_required": False}},
    ]

    questions.extend(triage)
    questions.extend(ownership)
    questions.extend(dedup)
    questions.extend(troubleshoot)
    questions.extend(recent)
    return questions


def main():
    # === Training Data ===
    all_training = []

    print("=== Training Data ===")
    sections = [
        ("Recent CVEs (2025)", generate_recent_cves),
        ("Gateway API migration", generate_gateway_api),
        ("K8s 1.32-1.35 features", generate_k8s_recent_features),
        ("Production failure patterns", generate_production_failure_patterns),
    ]

    for name, func in sections:
        examples = func()
        print(f"  {name}: {len(examples)}")
        all_training.extend(examples)

    random.shuffle(all_training)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "realworld_2025_2026.jsonl", "w") as f:
        for ex in all_training:
            f.write(json.dumps(ex) + "\n")
    print(f"  Total training: {len(all_training)} → realworld_2025_2026.jsonl")

    # === Operational Eval Benchmark ===
    print("\n=== Operational Eval Benchmark ===")
    questions = generate_operational_eval_benchmark()
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    eval_file = EVAL_DIR / "operational-triage-questions.jsonl"
    with open(eval_file, "w") as f:
        for q in questions:
            f.write(json.dumps(q) + "\n")
    print(f"  {len(questions)} eval questions → {eval_file.name}")

    # Subcategory breakdown
    subcats = {}
    for q in questions:
        sub = q.get("subcategory", "other")
        subcats[sub] = subcats.get(sub, 0) + 1
    for sub, count in sorted(subcats.items()):
        print(f"    {sub}: {count}")


if __name__ == "__main__":
    main()
