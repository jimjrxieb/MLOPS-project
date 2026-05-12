#!/usr/bin/env python3
"""
generate_diagnostic_chains.py — C-rank multi-step diagnostic training data.

This is Katie's sweet spot: events that require diagnosis before fix.
Each example teaches a complete chain: symptom → diagnosis → root cause → fix → verify.

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""

import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "diagnostic_chains.jsonl"

SYSTEM_PROMPT = (
    "You are Katie, a CKS/CKA/CKAD-certified Kubernetes platform engineer. "
    "When given a cluster event, you diagnose the root cause step by step using real tools "
    "(kubectl, crictl, journalctl, curl), then provide the complete fix with verification. "
    "Every diagnostic chain follows: symptom → check → root cause → fix → verify."
)

def msg(user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]}


def generate_crashloopbackoff():
    """CrashLoopBackOff — the classic multi-step diagnosis."""
    examples = []

    # OOM variant
    examples.append(msg(
        "Pod payments/api-7f8b9d is in CrashLoopBackOff. Diagnose and fix.",
        """**Step 1: Check pod status and restart count**
```bash
kubectl get pod api-7f8b9d -n payments -o wide
kubectl describe pod api-7f8b9d -n payments | grep -A5 "Last State"
```

**Step 2: Check container exit code**
```bash
kubectl get pod api-7f8b9d -n payments -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'
```
Result: `OOMKilled` — container exceeded memory limit.

**Step 3: Check current limits vs actual usage**
```bash
kubectl get pod api-7f8b9d -n payments -o jsonpath='{.spec.containers[0].resources}'
kubectl top pod api-7f8b9d -n payments --containers
```

**Step 4: Check if VPA has recommendations**
```bash
kubectl get vpa -n payments -o yaml | grep -A10 "containerRecommendations"
```

**Root cause:** Memory limit set to 256Mi but container uses ~400Mi under load.

**Fix:**
```yaml
# Increase memory limit (2x headroom over observed usage)
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "768Mi"
    cpu: "500m"
```

```bash
kubectl patch deployment api -n payments --type=json \\
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"768Mi"},
       {"op":"replace","path":"/spec/template/spec/containers/0/resources/requests/memory","value":"512Mi"}]'
```

**Verify:**
```bash
kubectl rollout status deployment/api -n payments --timeout=120s
kubectl get pod -n payments -l app=api --watch
# Confirm no more OOMKilled after 5 minutes
```"""
    ))

    # Bad config variant
    examples.append(msg(
        "Pod auth-service/login-5c9d8e is CrashLoopBackOff. Exit code 1. No OOM.",
        """**Step 1: Check logs for the crash reason**
```bash
kubectl logs auth-service/login-5c9d8e -n auth-service --previous
```

**Step 2: Check if it's a config issue**
```bash
kubectl describe pod login-5c9d8e -n auth-service | grep -A10 "Environment"
kubectl get configmap -n auth-service
kubectl get secret -n auth-service
```

**Step 3: Check if referenced ConfigMap/Secret exists**
```bash
kubectl get pod login-5c9d8e -n auth-service -o jsonpath='{.spec.containers[0].envFrom[*].configMapRef.name}'
kubectl get pod login-5c9d8e -n auth-service -o jsonpath='{.spec.containers[0].envFrom[*].secretRef.name}'
```

Result: Pod references ConfigMap `login-config` but it doesn't exist in the namespace.

**Root cause:** ConfigMap `login-config` was deleted or never created in this namespace.

**Fix:**
```bash
# Check if it exists in another namespace (common after migration)
kubectl get configmap login-config --all-namespaces

# If found, copy it:
kubectl get configmap login-config -n default -o yaml | \\
  sed 's/namespace: default/namespace: auth-service/' | \\
  kubectl apply -f -

# If not found, check git for the manifest:
# git log --all -- '**/login-config*'
```

**Verify:**
```bash
kubectl get configmap login-config -n auth-service
kubectl delete pod login-5c9d8e -n auth-service  # Force restart
kubectl get pods -n auth-service -l app=login --watch
```"""
    ))

    # Probe failure variant
    examples.append(msg(
        "Deployment cache-server in namespace infra keeps restarting. kubectl logs shows the app starts fine then gets killed.",
        """**Step 1: Check if it's probe-related**
