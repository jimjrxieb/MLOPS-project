#!/usr/bin/env python3
"""
CNPA (Cloud Native Platform Associate) Training Data Generator
================================================================
Generates training data covering the 13 CNPA topic gaps identified in the
Katie v2 corpus audit. Uses hybrid approach: hand-crafted seed examples +
parameterized templates for volume.

Target: ~3,000 high-quality examples across 14 modules.

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "cnpa_training_batch.jsonl"

SYSTEM_PROMPT = (
    "You are Katie, a CKA/CKS/CKAD/CNPA-certified autonomous Kubernetes engineer "
    "for GP-Copilot. You diagnose and fix production issues at 2 AM without human "
    "intervention. You provide complete, working fixes with exact commands and YAML "
    "manifests. You check ArgoCD ownership before any fix. You route by rank "
    "(E/D/C/B/S). You reference real tools: kubectl, Falco, Trivy, Kubescape, "
    "Kyverno, OPA/Rego, Helm, ArgoCD. You never hallucinate commands."
)

rng = random.Random(42)


def msg(user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]}


# ── Module 1: CNI & K8s Networking ────────────────────────────────────────
def generate_cni_networking():
    examples = []

    # Hand-crafted seeds
    examples.append(msg(
        "Compare Calico, Cilium, and Flannel CNI plugins for Kubernetes.",
        """**Calico:**
- Uses BGP for routing (no overlay by default) or VXLAN overlay
- Full NetworkPolicy support + Calico-specific GlobalNetworkPolicy
- eBPF dataplane option for high performance
- Best for: production clusters needing advanced network policy

```bash
# Install Calico
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml

# Check status
kubectl get pods -n calico-system
calicoctl node status
```

**Cilium:**
- eBPF-native (no iptables by default)
- L3/L4/L7 network policies (can filter HTTP paths, gRPC methods)
- Built-in observability with Hubble
- Service mesh without sidecars (Cilium Mesh)
- Best for: high-performance clusters, L7 visibility, sidecarless mesh

```bash
# Install Cilium
cilium install --version 1.15.0
cilium status
cilium hubble enable
```

**Flannel:**
- Simple VXLAN overlay
- No NetworkPolicy support (need Calico for policy if using Flannel)
- Minimal resource usage
- Best for: dev/test, learning environments, k3s default

| Feature | Calico | Cilium | Flannel |
|---------|--------|--------|---------|
| NetworkPolicy | Full + extended | Full + L7 | None |
| Dataplane | iptables/eBPF/BGP | eBPF | VXLAN |
| Performance | High | Highest | Moderate |
| Observability | Basic | Hubble (excellent) | None |
| Service mesh | No | Yes (sidecarless) | No |
| Complexity | Medium | Medium-High | Low |"""
    ))

    examples.append(msg(
        "How does kube-proxy work and what are the different modes?",
        """kube-proxy runs on every node and implements Kubernetes Service networking by programming the node's packet forwarding rules.

**iptables mode (default):**
- Creates iptables rules for each Service/Endpoint
- Random load balancing via iptables probability module
- O(n) rule lookup — slows down at >5,000 Services

```bash
# Check current mode
kubectl get cm kube-proxy -n kube-system -o yaml | grep mode

# View iptables rules for a service
iptables -t nat -L KUBE-SERVICES | grep my-service
```

**IPVS mode:**
- Uses Linux IPVS (IP Virtual Server) kernel module
- Hash-table lookup — O(1) regardless of Service count
- Supports multiple load balancing algorithms: rr, lc, dh, sh, sed, nq
- Better for large clusters (>1,000 Services)

```yaml
# Enable IPVS mode in kube-proxy config
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
mode: "ipvs"
ipvs:
  scheduler: "rr"  # round-robin
```

```bash
# Verify IPVS is active
kubectl logs -n kube-system -l k8s-app=kube-proxy | grep "Using ipvs"
ipvsadm -Ln  # List virtual servers on a node
```

**eBPF mode (Cilium replaces kube-proxy):**
- Cilium can fully replace kube-proxy
- eBPF programs attached directly to network interfaces
- No iptables/IPVS overhead
- Lowest latency, highest throughput

```bash
# Install Cilium without kube-proxy
cilium install --set kubeProxyReplacement=true
```

**When to switch from iptables:**
- >1,000 Services → IPVS
- Need L7 visibility → Cilium eBPF
- Latency-sensitive workloads → Cilium eBPF"""
    ))

    examples.append(msg(
        "How do you migrate from Ingress to Gateway API in Kubernetes?",
        """Gateway API is the successor to Ingress, providing more expressive routing.

