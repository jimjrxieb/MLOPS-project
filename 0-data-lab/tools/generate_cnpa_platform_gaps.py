#!/usr/bin/env python3
"""
CNPA Platform Engineering Gap Training Data Generator
======================================================
Priority 3: Targeted holes in platform engineering knowledge.

Targets: Sealed Secrets, External Secrets Operator, Kyverno/OPA as admission controllers,
Crossplane XRDs, Istio circuit breaking, GitOps terminology, OpenTelemetry.

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "cnpa_platform_gaps.jsonl"

SYSTEM_PROMPT = "You are JADE, a cloud-native platform architect. You specialize in Kubernetes platform engineering, service mesh, GitOps, and observability. Use exact tool and resource names: Kyverno, OPA/Gatekeeper, Crossplane, ArgoCD, Flux, Sealed Secrets, External Secrets Operator, OpenTelemetry."

def msg(system, user, assistant):
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}

def generate_secrets_gitops():
    """Sealed Secrets, External Secrets Operator, SOPS, KMS — missed in eval."""
    examples = []
    scenarios = [
        {
            "q": "How do you manage secrets in a GitOps workflow without storing them in Git?",
            "a": """Three main approaches for secrets in GitOps:

**1. Sealed Secrets (Bitnami)**
Encrypt secrets client-side, store encrypted version in Git:
```bash
# Install kubeseal CLI
brew install kubeseal

# Create a regular Secret, then seal it
kubectl create secret generic db-creds \\
  --from-literal=password=supersecret \\
  --dry-run=client -o yaml | \\
  kubeseal --format yaml > sealed-db-creds.yaml
```

```yaml
# sealed-db-creds.yaml — safe to commit to Git
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-creds
spec:
  encryptedData:
    password: AgBf2+... # encrypted with cluster's public key
```

**2. External Secrets Operator (ESO)**
Syncs secrets from external vaults into Kubernetes:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-creds
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: db-creds
  data:
  - secretKey: password
    remoteRef:
      key: prod/database/password
```

**3. SOPS + KMS**
Encrypt YAML values in-place using AWS KMS, GCP KMS, or age:
```bash
# Encrypt with SOPS
sops --encrypt --kms arn:aws:kms:us-east-1:123:key/abc secrets.yaml > secrets.enc.yaml

# ArgoCD/Flux decrypt at deploy time with SOPS plugin
```

**Recommendation:** Use External Secrets Operator for cloud-native stacks (AWS/GCP/Azure). Use Sealed Secrets for air-gapped or on-prem. Use SOPS for small teams who want file-level encryption."""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_admission_controller_examples():
    """Kyverno, OPA/Gatekeeper as admission controllers — missed in eval."""
    examples = []
    scenarios = [
        {
            "q": "Compare Kyverno and OPA Gatekeeper as Kubernetes admission controllers.",
            "a": """Both Kyverno and OPA Gatekeeper are Kubernetes admission controllers that enforce policies at deploy time:

**Kyverno:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: Enforce
  rules:
  - name: check-team-label
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "Label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
```

**OPA Gatekeeper:**
```yaml
# ConstraintTemplate (defines the policy logic in Rego)
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8srequiredlabels
      violation[{"msg": msg}] {
        provided := {label | input.review.object.metadata.labels[label]}
        required := {label | label := input.parameters.labels[_]}
        missing := required - provided
        count(missing) > 0
        msg := sprintf("Missing labels: %v", [missing])
      }
---
# Constraint (applies the template with parameters)
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-team-label
spec:
  match:
    kinds:
    - apiGroups: [""]
      kinds: ["Pod"]
  parameters:
    labels: ["team"]
```

**Comparison:**