```bash
kubectl describe pod -n infra -l app=cache-server | grep -A5 "Liveness\\|Readiness"
kubectl get events -n infra --field-selector involvedObject.kind=Pod --sort-by=.lastTimestamp | tail -20
```

**Step 2: Check probe configuration**
```bash
kubectl get deployment cache-server -n infra -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}' | python3 -m json.tool
```

Result: Liveness probe hits `/health` on port 8080 with `initialDelaySeconds: 5` and `timeoutSeconds: 1`.

**Step 3: Test the health endpoint manually**
```bash
kubectl exec -n infra -it $(kubectl get pod -n infra -l app=cache-server -o name | head -1) -- curl -s -o /dev/null -w "%{http_code} %{time_total}s" http://localhost:8080/health
```

Result: Returns 200 but takes 2.3 seconds. Probe timeout is 1 second.

**Root cause:** Liveness probe timeout (1s) is shorter than the health endpoint response time (2.3s) during cache warming. Kubelet kills the container thinking it's dead.

**Fix:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30    # Was 5 — give cache time to warm
  timeoutSeconds: 5           # Was 1 — endpoint is slow during load
  periodSeconds: 10
  failureThreshold: 3         # Allow 3 failures before kill
startupProbe:                 # Add startup probe for initial warmup
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 12        # 60 seconds to start (12 × 5s)
```

**Verify:**
```bash
kubectl rollout status deployment/cache-server -n infra --timeout=120s
# Watch for 5 minutes — no restarts
kubectl get pod -n infra -l app=cache-server -w
```"""
    ))

    # Missing secret variant
    examples.append(msg(
        "New deployment worker-processor in namespace jobs crashes immediately. kubectl logs shows 'FATAL: DATABASE_URL not set'.",
        """**Step 1: Check environment configuration**
```bash
kubectl get deployment worker-processor -n jobs -o jsonpath='{.spec.template.spec.containers[0].env[*].name}'
kubectl get deployment worker-processor -n jobs -o jsonpath='{.spec.template.spec.containers[0].envFrom}'
```

**Step 2: Check if the referenced Secret exists**
```bash
kubectl get secret -n jobs
kubectl get deployment worker-processor -n jobs -o yaml | grep -A3 secretRef
```

Result: Deployment references `secretRef: db-credentials` but the Secret doesn't exist in namespace `jobs`.

**Step 3: Check if it's an ExternalSecret issue**
```bash
kubectl get externalsecret -n jobs
kubectl describe externalsecret db-credentials -n jobs 2>/dev/null
```

Result: ExternalSecret exists but status shows `SecretSyncedError: could not find secret data`.

**Root cause:** ExternalSecret can't sync from AWS Secrets Manager — either the secret doesn't exist in ASM or the IRSA role doesn't have permission.

**Fix:**
```bash
# Check the SecretStore configuration
kubectl get secretstore -n jobs -o yaml

# Verify AWS secret exists
aws secretsmanager describe-secret --secret-id jobs/db-credentials --region us-east-1

# If the secret exists, check IRSA permissions
kubectl get sa -n jobs -o yaml | grep annotations -A2
# Verify the role has secretsmanager:GetSecretValue permission

# If the secret doesn't exist, create it:
aws secretsmanager create-secret \\
  --name jobs/db-credentials \\
  --secret-string '{"DATABASE_URL":"postgresql://user:pass@rds-endpoint:5432/db"}' \\
  --region us-east-1