**Key differences:**
- Ingress: single resource, limited routing
- Gateway API: GatewayClass → Gateway → HTTPRoute (separation of concerns)

**Step 1: Install Gateway API CRDs**
```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml
```

**Step 2: Create GatewayClass (platform team)**
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: production
spec:
  controllerName: gateway.envoyproxy.io/gatewayclass-controller
```

**Step 3: Create Gateway (platform team)**
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: gateway-system
spec:
  gatewayClassName: production
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: wildcard-cert
```

**Step 4: Create HTTPRoute (developer)**
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-routes
  namespace: production
spec:
  parentRefs:
  - name: main-gateway
    namespace: gateway-system
  hostnames:
  - "app.example.com"
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: api-service
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: frontend-service
      port: 3000
```

**Migration checklist:**
1. Install Gateway API CRDs
2. Deploy a Gateway controller (Envoy Gateway, Traefik, Cilium, NGINX)
3. Create GatewayClass + Gateway
4. Convert each Ingress rule to an HTTPRoute
5. Test with header-based routing before switching DNS
6. Remove old Ingress resources after validation"""
    ))

    # Parameterized: Pod networking troubleshooting
    symptoms = [
        ("Pod cannot reach another pod in the same namespace",
         "Check if NetworkPolicy is blocking:\n```bash\nkubectl get netpol -n {ns}\nkubectl describe netpol -n {ns}\n```\nCheck pod IPs and connectivity:\n```bash\nkubectl get pod -n {ns} -o wide\nkubectl exec {pod} -n {ns} -- wget -qO- --timeout=3 http://{target_ip}:{port}\n```\nCheck CNI pods are running:\n```bash\nkubectl get pods -n kube-system -l k8s-app=calico-node\n```"),
        ("Pod cannot resolve DNS names",
         "Check CoreDNS is running:\n```bash\nkubectl get pods -n kube-system -l k8s-app=kube-dns\nkubectl logs -n kube-system -l k8s-app=kube-dns\n```\nTest DNS from the pod:\n```bash\nkubectl exec {pod} -n {ns} -- nslookup kubernetes.default\nkubectl exec {pod} -n {ns} -- cat /etc/resolv.conf\n```\nCheck ndots setting (default 5 causes excessive DNS queries):\n```yaml\nspec:\n  dnsConfig:\n    options:\n    - name: ndots\n      value: \"2\"\n```"),
        ("Pod cannot reach external services (egress blocked)",
         "Check egress NetworkPolicy:\n```bash\nkubectl get netpol -n {ns} -o yaml | grep -A 20 egress\n```\nIf default-deny exists, add egress rule:\n```yaml\napiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: allow-external-egress\n  namespace: {ns}\nspec:\n  podSelector:\n    matchLabels:\n      app: {app}\n  policyTypes:\n  - Egress\n  egress:\n  - to:\n    - ipBlock:\n        cidr: 0.0.0.0/0\n        except:\n        - 10.0.0.0/8\n        - 172.16.0.0/12\n        - 192.168.0.0/16\n    ports:\n    - protocol: TCP\n      port: 443\n```"),
        ("Cross-namespace pod communication failing",
         "NetworkPolicy needs namespaceSelector for cross-namespace traffic:\n```yaml\napiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: allow-from-{source_ns}\n  namespace: {ns}\nspec:\n  podSelector:\n    matchLabels:\n      app: {app}\n  ingress:\n  - from:\n    - namespaceSelector:\n        matchLabels:\n          kubernetes.io/metadata.name: {source_ns}\n      podSelector:\n        matchLabels:\n          app: {source_app}\n    ports:\n    - protocol: TCP\n      port: {port}\n```\nVerify labels on source namespace:\n```bash\nkubectl get ns {source_ns} --show-labels\n```"),
    ]

    apps = ["api", "web", "worker", "gateway", "auth", "payments", "orders"]
    namespaces = ["production", "staging", "backend", "frontend", "data"]

    for _ in range(200):
        symptom, fix_template = rng.choice(symptoms)
        app = rng.choice(apps)
        ns = rng.choice(namespaces)
        port = rng.choice([80, 443, 8080, 8443, 3000, 5432, 6379])
        pod = f"{app}-{rng.randint(100,999)}"
        target_ip = f"10.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}"
        source_ns = rng.choice([n for n in namespaces if n != ns])
        source_app = rng.choice([a for a in apps if a != app])

        fix = fix_template.format(
            ns=ns, pod=pod, app=app, port=port, target_ip=target_ip,
            source_ns=source_ns, source_app=source_app
        )
        examples.append(msg(
            f"FINDING: {symptom}\nNamespace: {ns}, Pod: {pod}, App: {app}\nDiagnose and fix.",
            f"**Diagnosis and fix for {app} in {ns}:**\n\n{fix}"
        ))

    return examples


