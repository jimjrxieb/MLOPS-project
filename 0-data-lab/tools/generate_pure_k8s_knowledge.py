#!/usr/bin/env python3
"""
Pure Kubernetes & Platform Knowledge Generator
================================================
Deep understanding of HOW Kubernetes works so Katie develops
the right mental model for troubleshooting and security.

"Pod can't reach another pod" → think: NetworkPolicy, CNI, DNS, Service selector, Endpoints
NOT: storage, nodePort, ingress

Categories:
1. Kubernetes networking (Services, DNS, CNI, pod-to-pod, Ingress)
2. Kubernetes scheduling (how pods get placed, why they don't)
3. Kubernetes storage (PV lifecycle, CSI, what goes wrong)
4. OPA / Policy-as-Code (how Rego works, why policies exist)
5. Backstage / IDP (what platform engineering actually means)
6. Troubleshooting mental models (symptom → most likely cause)
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "pure_k8s_knowledge.jsonl"

SYSTEM = "You are JADE, a Kubernetes platform engineer who teaches by building mental models. When someone describes a symptom, you reason through the most likely causes in order. You understand how Kubernetes components interact and can trace a problem from symptom to root cause."


def msg(user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}


def k8s_networking():
    return [
        msg("How does pod-to-pod communication actually work in Kubernetes?",
            """Every pod gets its own IP address. Pod-to-pod communication uses the cluster network (overlay or direct routing), not NAT.

**The flow — Pod A (10.244.1.5) talks to Pod B (10.244.2.8):**
```
Pod A (10.244.1.5) on Node 1
  ↓ sends packet to 10.244.2.8
  ↓
Node 1 kernel routing table
  ↓ "10.244.2.0/24 → via Node 2"
  ↓ (CNI plugin configured this route)
  ↓
[VXLAN tunnel / BGP route / direct route] ← depends on CNI
  ↓
Node 2 kernel
  ↓ routes to Pod B's veth interface
  ↓
Pod B (10.244.2.8) on Node 2
```

**Three CNI networking models:**

| CNI | How it works | Performance |
|-----|-------------|-------------|
| **Flannel** | VXLAN overlay (encapsulates in UDP) | Slowest, simple |
| **Calico** | BGP routing (native L3, no encapsulation) | Fast, supports NetworkPolicy |
| **Cilium** | eBPF (kernel-level packet processing) | Fastest, rich NetworkPolicy + L7 |

**Key rule:** Kubernetes requires that every pod can reach every other pod without NAT. This is the "flat network" model. NetworkPolicy is the ONLY way to restrict this — without it, all pods can talk to all pods.

**When pod-to-pod fails, check in this order:**
1. **NetworkPolicy** — is there a default-deny blocking traffic?
2. **CNI health** — are the CNI pods running? (`kubectl get pods -n kube-system -l k8s-app=calico-node`)
3. **Pod IPs** — do both pods have IPs? (`kubectl get pods -o wide`)
4. **Node routing** — can nodes reach each other? (SSH to node, `ping <other-node-ip>`)
5. **DNS** — if using Service names, is CoreDNS healthy?

**NOT the cause of pod-to-pod issues:** Storage, Ingress, NodePort, LoadBalancer. These are completely separate systems."""),

        msg("How do Kubernetes Services work? What actually happens when a pod connects to a Service?",
            """A Service is a stable IP (ClusterIP) that load-balances to a set of pods. It's implemented by kube-proxy using iptables or IPVS on every node.

**What happens step by step:**

```
1. You create a Service with selector: app=web
2. Kubernetes creates Endpoints — list of pod IPs matching the selector
3. kube-proxy on EVERY node creates iptables DNAT rules:
   "traffic to ClusterIP:port → random backend pod IP:targetPort"
4. Pod connects to ClusterIP → iptables intercepts → DNAT to a backend pod
```

**Service types (from simple to complex):**

