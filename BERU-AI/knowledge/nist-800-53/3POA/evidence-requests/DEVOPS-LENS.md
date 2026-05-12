# Evidence Request — DEVOPS-LENS

```
TO:   Platform Engineer / DevSecOps Lead (DEVOPS-LENS)
FROM: 3POA Assessor / CISO Internal Audit
RE:   NIST 800-53 Evidence Collection — Code + Cluster Controls
DUE:  48 hours before assessment call
```

This request covers controls implemented in:

- `GP-CONSULTING/DEVOPS-LENS/01-APP-SEC/` — Code (SAST, deps, secrets, image scan)
- `GP-CONSULTING/DEVOPS-LENS/02-CLUSTER-HARDEN/` — Cluster (CIS, admission, RBAC, PSA)

For each control, provide: (1) SSP narrative (what you implemented), (2) evidence
artifacts, and (3) be prepared to run the validation command live.

---

## AC — Access Control

### AC-2 — Account Management

**What to provide**:

- RBAC audit: all ClusterRoles, Roles, bindings with their principals
- Service account inventory: which workloads use which accounts
- Evidence of last access review (who reviewed, when, what was found)

**Validation command** (run live during assessment):

```bash
kubectl get clusterrolebindings,rolebindings -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data['items']:
    name = item['metadata']['name']
    role = item.get('roleRef', {}).get('name', 'unknown')
    subjects = [s.get('name', 'unknown') for s in item.get('subjects', [])]
    print(f'{name}: {role} -> {subjects}')
" | sort | head -40
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/kubescape-results.json` (RBAC section)

---

### AC-3 — Access Enforcement

**What to provide**:

- Kyverno ClusterPolicies enforcing RBAC and image restrictions
- Evidence admission webhooks are active and blocking (not just auditing)
- At least one example of a policy blocking a non-compliant resource

**Validation command**:

```bash
kubectl get clusterpolicies -A -o wide
# Show enforce mode policies (not audit-only):
kubectl get clusterpolicies -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data['items']:
    mode = p['spec'].get('validationFailureAction', 'unknown')
    print(f'{p[\"metadata\"][\"name\"]}: {mode}')
" | grep -v audit
```

**Evidence artifact**: Kyverno PolicyReport — `kubectl get policyreport -A -o json`

---

### AC-4 — Information Flow Enforcement

**What to provide**:

- NetworkPolicy manifest for every production namespace
- Evidence that default-deny exists before allow rules
- VPC flow log or Calico/Cilium flow evidence showing denied traffic

**Validation command**:

```bash
# Show namespaces with and without NetworkPolicy:
kubectl get networkpolicies -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
covered = set(p['metadata']['namespace'] for p in data['items'])
print('Namespaces with policy:', covered)
"
kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'
```

**Evidence artifact**: NetworkPolicy YAML exports from production namespaces

---

### AC-6 — Least Privilege

**What to provide**:

- Evidence no service account has cluster-admin
- Evidence Pod Security Admission or Kyverno enforces non-root
- Last RBAC review output (rbac-lookup or kubescape RBAC scan)

**Validation command**:

```bash
# Check for cluster-admin bindings to service accounts:
kubectl get clusterrolebindings -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for b in data['items']:
    if b.get('roleRef', {}).get('name') == 'cluster-admin':
        subs = [s for s in b.get('subjects', []) if s.get('kind') == 'ServiceAccount']
        if subs:
            print(f'FINDING: {b[\"metadata\"][\"name\"]} -> {subs}')
"
```

**Evidence artifact**: `kubescape scan framework nsa --format json` RBAC section

---

## AU — Audit and Accountability

### AU-2 — Event Logging

**What to provide**:

- Kubernetes audit policy file (`/etc/kubernetes/audit-policy.yaml` or equivalent)
- Evidence audit logs are being written and not empty
- Evidence that the audit policy covers the event categories required by AU-2

**Validation command**:

```bash
# Show audit policy is loaded:
kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | grep -A5 audit
# Verify audit log file has recent entries (last 10 minutes):
tail -f /var/log/kubernetes/audit.log 2>/dev/null || \
  kubectl logs -n kube-system -l component=kube-apiserver 2>/dev/null | tail -20
```

