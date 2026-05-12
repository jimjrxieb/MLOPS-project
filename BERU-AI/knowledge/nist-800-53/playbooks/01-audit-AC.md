# BERU — AC Family Audit Playbook

> Access Control: AC-2, AC-3, AC-5, AC-6, AC-6(5), AC-6(9), AC-6(10), AC-17
> Tools: kubectl, rbac-lookup, Kubescape, Prowler, IAM Access Analyzer
> Audience: BERU (NIST-800-53 internal auditor)
> Read first: `../controls/AC-2.md`, `../controls/AC-3.md`, `../controls/AC-5.md`, `../controls/AC-6.md`, `../controls/AC-17.md`

---

## Inputs That Route Here

- Kubescape RBAC scan output
- kubectl RBAC dump
- AWS IAM Access Analyzer findings
- Prowler IAM checks
- Manual request: "Audit access control"

---

## Step 1 — Collect K8s Access Control Evidence

Run these commands and save every output. Do not assess before you have the evidence.

```bash
EVIDENCE="GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/$(date +%Y-%m-%d)-AC"
mkdir -p $EVIDENCE

# 1a. Full RBAC dump — ClusterRoles
kubectl get clusterroles -o yaml 2>&1 | tee $EVIDENCE/clusterroles-$(date +%Y%m%d).yaml

# 1b. Full RBAC dump — ClusterRoleBindings
kubectl get clusterrolebindings -o yaml 2>&1 | tee $EVIDENCE/clusterrolebindings-$(date +%Y%m%d).yaml

# 1c. Full RBAC dump — namespaced Roles (all namespaces)
kubectl get roles -A -o yaml 2>&1 | tee $EVIDENCE/roles-all-ns-$(date +%Y%m%d).yaml

# 1d. Full RBAC dump — namespaced RoleBindings
kubectl get rolebindings -A -o yaml 2>&1 | tee $EVIDENCE/rolebindings-all-ns-$(date +%Y%m%d).yaml

# 1e. Service accounts in all namespaces
kubectl get serviceaccounts -A 2>&1 | tee $EVIDENCE/serviceaccounts-$(date +%Y%m%d).txt

# 1f. Effective permissions mapping (requires rbac-lookup)
rbac-lookup --output wide 2>&1 | tee $EVIDENCE/rbac-lookup-$(date +%Y%m%d).txt

# 1g. Kubescape RBAC framework scan
kubescape scan framework nsa --format json --output $EVIDENCE/kubescape-nsa-$(date +%Y%m%d).json

# 1h. cluster-admin bindings — who has it?
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.roleRef.name == "cluster-admin") | {binding: .metadata.name, subjects: .subjects}' \
  2>&1 | tee $EVIDENCE/cluster-admin-bindings-$(date +%Y%m%d).json
```

For AWS IAM:
```bash
# 1i. Prowler IAM checks
prowler aws --checks iam_no_root_access_key_present \
  iam_avoid_root_usage iam_policy_no_statements_with_admin_access \
  iam_user_no_setup_initial_access_key --output-formats json \
  --output-filename $EVIDENCE/prowler-iam-$(date +%Y%m%d) 2>&1

# 1j. IAM Access Analyzer findings
aws accessanalyzer list-findings --analyzer-arn <analyzer-arn> \
  --output json 2>&1 | tee $EVIDENCE/access-analyzer-$(date +%Y%m%d).json
```

---

## Step 2 — Assess AC-2: Account Management

Read: `../controls/AC-2.md`

Questions to answer from the evidence:
1. Are service accounts scoped to a single workload? (not shared across deployments)
2. Are there dormant service accounts with no bound workloads?
3. Are IAM users using named accounts, not shared credentials?
4. Is there a documented account provisioning and deprovisioning process?

Assessment commands:
```bash
# Find service accounts with no pods bound to them
kubectl get serviceaccounts -A -o json | \
  jq '.items[] | select(.metadata.name != "default") | .metadata.namespace + "/" + .metadata.name' | \
  while read sa; do
    ns=$(echo $sa | cut -d'/' -f1 | tr -d '"')
    name=$(echo $sa | cut -d'/' -f2 | tr -d '"')
    pods=$(kubectl get pods -n $ns -o json | jq --arg sa "$name" \
      '[.items[] | select(.spec.serviceAccountName == $sa)] | length')
    echo "SA: $ns/$name → pods using it: $pods"
  done 2>&1 | tee $EVIDENCE/sa-usage-$(date +%Y%m%d).txt
```