| Feature | Kyverno | OPA Gatekeeper |
|---------|---------|----------------|
| Policy language | YAML (native K8s) | Rego (custom language) |
| Learning curve | Low — YAML patterns | High — Rego is complex |
| Mutation support | Yes (built-in) | Yes (via assign/modify) |
| Generate resources | Yes (auto-create NetworkPolicy, etc.) | No |
| Image verification | Yes (Cosign, Notary) | No (needs external) |
| Audit mode | `validationFailureAction: Audit` | `enforcementAction: dryrun` |

**Recommendation:** Kyverno for teams that want YAML-native policies. OPA Gatekeeper for teams already using Rego or needing complex cross-resource logic."""
        },
        {
            "q": "Design a CI/CD pipeline with security gates using admission controllers.",
            "a": """A secure CI/CD pipeline should have gates at every stage:

**Pipeline stages:**
```
Code → SAST → Build → Container Scan → Image Sign → Policy Check → Deploy → Runtime Monitor
```

**Stage 1: SAST (Static Analysis)**
```yaml
# GitHub Actions
- name: Run SAST
  uses: returntocorp/semgrep-action@v1
  with:
    config: p/owasp-top-ten
```

**Stage 2: Container Scan**
```bash
# Scan image for vulnerabilities with Trivy
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:$TAG
```

**Stage 3: Image Signing**
```bash
# Sign with Cosign
cosign sign --key cosign.key registry.example.com/myapp:$TAG
```

**Stage 4: Admission Controller enforcement (Kyverno)**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-and-scan
spec:
  validationFailureAction: Enforce
  rules:
  - name: verify-signature
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
              <COSIGN_PUBLIC_KEY>
              -----END PUBLIC KEY-----
  - name: require-scan-label
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "Pods must have a scan-passed label"
      pattern:
        metadata:
          labels:
            security-scan: "passed"
```

**Stage 5: OPA policy check (pre-deploy)**
```bash
# Validate manifests against OPA policies before applying
conftest test deployment.yaml --policy policies/
```

**Stage 6: Runtime monitoring with Falco**
- Falco watches for anomalous behavior post-deployment
- Admission controller blocks unsigned/unscanned images at the gate
- Kyverno or OPA Gatekeeper enforces security policies as the admission controller"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_crossplane_examples():
    """Crossplane XRD, Composition, Claim — missed in eval."""
    examples = []
    scenarios = [
        {
            "q": "How does Crossplane enable platform teams to offer cloud resources as Kubernetes APIs?",
            "a": """Crossplane extends Kubernetes with custom resource definitions (CRDs) that represent cloud infrastructure. Platform teams define abstractions that developers consume via standard `kubectl` commands.

**Core concepts:**

1. **Provider** — connects to a cloud (AWS, GCP, Azure):
```yaml
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-aws
spec:
  package: xpkg.upbound.io/upbound/provider-aws-s3:v1.1.0
```

2. **CompositeResourceDefinition (XRD)** — defines the API schema:
```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: CompositeResourceDefinition
metadata:
  name: xdatabases.platform.example.com
spec:
  group: platform.example.com
  names:
    kind: XDatabase
    plural: xdatabases
  claimNames:
    kind: Database
    plural: databases
  versions:
  - name: v1alpha1
    served: true
    referenceable: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              engine:
                type: string
                enum: ["postgres", "mysql"]
              size:
                type: string
                enum: ["small", "medium", "large"]
```

3. **Composition** — maps the abstraction to real cloud resources:
```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: database-aws
spec:
  compositeTypeRef:
    apiVersion: platform.example.com/v1alpha1
    kind: XDatabase
  resources:
  - name: rds-instance
    base:
      apiVersion: rds.aws.upbound.io/v1beta1
      kind: Instance
      spec:
        forProvider:
          engine: postgres
          instanceClass: db.t3.medium
          allocatedStorage: 20
```

4. **Claim** — what developers actually create:
```yaml
# Developer creates this — no cloud knowledge needed
apiVersion: platform.example.com/v1alpha1
kind: Database
metadata:
  name: my-app-db
  namespace: team-alpha