# Force ExternalSecret resync
kubectl annotate externalsecret db-credentials -n jobs force-sync=$(date +%s) --overwrite
```

**Verify:**
```bash
kubectl get externalsecret db-credentials -n jobs -o jsonpath='{.status.conditions}'
kubectl get secret db-credentials -n jobs
kubectl rollout restart deployment/worker-processor -n jobs
kubectl logs -n jobs -l app=worker-processor --tail=5 -f
```"""
    ))

    return examples


def generate_oomkilled():
    """OOMKilled — right-sizing diagnosis."""
    examples = []

    examples.append(msg(
        "Pod web-frontend in namespace prod was OOMKilled. Current limit is 512Mi.",
        """**Step 1: Confirm OOM and check history**
```bash
kubectl describe pod -n prod -l app=web-frontend | grep -A3 "Last State"
kubectl get events -n prod --field-selector reason=OOMKilling --sort-by=.lastTimestamp
```

**Step 2: Check actual memory usage pattern**
```bash
kubectl top pod -n prod -l app=web-frontend --containers
# If metrics-server has history, check peak usage:
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/prod/pods | \\
  python3 -c "import sys,json; [print(p['metadata']['name'], p['containers'][0]['usage']['memory']) for p in json.load(sys.stdin)['items'] if 'web-frontend' in p['metadata']['name']]"
```

**Step 3: Check VPA recommendations (if VPA installed)**
```bash
kubectl get vpa -n prod -l app=web-frontend -o jsonpath='{.items[0].status.recommendation.containerRecommendations[0]}'
```

**Step 4: Profile the actual requirement**
Current: 512Mi limit, pod uses ~480Mi under normal load, spikes to ~600Mi under traffic.

**Root cause:** Memory limit too tight — no headroom for traffic spikes.

**Fix:**
```yaml
resources:
  requests:
    memory: "512Mi"    # Match normal usage
  limits:
    memory: "1Gi"      # 2x headroom for spikes
```

```bash
kubectl set resources deployment/web-frontend -n prod \\
  --limits=memory=1Gi --requests=memory=512Mi
```

**Verify:**
```bash
kubectl rollout status deployment/web-frontend -n prod
# Monitor for 30 minutes during traffic:
watch kubectl top pod -n prod -l app=web-frontend
# Confirm no OOMKilled events
kubectl get events -n prod --field-selector reason=OOMKilling
```"""
    ))

    return examples


def generate_dns_resolution():
    """DNS resolution failures."""
    examples = []

    examples.append(msg(
        "Service api-gateway in namespace prod can't resolve backend-service.internal.svc.cluster.local. Pods are healthy.",
        """**Step 1: Verify CoreDNS is running**
```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=20
```

**Step 2: Test DNS from inside the pod**
```bash
kubectl exec -n prod -it $(kubectl get pod -n prod -l app=api-gateway -o name | head -1) -- nslookup backend-service.internal.svc.cluster.local
```

Result: `server can't find backend-service.internal.svc.cluster.local: NXDOMAIN`

**Step 3: Check if the service exists**
```bash
kubectl get svc backend-service -n internal
kubectl get endpoints backend-service -n internal
```

Result: Service exists in namespace `internal` but the pod is resolving with wrong domain.

**Root cause:** The FQDN is wrong. Cross-namespace service DNS format is `<service>.<namespace>.svc.cluster.local`, not `<service>.<namespace>.svc.cluster.local` with a typo in the namespace name.

**Step 4: Verify correct DNS name**
```bash
kubectl exec -n prod -it $(kubectl get pod -n prod -l app=api-gateway -o name | head -1) -- nslookup backend-service.internal.svc.cluster.local
```

If still failing, check NetworkPolicy:
```bash
kubectl get networkpolicy -n prod -o yaml | grep -A10 "egress"
# DNS requires egress to kube-system on port 53 (TCP and UDP)
```

**Fix (if NetworkPolicy blocks DNS):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: prod
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
        - protocol: TCP
          port: 53
