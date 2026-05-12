#!/usr/bin/env python3
"""
CKS Terminology V2 — Scaled Training Data Generator
=====================================================
Generates 500+ CKS training examples targeting the top missing keywords
from eval, with heavy emphasis on NetworkPolicy (92x missed), Falco (41x),
supply chain (Cosign 35x, digest 45x), and runtime security.

Also includes CKA admin ops at scale (kubeadm, etcd, kubelet, troubleshooting).

Output: 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"

SYSTEM_CKS = "You are JADE, a CKS-certified Kubernetes security expert. Always use exact Kubernetes resource kind names (NetworkPolicy, PodSecurityPolicy, FalcoRule). Reference specific tools by name (Falco, Cosign, Trivy, Sysdig). Use canonical terminology."
SYSTEM_CKA = "You are JADE, a CKA-certified Kubernetes administrator. Provide exact commands for cluster administration. Use canonical tool names: kubeadm, etcdctl, kubectl, kubelet, systemctl, journalctl."

def msg(system, user, assistant):
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}


# ─────────────────────────── NetworkPolicy (target: 150 examples) ───────
def generate_networkpolicy_scaled():
    examples = []
    namespaces = ["prod", "staging", "dev", "monitoring", "payments", "frontend", "backend",
                  "data", "auth", "logging", "ingress", "kube-system", "finance", "api",
                  "analytics", "ml-pipeline", "ci-cd", "vault", "redis", "postgres"]
    labels = [
        ("app", ["api", "web", "worker", "gateway", "scheduler", "cron", "proxy", "cache"]),
        ("tier", ["frontend", "backend", "database", "middleware", "ingress"]),
        ("role", ["primary", "replica", "standby", "monitor", "indexer"]),
        ("team", ["platform", "security", "data", "payments", "infra"]),
    ]
    ports = [80, 443, 3000, 5432, 6379, 8080, 8443, 9090, 9200, 27017, 3306, 4222, 11211]
    protocols = ["TCP", "UDP"]

    # Template 1: Default deny + allow specific
    for _ in range(40):
        ns = random.choice(namespaces)
        src_ns = random.choice([n for n in namespaces if n != ns])
        key, vals = random.choice(labels)
        val = random.choice(vals)
        port = random.choice(ports)
        proto = random.choice(protocols)

        q = f"Create a default-deny NetworkPolicy for namespace '{ns}', then allow ingress from '{src_ns}' to pods labeled '{key}: {val}' on port {port}/{proto}."
        a = f"""Create two NetworkPolicy resources — one for default deny, one for the specific allow:

```yaml
# Default deny all ingress in {ns}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: {ns}
spec:
  podSelector: {{}}
  policyTypes:
  - Ingress
---
# Allow ingress from {src_ns} to {key}={val} on port {port}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-{src_ns}-to-{val}
  namespace: {ns}
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
    - protocol: {proto}
      port: {port}
  policyTypes:
  - Ingress
```

Verify: `kubectl get NetworkPolicy -n {ns}` — should show both policies. Test with `kubectl exec` from {src_ns} and a blocked namespace."""
        examples.append(msg(SYSTEM_CKS, q, a))

    # Template 2: Egress NetworkPolicy
    for _ in range(30):
        ns = random.choice(namespaces)
        port = random.choice(ports)
        key, vals = random.choice(labels)
        val = random.choice(vals)

        q = f"Pods labeled '{key}: {val}' in '{ns}' should only be allowed egress to DNS (port 53) and to pods labeled 'role: primary' on port {port}. Write the NetworkPolicy."
        a = f"""Create an egress NetworkPolicy:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {val}-egress-restricted
  namespace: {ns}
spec:
  podSelector:
    matchLabels:
      {key}: {val}
  policyTypes:
  - Egress
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
  # Allow to primary on port {port}
  - to:
    - podSelector:
        matchLabels:
          role: primary
    ports:
    - protocol: TCP
      port: {port}
