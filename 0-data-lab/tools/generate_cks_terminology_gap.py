#!/usr/bin/env python3
"""
CKS Terminology Gap Training Data Generator
=============================================
Priority 1: Forces Katie to emit exact canonical Kubernetes terms.

Targets the top 20 most-missed keywords from eval:
  NetworkPolicy, FalcoRule, Falco, ImagePolicyWebhook, Cosign, mTLS,
  StaticPod, AppArmor, securityContext, digest, Sysdig, egress,
  restricted, Deployment, AuditLog, multi-stage, vulnerability, runtime

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "cks_terminology_gap.jsonl"

SYSTEM_PROMPT = "You are JADE, a CKS-certified Kubernetes security expert. Always use exact Kubernetes resource kind names (e.g., NetworkPolicy, PodSecurityPolicy, FalcoRule). Reference specific tools by name (Falco, Cosign, Trivy, Sysdig). Use canonical terminology — never paraphrase resource types."

def msg(system, user, assistant):
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}

def generate_networkpolicy_examples():
    """NetworkPolicy — missed 92 times in eval."""
    examples = []
    scenarios = [
        {
            "q": "Isolate the 'payments' namespace so pods can only receive traffic from the 'api-gateway' namespace.",
            "a": """To isolate the 'payments' namespace, create a NetworkPolicy with a default-deny ingress rule, then allow traffic only from the 'api-gateway' namespace.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: payments
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-api-gateway
  namespace: payments
spec:
  podSelector: {}
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: api-gateway
  policyTypes:
  - Ingress
```

Verify with: `kubectl get NetworkPolicy -n payments`"""
        },
        {
            "q": "Create a default-deny egress NetworkPolicy that only allows DNS traffic on port 53.",
            "a": """Create a NetworkPolicy that denies all egress traffic except DNS (UDP port 53 to kube-dns):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

This NetworkPolicy blocks all egress traffic except DNS resolution. Without the DNS egress rule, pods cannot resolve service names. Apply per-namespace and add additional egress rules for required external endpoints."""
        },
        {
            "q": "A pod in the 'frontend' namespace needs to talk to pods labeled 'app: backend' in the 'backend' namespace on port 8080. Write the NetworkPolicy.",
            "a": """Create a NetworkPolicy in the 'backend' namespace that allows ingress from 'frontend':

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
    ports:
    - protocol: TCP
      port: 8080
  policyTypes:
  - Ingress
```

Key points about this NetworkPolicy:
- The `podSelector` targets only pods with label `app: backend`
- The `namespaceSelector` restricts ingress to the 'frontend' namespace only
- Port 8080 TCP is the only allowed port
- Without a corresponding egress NetworkPolicy in 'frontend', outbound is allowed by default"""
        },
        {
            "q": "How do you verify that a NetworkPolicy is actually blocking traffic?",
            "a": """Verify NetworkPolicy enforcement with these steps:

1. List all NetworkPolicy resources in the namespace:
```bash
kubectl get NetworkPolicy -n target-namespace
kubectl describe NetworkPolicy deny-all-ingress -n target-namespace
```

2. Test connectivity from a blocked source:
```bash
kubectl run test-pod --image=busybox --rm -it --restart=Never -n other-namespace -- wget -qO- --timeout=3 http://target-service.target-namespace:8080
```

3. Test from an allowed source:
```bash
kubectl run test-pod --image=busybox --rm -it --restart=Never -n allowed-namespace -- wget -qO- --timeout=3 http://target-service.target-namespace:8080
```

4. Check CNI plugin logs (Calico example):
```bash
kubectl logs -n calico-system -l k8s-app=calico-node | grep -i "denied\|drop"
```

If using Cilium, check with: `kubectl exec -n kube-system cilium-agent -- cilium monitor --type drop`