| Type | What it does | Access from |
|------|-------------|-------------|
| **ClusterIP** | Internal-only virtual IP | Inside cluster only |
| **NodePort** | ClusterIP + opens a port (30000-32767) on every node | External via `<node-ip>:<nodeport>` |
| **LoadBalancer** | NodePort + provisions cloud LB (ELB, NLB) | External via LB IP/DNS |
| **ExternalName** | DNS alias (CNAME) to external service | Inside cluster only |

**How endpoints connect Services to pods:**
```bash
# Service selects pods with label app=web
kubectl get endpoints web-service
# NAME          ENDPOINTS
# web-service   10.244.1.5:8080, 10.244.2.8:8080, 10.244.3.3:8080
```

**When a Service has no endpoints (traffic goes nowhere):**
1. Selector doesn't match any pod labels (typo in label)
2. Pods exist but are NOT Ready (readiness probe failing)
3. Pods are in a different namespace than expected
4. Pods haven't started yet

**Debugging:**
```bash
kubectl get endpoints <service> -n <ns>       # Empty = no matching pods
kubectl get pods -n <ns> --show-labels        # Check labels match selector
kubectl describe service <service> -n <ns>    # Check selector and ports
```

**headless Service (clusterIP: None):**
- No ClusterIP, no iptables rules, no load balancing
- DNS returns individual pod IPs (A records)
- Used by StatefulSets where each pod needs a stable DNS name
- `pod-0.my-headless.namespace.svc.cluster.local` → specific pod IP"""),

        msg("A pod can't reach another pod via its Service name. Walk through the troubleshooting.",
            """**Systematic troubleshooting — most likely causes in order:**

**1. DNS resolution (most common)**
```bash
# From the source pod, test DNS
kubectl exec <source-pod> -n <ns> -- nslookup <service-name>
kubectl exec <source-pod> -n <ns> -- nslookup <service-name>.<target-ns>.svc.cluster.local
```
- If DNS fails → CoreDNS issue. Check: `kubectl get pods -n kube-system -l k8s-app=kube-dns`
- If DNS returns an IP → move to step 2

**2. Service has endpoints?**
```bash
kubectl get endpoints <service-name> -n <target-ns>
```
- Empty endpoints → labels don't match OR pods aren't Ready
- Check: `kubectl get service <name> -n <ns> -o jsonpath='{.spec.selector}'`
- Compare: `kubectl get pods -n <ns> --show-labels`

**3. Port mismatch?**
```bash
kubectl get service <name> -n <ns> -o jsonpath='{.spec.ports[*]}'
```
- Service `port` is what you connect TO
- `targetPort` is what the pod listens ON
- If targetPort=8080 but app listens on 3000, traffic hits a closed port

**4. NetworkPolicy blocking?**
```bash
kubectl get networkpolicy -n <target-ns>
kubectl describe networkpolicy -n <target-ns>
```
- Default-deny ingress without an allow rule for the source namespace
- Missing egress rule on the source pod's namespace
- **Most commonly missed:** default-deny egress blocks DNS (port 53 UDP)

**5. Pod readiness probe failing?**
```bash
kubectl describe pod <target-pod> -n <ns> | grep -A5 Readiness
kubectl get endpoints <service> -n <ns>
```
- Pod is Running but NOT Ready → not in Service endpoints → no traffic routed to it
- Fix the readiness probe or check why the app isn't responding

**6. Network-level (rare, usually CNI issue)**
```bash
# Test direct pod IP (bypass Service/DNS)
kubectl exec <source-pod> -- wget -qO- http://<target-pod-ip>:<port> --timeout=3
```
- If direct pod IP works but Service doesn't → kube-proxy/iptables issue
- If direct pod IP also fails → CNI issue, node routing, or firewall

**Order matters:** DNS → Endpoints → Ports → NetworkPolicy → Readiness → Network
NOT: Storage, Ingress, NodePort, PVC, StatefulSet (these are unrelated to pod-to-pod)"""),

        msg("What is an Ingress and how does it differ from a Service?",
            """An Ingress is an L7 (HTTP/HTTPS) routing rule. A Service is an L4 (TCP/UDP) load balancer. They solve different problems:

**Service (L4):** "Route TCP traffic on port 80 to these pods"
**Ingress (L7):** "Route HTTP requests for api.example.com/users to Service A, and api.example.com/products to Service B"

**How they work together:**
```
External client
  ↓ HTTPS request: api.example.com/users
  ↓
Ingress Controller (nginx, traefik, ALB) ← reads Ingress resources
  ↓ TLS termination, path matching
  ↓ Forwards to correct Service based on rules
  ↓
Service (ClusterIP)
  ↓ iptables DNAT to backend pod
  ↓
Pod
```

**Ingress resource:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls-cert
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /users
        pathType: Prefix
        backend:
          service:
            name: users-service
            port:
              number: 80
      - path: /products
        pathType: Prefix
        backend:
          service:
            name: products-service
            port:
              number: 80
```

**Key concepts:**
- **Ingress Controller** — the actual reverse proxy (nginx, traefik, AWS ALB). Must be installed separately. The Ingress resource is just config.
- **TLS termination** — Ingress decrypts HTTPS, forwards HTTP to backend Services
- **cert-manager** — automates TLS certificate provisioning from Let's Encrypt
- **IngressClass** — which controller handles this Ingress (important when multiple controllers exist)

**When to use what:**
- Internal pod-to-pod → Service (ClusterIP)
- External HTTP/HTTPS → Ingress + Service
- External non-HTTP (databases, gRPC) → Service (LoadBalancer or NodePort)
- Service mesh → VirtualService (Istio) replaces Ingress for advanced routing"""),
    ]


def k8s_scheduling():
    return [
        msg("How does the Kubernetes scheduler decide where to place a pod?",
            """The kube-scheduler watches for unscheduled pods and assigns them to nodes. It uses a two-phase process:

**Phase 1: Filtering (which nodes CAN run this pod?)**
```
All nodes
  ↓ Filter: Does the node have enough CPU/memory for requests?
  ↓ Filter: Does the node match nodeSelector labels?
  ↓ Filter: Does the node satisfy nodeAffinity rules?
  ↓ Filter: Does the node have taints that the pod doesn't tolerate?
  ↓ Filter: Does the node have available ports the pod needs?
  ↓ Filter: Is the node unschedulable (cordoned)?
Result: List of feasible nodes
```

**Phase 2: Scoring (which node is BEST?)**
```
Feasible nodes
  ↓ Score: Spread pods across nodes (anti-affinity)
  ↓ Score: Prefer nodes with image already cached
  ↓ Score: Balance resource usage across nodes
  ↓ Score: Honor preferredDuringScheduling affinity
Result: Highest-scoring node wins
```

**When a pod is stuck in Pending:**

| kubectl describe output | Cause | Fix |
|------------------------|-------|-----|
| "Insufficient cpu" | No node has enough free CPU | Add nodes or reduce requests |
| "Insufficient memory" | No node has enough free memory | Add nodes or reduce requests |
| "didn't match node selector" | nodeSelector label doesn't exist on any node | Label a node or fix selector |
| "node(s) had taint that the pod didn't tolerate" | Node has a taint, pod lacks toleration | Add toleration or remove taint |
| "unschedulable" | Node is cordoned (`kubectl cordon`) | `kubectl uncordon <node>` |
| "no PersistentVolume found" | PVC can't bind (wrong StorageClass, no capacity) | Create PV or fix StorageClass |

**Taints and tolerations:**
- Taint on node = "repel pods unless they tolerate me"
- Toleration on pod = "I'm ok running on a tainted node"
```bash
# Taint a node (only GPU workloads allowed)
kubectl taint nodes gpu-node-1 gpu=true:NoSchedule

# Pod must have this toleration to schedule there
tolerations:
- key: "gpu"
  operator: "Equal"
  value: "true"
  effect: "NoSchedule"
