# BERU — CM Family Audit Playbook

> Configuration Management: CM-2, CM-3, CM-6, CM-7, CM-8
> Tools: kube-bench, Kubescape, Polaris, Kyverno, ArgoCD, kubectl
> Audience: BERU (NIST-800-53 internal auditor)
> Read first: `../controls/CM-2.md`, `../controls/CM-3.md`, `../controls/CM-6.md`, `../controls/CM-7.md`, `../controls/CM-8.md`

---

## Inputs That Route Here

- kube-bench scan output (primary CM source)
- Polaris audit output
- Kyverno PolicyReport
- ArgoCD sync state / drift report
- Manual request: "Is our configuration baseline documented?"

---

## Step 1 — Collect Configuration Baseline Evidence

```bash
EVIDENCE="GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/$(date +%Y-%m-%d)-CM"
mkdir -p $EVIDENCE

# 1a. Full kube-bench run — CIS Kubernetes Benchmark L1 + L2
kube-bench run --json 2>&1 | tee $EVIDENCE/kubebench-full-$(date +%Y%m%d).json
kube-bench run 2>&1 | tee $EVIDENCE/kubebench-summary-$(date +%Y%m%d).txt

# 1b. Kubescape — CIS framework
kubescape scan framework cis-eks --format json \
  --output $EVIDENCE/kubescape-cis-$(date +%Y%m%d).json 2>&1

# 1c. Polaris — workload-level configuration audit
polaris audit --format=json --output-file $EVIDENCE/polaris-$(date +%Y%m%d).json 2>&1

# 1d. Kyverno PolicyReports — enforcement status
kubectl get policyreport -A -o yaml 2>&1 | tee $EVIDENCE/kyverno-policyreport-$(date +%Y%m%d).yaml
kubectl get clusterpolicyreport -o yaml 2>&1 | tee $EVIDENCE/kyverno-clusterpolicyreport-$(date +%Y%m%d).yaml

# 1e. Kyverno policies — are they in Enforce mode (not Audit)?
kubectl get clusterpolicies -o yaml | grep -A2 "validationFailureAction" 2>&1 | \
  tee $EVIDENCE/kyverno-enforcement-modes-$(date +%Y%m%d).txt

# 1f. ArgoCD application sync status
argocd app list -o json 2>&1 | tee $EVIDENCE/argocd-apps-$(date +%Y%m%d).json 2>/dev/null || \
  kubectl get application -n argocd -o json 2>&1 | tee $EVIDENCE/argocd-apps-$(date +%Y%m%d).json

# 1g. ArgoCD drift — any OutOfSync applications?
kubectl get application -n argocd -o json | \
  jq '.items[] | select(.status.sync.status != "Synced") | {name: .metadata.name, status: .status.sync.status}' \
  2>&1 | tee $EVIDENCE/argocd-drift-$(date +%Y%m%d).json

# 1h. Node configuration — OS-level baseline
kube-bench run --targets node 2>&1 | tee $EVIDENCE/kubebench-node-$(date +%Y%m%d).txt
```

---

## Step 2 — Assess CM-2: Baseline Configuration

Read: `../controls/CM-2.md`

Questions to answer:
1. Is there a documented baseline configuration for the cluster? (kube-bench L1 = baseline)
2. Does the actual configuration match the baseline?
3. When was the baseline last reviewed?

Assessment commands:
```bash
# Count PASS/FAIL/WARN from kube-bench
cat $EVIDENCE/kubebench-summary-$(date +%Y%m%d).txt | grep -E "== Summary ==" -A10

# Focus on failures — these are deviations from the baseline
cat $EVIDENCE/kubebench-full-$(date +%Y%m%d).json | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
fails = []
for test in data.get('Controls', []):
    for group in test.get('tests', []):
        for result in group.get('results', []):
            if result.get('status') == 'FAIL':
                fails.append({'id': result.get('test_number'), 'desc': result.get('test_desc')})
print(f'Total FAILs: {len(fails)}')
for f in fails:
    print(f\"  {f['id']}: {f['desc']}\")
"
```

**PASS criteria:** kube-bench L1 PASS rate ≥ 90%. FAIL items documented with justification or tracked in POA&M. Baseline review within 90 days.

**PARTIAL criteria:** kube-bench run but FAILs not tracked. Baseline exists but is undated.

**FAIL criteria:** No kube-bench run. No baseline documentation. FAILs not acknowledged.

---