spec:
  engine: postgres
  size: medium
```

**The platform team pattern:**
- Platform team creates XRDs + Compositions (the "golden path")
- Developers create Claims (simple, guardrailed)
- Crossplane's control plane reconciles Claims → cloud resources
- Same Kubernetes API, same RBAC, same GitOps workflow"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_istio_circuit_breaking():
    """Circuit breaking with DestinationRule, outlierDetection, connectionPool — 0% in eval."""
    examples = []
    scenarios = [
        {
            "q": "How do you configure circuit breaking in Istio?",
            "a": """Configure circuit breaking using a DestinationRule with connectionPool and outlierDetection:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: payment-service-cb
  namespace: production
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: DEFAULT
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 50
```

**How it works:**

**connectionPool** — limits concurrent connections:
- `maxConnections: 100` — max 100 TCP connections to the service
- `http1MaxPendingRequests: 100` — max 100 queued HTTP/1.1 requests
- `maxRetries: 3` — max 3 retry attempts

**outlierDetection** — ejects unhealthy endpoints:
- `consecutive5xxErrors: 5` — eject after 5 consecutive 5xx errors
- `interval: 10s` — check health every 10 seconds
- `baseEjectionTime: 30s` — ejected for at least 30 seconds
- `maxEjectionPercent: 50` — never eject more than 50% of endpoints

**Why circuit breaking prevents cascading failures:**
1. Service A calls Service B
2. Service B starts returning 5xx errors
3. outlierDetection ejects unhealthy Service B pods
4. connectionPool limits prevent Service A from overwhelming remaining pods
5. After baseEjectionTime, ejected pods are retried
6. Without circuit breaking, Service A would queue requests → timeout → cascade to Service C, D, E

**Verify:**
```bash
# Check Envoy stats for circuit breaker trips
kubectl exec <pod-with-sidecar> -c istio-proxy -- pilot-agent request GET stats | grep circuit
```"""
        },
        {
            "q": "How do you implement canary deployments with Istio VirtualService and DestinationRule?",
            "a": """Canary deployment splits traffic between stable and canary versions:

**Step 1: DestinationRule — define subsets**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: myapp-dr
  namespace: production
spec:
  host: myapp
  subsets:
  - name: stable
    labels:
      version: v1
  - name: canary
    labels:
      version: v2
```

**Step 2: VirtualService — route traffic by weight**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: myapp-vs
  namespace: production
spec:
  hosts:
  - myapp
  http:
  - route:
    - destination:
        host: myapp
        subset: stable
      weight: 90
    - destination:
        host: myapp
        subset: canary
      weight: 10
```

**Step 3: Gradually shift traffic**
```bash
# Start: 90% stable, 10% canary
# Monitor error rates, latency, success rates

# If canary is healthy, increase:
# 90/10 → 75/25 → 50/50 → 25/75 → 0/100

# If canary fails, rollback:
kubectl patch virtualservice myapp-vs -p '
{"spec":{"http":[{"route":[{"destination":{"host":"myapp","subset":"stable"},"weight":100}]}]}}'
```

**Header-based routing (for testing):**
```yaml
http:
- match:
  - headers:
      x-canary:
        exact: "true"
  route:
  - destination:
      host: myapp
      subset: canary
- route:
  - destination:
      host: myapp
      subset: stable
```

The VirtualService controls traffic routing. The DestinationRule defines which pods belong to each subset. Together they enable zero-downtime canary deployments with instant rollback."""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_otel_examples():
    """OpenTelemetry, OTLP, auto-instrumentation — missed in eval."""
    examples = []
    scenarios = [
        {
            "q": "What is OpenTelemetry and how do you instrument a Python application?",
            "a": """OpenTelemetry (OTel) is a vendor-neutral, open-source observability framework for generating and collecting traces, metrics, and logs. It replaces vendor-specific SDKs (Datadog, New Relic, Jaeger) with a single standard.