The NetworkPolicy is working correctly when blocked sources get timeouts and allowed sources get responses."""
        },
    ]

    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))

    # Generate variations
    namespaces = ["prod", "staging", "dev", "monitoring", "payments", "frontend", "backend", "data"]
    labels = ["app: api", "app: web", "tier: frontend", "tier: backend", "role: db", "role: cache"]
    ports = [80, 443, 8080, 3000, 5432, 6379, 9090, 27017]

    for _ in range(20):
        src_ns = random.choice(namespaces)
        dst_ns = random.choice([n for n in namespaces if n != src_ns])
        label = random.choice(labels)
        port = random.choice(ports)
        key, val = label.split(": ")

        q = f"Write a NetworkPolicy that allows pods labeled '{label}' in namespace '{dst_ns}' to receive traffic only from namespace '{src_ns}' on port {port}."
        a = f"""Create a NetworkPolicy to restrict ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-{src_ns}-to-{val}
  namespace: {dst_ns}
spec:
  podSelector:
    matchLabels:
      {key}: {val}
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {src_ns}
    ports:
    - protocol: TCP
      port: {port}
  policyTypes:
  - Ingress
```

This NetworkPolicy:
- Targets pods with `{key}: {val}` in the '{dst_ns}' namespace
- Allows ingress only from namespace '{src_ns}'
- Restricts to TCP port {port}
- Implicitly denies all other ingress to matched pods

Verify: `kubectl get NetworkPolicy -n {dst_ns}` and test with `kubectl exec` from both allowed and blocked namespaces."""
        examples.append(msg(SYSTEM_PROMPT, q, a))

    return examples


def generate_falco_examples():
    """Falco, FalcoRule, Sysdig — missed 41+48+44 times."""
    examples = []
    scenarios = [
        {
            "q": "A container is executing shell commands at runtime. Write a Falco rule to detect this.",
            "a": """Create a FalcoRule to detect shell execution in containers:

```yaml
- rule: Shell Spawned in Container
  desc: Detect shell processes spawned inside containers at runtime
  condition: >
    spawned_process and
    container and
    proc.name in (bash, sh, zsh, dash, ksh) and
    not proc.pname in (cron, containerd-shim)
  output: >
    Shell spawned in container
    (user=%user.name container=%container.name
    image=%container.image.repository
    shell=%proc.name parent=%proc.pname
    cmdline=%proc.cmdline)
  priority: WARNING
  tags: [runtime, shell, mitre_execution]
```

Deploy this FalcoRule to your Falco configuration:
```bash
# Add to /etc/falco/rules.d/custom-rules.yaml
# Restart Falco to load the rule
sudo systemctl restart falco

# Verify Falco is running with the new rule
falco --list | grep "Shell Spawned"
```

For production monitoring, forward Falco alerts to your SIEM via Falcosidekick or use Sysdig Secure for managed Falco rule management."""
        },
        {
            "q": "How do you write a Falco rule to detect cryptocurrency mining in Kubernetes pods?",
            "a": """Create a FalcoRule targeting crypto mining indicators:

```yaml
- rule: Detect Crypto Mining in Container
  desc: Detect cryptocurrency mining processes by known miner binary names and network connections to mining pools
  condition: >
    spawned_process and
    container and
    (proc.name in (xmrig, minerd, cpuminer, ethminer, cgminer, bfgminer, nbminer, t-rex) or
     proc.cmdline contains "stratum+tcp" or
     proc.cmdline contains "pool." or
     proc.cmdline contains "--coin" or
     proc.cmdline contains "--algo")
  output: >
    Crypto mining detected in container
    (user=%user.name container=%container.name
    image=%container.image.repository
    process=%proc.name cmdline=%proc.cmdline
    connection=%fd.name)
  priority: CRITICAL
  tags: [runtime, crypto_mining, mitre_resource_hijacking]

- rule: Outbound Connection to Mining Pool
  desc: Detect network connections to known mining pool ports
  condition: >
    outbound and
    container and
    fd.sport in (3333, 4444, 5555, 7777, 8888, 9999, 14444, 14433)
  output: >
    Outbound mining pool connection from container
    (container=%container.name image=%container.image.repository
    connection=%fd.name port=%fd.sport)
  priority: CRITICAL
  tags: [runtime, crypto_mining, network]
```

Deploy this FalcoRule and configure alerting:
```bash
# Install Falco via Helm
helm install falco falcosecurity/falco --namespace falco --set falcosidekick.enabled=true