```

**Verify:**
```bash
kubectl apply -f allow-dns.yaml
kubectl exec -n prod -it $(kubectl get pod -n prod -l app=api-gateway -o name | head -1) -- nslookup backend-service.internal.svc.cluster.local
# Should resolve to the ClusterIP
```"""
    ))

    return examples


def generate_argocd_scenarios():
    """ArgoCD operational issues."""
    examples = []

    examples.append(msg(
        "ArgoCD shows application 'portfolio-api' as OutOfSync and Degraded. Last sync was successful 2 hours ago.",
        """**Step 1: Check what drifted**
```bash
argocd app diff portfolio-api
# Or via kubectl:
kubectl get application portfolio-api -n argocd -o jsonpath='{.status.sync.status}'
kubectl get application portfolio-api -n argocd -o jsonpath='{.status.conditions}' | python3 -m json.tool
```

**Step 2: Check if someone manually changed a resource**
```bash
# Check ArgoCD resource tree for out-of-sync resources
argocd app resources portfolio-api --orphaned
kubectl get application portfolio-api -n argocd -o jsonpath='{.status.resources[?(@.status=="OutOfSync")]}' | python3 -m json.tool
```

Result: Deployment `portfolio-api` has different resource limits than what's in git. Someone ran `kubectl edit`.

**Step 3: Verify ArgoCD ownership**
```bash
kubectl get deployment portfolio-api -n portfolio -o jsonpath='{.metadata.labels.app\\.kubernetes\\.io/instance}'
```
Returns: `portfolio-api` — this IS ArgoCD-managed. Manual kubectl edits will be reverted.

**Root cause:** Someone manually patched resource limits via `kubectl edit`. ArgoCD self-heal detected the drift.

**Fix:** Do NOT kubectl patch. Fix in git:
```bash
# Check what the git source expects
argocd app get portfolio-api -o yaml | grep repoURL
# Edit the Helm values or kustomization in git
git clone <repo>
# Update the resource limits in the correct values file
git add . && git commit -m "fix: update portfolio-api resource limits"
git push

# Sync
argocd app sync portfolio-api
```

**NEVER** `kubectl edit` or `kubectl patch` an ArgoCD-managed resource. ArgoCD will revert it or go into sync loop.

**Verify:**
```bash
argocd app wait portfolio-api --sync --health --timeout 120
argocd app get portfolio-api
# Should show: Sync Status: Synced, Health Status: Healthy
```"""
    ))

    # Sync loop variant
    examples.append(msg(
        "ArgoCD application 'security-policies' is stuck in a sync loop. It syncs, then immediately goes OutOfSync again.",
        """**Step 1: Identify what keeps changing**
```bash
argocd app diff security-policies
# Check which resources keep going OutOfSync
kubectl get application security-policies -n argocd -o jsonpath='{.status.resources[?(@.status=="OutOfSync")].name}'
```

**Step 2: Check for mutating webhooks**
```bash
kubectl get mutatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations -o yaml | grep -B5 "namespaceSelector\\|objectSelector"
```

Result: Gatekeeper mutation webhook is modifying resources after ArgoCD deploys them.

**Root cause:** Gatekeeper (or Kyverno) mutation policies add/modify fields on resources after ArgoCD applies them. ArgoCD sees the mutation as drift and re-syncs, triggering the mutation again → infinite loop.

**Fix options:**

**Option A: Tell ArgoCD to ignore the mutated fields**
```yaml
# In the Application spec:
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /metadata/annotations/gatekeeper.sh~1mutation-id
        - /spec/template/metadata/labels/gatekeeper-mutated
```

**Option B: Move the mutation to the git source (preferred)**
Add the fields Gatekeeper would add directly in your manifests, so ArgoCD and Gatekeeper agree.

**Option C: Exclude the resource from ArgoCD management**
Only if the resource should be managed by the admission controller, not GitOps.

**Verify:**
```bash
argocd app sync security-policies
# Wait 60 seconds
argocd app get security-policies
# Should stay Synced — no more loop
kubectl get events -n argocd --field-selector involvedObject.name=security-policies --sort-by=.lastTimestamp | tail -5
```"""
    ))

    return examples


def generate_connection_issues():
    """App not working even though pods are healthy."""
    examples = []

    examples.append(msg(
        "Users report 502 errors on api.example.com. All pods show Running and Ready. Ingress is healthy.",
        """**Step 1: Verify pods are actually serving**
```bash
kubectl get pods -n prod -l app=api -o wide
# Check if readiness probe is actually passing
kubectl describe pod -n prod -l app=api | grep -A5 "Readiness"
```

**Step 2: Test from inside the cluster**
```bash
# Exec into a debug pod and curl the service directly
kubectl run debug --rm -it --image=curlimages/curl -n prod -- \\
  curl -v http://api-service.prod.svc.cluster.local:8080/health