```

**Node affinity:**
- `requiredDuringSchedulingIgnoredDuringExecution` — hard requirement (MUST match)
- `preferredDuringSchedulingIgnoredDuringExecution` — soft preference (TRY to match)"""),
    ]


def opa_policy_knowledge():
    return [
        msg("What is OPA (Open Policy Agent) and how does policy-as-code work?",
            """OPA is a general-purpose policy engine that decouples policy decisions from application logic. You write policies in Rego (a declarative query language), and OPA evaluates them against structured data.

**The concept:**
```
Input (JSON)     →  OPA  →  Decision (allow/deny + reasons)
                    ↑
               Policy (Rego)
```

**Why policy-as-code matters:**
- Policies are version-controlled in git (auditable, reviewable)
- Same policy language for Kubernetes, Terraform, CI/CD, APIs
- Automated enforcement (not "please follow the wiki page")
- Testable (unit tests for policies, just like application code)

**How Rego works:**
```rego
package kubernetes.admission

# Deny pods without resource limits
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits
    msg := sprintf("Container '%s' must have resource limits", [container.name])
}

# Deny privileged containers
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("Container '%s' must not be privileged", [container.name])
}
```

**How it's used in Kubernetes:**

1. **OPA Gatekeeper** — Kubernetes admission controller
   - Intercepts API requests (pod create, deployment update)
   - Evaluates Rego policies against the request
   - Blocks requests that violate policies
   - ConstraintTemplate (policy logic) + Constraint (where to apply)

2. **Conftest** — CI/CD policy checking
   - `conftest test deployment.yaml --policy policies/`
   - Catches violations before they reach the cluster
   - Runs in GitHub Actions, GitLab CI, etc.

3. **Terraform policy** — Infrastructure validation
   - `conftest test tfplan.json --policy terraform-policies/`
   - Blocks insecure Terraform plans (public S3, wide security groups)

**OPA vs Kyverno:**
- OPA/Gatekeeper: Rego language (powerful but steep learning curve)
- Kyverno: YAML-native (easier for K8s teams, less flexible for non-K8s)
- Both are valid admission controllers
- Choose based on team skills and whether you need non-K8s policies"""),

        msg("Write and explain a Rego policy that denies containers running as root.",
            """```rego
package kubernetes.admission

# Deny containers that run as root (UID 0)
deny[msg] {
    # Match Pod creation/update requests
    input.request.kind.kind == "Pod"

    # Iterate over all containers in the pod spec
    container := input.request.object.spec.containers[_]

    # Check if runAsNonRoot is not set or set to false
    not container_is_nonroot(container)

    # Build the denial message
    msg := sprintf(
        "Container '%s' must set securityContext.runAsNonRoot to true. Running as root is not allowed.",
        [container.name]
    )
}

# Helper: check if container has runAsNonRoot: true
container_is_nonroot(container) {
    container.securityContext.runAsNonRoot == true
}

# Also check pod-level securityContext
container_is_nonroot(container) {
    input.request.object.spec.securityContext.runAsNonRoot == true
}
```

**How Rego works line by line:**

1. `package kubernetes.admission` — namespace for the policy
2. `deny[msg]` — a rule that produces denial messages. If ANY `deny` rule evaluates to true, the request is blocked.
3. `input.request.kind.kind == "Pod"` — only apply to Pod requests
4. `container := input.request.object.spec.containers[_]` — iterate over ALL containers (the `[_]` means "for each")
5. `not container_is_nonroot(container)` — if the helper returns false, this condition is true → deny
6. `sprintf(...)` — format the error message with the container name

**Key Rego concepts:**
- Rules are AND'd within a block (all conditions must be true)
- `[_]` iterates over arrays (like a for-each)
- `not` negates a rule
- Helper functions factor out reusable logic
- Multiple rule bodies for the same name are OR'd (either can satisfy)

**Testing the policy:**
```bash
# Test with conftest
conftest test pod.yaml --policy policies/

# Output:
# FAIL - pod.yaml - Container 'web' must set securityContext.runAsNonRoot to true
```

**Deploy as Gatekeeper constraint:**
```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequirenonroot
spec:
  crd:
    spec:
      names:
        kind: K8sRequireNonRoot
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8srequirenonroot
      violation[{"msg": msg}] {
        container := input.review.object.spec.containers[_]
        not container.securityContext.runAsNonRoot
        msg := sprintf("Container %s must run as non-root", [container.name])
      }