# ── Module 2: DNS ─────────────────────────────────────────────────────────
def generate_dns():
    examples = []

    examples.append(msg(
        "How does CoreDNS work in Kubernetes and how do you troubleshoot DNS issues?",
        """CoreDNS is the default DNS server in Kubernetes, running as a Deployment in kube-system.

**How it works:**
1. kubelet configures each pod's `/etc/resolv.conf` to point to the CoreDNS ClusterIP
2. Pod makes DNS query → CoreDNS Service → CoreDNS pod
3. CoreDNS resolves: `<service>.<namespace>.svc.cluster.local`

**Corefile (CoreDNS config):**
```
.:53 {
    errors
    health { lameduck 5s }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    forward . /etc/resolv.conf { max_concurrent 1000 }
    cache 30
    loop
    reload
    loadbalance
}
```

**Troubleshooting steps:**
```bash
# 1. Check CoreDNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50

# 2. Test DNS from a debug pod
kubectl run dnstest --image=busybox:1.36 --rm -it -- nslookup kubernetes.default

# 3. Check pod's resolv.conf
kubectl exec <pod> -- cat /etc/resolv.conf
# Should show: nameserver <CoreDNS-ClusterIP>

# 4. Check CoreDNS ConfigMap
kubectl get cm coredns -n kube-system -o yaml

# 5. Check if CoreDNS Service exists
kubectl get svc kube-dns -n kube-system
```

**Common issues:**
- **ndots:5 (default)** causes 5 DNS queries per external lookup. Fix:
```yaml
spec:
  dnsConfig:
    options:
    - name: ndots
      value: "2"
```
- **CoreDNS OOMKilled** — increase memory limits
- **DNS timeout** — check NetworkPolicy isn't blocking UDP/TCP 53 to kube-system"""
    ))

    examples.append(msg(
        "How do you configure custom DNS entries in CoreDNS for Kubernetes?",
        """Edit the CoreDNS ConfigMap to add custom DNS entries.

**Add a stub domain (forward queries for a specific domain to another DNS server):**
```bash
kubectl edit cm coredns -n kube-system
```

```
.:53 {
    errors
    health
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
    }
    # Forward internal.corp queries to corporate DNS
    forward internal.corp 10.0.0.53
    # Default upstream
    forward . /etc/resolv.conf
    cache 30
    reload
}
```

**Add static entries (hosts plugin):**
```
.:53 {
    hosts {
        10.0.1.100 legacy-db.internal
        10.0.1.101 legacy-api.internal
        fallthrough
    }
    kubernetes cluster.local in-addr.arpa ip6.arpa
    forward . /etc/resolv.conf
    cache 30
}
```

**Use external-dns for automatic DNS records:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: external-dns
spec:
  template:
    spec:
      containers:
      - name: external-dns
        image: registry.k8s.io/external-dns/external-dns:v0.14.0
        args:
        - --source=service
        - --source=ingress
        - --provider=aws
        - --domain-filter=example.com
        - --policy=sync
```

After editing CoreDNS ConfigMap, it auto-reloads (no restart needed due to `reload` plugin)."""
    ))

    return examples