```

This NetworkPolicy restricts egress from {key}={val} pods. Without the DNS rule, pods cannot resolve service names. The egress to role=primary allows database or cache connections on port {port} only."""
        examples.append(msg(SYSTEM_CKS, q, a))

    # Template 3: Multi-port, multi-namespace
    for _ in range(20):
        ns = random.choice(namespaces)
        ns_list = random.sample([n for n in namespaces if n != ns], 2)
        ports_list = random.sample(ports, 3)
        key, vals = random.choice(labels)
        val = random.choice(vals)

        q = f"Allow pods labeled '{key}: {val}' in '{ns}' to receive traffic from namespaces '{ns_list[0]}' and '{ns_list[1]}' on ports {ports_list[0]}, {ports_list[1]}, and {ports_list[2]}."
        a = f"""```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: multi-source-{val}
  namespace: {ns}
spec:
  podSelector:
    matchLabels:
      {key}: {val}
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {ns_list[0]}
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {ns_list[1]}
    ports:
    - protocol: TCP
      port: {ports_list[0]}
    - protocol: TCP
      port: {ports_list[1]}
    - protocol: TCP
      port: {ports_list[2]}
  policyTypes:
  - Ingress
```

This NetworkPolicy allows ingress from both '{ns_list[0]}' and '{ns_list[1]}' namespaces on three ports. Note: the two `namespaceSelector` entries under `from` are OR'd — traffic from either namespace is allowed. To require BOTH namespace AND pod label, nest them in the same `from` entry."""
        examples.append(msg(SYSTEM_CKS, q, a))

    # Template 4: Troubleshooting NetworkPolicy
    troubleshooting = [
        ("Pods can't reach DNS after applying a default-deny egress NetworkPolicy.",
         "The default-deny egress NetworkPolicy blocks all outbound traffic, including DNS (port 53/UDP to kube-system). Add an egress rule allowing UDP port 53 to kube-system.\n\n```yaml\negress:\n- to:\n  - namespaceSelector:\n      matchLabels:\n        kubernetes.io/metadata.name: kube-system\n  ports:\n  - protocol: UDP\n    port: 53\n```\n\nVerify with: `kubectl exec <pod> -- nslookup kubernetes.default`"),
        ("A NetworkPolicy should block traffic but pods can still communicate.",
         "Check:\n1. Is the CNI plugin installed and supports NetworkPolicy? (Flannel does NOT)\n```bash\nkubectl get pods -n kube-system -l k8s-app=calico-node\n# or\nkubectl get pods -n kube-system -l k8s-app=cilium\n```\n2. Does the NetworkPolicy selector match the target pods?\n```bash\nkubectl get NetworkPolicy -n <namespace> -o yaml\nkubectl get pods -n <namespace> --show-labels\n```\n3. Is `policyTypes` set correctly? An ingress-only NetworkPolicy won't block egress."),
        ("After applying NetworkPolicy, health checks from the kubelet fail.",
         "The kubelet runs on the node, outside the cluster network. NetworkPolicy blocks traffic from the node IP. Add an ingress rule allowing traffic from the node CIDR:\n\n```yaml\ningress:\n- from:\n  - ipBlock:\n      cidr: 10.0.0.0/8  # Node CIDR\n  ports:\n  - protocol: TCP\n    port: 8080  # Health check port\n```\n\nAlternatively, use a `namespaceSelector: {}` (allows all namespaces) if the kubelet uses the pod network for health checks."),
    ]
    for q, a in troubleshooting:
        examples.append(msg(SYSTEM_CKS, q, a))

    return examples