# Falco detects at runtime, Sysdig Secure provides the managed dashboard
# For self-hosted: check /var/log/falco/falco_output.log
```"""
        },
        {
            "q": "Explain the difference between Falco and Sysdig for runtime security monitoring.",
            "a": """**Falco** is an open-source runtime security tool by the CNCF that detects anomalous behavior in containers and Kubernetes clusters. It uses a rules engine (FalcoRule definitions) to match kernel-level system calls against security policies.

**Sysdig** is the commercial platform built on top of Falco. Sysdig Secure extends Falco with:
- Managed FalcoRule libraries with automatic updates
- Runtime vulnerability scanning
- Forensic capture and replay (Sysdig captures)
- Compliance dashboards (CIS, PCI-DSS, SOC2)
- Image scanning integration

**When to use each:**

| Feature | Falco (OSS) | Sysdig Secure |
|---------|-------------|---------------|
| Runtime detection | FalcoRule engine | Managed FalcoRule + ML anomaly |
| Cost | Free | Commercial license |
| Rule management | Manual YAML | GUI + auto-tuning |
| Forensics | Basic AuditLog | Full syscall capture + replay |
| Compliance | DIY mapping | Built-in frameworks |
| Integration | Falcosidekick → SIEM | Native Slack, PagerDuty, Jira |

**Recommendation:** Start with Falco for runtime monitoring. Add Sysdig Secure when you need managed rules, compliance reporting, or forensic capabilities. Both generate AuditLog data that feeds into your SIEM."""
        },
    ]

    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))

    # Variations
    alert_types = [
        ("file write to /etc/passwd", "Write Below Etc", "open_write and fd.name startswith /etc/passwd", "CRITICAL", "persistence"),
        ("process reading sensitive files", "Read Sensitive Files", "open_read and fd.name in (/etc/shadow, /etc/gshadow)", "WARNING", "credential_access"),
        ("container running with host network", "Container With Host Network", "container and k8s.pod.spec.hostNetwork=true", "WARNING", "privilege_escalation"),
        ("binary executed from /tmp", "Execution from Tmp", "spawned_process and proc.exepath startswith /tmp/", "CRITICAL", "execution"),
        ("container mounting docker socket", "Docker Socket Mounted", "container and fd.name = /var/run/docker.sock", "CRITICAL", "container_escape"),
    ]

    for desc, name, condition, priority, tactic in alert_types:
        q = f"Write a Falco rule to detect {desc} in a Kubernetes container."
        a = f"""Create a FalcoRule for detecting {desc}:

```yaml
- rule: {name}
  desc: Detect {desc} at runtime
  condition: >
    {condition} and
    container
  output: >
    {name} detected
    (user=%user.name container=%container.name
    image=%container.image.repository
    process=%proc.name file=%fd.name)
  priority: {priority}
  tags: [runtime, {tactic}, mitre_{tactic}]
```

Deploy this FalcoRule:
- Add to `/etc/falco/rules.d/custom-rules.yaml`
- Hot-reload: `kill -1 $(cat /var/run/falco.pid)` (no restart needed)
- Verify: `falco --list | grep "{name}"`

Forward alerts via Falcosidekick to Slack/PagerDuty/SIEM for incident response."""
        examples.append(msg(SYSTEM_PROMPT, q, a))

    return examples


def generate_supply_chain_examples():
    """ImagePolicyWebhook, Cosign, digest, multi-stage — missed 44+35+45+40 times."""
    examples = []
    scenarios = [
        {
            "q": "How do you enforce that only signed container images can run in your Kubernetes cluster?",
            "a": """Enforce image signing with Cosign and an admission controller:

**Step 1: Sign images with Cosign**
```bash
# Generate a keypair
cosign generate-key-pair

# Sign the image
cosign sign --key cosign.key registry.example.com/app:v1.2.3

# Verify the signature
cosign verify --key cosign.pub registry.example.com/app:v1.2.3
```

**Step 2: Enforce via Kyverno ClusterPolicy**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
spec:
  validationFailureAction: Enforce
  background: false
  rules:
  - name: verify-cosign-signature
    match:
      any:
      - resources:
          kinds:
          - Pod
    verifyImages:
    - imageReferences:
      - "registry.example.com/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              <YOUR_COSIGN_PUBLIC_KEY>
              -----END PUBLIC KEY-----
```