```"""),
    ]


def idp_backstage_knowledge():
    return [
        msg("What is Backstage and why do platform teams use it as an Internal Developer Portal?",
            """Backstage is an open-source developer portal created by Spotify. It provides a single pane of glass for developers to discover services, documentation, and infrastructure.

**What Backstage does:**

```
Developer opens Backstage portal
  ├── Software Catalog → "What services exist? Who owns them?"
  ├── Templates → "Create a new microservice from a golden template"
  ├── TechDocs → "Read the API documentation"
  ├── Kubernetes tab → "See my pods, deployments, logs"
  ├── CI/CD tab → "See pipeline status, last deployment"
  └── Cost tab → "How much does my service cost?"
```

**Core components:**

1. **Software Catalog** — registry of all services, libraries, APIs
```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: payment-service
  description: Payment processing API
  annotations:
    backstage.io/techdocs-ref: dir:.
    github.com/project-slug: myorg/payment-service
    backstage.io/kubernetes-label-selector: app=payment-service
spec:
  type: service
  lifecycle: production
  owner: team-payments
  providesApis:
    - payment-api
```

2. **Software Templates** — self-service scaffolding
   - Developer clicks "Create new service"
   - Template creates: repo, CI pipeline, Dockerfile, Helm chart, Kubernetes manifests, monitoring dashboards
   - All pre-configured with security guardrails
   - This IS the golden path

3. **TechDocs** — documentation as code (Markdown in the repo, rendered in Backstage)

4. **Plugins** — extensible via plugin architecture
   - Kubernetes plugin shows pod/deployment status
   - GitHub Actions plugin shows CI/CD status
   - Cost plugin shows cloud spend per service

**Why platform teams use it:**
- **Service discovery:** "Who owns the auth service?" → Backstage catalog
- **Self-service:** Developers create services without filing tickets
- **Consistency:** Every new service starts from an approved template
- **Guardrails baked in:** Templates include securityContext, resource limits, NetworkPolicy by default

**The platform engineering pattern:**
```
Platform team creates:
  1. Backstage templates (golden paths)
  2. Kyverno/OPA policies (guardrails)
  3. Crossplane XRDs (infrastructure self-service)
  4. Monitoring dashboards (observability)

Developers get:
  1. Self-service portal (Backstage)
  2. Pre-approved secure defaults (no security expertise needed)
  3. Infrastructure as code (no cloud console access needed)
  4. Visibility into their services (one place for everything)