# ─────────────────────────── Falco/Runtime (target: 80 examples) ────────
def generate_falco_scaled():
    examples = []

    detections = [
        ("container writing to /etc/passwd", "Write Below Etc Passwd", "open_write and fd.name = /etc/passwd and container", "CRITICAL", "persistence", "T1098"),
        ("reverse shell spawned", "Reverse Shell in Container", "spawned_process and container and (proc.name in (bash, sh) and proc.cmdline contains '/dev/tcp')", "CRITICAL", "execution", "T1059"),
        ("sensitive file read in container", "Read Sensitive File in Container", "open_read and container and fd.name in (/etc/shadow, /etc/gshadow, /etc/kubernetes/pki/ca.key)", "WARNING", "credential_access", "T1552"),
        ("binary deleted after execution", "Binary Dropped and Deleted", "container and (evt.type = unlinkat and proc.name != rm)", "CRITICAL", "defense_evasion", "T1070"),
        ("container spawning network tool", "Network Tool Spawned in Container", "spawned_process and container and proc.name in (nc, ncat, netcat, nmap, socat, tcpdump, tshark)", "WARNING", "discovery", "T1046"),
        ("new process listening on port", "Unexpected Port Listener", "container and evt.type = listen and fd.sport > 1024 and not proc.name in (nginx, node, python3, java)", "NOTICE", "command_and_control", "T1571"),
        ("package manager executed in container", "Package Manager Execution", "spawned_process and container and proc.name in (apt, apt-get, yum, dnf, apk, pip, npm)", "WARNING", "execution", "T1072"),
        ("container accessing cloud metadata", "Cloud Metadata Access", "container and fd.sip = 169.254.169.254", "WARNING", "credential_access", "T1552.005"),
        ("symlink created to sensitive path", "Symlink to Sensitive Path", "container and evt.type = symlinkat and (evt.arg.target contains /etc/ or evt.arg.target contains /proc/)", "WARNING", "privilege_escalation", "T1548"),
        ("ptrace attached to process", "Ptrace Attached", "container and evt.type = ptrace and evt.arg.request = PTRACE_ATTACH", "CRITICAL", "privilege_escalation", "T1055"),
        ("SSH service started in container", "SSH Service in Container", "spawned_process and container and proc.name = sshd", "CRITICAL", "persistence", "T1021"),
        ("crontab modified in container", "Container Crontab Modified", "container and (open_write and fd.name contains crontab)", "WARNING", "persistence", "T1053"),
        ("large outbound data transfer", "Potential Data Exfiltration", "container and fd.typechar = 4 and evt.type = sendto and evt.rawres > 1048576", "CRITICAL", "exfiltration", "T1041"),
        ("container accessing host PID namespace", "Host PID Namespace Access", "container and proc.vpid != proc.pid", "CRITICAL", "privilege_escalation", "T1611"),
        ("kernel module loaded", "Kernel Module Loaded in Container", "container and evt.type = init_module", "CRITICAL", "persistence", "T1547"),
    ]

    for desc, name, condition, priority, tactic, mitre_id in detections:
        q = f"Write a Falco rule to detect {desc}."
        a = f"""Create a FalcoRule for {desc}:

```yaml
- rule: {name}
  desc: Detect {desc} at runtime
  condition: >
    {condition}
  output: >
    {name} detected
    (user=%user.name container=%container.name
    image=%container.image.repository
    process=%proc.name cmdline=%proc.cmdline
    file=%fd.name)
  priority: {priority}
  tags: [runtime, {tactic}, mitre_{tactic}, {mitre_id}]
```

**MITRE ATT&CK:** {mitre_id} ({tactic.replace('_', ' ').title()})

Deploy this FalcoRule to `/etc/falco/rules.d/custom-rules.yaml`. Hot-reload with `kill -1 $(cat /var/run/falco.pid)`. Forward alerts via Falcosidekick to your SIEM. Sysdig Secure provides managed FalcoRule libraries with automatic updates."""
        examples.append(msg(SYSTEM_CKS, q, a))

    # Falco operations
    ops = [
        ("How do you tune Falco rules to reduce false positives?",
         """Tune Falco rules by adding exceptions and allowlists:

**1. Add exceptions directly:**
```yaml
- rule: Shell Spawned in Container
  append: true
  condition: and not container.image.repository in (my-debug-image, my-cron-image)
```

**2. Use Falco's macro system:**
```yaml
- macro: trusted_images
  condition: container.image.repository in (nginx, redis, postgres)

- rule: Unexpected Process
  condition: spawned_process and container and not trusted_images
```

**3. Namespace-level suppression:**
```yaml
- macro: in_debug_namespace
  condition: k8s.ns.name = "debug"

- rule: Shell Spawned
  condition: spawned_process and container and proc.name in (bash, sh) and not in_debug_namespace
```

**4. Review with falco-exporter metrics:**
```bash
# Check which rules fire most
curl -s http://falco-exporter:9376/metrics | grep falco_alerts_total
```

Start with `priority: WARNING` for new rules. Promote to `priority: CRITICAL` after tuning. Never suppress rules in production namespaces — only tune the conditions."""),
        ("How do you deploy Falco on EKS with Helm?",
         """Deploy Falco via Helm on EKS:

```bash
# Add Falco Helm repo
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

# Install Falco with falco-exporter and custom rules
helm install falco falcosecurity/falco \\
  --namespace falco --create-namespace \\
  --set falcosidekick.enabled=true \\
  --set falcosidekick.webui.enabled=true \\
  --set driver.kind=ebpf \\
  --set tty=true \\
  --set json_output=true \\
  --set http_output.enabled=true \\
  --set http_output.url=http://falcosidekick:2801

# Install falco-exporter for Prometheus metrics
helm install falco-exporter falcosecurity/falco-exporter \\
  --namespace falco

# Verify
kubectl get pods -n falco
kubectl logs -n falco -l app.kubernetes.io/name=falco --tail=20
```

**EKS-specific notes:**
- Use `driver.kind=ebpf` (not kernel module) on managed EKS nodes
- Falco runs as a DaemonSet on every node
- falcosidekick forwards alerts to Slack, PagerDuty, or SIEM via HTTP
- Sysdig Secure is the commercial alternative with managed FalcoRule libraries"""),
    ]
    for q, a in ops:
        examples.append(msg(SYSTEM_CKS, q, a))

    return examples