## Step 3 — Assess CM-3: Configuration Change Control

Read: `../controls/CM-3.md`

Questions to answer:
1. Are cluster configuration changes made via git (ArgoCD), not ad-hoc kubectl?
2. Is there a change approval process (PR review, ticket)?
3. Are configuration changes logged?

Assessment commands:
```bash
# Check git repository for recent ArgoCD application changes
git -C /path/to/cluster-repo log --oneline --since="30 days ago" 2>&1 | \
  tee $EVIDENCE/git-changes-30d-$(date +%Y%m%d).txt

# Check ArgoCD for any manually applied changes (OutOfSync)
cat $EVIDENCE/argocd-drift-$(date +%Y%m%d).json

# Check if any non-ArgoCD changes were applied recently
kubectl get events -A --field-selector reason=Updated \
  --sort-by='.lastTimestamp' 2>&1 | head -20 | tee $EVIDENCE/k8s-events-updated-$(date +%Y%m%d).txt
```

Ask the control owner: "Show me the last three production configuration changes. Where are they in git?"

**PASS criteria:** All cluster config changes in git with PR review. ArgoCD 100% Synced. No OutOfSync applications from manual kubectl changes.

**PARTIAL criteria:** ArgoCD in use but some resources managed by kubectl (intentional exceptions documented).

**FAIL criteria:** No ArgoCD or equivalent. Changes made directly via kubectl with no git record. No change approval process.

---

## Step 4 — Assess CM-6: Configuration Settings

Read: `../controls/CM-6.md`

This maps directly to CIS benchmark compliance. Focus on the high-impact checks.

Assessment commands:
```bash
# kube-bench section 1 — API server configuration
kube-bench run --check 1.2.1,1.2.2,1.2.3,1.2.6,1.2.7,1.2.10,1.2.16,1.2.22,1.2.23,1.2.24 \
  2>&1 | tee $EVIDENCE/kubebench-cm6-apiserver-$(date +%Y%m%d).txt

# kube-bench section 1 — etcd configuration
kube-bench run --check 2.1,2.2,2.3 2>&1 | tee $EVIDENCE/kubebench-cm6-etcd-$(date +%Y%m%d).txt

# kube-bench section 4 — worker node configuration
kube-bench run --check 4.1.1,4.1.2,4.2.1,4.2.2,4.2.6 \
  2>&1 | tee $EVIDENCE/kubebench-cm6-node-$(date +%Y%m%d).txt
```

Key CM-6 checks and what they mean:

| kube-bench Check | Setting | Why It Matters |
| --- | --- | --- |
| 1.2.1 | `--anonymous-auth=false` | Prevents unauthenticated API access |
| 1.2.2 | `--token-auth-file` absent | Static token files are insecure |
| 1.2.6 | `--kubelet-certificate-authority` set | API-to-kubelet TLS |
| 1.2.22 | `--audit-log-path` set | Audit logging enabled |
| 1.2.23 | `--audit-log-maxage=30` | Audit retention |
| 2.1 | etcd `--cert-file` and `--key-file` | etcd TLS |
| 4.2.6 | `--protect-kernel-defaults=true` | Node kernel hardening |

**PASS criteria:** All mapped kube-bench checks PASS. Deviations documented with justification and compensating controls.

**PARTIAL criteria:** Most checks PASS. 1-3 known failures tracked in POA&M with remediation dates.

**FAIL criteria:** Core checks failing (1.2.1, 1.2.22, 2.1). No tracking of failures. No compensating controls.

---

## Step 5 — Assess CM-7: Least Functionality

Read: `../controls/CM-7.md`

Questions to answer:
1. Are unnecessary services, ports, and capabilities disabled?
2. Are Kyverno admission policies enforcing least-functionality at the workload level?
3. Are containers prevented from running as root, with excessive capabilities, or with host filesystem access?