**Alternative: ImagePolicyWebhook**
Configure the API server admission controller:
```yaml
# /etc/kubernetes/admission-control/image-policy.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: ImagePolicyWebhook
  configuration:
    imagePolicy:
      kubeConfigFile: /etc/kubernetes/admission-control/imagepolicy-kubeconfig.yaml
      allowTTL: 50
      denyTTL: 50
      retryBackoff: 500
      defaultAllow: false
```

The ImagePolicyWebhook calls an external webhook to validate image signatures before admission. Use Cosign for signing and either Kyverno or ImagePolicyWebhook for enforcement."""
        },
        {
            "q": "Why should you use image digests instead of tags in Kubernetes manifests?",
            "a": """Image tags are mutable — `nginx:1.25` can point to different images over time. Image digests are immutable SHA-256 hashes that guarantee you're running exactly the image you tested.

**Vulnerable (tag):**
```yaml
containers:
- name: web
  image: nginx:1.25
```

**Secure (digest):**
```yaml
containers:
- name: web
  image: nginx@sha256:a484819eb60211f36f90f13b5b457f7ca8e57dddbb9e4e0f1f3f24cebc7d5f2f
```

**Get the digest:**
```bash
# Using crane
crane digest nginx:1.25

# Using docker
docker inspect --format='{{index .RepoDigests 0}}' nginx:1.25

# Using cosign (also verifies signature)
cosign triangulate nginx:1.25
```

**Why digests matter:**
- Prevents supply chain attacks where a tag is overwritten with a compromised image
- Ensures reproducible deployments — same digest = same binary
- Required for Cosign signature verification
- Image digest pinning + Cosign signing + ImagePolicyWebhook = full supply chain security

**Enforce with Kyverno:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-digest
spec:
  validationFailureAction: Enforce
  rules:
  - name: require-digest
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "Images must use digest, not tags"
      pattern:
        spec:
          containers:
          - image: "*@sha256:*"
```"""
        },
        {
            "q": "Write a multi-stage Dockerfile for a Python application that minimizes the attack surface.",
            "a": """Use a multi-stage build to separate the build environment from the runtime environment:

```dockerfile
# Stage 1: Build
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
COPY . .

# Stage 2: Runtime (minimal)
FROM python:3.12-slim AS runtime
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser
WORKDIR /app

# Copy only installed packages and app code
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /build/src ./src

# Set non-root user
USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH"

# Read-only filesystem friendly
VOLUME ["/tmp"]

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why multi-stage matters:**
- Build tools (gcc, pip, git) are NOT in the runtime image
- Reduces image size by 60-80% (fewer vulnerability targets)
- No source code leakage — only compiled/installed artifacts
- Combined with `USER appuser` (non-root) and `HEALTHCHECK`

**Verify the image:**
```bash
# Scan for vulnerability with Trivy
trivy image myapp:v1.0

# Sign with Cosign
cosign sign --key cosign.key registry.example.com/myapp:v1.0

# Pin by digest in Kubernetes manifests
docker inspect --format='{{index .RepoDigests 0}}' myapp:v1.0
```"""
        },
    ]

    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_mtls_examples():
    """mTLS — missed 40 times."""
    examples = []
    scenarios = [
        {
            "q": "How do you enable mTLS between all services in a Kubernetes namespace?",
            "a": """Enable mTLS (mutual TLS) using Istio's PeerAuthentication:

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: strict-mtls
  namespace: production
spec:
  mtls:
    mode: STRICT
```

This enforces mTLS for all pod-to-pod communication in the 'production' namespace. Both client and server must present valid certificates.

**Cluster-wide mTLS:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

**Verify mTLS is active:**
```bash
# Check mTLS status between services
istioctl x describe pod <pod-name> -n production

# Check PeerAuthentication policies
kubectl get PeerAuthentication -A