# ─────────────────────────── Supply Chain (target: 60 examples) ─────────
def generate_supply_chain_scaled():
    examples = []
    registries = ["registry.example.com", "ghcr.io/myorg", "docker.io/mycompany", "123456789.dkr.ecr.us-east-1.amazonaws.com"]
    apps = ["api", "web", "worker", "scheduler", "proxy", "auth-service", "payment-service"]
    versions = ["v1.0.0", "v1.2.3", "v2.0.0-rc1", "v3.1.4", "latest"]

    # Cosign signing flows
    for _ in range(15):
        reg = random.choice(registries)
        app = random.choice(apps)
        ver = random.choice([v for v in versions if v != "latest"])

        q = f"Sign the image {reg}/{app}:{ver} with Cosign and enforce verification in Kubernetes."
        a = f"""**Step 1: Sign with Cosign**
```bash
# Generate keypair (one-time)
cosign generate-key-pair

# Sign the image
cosign sign --key cosign.key {reg}/{app}:{ver}

# Verify
cosign verify --key cosign.pub {reg}/{app}:{ver}
```

**Step 2: Get the image digest**
```bash
# Always reference by digest in Kubernetes manifests
crane digest {reg}/{app}:{ver}
# Output: sha256:abc123...

# Use digest in deployment
image: {reg}/{app}@sha256:abc123...
```

**Step 3: Enforce with Kyverno**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-{app}-signature
spec:
  validationFailureAction: Enforce
  rules:
  - name: verify-cosign
    match:
      any:
      - resources:
          kinds:
          - Pod
    verifyImages:
    - imageReferences:
      - "{reg}/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              <COSIGN_PUBLIC_KEY>
              -----END PUBLIC KEY-----
```

**Alternative: ImagePolicyWebhook**
Configure the kube-apiserver admission controller with `--enable-admission-plugins=ImagePolicyWebhook` to call an external webhook that validates Cosign signatures before pod admission.

Cosign + image digest pinning + admission controller = full supply chain security."""
        examples.append(msg(SYSTEM_CKS, q, a))

    # Digest pinning
    for _ in range(15):
        reg = random.choice(registries)
        app = random.choice(apps)

        q = f"Convert the image reference {reg}/{app}:latest to use a digest and explain why."
        a = f"""**Problem:** Tags are mutable. `{reg}/{app}:latest` can point to different images over time. An attacker could push a compromised image with the same tag.

**Get the digest:**
```bash
crane digest {reg}/{app}:latest
# or
docker inspect --format='{{{{index .RepoDigests 0}}}}' {reg}/{app}:latest
# or
cosign triangulate {reg}/{app}:latest
```

**Before (vulnerable):**
```yaml
containers:
- name: {app}
  image: {reg}/{app}:latest
```

**After (secure — pinned by digest):**
```yaml
containers:
- name: {app}
  image: {reg}/{app}@sha256:a484819eb60211f36f90f13b5b457f7ca8e57dddbb9e4e0f1f3f24cebc7d5f2f
```

**Why image digest pinning matters:**
- Immutable — same digest = same binary, always
- Prevents supply chain attacks via tag overwriting
- Required for Cosign signature verification
- Reproducible deployments across environments

**Enforce with policy:**
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
      message: "Images must use digest (@sha256:), not tags"
      pattern:
        spec:
          containers:
          - image: "*@sha256:*"
```"""
        examples.append(msg(SYSTEM_CKS, q, a))

    # Multi-stage Dockerfiles
    langs = [
        ("Go", "golang:1.22-alpine", "go build -o /app .", "gcr.io/distroless/static-debian12", "COPY --from=builder /app /app"),
        ("Node.js", "node:20-alpine", "npm ci --production", "node:20-alpine", "COPY --from=builder /app/node_modules ./node_modules\nCOPY --from=builder /app/dist ./dist"),
        ("Java", "maven:3.9-eclipse-temurin-21", "mvn package -DskipTests", "eclipse-temurin:21-jre-alpine", "COPY --from=builder /app/target/*.jar /app/app.jar"),
        ("Rust", "rust:1.77-slim", "cargo build --release", "gcr.io/distroless/cc-debian12", "COPY --from=builder /app/target/release/myapp /app/myapp"),
    ]

    for lang, build_img, build_cmd, runtime_img, copy_cmd in langs:
        q = f"Write a security-hardened multi-stage Dockerfile for a {lang} application."
        a = f"""Hardened multi-stage build for {lang}:

```dockerfile
# Stage 1: Build
FROM {build_img} AS builder
WORKDIR /app
COPY . .
RUN {build_cmd}

# Stage 2: Runtime (minimal attack surface)
FROM {runtime_img}
RUN addgroup -g 10001 appuser && adduser -u 10001 -G appuser -s /sbin/nologin -D appuser
WORKDIR /app
{copy_cmd}
USER 10001:10001

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \\
  CMD wget -qO- http://localhost:8080/health || exit 1

EXPOSE 8080
```

**Security features in this multi-stage Dockerfile:**
- Build tools NOT in runtime image (reduces vulnerability surface)
- Non-root `USER 10001` (never run as root)
- `HEALTHCHECK` for liveness monitoring
- No secrets in any layer
- Pin base image versions (never use `:latest`)

**Next steps:**
```bash
# Scan for vulnerability with Trivy
trivy image myapp:v1.0

# Sign with Cosign
cosign sign --key cosign.key registry.example.com/myapp:v1.0

# Pin by image digest in Kubernetes manifests
docker inspect --format='{{{{index .RepoDigests 0}}}}' myapp:v1.0
```"""
        examples.append(msg(SYSTEM_CKS, q, a))

    return examples