# ── Module 3: Service Mesh ────────────────────────────────────────────────
def generate_service_mesh():
    examples = []

    examples.append(msg(
        "How do you enable strict mTLS in Istio across the entire mesh?",
        """Enable mesh-wide strict mTLS with a PeerAuthentication policy:

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system  # mesh-wide when in istio-system
spec:
  mtls:
    mode: STRICT
```

**Per-namespace override (if needed):**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: legacy-apps
spec:
  mtls:
    mode: PERMISSIVE  # Allow both mTLS and plaintext during migration
```

**Verify mTLS is active:**
```bash
# Check if mTLS is enabled between services
istioctl x describe pod <pod-name> -n <namespace>

# Check proxy config
istioctl proxy-config cluster <pod-name> -n <namespace> | grep tls

# Check mTLS status with Kiali
kubectl port-forward svc/kiali -n istio-system 20001:20001
```

**AuthorizationPolicy (L7 access control with mTLS):**
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-payment-from-api
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/production/sa/api-service"]
    to:
    - operation:
        methods: ["POST"]
        paths: ["/api/v1/charge"]
```

This ensures only the api-service ServiceAccount can POST to the payment endpoint — identity verified by mTLS certificates."""
    ))

    examples.append(msg(
        "Compare sidecar-based service mesh (Istio) vs sidecarless (Cilium Service Mesh).",
        """**Sidecar model (Istio, Linkerd):**
- Every pod gets an Envoy proxy sidecar injected
- Proxy intercepts all traffic in/out of the pod
- ~50MB memory overhead per sidecar
- Adds ~1-3ms latency per hop

```yaml
# Istio sidecar injection (per namespace)
kubectl label namespace production istio-injection=enabled

# Per-pod opt-out
metadata:
  annotations:
    sidecar.istio.io/inject: "false"
```

**Sidecarless model (Cilium, Istio Ambient):**
- No sidecar containers — mesh logic runs in the CNI (node-level)
- eBPF programs handle L3/L4 policy, mTLS, and observability
- Zero per-pod overhead
- Lower latency (~0.1ms)

```bash
# Cilium with mesh enabled
cilium install --set mesh.enabled=true
# L7 policies without sidecars:
cilium hubble observe --namespace production
```

**Istio Ambient Mesh (hybrid):**
- L4 (mTLS, TCP policy) → ztunnel (per-node DaemonSet, no sidecar)
- L7 (HTTP routing, retries) → waypoint proxy (only where needed)

```yaml
# Enable ambient mode for a namespace
kubectl label namespace production istio.io/dataplane-mode=ambient
```

| Feature | Sidecar (Istio) | Sidecarless (Cilium) | Ambient (Istio) |
|---------|-----------------|---------------------|------------------|
| Memory overhead | ~50MB/pod | 0/pod | ~10MB/node |
| Latency added | 1-3ms/hop | <0.1ms | <0.5ms (L4) |
| L7 features | Full | Growing | Full (via waypoint) |
| mTLS | Yes | Yes (WireGuard) | Yes (ztunnel) |
| Observability | Envoy metrics | Hubble (eBPF) | Both |
| Maturity | Production | Production | Beta |"""
    ))

    return examples


# ── Module 4: Observability ───────────────────────────────────────────────
def generate_observability():
    examples = []

    examples.append(msg(
        "Design a complete observability stack for Kubernetes using open-source tools.",
        """The three pillars of observability: metrics, logs, traces.

**Metrics: Prometheus + Grafana**
```bash
# Install kube-prometheus-stack (Prometheus + Grafana + alerting)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

ServiceMonitor for custom app metrics:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: myapp
  endpoints:
  - port: metrics
    interval: 30s
  namespaceSelector:
    any: true
```

**Logs: Grafana Loki + Promtail**
```bash
helm install loki grafana/loki-stack -n monitoring \\
  --set promtail.enabled=true \\
  --set loki.persistence.enabled=true
```

LogQL query examples:
```logql
# Error logs from production namespace
{namespace="production"} |= "error" | json | level="error"

# Request latency from structured logs
{app="api"} | json | latency > 500
```

**Traces: Grafana Tempo + OpenTelemetry**
```bash
helm install tempo grafana/tempo -n monitoring
```

OTel Collector for trace collection:
```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: otel
  namespace: monitoring
spec:
  config: |
    receivers:
      otlp:
        protocols:
          grpc: { endpoint: 0.0.0.0:4317 }
          http: { endpoint: 0.0.0.0:4318 }
    exporters:
      otlp:
        endpoint: tempo.monitoring:4317
        tls: { insecure: true }
    service:
      pipelines:
        traces:
          receivers: [otlp]
          exporters: [otlp]
```

**Alerting: Alertmanager**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: sre-alerts
spec:
  groups:
  - name: availability
    rules:
    - alert: HighErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
        /
        sum(rate(http_requests_total[5m])) by (service)
        > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "{{ $labels.service }} error rate > 5%"
```"""
    ))

    # Parameterized: PromQL queries
    promql_scenarios = [
        ("CPU usage by namespace", 'sum(rate(container_cpu_usage_seconds_total{{namespace="{ns}"}}[5m])) by (pod)'),
        ("Memory usage percentage", '(container_memory_working_set_bytes{{namespace="{ns}",container!=""}} / kube_pod_container_resource_limits{{resource="memory",namespace="{ns}"}}) * 100'),
        ("Pod restart count", 'sum(kube_pod_container_status_restarts_total{{namespace="{ns}"}}) by (pod) > {threshold}'),
        ("Request rate per service", 'sum(rate(http_requests_total{{namespace="{ns}"}}[5m])) by (service)'),
        ("P99 latency", 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{{namespace="{ns}"}}[5m])) by (le, service))'),
        ("Disk usage on nodes", '(1 - node_filesystem_avail_bytes{{mountpoint="/"}} / node_filesystem_size_bytes{{mountpoint="/"}}) * 100 > {threshold}'),
        ("Network receive bytes", 'sum(rate(container_network_receive_bytes_total{{namespace="{ns}"}}[5m])) by (pod)'),
        ("OOMKilled pods", 'kube_pod_container_status_last_terminated_reason{{reason="OOMKilled",namespace="{ns}"}}'),
    ]

    for _ in range(100):
        desc, query_template = rng.choice(promql_scenarios)
        ns = rng.choice(["production", "staging", "monitoring", "backend"])
        threshold = rng.choice([3, 5, 10, 80, 90])
        query = query_template.format(ns=ns, threshold=threshold)

        examples.append(msg(
            f"Write a PromQL query for: {desc} in namespace {ns}",
            f"```promql\n{query}\n```\n\n"
            f"Use in a Grafana dashboard panel or PrometheusRule alert.\n"
            f"Add `for: 5m` in alerting rules to avoid flapping."
        ))

    return examples