**Evidence artifact**: Audit policy YAML + sample audit log entries

---

### AU-6 — Audit Review

**What to provide**:

- Grafana dashboard showing security events (or link to Splunk dashboard)
- Evidence of a recent alert that was reviewed and actioned
- Alert routing configuration (who gets paged for what)

**Validation command**:

```bash
# Show Prometheus alert rules for security:
kubectl get prometheusrule -A | grep -i sec
curl -s http://prometheus:9090/api/v1/rules | python3 -c "
import json, sys
rules = json.load(sys.stdin)
for g in rules['data']['groups']:
    for r in g['rules']:
        if r.get('type') == 'alerting' and 'security' in r.get('name', '').lower():
            print(r['name'], r.get('state', 'unknown'))
"
```

**Evidence artifact**: Prometheus alert rules YAML + Grafana dashboard screenshot

---

## CA — Assessment, Authorization, and Monitoring

### CA-2 — Control Assessments

**What to provide**:

- Most recent kubescape scan report with score and findings
- Evidence that findings from the last scan were triaged
- Remediation records for any HIGH findings

**Validation command**:

```bash
kubescape scan framework nsa --format json --output /tmp/ca2-kubescape.json 2>/dev/null
cat /tmp/ca2-kubescape.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Score: {data.get(\"riskScore\", \"N/A\")}')
"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/artifacts/kubescape/`

---

### CA-7 — Continuous Monitoring

**What to provide**:

- Evidence monitoring is automated (not manual-only)
- Prometheus scrape targets showing security tool metrics
- Evidence alert thresholds are set and active

**Validation command**:

```bash
kubectl get servicemonitor -A | grep -E "falco|kyverno|trivy"
curl -s http://prometheus:9090/api/v1/targets | python3 -c "
import json, sys
t = json.load(sys.stdin)
active = [tgt['labels'].get('job') for tgt in t['data']['activeTargets']]
print('Active scrape targets:', list(set(active)))
"
```

**Evidence artifact**: Prometheus targets list + ServiceMonitor manifests

---

## CM — Configuration Management

### CM-2 — Baseline Configuration

**What to provide**:

- Helm values files for production workloads (this IS the documented baseline)
- Evidence that baseline is version-controlled in git
- Evidence that deviations from baseline trigger alerts

**Validation command**:

```bash
# Show ArgoCD apps and their sync status (any OutOfSync = drift from baseline):
argocd app list --output json | python3 -c "
import json, sys
apps = json.load(sys.stdin)
for a in apps:
    print(f'{a[\"name\"]}: {a[\"status\"][\"sync\"][\"status\"]} / {a[\"status\"][\"health\"][\"status\"]}')
"
```

**Evidence artifact**: ArgoCD application sync status + Helm values in git

---

### CM-6 — Configuration Settings

**What to provide**:

- kube-bench report (CIS Kubernetes Benchmark)
- Evidence FAIL items have been remediated or have accepted risk
- Any Ansible playbook runs for node hardening

**Validation command**:

```bash
kube-bench run --targets node,master --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for ctrl in data.get('Controls', []):
    fails = [t for t in ctrl.get('tests', []) for r in t.get('results', []) if r['status'] == 'FAIL']
    if fails:
        print(f'{ctrl[\"id\"]}: {len(fails)} FAIL items')
"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/kubebench-results.json`

---

### CM-7 — Least Functionality

**What to provide**:

- Kyverno policies denying: privileged containers, hostPath mounts, hostNetwork, host PID
- Evidence Pod Security Admission is active at baseline or restricted level
- Evidence workloads run as non-root

**Validation command**:

```bash
# Check PSA labels on namespaces:
kubectl get ns -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for ns in data['items']:
    labels = ns.get('metadata', {}).get('labels', {})
    psa = {k: v for k, v in labels.items() if 'pod-security' in k}
    if psa:
        print(f'{ns[\"metadata\"][\"name\"]}: {psa}')
"
# Run polaris to check workload security contexts:
polaris audit --format=summary 2>/dev/null | tail -20
```

**Evidence artifact**: `polaris audit --format json` output + PSA namespace labels

---

### CM-8 — System Component Inventory

**What to provide**:

- Backstage catalog YAML for production services
- Trivy SBOM output for at least one production image
- Evidence that new services require catalog registration

**Validation command**:

```bash
# Count services in Backstage catalog:
curl -s http://backstage:7007/api/catalog/entities | python3 -c "
import json, sys
entities = json.load(sys.stdin)
by_kind = {}
for e in entities:
    k = e.get('kind', 'unknown')
    by_kind[k] = by_kind.get(k, 0) + 1
print(by_kind)
"
# SBOM for an image:
trivy image --format cyclonedx --output /tmp/sbom-example.json <image:tag>
```

**Evidence artifact**: Backstage catalog entity list + SBOM JSON

---

## RA — Risk Assessment

### RA-5 — Vulnerability Scanning

**What to provide**:

- Trivy scan of production images (last 7 days)
- Grype scan results
- Evidence HIGH/CRITICAL findings were addressed
- CI/CD gate configuration that blocks HIGH/CRITICAL builds

**Validation command**:

```bash
trivy image --severity HIGH,CRITICAL --format json <production-image:tag> | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('Results', []):
    vulns = r.get('Vulnerabilities', []) or []
    crit = [v for v in vulns if v['Severity'] == 'CRITICAL']
    high = [v for v in vulns if v['Severity'] == 'HIGH']
    print(f'{r[\"Target\"]}: {len(crit)} CRITICAL, {len(high)} HIGH')
"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/trivy-results.json`

---

## SA — System and Services Acquisition

### SA-10 — Developer Configuration Management

**What to provide**:

- Semgrep CI pipeline configuration
- Conftest CI gate configuration
- Evidence at least one build was blocked by these gates (CI failure log)

**Validation command**:

```bash
# Validate Semgrep rules parse:
semgrep --validate --config=GP-CONSULTING/DEVOPS-LENS/01-APP-SEC/01-scanners/semgrep-rules/ 2>&1 | tail -5
# Validate Conftest policies:
conftest verify --policy GP-CONSULTING/DEVOPS-LENS/02-CLUSTER-HARDEN/01-policies/conftest/
```

**Evidence artifact**: CI pipeline config YAML + example failed build log

---

### SA-12 — Supply Chain Protection

**What to provide**:

- cosign public key used for image verification
- Evidence images are signed in the build pipeline
- Kyverno policy requiring cosign signature before deployment

**Validation command**:

```bash
# Verify a production image is signed:
cosign verify --certificate-identity-regexp=".*" --certificate-oidc-issuer-regexp=".*" <production-image:tag> 2>&1 | head -10
# Show Kyverno policy requiring signatures:
kubectl get clusterpolicy require-image-signature -o yaml 2>/dev/null || \
  kubectl get clusterpolicy -A | grep -i sign
```

**Evidence artifact**: cosign transparency log URL + Kyverno image verification policy YAML

---

## SC — System and Communications Protection

### SC-7 — Boundary Protection

**What to provide**:

- NetworkPolicy manifests for production namespaces
- Evidence default-deny egress is in place
- Evidence pods cannot communicate with the Kubernetes API server without RBAC

**Validation command**:

```bash
# Show default-deny policies:
kubectl get networkpolicies -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data['items']:
    spec = p.get('spec', {})
    # Default deny has empty podSelector and no ingress/egress
    if spec.get('podSelector') == {} and not spec.get('ingress') and not spec.get('egress'):
        print(f'Default deny: {p[\"metadata\"][\"namespace\"]}/{p[\"metadata\"][\"name\"]}')
"
```

**Evidence artifact**: NetworkPolicy YAML exports

---

### SC-8 — Transmission Confidentiality

**What to provide**:

- Istio/mTLS configuration or equivalent service mesh config
- Evidence TLS is required for ingress (no HTTP endpoints in production)
- cert-manager issuer configuration

**Validation command**:

```bash
kubectl get peerauthentication -A  # mTLS enforcement
kubectl get destinationrule -A | grep -i mtls
kubectl get ingress -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i in data['items']:
    tls = i.get('spec', {}).get('tls', [])
    print(f'{i[\"metadata\"][\"name\"]}: TLS={bool(tls)}')
"
```

**Evidence artifact**: PeerAuthentication YAML + Ingress TLS config

---

### SC-12 — Cryptographic Key Management