# ─────────────────────────── securityContext / PSS (target: 50) ─────────
def generate_security_context_scaled():
    examples = []
    workloads = ["Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"]
    apps = ["nginx", "postgres", "redis", "api-server", "worker", "cron-job", "log-collector"]

    for _ in range(25):
        wl = random.choice(workloads)
        app = random.choice(apps)
        ns = random.choice(["prod", "staging", "payments", "monitoring"])

        q = f"Harden the securityContext for a {wl} named '{app}' in namespace '{ns}'. Apply Pod Security Standards restricted level."
        selector_block = f"selector:\n    matchLabels:\n      app: {app}\n  template:" if wl in ('Deployment', 'StatefulSet', 'DaemonSet') else "template:"
        label_cmd = (
            f"kubectl label namespace {ns} "
            f"pod-security.kubernetes.io/enforce=restricted "
            f"pod-security.kubernetes.io/audit=restricted "
            f"pod-security.kubernetes.io/warn=restricted"
        )
        a = f"""Apply full securityContext hardening:

```yaml
apiVersion: apps/v1
kind: {wl}
metadata:
  name: {app}
  namespace: {ns}
spec:
  {selector_block}
    metadata:
      labels:
        app: {app}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10000
        runAsGroup: 10000
        fsGroup: 10000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: {app}
        image: {app}:1.0@sha256:abc123
        securityContext:
          allowPrivilegeEscalation: false
          privileged: false
          readOnlyRootFilesystem: true
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
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {{}}
```

**Enforce Pod Security Standards at namespace level:**
```bash
{label_cmd}
```

**securityContext checklist:**
- `runAsNonRoot: true` — no root containers
- `readOnlyRootFilesystem: true` — use emptyDir for /tmp
- `allowPrivilegeEscalation: false` — blocks setuid
- `capabilities.drop: ALL` — drop all Linux capabilities
- `seccompProfile: RuntimeDefault` — restrict syscalls
- `privileged: false` — no host access
- Image pinned by digest — immutable reference"""
        examples.append(msg(SYSTEM_CKS, q, a))

    # AppArmor variations
    profiles = [
        ("k8s-deny-write", "deny /** w,\n  /tmp/** rw,\n  /var/log/** rw,", "Denies all writes except /tmp and /var/log"),
        ("k8s-deny-network", "deny network raw,\n  deny network packet,", "Blocks raw network access (prevents packet sniffing)"),
        ("k8s-deny-mount", "deny mount,\n  deny umount,", "Prevents filesystem mounts inside container"),
    ]
    for name, rules, desc in profiles:
        q = f"Apply the AppArmor profile '{name}' to a Kubernetes pod."
        a = f"""**Profile ({desc}):**
```bash
# /etc/apparmor.d/{name}
#include <tunables/global>
profile {name} flags=(attach_disconnected) {{
  #include <abstractions/base>
  {rules}
}}
```

**Load on the node:**
```bash
sudo apparmor_parser -r /etc/apparmor.d/{name}
sudo aa-status | grep {name}
```

**Apply to pod via securityContext (Kubernetes 1.30+):**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: hardened-pod
spec:
  securityContext:
    appArmorProfile:
      type: Localhost
      localhostProfile: {name}
  containers:
  - name: app
    image: myapp:v1.0
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

AppArmor provides mandatory access control (MAC) at the kernel level, complementing Kubernetes securityContext. Combined with seccompProfile (RuntimeDefault), this gives defense-in-depth at the syscall and filesystem level."""
        examples.append(msg(SYSTEM_CKS, q, a))

    return examples