**PASS criteria:** Named service accounts scoped to single workloads. Dormant accounts documented or removed. Human accounts individually named.

**PARTIAL criteria:** Service accounts exist but usage is undocumented. Some shared or default service accounts in use for real workloads.

**FAIL criteria:** Workloads running as `default` service account with permissions. No account inventory. Shared human credentials.

---

## Step 3 — Assess AC-3: Access Enforcement

Read: `../controls/AC-3.md`

Questions to answer:
1. Is RBAC enabled on the API server?
2. Are all requests going through RBAC enforcement (no anonymous auth)?
3. Are there any bindings that bypass RBAC (e.g., permissive ClusterRoles)?

Assessment commands:
```bash
# Check RBAC authorization mode is enabled
kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | \
  grep -A5 "authorization-mode" 2>&1 | tee $EVIDENCE/apiserver-authz-$(date +%Y%m%d).txt

# Check anonymous auth is disabled
kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | \
  grep "anonymous-auth" 2>&1 | tee $EVIDENCE/apiserver-anon-$(date +%Y%m%d).txt

# Look for permissive bindings (all subjects / system:unauthenticated)
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.subjects[]?.name == "system:unauthenticated" or .subjects[]?.name == "system:anonymous")' \
  2>&1 | tee $EVIDENCE/permissive-bindings-$(date +%Y%m%d).json
```

**PASS criteria:** `--authorization-mode=RBAC` confirmed. `--anonymous-auth=false`. No unauthenticated subject bindings.

**PARTIAL criteria:** RBAC enabled but anonymous auth not explicitly disabled. One or two permissive bindings with justification.

**FAIL criteria:** RBAC not in authorization mode. Anonymous auth enabled. `system:unauthenticated` has any binding.

---

## Step 4 — Assess AC-5: Separation of Duties

Read: `../controls/AC-5.md`

Questions to answer:
1. Are admin/cluster-admin accounts separate from developer accounts?
2. Is the person who approves changes different from the person who implements them?
3. Is break-glass access documented and monitored?

Assessment commands:
```bash
# Who has cluster-admin? Should be a very short list.
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.roleRef.name == "cluster-admin") | {name: .metadata.name, subjects: .subjects}' \
  2>&1 | tee $EVIDENCE/cluster-admin-subjects-$(date +%Y%m%d).json

# Check ArgoCD — is any service account cluster-admin?
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.subjects[]?.namespace == "argocd") | {name: .metadata.name, role: .roleRef.name}' \
  2>&1 | tee $EVIDENCE/argocd-bindings-$(date +%Y%m%d).json
```

Ask the control owner: "Walk me through how a developer gets production access. Who approves it?"

**PASS criteria:** cluster-admin is limited to 1-3 named individuals for break-glass. Developers have namespaced roles only. Approval is documented.

**PARTIAL criteria:** cluster-admin list is reasonable but approval process is undocumented. Some service accounts have broader than needed access.

**FAIL criteria:** cluster-admin is assigned to service accounts or developer groups. No break-glass documentation. No approval process.

---

## Step 5 — Assess AC-6: Least Privilege (Primary)

Read: `../controls/AC-6.md`

This is the highest-value access control check. Methodically check each layer.

### 5a. K8s RBAC — Wildcard Verb/Resource Check

```bash
# Find all ClusterRoles with wildcard verbs or resources
kubectl get clusterroles -o json | \
  jq '.items[] | select(.rules[].verbs[]? == "*" or .rules[].resources[]? == "*") |
      {name: .metadata.name, rules: .rules}' \
  2>&1 | tee $EVIDENCE/wildcard-clusterroles-$(date +%Y%m%d).json

# Find all namespaced Roles with wildcards
kubectl get roles -A -o json | \
  jq '.items[] | select(.rules[].verbs[]? == "*" or .rules[].resources[]? == "*") |
      {namespace: .metadata.namespace, name: .metadata.name, rules: .rules}' \
  2>&1 | tee $EVIDENCE/wildcard-roles-$(date +%Y%m%d).json

# Use rbac-lookup to see what service accounts can actually do
rbac-lookup serviceaccount --output wide 2>&1 | tee $EVIDENCE/sa-permissions-$(date +%Y%m%d).txt
```

### 5b. K8s — AC-6(5) Privileged Accounts