**What to provide**:

- ExternalSecrets configuration (what vault/KMS is the backend)
- Evidence no secrets are stored in ConfigMaps or environment variables in manifests
- Key rotation schedule

**Validation command**:

```bash
kubectl get externalsecret -A
# Scan for secrets in ConfigMaps (should find none):
kubectl get configmaps -A -o json | python3 -c "
import json, sys, re
data = json.load(sys.stdin)
pattern = re.compile(r'(password|secret|key|token|credential)', re.IGNORECASE)
for cm in data['items']:
    for k, v in cm.get('data', {}).items():
        if pattern.search(k) or (isinstance(v, str) and pattern.search(v[:100])):
            print(f'FINDING: {cm[\"metadata\"][\"namespace\"]}/{cm[\"metadata\"][\"name\"]}: {k}')
"
```

**Evidence artifact**: ExternalSecretStore config + Gitleaks scan results

---

### SC-28 — Protection at Rest

**What to provide**:

- etcd encryption configuration
- Evidence Secrets are encrypted at rest (not base64 only)
- KMS encryption provider configuration if used

**Validation command**:

```bash
# Check etcd encryption config:
cat /etc/kubernetes/encryption-config.yaml 2>/dev/null || \
  kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | grep encryption-provider-config
# Verify a Secret is actually encrypted in etcd:
# (requires etcdctl access)
ETCDCTL_API=3 etcdctl get /registry/secrets/default/test-secret --hex 2>/dev/null | head -5
```

**Evidence artifact**: Encryption provider config + etcd stored secret (hex shows encryption)

---

## SI — System and Information Integrity

### SI-2 — Flaw Remediation

**What to provide**:

- Dependabot or Renovate configuration
- Evidence PRs were created and merged for vulnerability fixes
- Mean time to remediate HIGH/CRITICAL findings

**Validation command**:

```bash
# Show recent Trivy findings with fix available:
trivy image --severity HIGH,CRITICAL --format json <image:tag> | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('Results', []):
    for v in r.get('Vulnerabilities', []) or []:
        if v.get('FixedVersion'):
            print(f'{v[\"VulnerabilityID\"]}: {v[\"PkgName\"]} {v[\"InstalledVersion\"]} -> {v[\"FixedVersion\"]}')
" | head -20
```

**Evidence artifact**: Dependabot/Renovate PR history + Trivy results showing fixed versions

---

### SI-3 — Malicious Code Protection

**What to provide**:

- Semgrep ruleset used in CI
- Falco rule file for malicious code detection (runtime)
- Evidence of at least one detection event in the last 30 days

**Validation command**:

```bash
semgrep --config=p/owasp-top-ten --test 2>&1 | tail -10
# Show Falco rules related to malicious execution:
grep -r "spawned_shell\|write_binary\|modify_binary_dirs" /etc/falco/rules.d/ | head -10
```

**Evidence artifact**: Semgrep CI run log + Falco alert events from Splunk

---

### SI-4 — System Monitoring

**What to provide**:

- Prometheus alert rules for security events
- Grafana dashboard showing monitoring coverage
- Evidence monitoring is continuous (not manual/periodic)

**Validation command**:

```bash
kubectl get prometheusrule -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for pr in data['items']:
    for g in pr['spec'].get('groups', []):
        alerts = [r['alert'] for r in g.get('rules', []) if 'alert' in r]
        if alerts:
            print(f'{pr[\"metadata\"][\"name\"]}: {alerts}')
"
```

**Evidence artifact**: PrometheusRule YAML + Grafana dashboard export

---

### SI-7 — Software Integrity

**What to provide**:

- cosign verification of production images
- SBOM for production images (CycloneDX or SPDX format)
- Evidence integrity check runs on every deployment

**Validation command**:

```bash
# Verify image signature:
cosign verify --certificate-identity-regexp=".*" --certificate-oidc-issuer-regexp=".*" <image:tag>
# Show SBOM components:
trivy image --format cyclonedx <image:tag> | python3 -c "
import json, sys
data = json.load(sys.stdin)
components = data.get('components', [])
print(f'SBOM components: {len(components)}')
"
```

**Evidence artifact**: cosign transparency log entry + CycloneDX SBOM JSON