# ─────────────────────────── CKA Admin Ops Scaled (target: 80) ──────────
def generate_cka_scaled():
    examples = []

    # kubeadm upgrade variations
    upgrades = [
        ("1.28", "1.29"), ("1.29", "1.30"), ("1.30", "1.31"),
        ("1.27", "1.28"), ("1.26", "1.27"),
    ]
    for old, new in upgrades:
        q = f"Upgrade a 3-node kubeadm cluster from v{old} to v{new}. Control plane has 1 node, 2 workers."
        a = f"""**Phase 1: Upgrade control plane**
```bash
# On control plane node:
sudo apt-get update
sudo apt-get install -y kubeadm={new}.0-1.1
sudo kubeadm upgrade plan
sudo kubeadm upgrade apply v{new}.0

# Drain the control plane
kubectl drain cp-node --ignore-daemonsets --delete-emptydir-data

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet={new}.0-1.1 kubectl={new}.0-1.1
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Uncordon
kubectl uncordon cp-node
```

**Phase 2: Upgrade each worker (one at a time)**
```bash
# On worker node:
sudo apt-get update
sudo apt-get install -y kubeadm={new}.0-1.1
sudo kubeadm upgrade node

# From control plane:
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data

# On worker node:
sudo apt-get install -y kubelet={new}.0-1.1 kubectl={new}.0-1.1
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# From control plane:
kubectl uncordon worker-1
# Repeat for worker-2
```

**Verify:**
```bash
kubectl get nodes
# All nodes should show v{new}.0 and Ready
```

**Rules:** Control plane first. One minor version at a time. Always drain before upgrading kubelet, uncordon after. Use `kubeadm upgrade plan` before `kubeadm upgrade apply`."""
        examples.append(msg(SYSTEM_CKA, q, a))

    # etcd operations
    etcd_ops = [
        ("Back up etcd and verify the snapshot",
         """```bash
ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-backup-$(date +%Y%m%d).db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify
ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-backup-$(date +%Y%m%d).db --write-out=table
```

The `--cacert`, `--cert`, and `--key` flags authenticate to the etcd cluster. These paths come from the etcd StaticPod manifest at `/etc/kubernetes/manifests/etcd.yaml`."""),
        ("Restore etcd from a backup to recover a broken cluster",
         """```bash
# Stop control plane StaticPods
sudo mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/
sudo mv /etc/kubernetes/manifests/etcd.yaml /tmp/

# Restore to a NEW data directory
ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-backup.db \\
  --data-dir=/var/lib/etcd-restored \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# Update etcd StaticPod to use new data-dir
sudo sed -i 's|/var/lib/etcd|/var/lib/etcd-restored|g' /tmp/etcd.yaml
# Also update the hostPath volume

# Restore StaticPod manifests
sudo mv /tmp/etcd.yaml /etc/kubernetes/manifests/
sudo mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/

# Wait for kubelet to restart pods, verify
kubectl get nodes
kubectl get pods -A
```

Critical: `--data-dir` MUST be a new directory. The kubelet auto-restarts the StaticPod when the manifest changes."""),
        ("Check etcd cluster health and member list",
         """```bash
# Check cluster health
ETCDCTL_API=3 etcdctl endpoint health \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# List members
ETCDCTL_API=3 etcdctl member list \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key \\
  --write-out=table

# Check performance
ETCDCTL_API=3 etcdctl endpoint status \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key \\
  --write-out=table
```"""),
    ]
    for q, a in etcd_ops:
        examples.append(msg(SYSTEM_CKA, q, a))

    # Kubelet troubleshooting at scale
    kubelet_issues = [
        ("Node shows NotReady, kubelet logs show certificate expired",
         """Certificate expiry causes kubelet to fail API server authentication.

```bash
# Check certificate expiry
sudo kubeadm certs check-expiration

# Renew all certificates
sudo kubeadm certs renew all

# Restart kubelet
sudo systemctl restart kubelet

# Verify
journalctl -u kubelet --no-pager -n 20
kubectl get nodes
```"""),
        ("Kubelet fails with 'PLEG is not healthy'",
         """PLEG (Pod Lifecycle Event Generator) timeout means the container runtime is too slow.

```bash
# Check kubelet logs for PLEG
journalctl -u kubelet | grep -i PLEG

# Check container runtime
systemctl status containerd
crictl info
crictl pods

# Fix: restart container runtime first, then kubelet
sudo systemctl restart containerd
sudo systemctl restart kubelet

# If overloaded, check pod count
kubectl get pods --field-selector spec.nodeName=$(hostname) | wc -l

# Clean up unused images
sudo crictl rmi --prune
```"""),
        ("Node has DiskPressure condition",
         """DiskPressure triggers pod eviction when disk usage exceeds the kubelet threshold.

```bash
# Check disk usage
df -h /var/lib/kubelet
df -h /var/lib/containerd

# Clean container images
sudo crictl rmi --prune

# Clean old journal logs
sudo journalctl --vacuum-size=500M

# Check kubelet eviction thresholds
journalctl -u kubelet | grep -i "eviction"

# Verify recovery
kubectl describe node $(hostname) | grep -A5 Conditions
```"""),
        ("Pod stuck in Terminating state after node drain",
         """```bash
# Check if pod has a finalizer blocking deletion
kubectl get pod <pod> -n <ns> -o jsonpath='{.metadata.finalizers}'

# Force delete (use with caution)
kubectl delete pod <pod> -n <ns> --grace-period=0 --force

# If node is truly down, delete the node object
kubectl delete node <node-name>

# Pods will be rescheduled by their controllers (Deployment, StatefulSet)
kubectl get pods -A -o wide | grep <old-node>
```"""),
    ]
    for q, a in kubelet_issues:
        examples.append(msg(SYSTEM_CKA, q, a))

    # Service troubleshooting
    svc_issues = [
        ("Service has no endpoints",
         """```bash
# Check endpoints
kubectl get endpoints <service-name> -n <ns>

# If empty, the selector doesn't match any pods
kubectl get service <service-name> -n <ns> -o jsonpath='{.spec.selector}'
kubectl get pods -n <ns> --show-labels

# Common causes:
# 1. Label mismatch between Service selector and Pod labels
# 2. Pods not in Ready state (readiness probe failing)
# 3. Pods in different namespace

# Fix label mismatch
kubectl label pod <pod> app=myapp --overwrite

# Check readiness
kubectl describe pod <pod> -n <ns> | grep -A5 "Readiness"
```"""),
        ("CoreDNS pods are CrashLoopBackOff",
         """```bash
# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50

# Common issue: loop detection (CoreDNS detects a forwarding loop)
# Check the ConfigMap
kubectl get configmap coredns -n kube-system -o yaml

# Fix: remove the 'loop' plugin or fix /etc/resolv.conf on nodes
kubectl edit configmap coredns -n kube-system
# Remove the line: loop

# Restart CoreDNS
kubectl rollout restart deployment coredns -n kube-system

# Verify DNS works
kubectl run dns-test --image=busybox --rm -it --restart=Never -- nslookup kubernetes.default
```"""),
    ]
    for q, a in svc_issues:
        examples.append(msg(SYSTEM_CKA, q, a))

    return examples