```bash
# All ClusterRoleBindings — look for service accounts with cluster-admin
kubectl get clusterrolebindings -o yaml 2>&1 | grep -B5 "cluster-admin" | \
  tee $EVIDENCE/cluster-admin-check-$(date +%Y%m%d).txt

# kube-bench check 5.1.6 (cluster-admin usage)
kube-bench run --check 5.1.6 2>&1 | tee $EVIDENCE/kubebench-5.1.6-$(date +%Y%m%d).txt
```

**AC-6 PASS criteria:**
- No ClusterRoles with `verbs: ["*"]` unless system roles (system:, kubeadm:, etc.)
- No service accounts bound to cluster-admin
- kube-bench 5.1.6: PASS

**AC-6 PARTIAL criteria:**
- Wildcards exist but are limited to non-production or documented legacy
- One service account with elevated permissions, documented and under review

**AC-6 FAIL criteria:**
- Application service accounts with wildcard verbs
- Any service account bound to cluster-admin
- Wildcards on secrets, configmaps resources without justification

### 5c. AWS IAM — Least Privilege Check

```bash
# Check for managed policies with admin access
aws iam list-policies --scope Local --query 'Policies[*].{Name:PolicyName,Arn:Arn}' \
  --output json 2>&1 | tee $EVIDENCE/iam-local-policies-$(date +%Y%m%d).json

# Check for inline policies (harder to audit)
aws iam list-users --query 'Users[*].UserName' --output text | \
  while read user; do
    inline=$(aws iam list-user-policies --user-name $user --output json)
    echo "User: $user → inline policies: $inline"
  done 2>&1 | tee $EVIDENCE/iam-inline-policies-$(date +%Y%m%d).txt
```

---

## Step 6 — Assess AC-17: Remote Access

Read: `../controls/AC-17.md`

Questions to answer:
1. Is `kubectl exec` restricted by policy?
2. Is remote access to cluster nodes audited?
3. Are there open NodePort or HostPort services that bypass NetworkPolicy?

Assessment commands:
```bash
# Check for Kyverno policy restricting kubectl exec
kubectl get clusterpolicies -o yaml | grep -A10 "exec" 2>&1 | \
  tee $EVIDENCE/kyverno-exec-policy-$(date +%Y%m%d).txt

# Find NodePort services
kubectl get services -A --field-selector spec.type=NodePort \
  2>&1 | tee $EVIDENCE/nodeport-services-$(date +%Y%m%d).txt

# Find hostPort usage in pods
kubectl get pods -A -o json | \
  jq '.items[] | select(.spec.containers[].ports[]?.hostPort != null) |
      {namespace: .metadata.namespace, pod: .metadata.name}' \
  2>&1 | tee $EVIDENCE/hostport-pods-$(date +%Y%m%d).json
```

**PASS criteria:** `kubectl exec` restricted by Kyverno policy. No unexpected NodePort services. HostPort usage documented and justified.

**PARTIAL criteria:** exec restriction in audit mode (not enforce). NodePort services exist with documented justification.

**FAIL criteria:** No exec restriction policy. NodePort/HostPort services unexplained. No remote access audit trail.

---

## Step 7 — Fill BERU Findings

For each control assessed, produce one finding using `../templates/beru-finding.md`.

| Control | Control Owner (matrix) | Typical Fixer | Rank Range |
| --- | --- | --- | --- |
| AC-2 | PlatEng + ISSO | Manual / ArgoCD PR | C–B |
| AC-3 | PlatEng | kube-apiserver config | C |
| AC-5 | ISSO + CISO | Process + git approval | B |
| AC-6 | PlatEng (K8s) / CloudSec (IAM) | scope-rbac.sh / IAM policy update | C–B |
| AC-6(5) | PlatEng + CISO | Remove cluster-admin SAs | B |
| AC-17 | PlatEng | Kyverno exec policy | D–C |

Route all fixes to: JADE (DEVOPS-LENS/02-CLUSTER-HARDEN) or CloudSec team.
Route B/S findings to J with the full evidence package.

---

## Step 8 — Save and Reference SSP Examples

For each AC control that is PARTIAL or FAIL, write an SSP narrative.
Reference: `../ssp-examples/AC-ssp-great.md` for quality standard.

The great-tier narrative includes:
- The specific tool enforcing the control (Kyverno policy name, IAM policy ARN)
- The enforcement mode (Enforce, not Audit)
- The last review date and result
- The evidence artifact path