**Core components:**
- **SDK** — instruments your application code
- **OTLP** (OpenTelemetry Protocol) — standard wire format for telemetry data
- **Collector** — receives, processes, and exports telemetry data
- **Exporter** — sends data to backends (Jaeger, Prometheus, Grafana Tempo)
- **Auto-instrumentation** — automatic tracing without code changes

**Instrument a Python app:**

```bash
# Install OTel packages
pip install opentelemetry-api opentelemetry-sdk \\
  opentelemetry-instrumentation-flask \\
  opentelemetry-exporter-otlp
```

```python
# app.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Configure the tracer
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Auto-instrument Flask
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Manual spans for custom logic
tracer = trace.get_tracer(__name__)

@app.route("/process")
def process():
    with tracer.start_as_current_span("process-payment") as span:
        span.set_attribute("payment.amount", 99.99)
        # ... business logic
        return "OK"
```

**Zero-code auto-instrumentation:**
```bash
# Instrument without changing code
opentelemetry-instrument --service_name my-app python app.py
```

**OTel Collector config:**
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    timeout: 5s

exporters:
  jaeger:
    endpoint: jaeger:14250
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

OpenTelemetry is vendor-neutral — switch backends by changing the exporter, not your application code."""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_platform_engineering_examples():
    """IDP, golden path, multi-tenancy, self-service — missed in eval."""
    examples = []
    scenarios = [
        {
            "q": "What is an Internal Developer Platform and what should a platform team provide?",
            "a": """An Internal Developer Platform (IDP) is the set of tools, workflows, and guardrails that a platform team provides to developers for self-service infrastructure.

**Core components a platform team should provide:**

1. **Golden paths** — opinionated, pre-configured templates:
   - Standardized Helm charts or Kustomize bases
   - Pre-approved base images (scanned, signed)
   - CI/CD pipeline templates (GitHub Actions, GitLab CI)

2. **Infrastructure abstraction** — hide cloud complexity:
   - Crossplane XRDs for databases, caches, queues
   - Terraform modules wrapped as self-service APIs
   - Namespace provisioning with RBAC, NetworkPolicy, ResourceQuota pre-applied

3. **Guardrails** — enforce standards without blocking:
   - Kyverno or OPA Gatekeeper policies as admission controllers
   - Resource limits and LimitRange per namespace
   - Image signing enforcement with Cosign

4. **Observability** — built into every deployment:
   - Prometheus + Grafana dashboards per team namespace
   - OpenTelemetry auto-instrumentation injected via webhook
   - Centralized logging with Loki or Elasticsearch

5. **Self-service workflows:**
   - Developers create a namespace by filing a PR to a GitOps repo
   - ArgoCD or Flux auto-syncs the namespace with all guardrails
   - No tickets, no waiting for platform team

6. **Developer experience (DevEx):**
   - CLI tools for common operations
   - Documentation as code (runbooks in the same repo)
   - Templates catalog (Backstage or custom portal)

**The platform team's goal:** Make the secure path the easy path. Developers shouldn't need to know about NetworkPolicy, securityContext, or ResourceQuota — the golden path includes them by default."""
        },
        {
            "q": "Design a self-service namespace provisioning workflow with security guardrails.",
            "a": """Self-service namespace provisioning with automated security:

**Developer creates a PR:**
```yaml
# namespaces/team-alpha.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-alpha
  labels:
    team: alpha
    environment: dev
    pod-security.kubernetes.io/enforce: restricted
```