```

Result: `Connection refused` — the app isn't listening on port 8080.

**Step 3: Check what port the app actually listens on**
```bash
kubectl exec -n prod $(kubectl get pod -n prod -l app=api -o name | head -1) -- ss -tlnp
# Or:
kubectl exec -n prod $(kubectl get pod -n prod -l app=api -o name | head -1) -- netstat -tlnp
```

Result: App listens on port 3000, not 8080.

**Step 4: Check Service and Deployment port configuration**
```bash
kubectl get svc api-service -n prod -o yaml | grep -A5 ports
kubectl get deployment api -n prod -o jsonpath='{.spec.template.spec.containers[0].ports}'
```

**Root cause:** Service `targetPort` is 8080 but container listens on 3000. The readiness probe passes because it checks a different port or uses exec.

**Fix:**
```bash
kubectl patch svc api-service -n prod --type=json \\
  -p '[{"op":"replace","path":"/spec/ports/0/targetPort","value":3000}]'
```

Or if ArgoCD-managed, fix in git:
```yaml
# In the Service spec:
spec:
  ports:
    - port: 80
      targetPort: 3000    # Match what the app actually listens on
      protocol: TCP
```

Also fix the container port declaration:
```yaml
# In the Deployment spec:
containers:
  - name: api
    ports:
      - containerPort: 3000   # Document the real port
```

**Verify:**
```bash
kubectl run debug --rm -it --image=curlimages/curl -n prod -- \\
  curl -s -o /dev/null -w "%{http_code}" http://api-service.prod.svc.cluster.local/health
# Should return 200

# Test external
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health
```"""
    ))

    return examples


def generate_eviction_scenarios():
    """Pod eviction and node pressure."""
    examples = []

    examples.append(msg(
        "Multiple pods in namespace analytics were evicted. kubectl get events shows 'The node was low on resource: ephemeral-storage'.",
        """**Step 1: Identify which node and check conditions**
```bash
kubectl get events -n analytics --field-selector reason=Evicted --sort-by=.lastTimestamp
kubectl describe node <node-name> | grep -A10 "Conditions"
```

**Step 2: Check disk usage on the node**
```bash
kubectl get node <node-name> -o jsonpath='{.status.allocatable.ephemeral-storage}'
# Check what's consuming disk
kubectl describe node <node-name> | grep -A20 "Non-terminated Pods"
```

**Step 3: Find the disk hogs**
```bash
# Check container log sizes
kubectl get pods -n analytics -o name | while read pod; do
  echo "$pod: $(kubectl exec -n analytics $pod -- du -sh /var/log 2>/dev/null || echo 'N/A')"
done

