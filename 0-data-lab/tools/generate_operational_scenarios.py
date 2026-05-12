#!/usr/bin/env python3
"""
Operational Scenario Training Data Generator
==============================================
Real-world situations Katie will face in production:
- ArgoCD drift wars (the #1 lesson from Portfolio)
- GitOps ownership checks before remediation
- Security hardening that respects infrastructure management
- Incident response routing decisions
- Multi-tool finding deduplication
- Client-facing communication

These aren't textbook questions — they're the exact scenarios that cost hours on real engagements.

Output: 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "operational_scenarios.jsonl"

SYSTEM_PROMPT = "You are Katie, a fast security triage and routing engine for GP-Copilot. Before fixing any Kubernetes resource, you MUST check who manages it. ArgoCD-managed resources are NEVER fixed with kubectl — fixes go through git. You route findings by rank (E/D/C/B/S) and always check resource ownership first."


def msg(user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}


def generate_argocd_scenarios():
    """ArgoCD drift war scenarios — the #1 lesson from Portfolio."""
    examples = []

    scenarios = [
        # === CORE PATTERN: kubectl patch on ArgoCD resource ===
        {
            "q": "Kubescape flagged that the 'web-app' Deployment in namespace 'portfolio' is missing securityContext.seccompProfile. I want to kubectl patch it. Should I?",
            "a": """**STOP. Check ownership first.**

```bash
kubectl get deployment web-app -n portfolio -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
```

If this returns an ArgoCD application name (e.g., `portfolio`), then **DO NOT kubectl patch**. ArgoCD will revert your change on the next sync cycle. Your fix will disappear and the finding will reappear.

**If ArgoCD-managed → Fix in git:**
1. Find the source repo: `kubectl get application portfolio -n argocd -o jsonpath='{.spec.source.repoURL}'`
2. Find the path: `kubectl get application portfolio -n argocd -o jsonpath='{.spec.source.path}'`
3. Edit the Helm chart `values.yaml` or the Deployment template to add:
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault
```
4. Commit, push, let ArgoCD sync
5. Verify: `argocd app get portfolio --refresh`

**If NOT ArgoCD-managed → Fix with kubectl:**
```bash
kubectl patch deployment web-app -n portfolio --type=merge -p '{"spec":{"template":{"spec":{"securityContext":{"seccompProfile":{"type":"RuntimeDefault"}}}}}}'
```

**Rank:** D (deterministic fix, but requires ownership check first)
**Route:** Check ownership → if git-managed, escalate to B-rank (human pushes to git); if kubectl-owned, E/D-rank auto-fix."""
        },
        {
            "q": "I added resource limits to a Deployment with kubectl patch, but they keep disappearing. What's happening?",
            "a": """**This is a drift war.** The Deployment is managed by ArgoCD (or Flux). When you kubectl patch a GitOps-managed resource, the controller detects the drift and reverts it to match the git source on the next sync.

**How to confirm:**
```bash
# Check if ArgoCD manages this resource
kubectl get deployment <name> -n <ns> -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'

# Check ArgoCD sync status — it will show OutOfSync
argocd app get <app-name>
kubectl get application <app-name> -n argocd -o jsonpath='{.status.sync.status}'
```

**The fix:**
1. Find the git repo and path:
```bash
kubectl get application <app-name> -n argocd -o jsonpath='{.spec.source.repoURL}'
kubectl get application <app-name> -n argocd -o jsonpath='{.spec.source.path}'
```
2. Add resource limits in the Helm chart `values.yaml` or Deployment template
3. Git commit and push
4. ArgoCD syncs the change — now it persists

**Hard rule:** ArgoCD-managed resources are NEVER fixed with kubectl. Fixes go through git. This is non-negotiable. We learned this the hard way — kubectl patches on ArgoCD resources caused hours of debugging on the Portfolio engagement.

**Rank:** B (requires human to push to git repo)"""
        },
        {
            "q": "I need to add Pod Security Admission labels to the 'production' namespace. The namespace is managed by ArgoCD. Can I kubectl label it?",
            "a": """**No. ArgoCD self-heal will revert your label on the next sync.**

We hit this exact problem on Portfolio — `kubectl label ns portfolio pod-security.kubernetes.io/enforce=restricted` was reverted by ArgoCD back to `enforce=baseline` because the Helm chart's namespace template didn't have the restricted label.

**The correct approach:**
1. Find the ArgoCD app that manages this namespace:
```bash
kubectl get ns production -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
```

2. Find the Helm chart source:
```bash
kubectl get application <app-name> -n argocd -o jsonpath='{.spec.source.path}'
```

3. Edit the namespace template in the Helm chart:
```yaml
# templates/namespace.yaml (or values.yaml depending on chart structure)
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

4. Commit, push, let ArgoCD sync

**Exception:** If the namespace is NOT managed by ArgoCD (e.g., kube-system, gatekeeper-system, monitoring):
```bash
kubectl label ns <namespace> pod-security.kubernetes.io/enforce=restricted
```
This is safe because no GitOps controller will revert it.

**Rank:** B (human must push to git for ArgoCD-managed namespaces)
**Route:** Escalate to human dashboard with clear instructions on which Helm chart to modify."""
        },
        # === OWNERSHIP CHECK PATTERNS ===
        {
            "q": "How do I check if a Kubernetes resource is managed by ArgoCD before applying a security fix?",
            "a": """**Always check ownership before fixing. This is step 1 of every remediation.**

```bash
# Method 1: Check ArgoCD tracking label
kubectl get <resource-type> <name> -n <namespace> -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
# Returns app name → ArgoCD-managed. Empty → kubectl OK.

# Method 2: Check all ArgoCD applications and their sources
kubectl get applications -n argocd -o custom-columns='APP:.metadata.name,PATH:.spec.source.path,SYNC:.status.sync.status'

# Method 3: Check for Flux management
kubectl get kustomizations -A -o custom-columns='NAME:.metadata.name,PATH:.spec.path,READY:.status.conditions[0].status'
```

**Decision tree:**
- **Returns ArgoCD app name** → Fix in git (push to the repo/path shown in the Application spec)
- **Returns Flux kustomization** → Fix in git (push to the sourceRef path)
- **Returns empty** → Fix with kubectl directly
- **Has Helm release label but no ArgoCD** → Fix with `helm upgrade`

**Resource types typically safe for kubectl (not GitOps-managed):**
- Gatekeeper ConstraintTemplates and Constraints
- ClusterRoleBindings created by cluster bootstrap
- LimitRanges and ResourceQuotas in non-app namespaces
- CIS benchmark remediations (API server flags, kubelet config)
- Falco DaemonSet (Helm-managed, not ArgoCD)

**Resource types that are ALWAYS ArgoCD-managed (never kubectl):**
- Application Deployments, Services, ConfigMaps, Ingresses
- Namespace labels in app namespaces
- Any resource with `app.kubernetes.io/instance` label

**Rank:** This check is rank E — fully deterministic, no AI needed."""
        },
        # === REAL FAILURE SCENARIOS ===
        {
            "q": "We ran argocd app sync --replace on an application and lost PVC data. What happened and how do we prevent this?",
            "a": """**`argocd app sync --replace` deletes and recreates ALL resources in the application, including PersistentVolumeClaims.** When PVCs are deleted, the backing PersistentVolume may be deleted too (depends on reclaimPolicy).

**What happened:**
1. `--replace` deleted the PVC
2. The PV reclaimPolicy was `Delete` (default for most StorageClasses)
3. The backing storage was destroyed
4. ArgoCD recreated the PVC, but it got a new PV with empty data
5. If Pod Security Admission was `enforce=restricted`, the new PVC couldn't mount because the provisioner runs as root

**Prevention rules:**
1. **Never use `argocd app sync --replace`** — this is a hard stop
2. Use `argocd app sync --force` if you need to force a sync (it patches instead of replacing)
3. Or just let auto-sync handle it (ArgoCD syncs every 3 minutes by default)
4. Set PV reclaimPolicy to `Retain` for production data:
```bash
kubectl patch pv <pv-name> -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
```

**Recovery if data is lost:**
- If reclaimPolicy was Retain, the PV still exists — rebind it
- If Delete, restore from backup (you do have etcd backups, right?)
```bash
ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-backup.db --data-dir=/var/lib/etcd-restored
```

**Rank:** S (data loss incident, human only)"""
        },
        {
            "q": "Kubescape found 15 findings across Deployments in the 'portfolio' namespace. Some are ArgoCD-managed, some are Gatekeeper-managed. How do I triage these?",
            "a": """**Split findings by resource owner before routing any fixes:**

**Step 1: Batch ownership check**
```bash
# Get all Deployments and their ArgoCD ownership
kubectl get deployments -n portfolio -o custom-columns='NAME:.metadata.name,ARGOCD:.metadata.labels.app\\.kubernetes\\.io/instance'
```

**Step 2: Split into two groups**

| Owner | Fix Method | Rank |
|-------|-----------|------|
| ArgoCD-managed Deployments | Fix in git, push to Helm chart | B (human pushes) |
| Non-ArgoCD resources (Gatekeeper, ResourceQuota) | Fix with kubectl directly | D/E (auto-fix) |

**Step 3: Route each group**

**ArgoCD-managed (B-rank):**
- Collect all findings for ArgoCD Deployments
- Bundle into ONE git commit per Deployment (one fix per commit, one sync per commit)
- Fixes go in the Helm chart `values.yaml`:
  - securityContext (runAsNonRoot, readOnlyRootFilesystem, capabilities)
  - resource limits/requests
  - seccompProfile
  - image tag → digest pinning
- Push to git, verify ArgoCD sync
- **Never kubectl patch these**

**Kubectl-owned (D/E-rank):**
- Gatekeeper constraints → `kubectl apply -f constraint.yaml`
- LimitRange/ResourceQuota → `kubectl apply -f limitrange.yaml`
- NetworkPolicy (if not in Helm chart) → `kubectl apply -f netpol.yaml`
- PSA labels on non-ArgoCD namespaces → `kubectl label ns`
- These can be auto-fixed by JSA agents

**Step 4: Deduplicate**
If Kubescape and Polaris both flag the same Deployment for "container running as root", that's one fix, not two. Deduplicate by resource + finding type before routing.

**Rank assignment:**
- ArgoCD Deployments → B-rank (human pushes git)
- Gatekeeper constraints → E-rank (deterministic kubectl apply)
- Resource limits on non-ArgoCD → D-rank (auto-fix with logging)"""
        },
        # === GIT-BASED REMEDIATION WORKFLOW ===
        {
            "q": "A Deployment managed by ArgoCD needs securityContext hardening (runAsNonRoot, readOnlyRootFilesystem, drop ALL capabilities, seccompProfile). Walk me through the correct fix.",
            "a": """**Git-based remediation for ArgoCD-managed Deployments:**

**Step 1: Find the source**
```bash
# Get the ArgoCD app that manages this Deployment
APP=$(kubectl get deployment <name> -n <ns> -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}')

# Get repo URL and path
kubectl get application $APP -n argocd -o jsonpath='{.spec.source.repoURL}'
kubectl get application $APP -n argocd -o jsonpath='{.spec.source.path}'
```

**Step 2: Clone and edit**
```bash
git clone <repo-url>
cd <path>
```

**Step 3: Edit the Helm chart values.yaml (or Deployment template)**
```yaml
# values.yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10000
  runAsGroup: 10000
  fsGroup: 10000
  seccompProfile:
    type: RuntimeDefault

containerSecurityContext:
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
```

If the chart uses `securityContext` directly in the template:
```yaml
# templates/deployment.yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: {{ .Values.name }}
        securityContext:
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
```

**Step 4: If the app needs /tmp writes, add emptyDir**
```yaml
volumeMounts:
- name: tmp
  mountPath: /tmp
volumes:
- name: tmp
  emptyDir: {}
```

**Step 5: Commit and push (one fix per commit)**
```bash
git add values.yaml
git commit -m "security: add securityContext hardening (runAsNonRoot, readOnlyRootFilesystem, drop ALL)"
git push
```

**Step 6: Verify ArgoCD sync**
```bash
argocd app get $APP --refresh
# Wait for Synced + Healthy
kubectl get deployment <name> -n <ns> -o jsonpath='{.spec.template.spec.securityContext}'
```

**Hard rules:**
- One commit per fix type (don't batch securityContext + resource limits)
- Never `argocd app sync --replace`
- Verify sync status between commits
- If ArgoCD shows OutOfSync after your push, check for conflicts with other chart values"""
        },
        # === WHAT KUBECTL IS OK FOR ===
        {
            "q": "What security remediations CAN I safely apply with kubectl without worrying about ArgoCD?",
            "a": """**Resources NOT managed by ArgoCD — safe for kubectl:**

**1. Gatekeeper / OPA constraints and templates**
```bash
kubectl apply -f constraint-template.yaml
kubectl apply -f constraint.yaml
# ArgoCD doesn't manage these (unless someone put them in an ArgoCD app)
```

**2. PSA namespace labels on non-ArgoCD namespaces**
```bash
kubectl label ns monitoring pod-security.kubernetes.io/enforce=restricted
kubectl label ns gatekeeper-system pod-security.kubernetes.io/enforce=privileged
# Safe because these namespaces aren't in any ArgoCD Application
```

**3. ClusterRoleBindings from cluster bootstrap**
```bash
kubectl delete clusterrolebinding permissive-binding
# These were created by kubeadm/k3s, not ArgoCD
```

**4. Kyverno ClusterPolicies (if not ArgoCD-managed)**
```bash
kubectl apply -f require-nonroot.yaml
# Verify first: kubectl get clusterpolicy require-nonroot -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
```

**5. CIS benchmark remediations on nodes**
```bash
# These are node-level, not Kubernetes API objects
sudo chmod 600 /etc/kubernetes/manifests/kube-apiserver.yaml
sudo chmod 600 /var/lib/kubelet/config.yaml
```

**6. ResourceQuota / LimitRange in non-app namespaces**
```bash
kubectl apply -f resourcequota.yaml -n monitoring
```

**7. NetworkPolicy (if not in a Helm chart)**
```bash
# Check first!
kubectl get networkpolicy -n <ns> -o jsonpath='{.items[*].metadata.labels.app\\.kubernetes\\.io/instance}'
# If empty → safe for kubectl
kubectl apply -f default-deny.yaml -n <ns>
```

**Always check first:**
```bash
kubectl get <resource> <name> -n <ns> -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
```
Empty = safe for kubectl. App name = go to git."""
        },
        # === MULTI-SCANNER DEDUPLICATION ===
        {
            "q": "Kubescape says 'container running as root' on Deployment/web-app. Polaris says the same thing. Checkov also flagged it. That's 3 findings but really 1 problem. How should I handle this?",
            "a": """**Deduplicate before routing.** Three scanners found the same issue — this is ONE fix, not three.

**Deduplication logic:**
- Same resource (Deployment/web-app) + same finding type (running as root) = 1 finding
- Pick the highest severity from the three scanners
- Log all scanner sources for audit trail
- Route once, not three times

**How to identify duplicates:**
```
Finding 1: Kubescape C-0013 → Deployment/web-app → "Container running as root"
Finding 2: Polaris run-as-root → Deployment/web-app → "Container running as root"
Finding 3: Checkov CKV_K8S_6 → Deployment/web-app → "Should not run as root"
```

**Fingerprint:** `title(running as root) + resource(Deployment/web-app) + severity(HIGH)` → same hash → deduplicate

**Routing the single finding:**
1. Check ownership: `kubectl get deployment web-app -n <ns> -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'`
2. If ArgoCD-managed → B-rank (fix in git: add `runAsNonRoot: true` to Helm chart)
3. If kubectl-owned → D-rank (auto-fix: `kubectl patch`)
4. Log: "Finding deduplicated from 3 scanners: Kubescape C-0013, Polaris run-as-root, Checkov CKV_K8S_6"

**Rank:** D (deterministic fix once ownership is determined)
**Deduplication is critical** — without it, you waste time applying the same fix three times, or worse, sending three separate notifications to the client."""
        },
        # === HELM UPGRADE vs GIT PUSH ===
        {
            "q": "Falco is deployed via Helm but NOT managed by ArgoCD. I need to add a custom Falco rule. Do I kubectl apply or helm upgrade?",
            "a": """**Helm-managed (not ArgoCD) → use helm upgrade, not kubectl apply.**

If you kubectl apply a ConfigMap that Helm manages, the next `helm upgrade` will overwrite your change. Similar to ArgoCD drift, but with Helm.

**Check management:**
```bash
# Check if Helm manages it
kubectl get configmap falco-rules -n falco -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/managed-by}'
# Returns "Helm" → use helm upgrade

# Check if ArgoCD manages it
kubectl get configmap falco-rules -n falco -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
# Empty → not ArgoCD
```

**Add custom Falco rule via Helm:**
```bash
# Create a values override file
cat > falco-custom-rules.yaml << 'EOF'
customRules:
  custom-rules.yaml: |-
    - rule: Shell Spawned in Container
      desc: Detect shell execution in containers
      condition: spawned_process and container and proc.name in (bash, sh, zsh)
      output: "Shell spawned (user=%user.name container=%container.name image=%container.image.repository)"
      priority: WARNING
      tags: [runtime, shell]
EOF

# Upgrade Falco with custom rules
helm upgrade falco falcosecurity/falco -n falco -f falco-custom-rules.yaml
```

**The ownership hierarchy:**
1. ArgoCD-managed → fix in git, push, let ArgoCD sync
2. Helm-managed (not ArgoCD) → `helm upgrade` with values override
3. kubectl-managed (no controller) → `kubectl apply` directly

**Rank:** D (deterministic Helm upgrade with known values)"""
        },
        # === INCIDENT SCENARIOS ===
        {
            "q": "Falco alert: 'Shell Spawned in Container' in production namespace. The pod is part of an ArgoCD-managed Deployment. What do I do?",
            "a": """**This is a runtime security incident — respond first, fix ownership later.**

**Immediate response (regardless of ArgoCD):**
```bash
# Step 1: Isolate the pod with a NetworkPolicy (block all traffic)
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-compromised-pod
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: <pod-app-label>
  policyTypes:
  - Ingress
  - Egress
EOF

# Step 2: Capture forensics before killing
kubectl logs <pod-name> -n production > /tmp/forensics-$(date +%s).log
kubectl describe pod <pod-name> -n production > /tmp/forensics-describe-$(date +%s).log
kubectl exec <pod-name> -n production -- ps aux > /tmp/forensics-ps-$(date +%s).log 2>/dev/null

# Step 3: Kill the pod (the Deployment will recreate it)
kubectl delete pod <pod-name> -n production
```

**The NetworkPolicy is NOT ArgoCD-managed** (we just created it with kubectl), so no drift war. This is an incident response action, not a GitOps change.

**Post-incident (fix root cause):**
Since the Deployment is ArgoCD-managed:
1. Push a securityContext hardening commit to git:
   - `readOnlyRootFilesystem: true` (prevents writing scripts)
   - `capabilities.drop: ALL` (prevents privilege escalation)
   - `seccompProfile: RuntimeDefault` (restricts syscalls)
2. Let ArgoCD sync the hardened Deployment
3. The NetworkPolicy isolation can be removed after the new pods are running

**Rank:**
- Immediate response (isolate + capture) → E-rank (deterministic, no approval needed)
- Root cause fix → B-rank (human pushes to git)
- Cleanup (remove isolation NetworkPolicy) → E-rank (deterministic)"""
        },
        {
            "q": "A finding says a container image uses :latest tag. The Deployment is in an ArgoCD-managed namespace. How do I fix it?",
            "a": """**Pin the image to a digest in the git source, not with kubectl.**

**Step 1: Get the current image and its digest**
```bash
# Get current image
kubectl get deployment <name> -n <ns> -o jsonpath='{.spec.template.spec.containers[0].image}'
# Output: nginx:latest

# Get the digest for pinning
crane digest nginx:latest
# Output: sha256:a484819eb60211f36f90f13b5b457f7ca8e57dddbb9e4e0f1f3f24cebc7d5f2f
```

**Step 2: Verify ArgoCD ownership**
```bash
kubectl get deployment <name> -n <ns> -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
# Returns app name → MUST fix in git
```

**Step 3: Fix in the Helm chart**
```yaml
# values.yaml
image:
  repository: nginx
  tag: ""  # Remove the tag
  digest: sha256:a484819eb60211f36f90f13b5b457f7ca8e57dddbb9e4e0f1f3f24cebc7d5f2f
```

Or in the template directly:
```yaml
image: nginx@sha256:a484819eb60211f36f90f13b5b457f7ca8e57dddbb9e4e0f1f3f24cebc7d5f2f
```

**Step 4: Sign the image with Cosign (if not already signed)**
```bash
cosign sign --key cosign.key nginx@sha256:a484819eb60211f36f90f13b5b457f7ca8e57dddbb9e4e0f1f3f24cebc7d5f2f
```

**Step 5: Git commit and push**
```bash
git commit -m "security: pin nginx image to digest, remove :latest tag"
git push
# ArgoCD syncs the change
```

**Why this matters:**
- `:latest` is mutable — someone could push a compromised image with the same tag
- Image digest is immutable — same SHA256 = same binary, always
- Combined with Cosign signature verification, this prevents supply chain attacks

**Rank:** B (requires human git push for ArgoCD-managed Deployment)"""
        },
    ]

    for s in scenarios:
        examples.append(msg(s["q"], s["a"]))

    return examples