# ── Module 5: GitOps & CI/CD ─────────────────────────────────────────────
def generate_gitops():
    examples = []

    examples.append(msg(
        "Compare ArgoCD and Flux for GitOps in Kubernetes.",
        """Both are CNCF GitOps controllers that sync Kubernetes state from Git.

**ArgoCD:**
- Web UI with real-time sync visualization
- Application CRD defines what to deploy
- Multi-tenancy via AppProjects
- SSO integration (OIDC, SAML)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/app-config
    path: overlays/production
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

**Flux:**
- No UI (CLI + CRDs only)
- GitRepository + Kustomization CRDs
- Native Helm support via HelmRelease
- Multi-tenancy via namespaced reconcilers

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: app-config
  namespace: flux-system
spec:
  url: https://github.com/org/app-config
  interval: 1m
  ref:
    branch: main
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: myapp
  namespace: flux-system
spec:
  sourceRef:
    kind: GitRepository
    name: app-config
  path: ./overlays/production
  interval: 5m
  prune: true
```

| Feature | ArgoCD | Flux |
|---------|--------|------|
| UI | Yes (web dashboard) | No (CLI only) |
| Helm support | Via Application | Native HelmRelease CRD |
| Multi-cluster | Yes (hub-spoke) | Yes (via Kustomization) |
| RBAC | AppProjects + OIDC | Kubernetes RBAC |
| Notifications | Built-in | Via notification-controller |
| Image automation | Via Argo Image Updater | Built-in image-automation-controller |

**Choose ArgoCD** when: you need a UI, multi-team visibility, or complex multi-cluster deployments.
**Choose Flux** when: you want lightweight GitOps, prefer pure CRDs, or need native Helm release management."""
    ))

    examples.append(msg(
        "How do you implement ArgoCD ApplicationSets for multi-cluster or multi-environment deployments?",
        """ApplicationSets generate ArgoCD Applications from templates + generators.

**Git directory generator (one app per environment):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-environments
  namespace: argocd
spec:
  generators:
  - git:
      repoURL: https://github.com/org/app-config
      revision: main
      directories:
      - path: overlays/*
  template:
    metadata:
      name: 'myapp-{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/app-config
        targetRevision: main
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
```

This creates `myapp-dev`, `myapp-staging`, `myapp-production` from:
```
overlays/
  dev/
  staging/
  production/
```

**Cluster generator (deploy to all clusters):**
```yaml
spec:
  generators:
  - clusters:
      selector:
        matchLabels:
          env: production
  template:
    spec:
      destination:
        server: '{{server}}'
        namespace: production
```

**Matrix generator (environments x clusters):**
```yaml
spec:
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/org/app-config
          directories:
          - path: apps/*
      - clusters:
          selector:
            matchLabels:
              env: production
```"""
    ))

    return examples