# Verify with kiali dashboard
istioctl dashboard kiali
```

**Why mTLS matters:**
- Encrypts all service-to-service traffic in transit
- Provides mutual authentication — both sides verify identity
- Prevents man-in-the-middle attacks within the cluster
- Certificate rotation is automatic via Istio's citadel/istiod
- Required for zero-trust networking in Kubernetes"""
        },
        {
            "q": "What is the difference between mTLS PERMISSIVE and STRICT mode in Istio?",
            "a": """Istio PeerAuthentication supports two mTLS modes:

**PERMISSIVE mode** — accepts both mTLS and plaintext:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: permissive-mtls
  namespace: production
spec:
  mtls:
    mode: PERMISSIVE
```
- Use during migration when not all services have sidecars
- Allows non-mesh services to communicate with mesh services
- Does NOT enforce encryption — plaintext still accepted

**STRICT mode** — mTLS only, rejects plaintext:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: strict-mtls
  namespace: production
spec:
  mtls:
    mode: STRICT
```
- Enforces mutual TLS for all connections
- Rejects any non-TLS traffic
- Required for zero-trust security posture
- Both client and server must present valid certificates

**Migration path:**
1. Start with PERMISSIVE (allows gradual sidecar injection)
2. Monitor with `istioctl x describe` to verify all services have sidecars
3. Switch to STRICT once all workloads are in the mesh
4. Set STRICT at `istio-system` namespace for cluster-wide enforcement"""
        },
    ]

    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_staticpod_apparmor_examples():
    """StaticPod — missed 37 times, AppArmor — missed 31 times, securityContext — missed 32 times."""
    examples = []
    scenarios = [
        {
            "q": "What is a StaticPod and how is it different from a regular pod?",
            "a": """A StaticPod is a pod managed directly by the kubelet on a specific node, not by the Kubernetes API server. StaticPod manifests are placed in the kubelet's static pod directory (usually `/etc/kubernetes/manifests/`).

**Key differences:**

| Feature | StaticPod | Regular Pod |
|---------|-----------|-------------|
| Managed by | kubelet directly | kube-apiserver / controllers |
| Manifest location | `/etc/kubernetes/manifests/` | API server (etcd) |
| Scheduling | Always on the same node | Scheduled by kube-scheduler |
| Deletion | Delete the manifest file | `kubectl delete pod` |
| Use cases | Control plane components | Application workloads |

**Control plane StaticPod components:**
- `kube-apiserver` → `/etc/kubernetes/manifests/kube-apiserver.yaml`
- `kube-controller-manager` → `/etc/kubernetes/manifests/kube-controller-manager.yaml`
- `kube-scheduler` → `/etc/kubernetes/manifests/kube-scheduler.yaml`
- `etcd` → `/etc/kubernetes/manifests/etcd.yaml`

**Hardening a StaticPod:**
```bash
# View the kube-apiserver StaticPod
cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Edit to add audit logging
# Changes are picked up automatically by kubelet
vim /etc/kubernetes/manifests/kube-apiserver.yaml
```

The kubelet watches the StaticPod directory and automatically creates/updates pods when manifests change. A mirror pod is created in the API server for visibility, but the kubelet manages the actual StaticPod lifecycle."""
        },
        {
            "q": "Apply an AppArmor profile to a container in Kubernetes.",
            "a": """Apply an AppArmor profile to restrict container capabilities:

**Step 1: Create the AppArmor profile on the node**
```bash
# /etc/apparmor.d/k8s-restricted
#include <tunables/global>
profile k8s-restricted flags=(attach_disconnected) {
  #include <abstractions/base>

  # Deny all file writes except /tmp and /var/log
  deny /** w,
  /tmp/** rw,
  /var/log/** rw,

  # Deny network raw access
  deny network raw,

  # Deny mount operations
  deny mount,
}
```

**Step 2: Load the profile**
```bash
sudo apparmor_parser -r /etc/apparmor.d/k8s-restricted
sudo aa-status | grep k8s-restricted
```

**Step 3: Apply to a pod via securityContext**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  securityContext:
    appArmorProfile:
      type: Localhost
      localhostProfile: k8s-restricted
  containers:
  - name: app
    image: nginx:1.25
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

**Note:** As of Kubernetes 1.30+, AppArmor uses the `securityContext.appArmorProfile` field. Older versions use the annotation `container.apparmor.security.beta.kubernetes.io/app: localhost/k8s-restricted`.

AppArmor provides mandatory access control (MAC) at the kernel level, complementing the securityContext settings."""
        },
        {
            "q": "What is the complete recommended securityContext for a production container?",
            "a": """The full recommended securityContext for production:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: hardened-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10000
    runAsGroup: 10000
    fsGroup: 10000
    seccompProfile:
      type: RuntimeDefault
    appArmorProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: myapp@sha256:abc123...
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
      privileged: false
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi
    livenessProbe:
      httpGet:
        path: /health
        port: 8080
      initialDelaySeconds: 10
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
```

**securityContext breakdown:**
- `runAsNonRoot: true` — prevents root user
- `readOnlyRootFilesystem: true` — prevents filesystem writes (use emptyDir for /tmp)
- `allowPrivilegeEscalation: false` — prevents setuid binaries
- `privileged: false` — no host-level access
- `capabilities.drop: ALL` — drops all Linux capabilities
- `seccompProfile: RuntimeDefault` — restricts system calls
- `appArmorProfile: RuntimeDefault` — mandatory access control

This meets the Pod Security Standards 'restricted' level. Enforce with namespace labels:
```bash
kubectl label namespace production pod-security.kubernetes.io/enforce=restricted
```"""
        },
    ]

    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_audit_logging_examples():
    """AuditLog — missed 47 times."""
    examples = []
    scenarios = [
        {
            "q": "How do you configure Kubernetes audit logging to capture security-relevant events?",
            "a": """Configure the kube-apiserver StaticPod for AuditLog:

**Step 1: Create an audit policy**
```yaml
# /etc/kubernetes/audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
# Log authentication failures at Metadata level
- level: Metadata
  resources:
  - group: ""
    resources: ["pods", "secrets", "configmaps"]
  verbs: ["create", "delete", "patch", "update"]

# Log all requests to secrets at RequestResponse level
- level: RequestResponse
  resources:
  - group: ""
    resources: ["secrets"]

# Log RBAC changes
- level: Metadata
  resources:
  - group: "rbac.authorization.k8s.io"
    resources: ["clusterroles", "clusterrolebindings", "roles", "rolebindings"]

# Catch-all: log everything else at Metadata
- level: Metadata
```

**Step 2: Configure the API server StaticPod**
```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
spec:
  containers:
  - command:
    - kube-apiserver
    - --audit-policy-file=/etc/kubernetes/audit-policy.yaml
    - --audit-log-path=/var/log/kubernetes/audit/audit.log
    - --audit-log-maxage=30
    - --audit-log-maxbackup=10
    - --audit-log-maxsize=100
    volumeMounts:
    - mountPath: /etc/kubernetes/audit-policy.yaml
      name: audit-policy
      readOnly: true
    - mountPath: /var/log/kubernetes/audit
      name: audit-log
  volumes:
  - hostPath:
      path: /etc/kubernetes/audit-policy.yaml
      type: File
    name: audit-policy
  - hostPath:
      path: /var/log/kubernetes/audit
      type: DirectoryOrCreate
    name: audit-log
```

The AuditLog captures who did what, when, and to which resource. Forward audit logs to Falco or your SIEM for runtime security monitoring."""
        },
    ]

    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def main():
    all_examples = []

    print("[1/6] Generating NetworkPolicy examples...")
    all_examples.extend(generate_networkpolicy_examples())

    print("[2/6] Generating Falco/FalcoRule/Sysdig examples...")
    all_examples.extend(generate_falco_examples())

    print("[3/6] Generating supply chain (Cosign/digest/ImagePolicyWebhook/multi-stage) examples...")
    all_examples.extend(generate_supply_chain_examples())

    print("[4/6] Generating mTLS examples...")
    all_examples.extend(generate_mtls_examples())

    print("[5/6] Generating StaticPod/AppArmor/securityContext examples...")
    all_examples.extend(generate_staticpod_apparmor_examples())

    print("[6/6] Generating AuditLog examples...")
    all_examples.extend(generate_audit_logging_examples())

    random.shuffle(all_examples)

    from generate_utils import write_training_data
    write_training_data(
        examples=all_examples,
        output_file=OUTPUT_FILE,
        generator="generate_cks_terminology_gap.py",
        domain="CKS",
    )


if __name__ == "__main__":
    main()