def generate_triage_routing_scenarios():
    """Real triage decisions Katie makes in production."""
    examples = []

    scenarios = [
        {
            "q": "Trivy found CVE-2024-3094 (CRITICAL) in xz-utils 5.6.0 in the base image of a production Deployment. Route this finding.",
            "a": """**CVE-2024-3094 is the xz backdoor — CRITICAL supply chain compromise.**

**Triage:**
- Severity: CRITICAL
- Scanner: Trivy
- Type: Dependency vulnerability (CVE)
- Resource: Production Deployment base image

**Rank: C** — This is not a simple version bump. CVE-2024-3094 was a deliberate supply chain attack. Requires JADE review for:
1. Blast radius assessment (which services use this image?)
2. Whether the compromised code path is reachable
3. Whether the fix (downgrade to xz 5.4.x or upgrade to 5.6.1+) breaks anything

**Route: JADE** with enrichment:
- Pull similar CVEs from RAG for context
- Check FindingsStore for other services using the same base image
- Estimated blast radius: HIGH

**Do NOT auto-fix** — a base image change on a production Deployment needs:
1. Build new image with patched xz
2. Test in staging
3. Update image reference (via git if ArgoCD-managed)
4. Verify deployment health post-rollout"""
        },
        {
            "q": "Bandit found B101 (assert used for security check) in a Python file. Rank and route.",
            "a": """**Rank: E** — Deterministic pattern fix, no AI needed.

**Route: Runbook → sast_fixer**

`assert` statements are stripped when Python runs with optimization (`-O` flag). Using them for security checks means the check disappears in production.

**Auto-fix:**
```python
# Before (insecure)
assert user.is_authenticated, "Not authenticated"

# After (secure)
if not user.is_authenticated:
    raise PermissionError("Not authenticated")
```

**Confidence: 1.0** — This is a deterministic replacement.
**Scanner: Bandit B101**
**No ownership check needed** — this is a code change, not a Kubernetes resource. Goes through normal PR review."""
        },
        {
            "q": "Polaris found 'hostNetwork: true' on a DaemonSet in kube-system. Route this.",
            "a": """**Check before routing — some kube-system DaemonSets legitimately need hostNetwork.**

**Expected hostNetwork=true:**
- `kube-proxy` — needs host network for iptables/IPVS management
- `calico-node` / `cilium` — CNI plugins need host network
- `falco` — needs host access for syscall monitoring
- `node-exporter` — needs host network for node metrics

**Check what DaemonSet this is:**
```bash
kubectl get daemonset -n kube-system -o custom-columns='NAME:.metadata.name,HOST_NET:.spec.template.spec.hostNetwork'
```

**If it's a system component (kube-proxy, CNI, Falco):**
- Rank: E (suppress — known-good, expected behavior)
- Route: Suppress finding, log as "accepted risk: system component requires hostNetwork"

**If it's an application DaemonSet that shouldn't have hostNetwork:**
- Rank: D (fix by removing hostNetwork)
- Route: Check ownership (ArgoCD or kubectl), then remove `hostNetwork: true`

**Key lesson:** Not every finding is a real vulnerability. Katie must understand context before routing. kube-system is special."""
        },
        {
            "q": "Gitleaks found a hardcoded AWS access key in a committed file. This is in a client's repo. Route this.",
            "a": """**Rank: S — Human only. Immediate escalation.**

**This is a live credential exposure:**
1. The key is in git history — even if you delete the file, it's in the log
2. Anyone with repo access can extract it
3. The key may already be compromised

**Immediate actions (human must execute):**
1. **Revoke the key NOW** — before anything else:
```bash
aws iam delete-access-key --user-name <user> --access-key-id <key-id>
```

2. **Check CloudTrail** for unauthorized usage:
```bash
aws cloudtrail lookup-events --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=<key-id>
```

3. **Purge from git history:**
```bash
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch <file>' --prune-empty -- --all
# Or use BFG Repo-Cleaner (faster)
bfg --delete-files <file> .
git push --force
```

4. **Rotate all credentials** that might have been adjacent to the leaked key

**Route: Human dashboard — S-rank**
- Cannot be auto-fixed (requires AWS console/CLI access)
- Cannot be deferred (live credential exposure)
- Flag to client immediately
- JSA agents do NOT handle S-rank findings"""
        },
        {
            "q": "Checkov found CKV_K8S_28 (missing NetworkPolicy) on 12 namespaces. Route this.",
            "a": """**Rank: D** — Deterministic fix, but batch carefully.

**Before fixing, check each namespace's ownership:**
```bash
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  owner=$(kubectl get ns $ns -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}' 2>/dev/null)
  echo "$ns: ${owner:-kubectl}"
done
```

**Split into two groups:**

**ArgoCD-managed namespaces** → B-rank
- NetworkPolicy goes in the Helm chart
- Push to git, ArgoCD syncs
- Human must do this

**Kubectl-owned namespaces** → D-rank (auto-fix)
```bash
# Generate default-deny NetworkPolicy for each namespace
for ns in monitoring gatekeeper-system falco; do
  kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: $ns
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
EOF
done
```

**Always include DNS egress** in default-deny policies — without it, pods can't resolve service names.

**Deduplication:** 12 findings but probably 2-3 groups (ArgoCD-managed, Helm-managed, kubectl). Route per group, not per finding."""
        },
    ]

    for s in scenarios:
        examples.append(msg(s["q"], s["a"]))

    return examples


def main():
    all_examples = []

    print("[1/2] Generating ArgoCD/GitOps operational scenarios...")
    argocd = generate_argocd_scenarios()
    all_examples.extend(argocd)

    print("[2/2] Generating triage routing scenarios...")
    triage = generate_triage_routing_scenarios()
    all_examples.extend(triage)

    random.shuffle(all_examples)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nGenerated {len(all_examples)} operational scenario examples")
    print(f"  ArgoCD/GitOps ownership: {len(argocd)}")
    print(f"  Triage routing: {len(triage)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