# ── Module 6: Platform Engineering ────────────────────────────────────────
def generate_platform_engineering():
    examples = []

    examples.append(msg(
        "What is KEDA and how does it differ from HPA for autoscaling?",
        """KEDA (Kubernetes Event-Driven Autoscaling) extends HPA with external event sources.

**HPA** scales based on CPU/memory metrics only:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**KEDA** scales from 0 based on external events:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: worker-scaler
spec:
  scaleTargetRef:
    name: worker
  minReplicaCount: 0    # Scale to zero!
  maxReplicaCount: 50
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka:9092
      consumerGroup: workers
      topic: jobs
      lagThreshold: "100"  # Scale when 100+ messages in queue
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: http_requests_queued
      threshold: "50"
      query: sum(http_requests_queued{app="worker"})
```

```bash
# Install KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda -n keda --create-namespace
```

| Feature | HPA | KEDA |
|---------|-----|------|
| Scale to zero | No (min 1) | Yes |
| Metrics sources | CPU, memory, custom | 60+ scalers (Kafka, SQS, Redis, Prometheus, Cron, etc.) |
| Event-driven | No | Yes |
| Cron-based | No | Yes (scheduled scaling) |
| Install | Built-in | Requires KEDA operator |

**Use HPA** for: simple CPU/memory-based scaling.
**Use KEDA** for: queue workers, event processors, batch jobs, scale-to-zero."""
    ))

    examples.append(msg(
        "How do you set up vCluster for multi-tenancy in Kubernetes?",
        """vCluster creates lightweight virtual Kubernetes clusters inside namespaces of a host cluster.

```bash
# Install vCluster CLI
curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64"
chmod +x vcluster && sudo mv vcluster /usr/local/bin/

# Create a virtual cluster
vcluster create team-alpha -n team-alpha --connect=false

# Connect to the vCluster
vcluster connect team-alpha -n team-alpha
# Now kubectl commands target the virtual cluster
kubectl get nodes  # Shows virtual node
```

**How it works:**
- vCluster runs a lightweight K8s control plane (k3s/k0s) inside a pod
- Resources created in the vCluster are synced to the host namespace
- Each team gets full cluster-admin inside their vCluster
- Host cluster resources are isolated per namespace

**Helm-based deployment:**
```yaml
# vcluster-values.yaml
vcluster:
  image: rancher/k3s:v1.28.2-k3s1
sync:
  ingresses:
    enabled: true
  persistentvolumes:
    enabled: true
syncer:
  extraArgs:
  - --tls-san=team-alpha.example.com
```

```bash
helm install team-alpha vcluster/vcluster -n team-alpha -f vcluster-values.yaml
```

**vs. Namespace multi-tenancy:**

| | Namespaces | vCluster |
|---|---|---|
| Isolation | Soft (NetworkPolicy, RBAC) | Hard (separate API server) |
| CRDs | Shared across cluster | Per-vCluster |
| cluster-admin | No (too dangerous) | Yes (scoped to vCluster) |
| Resource overhead | None | ~200MB per vCluster |
| Best for | Teams sharing a cluster | Teams needing full control |"""
    ))

    return examples


# ── Module 7: IaC ────────────────────────────────────────────────────────
def generate_iac():
    examples = []

    examples.append(msg(
        "How do you structure a Helm chart for a production Kubernetes application?",
        """A production Helm chart should include security, observability, and resilience by default.

```
mychart/
  Chart.yaml
  values.yaml
  templates/
    deployment.yaml
    service.yaml
    hpa.yaml
    networkpolicy.yaml
    servicemonitor.yaml
    _helpers.tpl
```

**values.yaml (secure defaults):**
```yaml
replicaCount: 2

image:
  repository: registry.example.com/myapp
  tag: ""  # Set by CI/CD, never :latest
  pullPolicy: IfNotPresent

securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

containerSecurityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: [ALL]

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilization: 70

probes:
  liveness:
    path: /healthz
    port: 8080
    initialDelaySeconds: 15
  readiness:
    path: /ready
    port: 8080
    initialDelaySeconds: 5

serviceMonitor:
  enabled: true
  interval: 30s

networkPolicy:
  enabled: true

serviceAccount:
  create: true
  automountServiceAccountToken: false
```

**Anti-patterns to avoid:**
- `image.tag: latest` → pin digests or semver
- No resource limits → OOM kills, noisy neighbors
- `securityContext: {}` → fails admission control
- No probes → K8s can't detect unhealthy pods
- No NetworkPolicy → unrestricted pod communication"""
    ))

    return examples


# ── Module 8: Cloud Networking ────────────────────────────────────────────
def generate_cloud_networking():
    examples = []

    examples.append(msg(
        "Explain VPC design for an EKS cluster with public and private subnets.",
        """Production EKS VPC layout:

```
VPC: 10.0.0.0/16
├── Public subnets (for ALB, NAT Gateway)
│   ├── 10.0.1.0/24  (us-east-1a)
│   ├── 10.0.2.0/24  (us-east-1b)
│   └── 10.0.3.0/24  (us-east-1c)
├── Private subnets (for EKS worker nodes)
│   ├── 10.0.11.0/24 (us-east-1a)
│   ├── 10.0.12.0/24 (us-east-1b)
│   └── 10.0.13.0/24 (us-east-1c)
└── Isolated subnets (for RDS, ElastiCache)
    ├── 10.0.21.0/24 (us-east-1a)
    └── 10.0.22.0/24 (us-east-1b)
```

**Terraform:**
```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.0"

  name = "eks-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnets = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false  # One per AZ for HA
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # Tags required for EKS
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}
```

**Key design decisions:**
- Worker nodes in **private subnets** — no direct internet access
- NAT Gateway in **public subnets** — outbound internet for pulling images
- ALB in **public subnets** — ingress traffic
- RDS in **isolated subnets** — no internet access, only VPC internal
- One NAT Gateway per AZ for high availability (cost vs resilience tradeoff)
- `/24` subnets give 251 usable IPs per subnet (enough for most workloads)"""
    ))

    return examples