# Check emptyDir volumes
kubectl get pods -n analytics -o json | python3 -c "
import json,sys
for pod in json.load(sys.stdin)['items']:
  for vol in pod['spec'].get('volumes',[]):
    if 'emptyDir' in vol and vol['emptyDir'].get('sizeLimit') is None:
      print(f\"{pod['metadata']['name']}: emptyDir '{vol['name']}' has no sizeLimit\")
"
```

**Root cause:** Analytics pods write large temp files to emptyDir volumes without sizeLimit. When total ephemeral storage exceeds 80% of allocatable, kubelet evicts pods.

**Fix:**
```yaml
# Add sizeLimit to emptyDir volumes
volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 1Gi
  - name: cache
    emptyDir:
      sizeLimit: 2Gi

# Add ephemeral-storage limits to containers
resources:
  requests:
    ephemeral-storage: "2Gi"
  limits:
    ephemeral-storage: "4Gi"
```

**Verify:**
```bash
kubectl apply -f updated-deployment.yaml
kubectl rollout status deployment/analytics-processor -n analytics
# Monitor node disk pressure
kubectl describe node <node-name> | grep -A5 "Conditions"
# Should not show DiskPressure=True
```"""
    ))

    return examples


def generate_admission_deny_complex():
    """Admission denies that require multi-step fixes (C-rank, not D-rank)."""
    examples = []

    examples.append(msg(
        "Kyverno denied my deployment: 'validation error: Containers must have a readOnlyRootFilesystem'. But my app writes to /tmp and /var/cache.",
        """**Step 1: Understand the policy**
```bash
kubectl get clusterpolicy require-readonly-rootfs -o yaml | grep -A10 "validation"
```

This policy requires `securityContext.readOnlyRootFilesystem: true` on all containers.

**Step 2: Identify writable paths your app needs**
```bash
# Check what paths the app writes to (if you can exec into a running version)
kubectl exec -it <pod> -- find / -writable -type d 2>/dev/null
# Common writable paths:
# /tmp                    — temp files
# /var/cache              — application cache
# /var/run                — PID files
# /home/<user>            — user home dir
# /app/logs               — application logs
```

**Step 3: Apply the fix — readOnlyRootFilesystem + emptyDir for writable paths**
```yaml
spec:
  containers:
    - name: app
      securityContext:
        readOnlyRootFilesystem: true
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
      volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /var/cache
        - name: run
          mountPath: /var/run
  volumes:
    - name: tmp
      emptyDir:
        sizeLimit: 100Mi
    - name: cache
      emptyDir:
        sizeLimit: 500Mi
    - name: run
      emptyDir:
        sizeLimit: 10Mi
```

**Key rule:** Every writable path needs its own emptyDir volume. Missing one = app crashes with "Read-only file system" error.

**Verify:**
```bash
kubectl apply -f updated-deployment.yaml
# Pod should start without Kyverno deny
kubectl get pods -l app=<app-name> --watch
# Test that the app can write to /tmp
kubectl exec -it <pod> -- touch /tmp/test && echo "OK" || echo "FAIL"
# Test that root filesystem is read-only
kubectl exec -it <pod> -- touch /etc/test 2>&1 | grep "Read-only"
```"""
    ))

    examples.append(msg(
        "OPA Gatekeeper denied my deployment: 'container must define a seccomp profile'. How do I add seccomp without breaking the app?",
        """**Step 1: Check what the policy requires**
```bash
kubectl get constrainttemplate -o name | grep seccomp
kubectl get constraint -o yaml | grep -B5 -A15 seccomp
```

**Step 2: Check if the node supports seccomp**
```bash
kubectl get node -o jsonpath='{.items[0].status.nodeInfo.containerRuntimeVersion}'
# containerd 1.6+ supports RuntimeDefault seccomp
```

**Step 3: Start with RuntimeDefault (safe for most apps)**
```yaml
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault     # Blocks dangerous syscalls, allows normal app operation
  containers:
    - name: app
      securityContext:
        seccompProfile:
          type: RuntimeDefault
```

RuntimeDefault is safe for 99% of applications. It blocks `ptrace`, `mount`, `reboot`, `kexec_load` — syscalls normal apps never use.

**Step 4: If RuntimeDefault breaks the app (rare), profile it**
```bash
# Run the app with audit mode to see what syscalls it uses
# Create a logging seccomp profile:
cat > /tmp/audit-seccomp.json << 'EOF'
{
  "defaultAction": "SCMP_ACT_LOG",
  "architectures": ["SCMP_ARCH_X86_64"]
}
EOF

# Apply and check audit log
# Then create a custom profile with only the syscalls your app needs
```

**Verify:**
```bash
kubectl apply -f updated-deployment.yaml
# Should pass Gatekeeper validation
kubectl get pods -l app=<app-name> --watch
# Verify seccomp is active:
kubectl get pod <pod-name> -o jsonpath='{.spec.securityContext.seccompProfile}'
```"""
    ))

    return examples


def main():
    all_examples = []

    generators = [
        ("CrashLoopBackOff chains", generate_crashloopbackoff),
        ("OOMKilled diagnosis", generate_oomkilled),
        ("DNS resolution", generate_dns_resolution),
        ("ArgoCD operations", generate_argocd_scenarios),
        ("Connection issues", generate_connection_issues),
        ("Eviction scenarios", generate_eviction_scenarios),
        ("Complex admission denies", generate_admission_deny_complex),
    ]

    for name, gen_fn in generators:
        examples = gen_fn()
        all_examples.extend(examples)
        print(f"  {name}: {len(examples)} examples")

    random.shuffle(all_examples)

    from generate_utils import write_training_data
    write_training_data(
        examples=all_examples,
        output_file=OUTPUT_FILE,
        generator="generate_diagnostic_chains.py",
        domain="CKA",
    )


if __name__ == "__main__":
    main()