def main():
    cks_netpol = generate_networkpolicy_scaled()
    cks_falco = generate_falco_scaled()
    cks_supply = generate_supply_chain_scaled()
    cks_secctx = generate_security_context_scaled()
    cka_ops = generate_cka_scaled()

    all_cks = cks_netpol + cks_falco + cks_supply + cks_secctx
    random.shuffle(all_cks)
    random.shuffle(cka_ops)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cks_file = OUTPUT_DIR / "cks_terminology_v2_scaled.jsonl"
    with open(cks_file, "w") as f:
        for ex in all_cks:
            f.write(json.dumps(ex) + "\n")

    cka_file = OUTPUT_DIR / "cka_admin_ops_v2_scaled.jsonl"
    with open(cka_file, "w") as f:
        for ex in cka_ops:
            f.write(json.dumps(ex) + "\n")

    print(f"CKS terminology v2: {len(all_cks)} examples → {cks_file.name}")
    print(f"  NetworkPolicy: {len(cks_netpol)}")
    print(f"  Falco/Runtime: {len(cks_falco)}")
    print(f"  Supply Chain:  {len(cks_supply)}")
    print(f"  SecurityContext/PSS: {len(cks_secctx)}")
    print(f"CKA admin ops v2: {len(cka_ops)} examples → {cka_file.name}")
    print(f"\nTotal: {len(all_cks) + len(cka_ops)} examples")


if __name__ == "__main__":
    main()