**Kyverno auto-generates security resources:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-namespace-guardrails
spec:
  rules:
  - name: generate-network-policy
    match:
      any:
      - resources:
          kinds:
          - Namespace
    generate:
      kind: NetworkPolicy
      apiVersion: networking.k8s.io/v1
      name: default-deny
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
  - name: generate-resource-quota
    match:
      any:
      - resources:
          kinds:
          - Namespace
    generate:
      kind: ResourceQuota
      apiVersion: v1
      name: team-quota
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          hard:
            requests.cpu: "4"
            requests.memory: 8Gi
            limits.cpu: "8"
            limits.memory: 16Gi
            count/pods: "50"
  - name: generate-limit-range
    match:
      any:
      - resources:
          kinds:
          - Namespace
    generate:
      kind: LimitRange
      apiVersion: v1
      name: default-limits
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          limits:
          - default:
              cpu: 500m
              memory: 256Mi
            defaultRequest:
              cpu: 100m
              memory: 128Mi
            type: Container
```

**ArgoCD auto-syncs the namespace:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: namespaces
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/org/platform-config
    path: namespaces/
  destination:
    server: https://kubernetes.default.svc
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**Flow:**
1. Developer opens PR adding `namespaces/team-alpha.yaml`
2. CI validates the YAML, checks team label exists
3. PR merged → ArgoCD syncs → Namespace created
4. Kyverno auto-generates NetworkPolicy, ResourceQuota, LimitRange
5. RBAC bound via namespace label → team's ServiceAccount gets access
6. Zero manual platform team work, full automation with guardrails"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_promql_examples():
    """PromQL, ServiceMonitor, container_memory_working_set_bytes — missed in eval."""
    examples = []
    scenarios = [
        {
            "q": "Write a PromQL query to alert when pod memory exceeds 80% of its limit.",
            "a": """PromQL query for pod memory usage as a percentage of limit:

```promql
(
  container_memory_working_set_bytes{container!="", container!="POD"}
  /
  kube_pod_container_resource_limits{resource="memory", container!=""}
) > 0.8
```

**As a Prometheus alerting rule:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-memory-alerts
  namespace: monitoring
spec:
  groups:
  - name: pod-memory
    rules:
    - alert: PodMemoryNearLimit
      expr: |
        (
          container_memory_working_set_bytes{container!="", container!="POD"}
          /
          kube_pod_container_resource_limits{resource="memory", container!=""}
        ) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.pod }} memory at {{ $value | humanizePercentage }} of limit"
        description: "Container {{ $labels.container }} in pod {{ $labels.pod }} (namespace {{ $labels.namespace }}) has been using more than 80% of its memory limit for 5 minutes. Current ratio: {{ $value | humanizePercentage }}"
```

**Key metrics explained:**
- `container_memory_working_set_bytes` — actual memory in use (RSS + cache that can't be freed). This is what the OOM killer watches.
- `kube_pod_container_resource_limits{resource="memory"}` — the `limits.memory` value from the pod spec
- The ratio gives a 0-1 value; `> 0.8` means over 80% threshold
- `for: 5m` means the condition must be true for 5 consecutive minutes before alerting

**Configure scraping with ServiceMonitor:**
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
    path: /metrics
    interval: 30s
  namespaceSelector:
    matchNames:
    - production
```"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def main():
    all_examples = []

    print("[1/7] Generating secrets in GitOps examples...")
    all_examples.extend(generate_secrets_gitops())

    print("[2/7] Generating admission controller examples...")
    all_examples.extend(generate_admission_controller_examples())

    print("[3/7] Generating Crossplane examples...")
    all_examples.extend(generate_crossplane_examples())

    print("[4/7] Generating Istio circuit breaking examples...")
    all_examples.extend(generate_istio_circuit_breaking())

    print("[5/7] Generating OpenTelemetry examples...")
    all_examples.extend(generate_otel_examples())

    print("[6/7] Generating platform engineering examples...")
    all_examples.extend(generate_platform_engineering_examples())

    print("[7/7] Generating PromQL/ServiceMonitor examples...")
    all_examples.extend(generate_promql_examples())

    random.shuffle(all_examples)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nGenerated {len(all_examples)} CNPA platform engineering gap examples")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