# ── Module 9: Container Runtime ───────────────────────────────────────────
def generate_container_runtime():
    examples = []

    examples.append(msg(
        "Explain the container runtime stack: containerd, CRI, OCI, and how they relate.",
        """The container runtime stack in Kubernetes:

```
kubelet
  ↓ CRI (Container Runtime Interface)
containerd (or CRI-O)
  ↓ OCI Runtime Spec
runc (or kata-containers, gVisor)
  ↓
Linux kernel (namespaces, cgroups, seccomp)
```

**CRI (Container Runtime Interface):**
- gRPC API that kubelet uses to manage containers
- `RuntimeService` — create/start/stop/remove containers
- `ImageService` — pull/list/remove images
- kubelet doesn't care which runtime implements CRI

**containerd:**
- Default runtime in most K8s distributions (EKS, GKE, AKS, k3s)
- Manages full container lifecycle
- Uses runc to actually create containers
- Replaced Docker as the K8s runtime (dockershim removed in 1.24)

```bash
# Check which runtime your cluster uses
kubectl get nodes -o wide  # CONTAINER-RUNTIME column
# crictl (CRI CLI) to inspect containers
crictl ps
crictl images
```

**OCI (Open Container Initiative):**
- **OCI Image Spec** — defines container image format (layers, config, manifest)
- **OCI Runtime Spec** — defines how to run a container (namespaces, cgroups, mounts)
- runc is the reference OCI runtime implementation

**Alternative runtimes:**
- **gVisor (runsc)** — user-space kernel, intercepts syscalls, sandboxed
- **Kata Containers** — lightweight VMs, hardware isolation
- **youki** — OCI runtime written in Rust (faster startup)

```yaml
# Use gVisor as RuntimeClass
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
---
apiVersion: v1
kind: Pod
metadata:
  name: sandboxed-pod
spec:
  runtimeClassName: gvisor
  containers:
  - name: app
    image: nginx
```"""
    ))

    return examples


# ── Module 10: Autoscaling ────────────────────────────────────────────────
def generate_autoscaling():
    examples = []

    examples.append(msg(
        "Compare HPA, VPA, Cluster Autoscaler, and KEDA for Kubernetes autoscaling.",
        """Four layers of autoscaling in Kubernetes:

**1. HPA (Horizontal Pod Autoscaler)** — scales pod count
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**2. VPA (Vertical Pod Autoscaler)** — adjusts resource requests/limits
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  updatePolicy:
    updateMode: "Auto"  # or "Off" for recommendations only
  resourcePolicy:
    containerPolicies:
    - containerName: api
      minAllowed:
        cpu: 50m
        memory: 64Mi
      maxAllowed:
        cpu: 2
        memory: 4Gi
```

**3. Cluster Autoscaler** — scales node count
```bash
# Adjusts node groups based on pending pods
# Configured via cloud provider (EKS managed node group, GKE node pool)
```

**4. KEDA** — event-driven scaling (scale to zero)
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
spec:
  scaleTargetRef:
    name: worker
  minReplicaCount: 0
  triggers:
  - type: kafka
    metadata:
      topic: jobs
      lagThreshold: "100"
```

| Scaler | What it scales | Input | Scale to zero |
|--------|---------------|-------|---------------|
| HPA | Pod replicas | CPU/memory/custom | No (min 1) |
| VPA | Pod resources | Historical usage | N/A |
| Cluster Autoscaler | Nodes | Pending pods | Yes (node pools) |
| KEDA | Pod replicas | External events | Yes |

**Don't combine HPA + VPA on the same metric** (CPU). Use VPA for right-sizing, HPA for scaling."""
    ))

    return examples