```

**The key insight:** Backstage is the UI layer of an Internal Developer Platform. Behind it sits Kubernetes, ArgoCD, Crossplane, Kyverno — but developers only see the portal. The platform team makes the secure path the easy path."""),

        msg("What does a platform engineering team actually build and maintain?",
            """A platform engineering team builds the Internal Developer Platform (IDP) — the tooling, guardrails, and automation that lets developers ship securely without needing to be infrastructure experts.

**What the team builds:**

**1. Golden paths (standardized templates)**
- Backstage software templates for each service type
- Pre-configured: Dockerfile (multi-stage, non-root), Helm chart (securityContext, resource limits), CI pipeline (SAST, image scan, sign)
- Developers choose a template → get a production-ready service in minutes

**2. Kubernetes platform layer**
- Namespace provisioning with RBAC, NetworkPolicy, ResourceQuota, LimitRange auto-applied
- Kyverno or OPA Gatekeeper policies as admission controllers
- Pod Security Standards enforcement per namespace
- Cert-manager for automatic TLS certificates

**3. GitOps delivery**
- ArgoCD or Flux for continuous deployment
- Every change goes through git → reviewed → merged → auto-deployed
- No `kubectl apply` in production (ArgoCD manages everything)
- Promotion pipeline: dev → staging → production

**4. Observability stack**
- Prometheus + Grafana for metrics (per-team dashboards)
- Loki for centralized logging
- Jaeger or Tempo for distributed tracing
- OpenTelemetry auto-instrumentation (injected via webhook, no code changes)
- Alerting rules that route to the owning team

**5. Infrastructure self-service**
- Crossplane XRDs for databases, caches, message queues
- Developers create a `Database` claim → Crossplane provisions RDS
- No AWS console access, no Terraform knowledge needed
- Same `kubectl apply` workflow as application deployments

**6. Security guardrails**
- Image signing (Cosign) + verification (Kyverno)
- Vulnerability scanning in CI (Trivy) + admission (image policy)
- Falco for runtime threat detection
- Network policies generated per namespace

**7. Developer experience (DevEx)**
- Backstage portal (catalog, templates, docs, status)
- CLI tools for common operations
- Runbooks in the same repo as the code
- Slack/Teams integration for alerts and approvals

**What the team does NOT do:**
- Write application code (developers do that)
- Deploy individual services (ArgoCD does that)
- Approve every change (policies enforce automatically)
- Manually configure infrastructure (Crossplane/Terraform does that)

**The team's north star:** Make the secure, compliant, observable path THE DEFAULT. If developers have to opt-out of security instead of opt-in, you've won."""),
    ]


def troubleshooting_mental_models():
    return [
        msg("A pod can't connect to another pod. What's your troubleshooting mental model?",
            """**Pod-to-pod connectivity — check in this order:**

```
SYMPTOM: Pod A can't reach Pod B
  │
  ├── 1. Can Pod A resolve Pod B's name?
  │   └── kubectl exec pod-a -- nslookup service-b
  │       ├── FAIL → CoreDNS issue (check kube-dns pods)
  │       └── OK → got an IP, move to step 2
  │
  ├── 2. Does the Service have endpoints?
  │   └── kubectl get endpoints service-b
  │       ├── EMPTY → selector doesn't match pods, or pods not Ready
  │       │   ├── Check labels: kubectl get pods --show-labels
  │       │   └── Check readiness: kubectl describe pod <pod-b>
  │       └── HAS IPs → move to step 3
  │
  ├── 3. Is a NetworkPolicy blocking traffic?
  │   └── kubectl get networkpolicy -n <namespace>
  │       ├── DEFAULT DENY exists without matching allow rule
  │       │   ├── Missing ingress rule for source namespace/pod
  │       │   └── Missing egress DNS rule (port 53/UDP)
  │       └── No NetworkPolicy → move to step 4
  │
  ├── 4. Is the port correct?
  │   └── Service port vs targetPort vs what the app listens on
  │       ├── Service port=80, targetPort=8080, app listens on 3000 → MISMATCH
  │       └── All match → move to step 5
  │
  ├── 5. Can Pod A reach Pod B by IP directly?
  │   └── kubectl exec pod-a -- wget -qO- http://<pod-b-ip>:<port> --timeout=3
  │       ├── WORKS → Service/DNS issue (kube-proxy, iptables)
  │       └── FAILS → CNI or node networking issue
  │           ├── Are CNI pods healthy? (calico-node, cilium)
  │           └── Can nodes reach each other? (ping between nodes)
  │
  └── NOT the cause: PVC, StorageClass, Ingress, NodePort, HPA