Assessment commands:
```bash
# Check Kyverno policies for least-functionality enforcement
kubectl get clusterpolicies -o json | \
  jq '.items[] | {name: .metadata.name, mode: .spec.validationFailureAction}' \
  2>&1 | tee $EVIDENCE/kyverno-policies-$(date +%Y%m%d).json

# Find pods running as root
kubectl get pods -A -o json | \
  jq '.items[] | select(
    (.spec.securityContext.runAsNonRoot == false or .spec.securityContext.runAsNonRoot == null) and
    (.spec.containers[].securityContext.runAsNonRoot == false or
     .spec.containers[].securityContext.runAsNonRoot == null)
  ) | {namespace: .metadata.namespace, pod: .metadata.name}' \
  2>&1 | tee $EVIDENCE/pods-running-as-root-$(date +%Y%m%d).json

# Find pods with privilege escalation allowed
kubectl get pods -A -o json | \
  jq '.items[] | select(.spec.containers[].securityContext.allowPrivilegeEscalation == true) |
      {namespace: .metadata.namespace, pod: .metadata.name}' \
  2>&1 | tee $EVIDENCE/pods-priv-escalation-$(date +%Y%m%d).json

# Find pods with hostPath volumes
kubectl get pods -A -o json | \
  jq '.items[] | select(.spec.volumes[]?.hostPath != null) |
      {namespace: .metadata.namespace, pod: .metadata.name, hostPath: [.spec.volumes[].hostPath.path]}' \
  2>&1 | tee $EVIDENCE/pods-hostpath-$(date +%Y%m%d).json

# Polaris checks for CM-7
cat $EVIDENCE/polaris-$(date +%Y%m%d).json | python3 -c "
import sys, json
data = json.load(sys.stdin)
cm7_checks = ['runAsNonRoot', 'privilegeEscalation', 'capabilities', 'hostPathVolumes', 'hostPIDSet', 'hostIPCSet', 'hostNetworkSet']
for resource in data.get('Results', []):
    for check, result in resource.get('PodResult', {}).get('ContainerResults', [{}])[0].get('Results', {}).items():
        if check in cm7_checks and not result.get('Success', True):
            print(f\"{resource['Name']}: FAIL {check}\")
"
```

**PASS criteria:** Kyverno `require-non-root`, `deny-privileged-containers`, `restrict-capabilities` all in Enforce mode. Zero pods running as root in production namespaces. No unexpected hostPath mounts.

**PARTIAL criteria:** Kyverno policies in Audit mode (not Enforce). Some violations in non-prod namespaces with tickets.

**FAIL criteria:** No pod security policies or Kyverno CM-7 policies. Root containers in production. HostPath mounts without justification.

---

## Step 6 — Assess CM-8: System Component Inventory

Read: `../controls/CM-8.md`

Questions to answer:
1. Is there an up-to-date inventory of all cluster components (nodes, namespaces, deployments)?
2. Is the SBOM (Software Bill of Materials) for container images maintained?
3. Does the inventory match what is actually running?

Assessment commands:
```bash
# Cluster component inventory
kubectl get nodes -o wide 2>&1 | tee $EVIDENCE/nodes-inventory-$(date +%Y%m%d).txt
kubectl get namespaces 2>&1 | tee $EVIDENCE/namespaces-$(date +%Y%m%d).txt
kubectl get deployments -A 2>&1 | tee $EVIDENCE/deployments-$(date +%Y%m%d).txt
kubectl get daemonsets -A 2>&1 | tee $EVIDENCE/daemonsets-$(date +%Y%m%d).txt

# SBOM — Trivy generates SBOM for each image
# Pull the image list first
kubectl get pods -A -o json | \
  jq -r '.items[].spec.containers[].image' | sort -u \
  2>&1 | tee $EVIDENCE/image-list-$(date +%Y%m%d).txt

# Generate SBOM for one image as sample
head -1 $EVIDENCE/image-list-$(date +%Y%m%d).txt | xargs -I{} \
  trivy image --format cyclonedx --output $EVIDENCE/sample-sbom.json {} 2>&1
```

**PASS criteria:** Documented inventory matches kubectl output. SBOM generation automated in CI. Inventory reviewed quarterly.

**PARTIAL criteria:** Inventory exists but is outdated (>90 days). SBOM for some images only.

**FAIL criteria:** No inventory. No SBOM. No way to tell what is running or what its dependencies are.

---

## Step 7 — Fill BERU Findings

| Control | Control Owner | Fixer Route | Rank Range |
| --- | --- | --- | --- |
| CM-2 | PlatEng | kube-bench remediation per CIS | C |
| CM-3 | PlatEng + DevSecOps | ArgoCD enforcement | C–B |
| CM-6 | PlatEng | kube-apiserver config (git PR) | C |
| CM-7 | PlatEng | Kyverno policy Enforce mode | C |
| CM-8 | DevSecOps | Trivy SBOM in CI pipeline | D–C |

Reference: `../ssp-examples/CM-ssp-great.md` for SSP narrative quality standard.