# ── Module 11: Troubleshooting (parameterized) ───────────────────────────
def generate_troubleshooting():
    examples = []

    scenarios = [
        {
            "symptom": "Service {svc} in namespace {ns} returns connection refused",
            "steps": """1. Check if pods are running:
```bash
kubectl get pods -n {ns} -l app={app}
kubectl describe pod -n {ns} -l app={app} | grep -A5 "State:"
```

2. Check Service endpoints:
```bash
kubectl get endpoints {svc} -n {ns}
# If ENDPOINTS is empty → selector doesn't match pod labels
kubectl get svc {svc} -n {ns} -o yaml | grep -A3 selector
kubectl get pods -n {ns} --show-labels
```

3. Check port mapping:
```bash
kubectl get svc {svc} -n {ns} -o yaml | grep -A5 ports
# Verify targetPort matches container port
kubectl get pod -n {ns} -l app={app} -o jsonpath='{{.items[0].spec.containers[0].ports}}'
```

4. Test from inside the cluster:
```bash
kubectl run debug --image=busybox:1.36 --rm -it -- wget -qO- --timeout=3 http://{svc}.{ns}:{port}
```"""
        },
        {
            "symptom": "Pods in namespace {ns} stuck in Pending state",
            "steps": """1. Check events:
```bash
kubectl describe pod -n {ns} -l app={app} | grep -A10 Events
```

2. Common causes:
- **Insufficient resources**: `0/3 nodes are available: 3 Insufficient cpu`
```bash
kubectl top nodes
kubectl describe node | grep -A5 "Allocated resources"
```
- **No matching node (taints/tolerations)**:
```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints
```
- **PVC not bound**:
```bash
kubectl get pvc -n {ns}
kubectl describe pvc -n {ns} | grep -A5 Events
```
- **Scheduling constraint (affinity/nodeSelector)**:
```bash
kubectl get pod -n {ns} -o yaml | grep -A10 nodeSelector
kubectl get pod -n {ns} -o yaml | grep -A20 affinity
```

3. Fix: scale node pool, adjust requests, or relax scheduling constraints."""
        },
        {
            "symptom": "Ingress/HTTPRoute for {app}.example.com returns 404",
            "steps": """1. Check the HTTPRoute/Ingress:
```bash
kubectl get httproute -n {ns}
kubectl get ingress -n {ns}
kubectl describe httproute -n {ns} | grep -A20 Rules
```

2. Check backend Service exists and has endpoints:
```bash
kubectl get svc {svc} -n {ns}
kubectl get endpoints {svc} -n {ns}
```

3. Check Gateway/IngressController:
```bash
kubectl get gateway -A
kubectl get pods -n gateway-system
kubectl logs -n gateway-system -l app=envoy-gateway --tail=50
```

4. Test backend directly:
```bash
kubectl port-forward svc/{svc} -n {ns} {port}:{port}
curl http://localhost:{port}/
```

5. Check TLS if HTTPS:
```bash
kubectl get secret -n {ns} | grep tls
kubectl describe certificate -n {ns}  # if using cert-manager
```"""
        },
    ]

    apps = ["api", "web", "auth", "payments", "orders", "search", "notifications"]
    namespaces = ["production", "staging", "backend", "frontend"]

    for _ in range(200):
        scenario = rng.choice(scenarios)
        app = rng.choice(apps)
        ns = rng.choice(namespaces)
        svc = f"{app}-service"
        port = rng.choice([80, 443, 8080, 3000])

        symptom = scenario["symptom"].format(svc=svc, ns=ns, app=app)
        steps = scenario["steps"].format(svc=svc, ns=ns, app=app, port=port)

        examples.append(msg(
            f"INCIDENT: {symptom}\nDiagnose and fix.",
            f"**Troubleshooting {app} in {ns}:**\n\n{steps}"
        ))

    return examples


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    all_examples = []

    generators = [
        ("CNI & K8s Networking", generate_cni_networking),
        ("DNS", generate_dns),
        ("Service Mesh", generate_service_mesh),
        ("Observability", generate_observability),
        ("GitOps & CI/CD", generate_gitops),
        ("Platform Engineering", generate_platform_engineering),
        ("IaC (Helm)", generate_iac),
        ("Cloud Networking", generate_cloud_networking),
        ("Container Runtime", generate_container_runtime),
        ("Autoscaling", generate_autoscaling),
        ("Troubleshooting", generate_troubleshooting),
    ]

    for i, (name, gen_fn) in enumerate(generators, 1):
        examples = gen_fn()
        all_examples.extend(examples)
        print(f"  [{i}/{len(generators)}] {name}: {len(examples)} examples")

    rng.shuffle(all_examples)

    from generate_utils import write_training_data
    write_training_data(
        examples=all_examples,
        output_file=OUTPUT_FILE,
        generator="generate_cnpa_training.py",
        domain="CNPA",
    )


if __name__ == "__main__":
    main()