```

**The key insight:** Pod-to-pod is a NETWORKING problem. Storage, ingress, and scaling are completely separate subsystems. If Katie is asked about pod connectivity, she should think DNS → Endpoints → NetworkPolicy → Ports → CNI. Never storage."""),

        msg("A Deployment's pods keep restarting. What's your troubleshooting mental model?",
            """**Pod restart / CrashLoopBackOff — check in this order:**

```
SYMPTOM: Pod keeps restarting (CrashLoopBackOff)
  │
  ├── 1. What's the exit code?
  │   └── kubectl describe pod <pod> | grep "Exit Code"
  │       ├── Exit 0 → app completed successfully but restartPolicy=Always restarts it
  │       ├── Exit 1 → application error (bad config, missing env var, crash)
  │       ├── Exit 137 → OOMKilled (memory limit exceeded)
  │       └── Exit 139 → SIGSEGV (segfault in application)
  │
  ├── 2. Check logs (including previous container)
  │   └── kubectl logs <pod> --previous
  │       ├── Application error messages → fix the app
  │       ├── "Permission denied" → running as non-root but app needs write access
  │       │   └── Add emptyDir for writable paths, check fsGroup
  │       └── No logs (container dies immediately) → check command/entrypoint
  │
  ├── 3. Is it OOMKilled?
  │   └── kubectl describe pod <pod> | grep OOMKilled
  │       ├── YES → memory limit too low. Increase limits.memory
  │       └── NO → move to step 4
  │
  ├── 4. Is the readiness/liveness probe killing it?
  │   └── kubectl describe pod <pod> | grep -A5 "Liveness\|Readiness"
  │       ├── Liveness probe failing → kills and restarts the container
  │       │   ├── initialDelaySeconds too short (app not ready yet)
  │       │   ├── Wrong port or path
  │       │   └── App genuinely unhealthy
  │       └── Probes passing → move to step 5
  │
  ├── 5. Is it a securityContext issue?
  │   └── readOnlyRootFilesystem: true but app tries to write to /var/cache
  │       ├── Add emptyDir volume for writable paths
  │       └── Check if app needs specific UID/GID (runAsUser/fsGroup mismatch)
  │
  └── NOT the cause: NetworkPolicy, Ingress, Service, HPA, DNS
```

**The key insight:** CrashLoopBackOff is an APPLICATION problem (exit code, memory, config). Not a networking or scheduling problem. Check logs first, exit code second, resources third."""),

        msg("A pod is stuck in Pending. What's your troubleshooting mental model?",
            """**Pod Pending — check in this order:**

```
SYMPTOM: Pod stuck in Pending
  │
  ├── 1. kubectl describe pod <pod> — look at Events
  │   └── The Events section tells you WHY it's pending
  │
  ├── 2. "Insufficient cpu" or "Insufficient memory"
  │   └── No node has enough free resources for pod's requests
  │       ├── requests.cpu or requests.memory too high
  │       ├── Other pods consuming all node capacity
  │       ├── Fix: add nodes, reduce requests, or evict low-priority pods
  │       └── Check: kubectl describe nodes | grep -A5 "Allocated resources"
  │
  ├── 3. "didn't match node selector"
  │   └── Pod has nodeSelector but no node has that label
  │       ├── kubectl get nodes --show-labels
  │       └── kubectl label node <node> <key>=<value>
  │
  ├── 4. "had taint that the pod didn't tolerate"
  │   └── Node has a taint, pod doesn't have matching toleration
  │       ├── kubectl describe node <node> | grep Taint
  │       └── Add toleration to pod spec, or remove taint from node
  │
  ├── 5. "unschedulable"
  │   └── Node is cordoned
  │       └── kubectl uncordon <node>
  │
  ├── 6. "no persistent volumes available" / "waiting for volume"
  │   └── PVC can't bind to a PV
  │       ├── No PV with matching storageClassName and accessMode
  │       ├── StorageClass provisioner isn't creating PVs (CSI driver issue)
  │       ├── PV exists but is already Bound to another PVC
  │       └── Check: kubectl get pv,pvc -A
  │
  └── NOT the cause: NetworkPolicy, DNS, Service endpoints, liveness probes
```

**The key insight:** Pending is a SCHEDULING problem. The pod hasn't started yet — networking, probes, and DNS don't apply. Read the Events from `kubectl describe pod` — Kubernetes tells you exactly why it's pending."""),
    ]


def main():
    all_examples = []

    sections = [
        ("Kubernetes networking", k8s_networking),
        ("Kubernetes scheduling", k8s_scheduling),
        ("OPA / Policy-as-Code", opa_policy_knowledge),
        ("Backstage / IDP", idp_backstage_knowledge),
        ("Troubleshooting mental models", troubleshooting_mental_models),
    ]

    for name, gen_func in sections:
        examples = gen_func()
        print(f"  {name}: {len(examples)}")
        all_examples.extend(examples)

    random.shuffle(all_examples)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nTotal: {len(all_examples)} pure Kubernetes/platform knowledge examples")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
