#!/usr/bin/env python3
"""
generate_tool_integration.py — Training data for k8sgpt/kubectl-ai integration.

Katie needs to respond in the format these tools expect:
- k8sgpt: explanation + fix for a cluster analysis result
- kubectl-ai: natural language → exact kubectl commands

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""

import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "tool_integration.jsonl"

SYSTEM_PROMPT_K8SGPT = (
    "You are Katie, a Kubernetes expert analyzing cluster issues found by k8sgpt. "
    "Explain the problem clearly, then provide the exact fix. "
    "Be concise — k8sgpt users want diagnosis + fix, not lectures."
)

SYSTEM_PROMPT_KUBECTL_AI = (
    "You are Katie, a Kubernetes expert. Convert the user's natural language request "
    "into exact kubectl commands. Show only the commands needed — no explanation unless "
    "the user asks why. If multiple steps are needed, number them."
)


def msg_k8sgpt(analysis, response):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT_K8SGPT},
        {"role": "user", "content": analysis},
        {"role": "assistant", "content": response},
    ]}


def msg_kubectl(question, response):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT_KUBECTL_AI},
        {"role": "user", "content": question},
        {"role": "assistant", "content": response},
    ]}


def generate_k8sgpt_responses():
    """Responses to k8sgpt analyze output."""
    examples = []

    # Pod issues
    examples.append(msg_k8sgpt(
        "k8sgpt analysis: Pod payments/checkout-7d9f8c has CrashLoopBackOff. Container exit code 137 (OOMKilled). Memory limit: 128Mi.",
        """**Problem:** Container is being OOM-killed — it needs more than 128Mi of memory.

**Fix:**
```bash
kubectl patch deployment checkout -n payments --type=json \\
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"512Mi"},
       {"op":"replace","path":"/spec/template/spec/containers/0/resources/requests/memory","value":"256Mi"}]'
```

**Verify:** `kubectl get pod -n payments -l app=checkout --watch` — should stabilize within 60s."""
    ))

    examples.append(msg_k8sgpt(
        "k8sgpt analysis: Pod monitoring/grafana-5c8d7e has ImagePullBackOff. Image: grafana/grafana:10.2.4. Error: unauthorized.",
        """**Problem:** Can't pull image — registry requires authentication.

**Fix:**
```bash
# Create pull secret (if you have registry credentials)
kubectl create secret docker-registry grafana-pull-secret \\
  -n monitoring \\
  --docker-server=docker.io \\
  --docker-username=YOUR_USER \\
  --docker-password=YOUR_TOKEN

# Add to deployment
kubectl patch deployment grafana -n monitoring --type=json \\
  -p '[{"op":"add","path":"/spec/template/spec/imagePullSecrets","value":[{"name":"grafana-pull-secret"}]}]'
```

If the image is public and this is a rate limit issue:
```bash
# Check: docker.io rate limits anonymous pulls to 100/6hr
# Fix: add any Docker Hub credentials to avoid anonymous rate limit
```"""
    ))

    examples.append(msg_k8sgpt(
        "k8sgpt analysis: Service prod/api-gateway has no endpoints. Selector: app=api-gateway. 3 pods exist with label app=api.",
        """**Problem:** Service selector `app=api-gateway` doesn't match pod label `app=api`.

**Fix:**
```bash
kubectl patch svc api-gateway -n prod --type=json \\
  -p '[{"op":"replace","path":"/spec/selector/app","value":"api"}]'
```

Or fix the pod labels to match the service:
```bash
kubectl patch deployment api -n prod --type=json \\
  -p '[{"op":"replace","path":"/spec/template/metadata/labels/app","value":"api-gateway"}]'
```

**Verify:** `kubectl get endpoints api-gateway -n prod` — should show pod IPs."""
    ))

    examples.append(msg_k8sgpt(
        "k8sgpt analysis: PersistentVolumeClaim data-postgres-0 in namespace database is Pending. No matching PV found. StorageClass: gp3.",
        """**Problem:** PVC can't bind — either StorageClass `gp3` doesn't exist or there's an AZ mismatch.

**Diagnose:**
```bash
kubectl get sc gp3
kubectl describe pvc data-postgres-0 -n database | grep -A5 Events
```

**If StorageClass doesn't exist:**
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

**If AZ mismatch** (StatefulSet pinned to node in different AZ than EBS volume):
```bash
# Check node AZ
kubectl get node -l topology.kubernetes.io/zone
# Delete the PVC and let it rebind in the correct AZ
kubectl delete pvc data-postgres-0 -n database
# Pod will recreate it in the right AZ
```"""
    ))

    # Node issues
    examples.append(msg_k8sgpt(
        "k8sgpt analysis: Node ip-10-0-2-15 has condition DiskPressure=True. Available: 1.2Gi of 50Gi.",
        """**Problem:** Node disk is 97.6% full. Kubelet will start evicting pods.

**Immediate:**
```bash
# Check what's consuming disk
kubectl debug node/ip-10-0-2-15 -it --image=busybox -- sh -c 'du -sh /host/var/lib/containerd/* | sort -rh | head -10'

# Clean unused container images
kubectl debug node/ip-10-0-2-15 -it --image=busybox -- sh -c 'crictl rmi --prune'

# Check for large log files
kubectl debug node/ip-10-0-2-15 -it --image=busybox -- sh -c 'find /host/var/log -size +100M -exec ls -lh {} \\;'
```

**Long-term fix:** Increase node disk or add Karpenter NodePool with larger root volume:
```yaml
spec:
  template:
    spec:
      blockDeviceMappings:
        - deviceName: /dev/xvda
          ebs:
            volumeSize: 100Gi    # Was 50Gi
            volumeType: gp3
```"""
    ))

    return examples


def generate_kubectl_ai_responses():
    """Natural language → kubectl commands."""
    examples = []

    examples.append(msg_kubectl(
        "show me all pods that are not running in the payments namespace",
        """```bash
kubectl get pods -n payments --field-selector=status.phase!=Running
```"""
    ))

    examples.append(msg_kubectl(
        "why is my pod crashing in the auth namespace",
        """```bash
# 1. Find the crashing pod
kubectl get pods -n auth | grep -E 'CrashLoop|Error'

# 2. Check the logs
kubectl logs -n auth <pod-name> --previous

# 3. Check events
kubectl describe pod -n auth <pod-name> | tail -20
```"""
    ))

    examples.append(msg_kubectl(
        "scale the web deployment to 5 replicas in prod",
        """```bash
kubectl scale deployment web -n prod --replicas=5
```"""
    ))

    examples.append(msg_kubectl(
        "show me which pods are using the most memory across all namespaces",
        """```bash
kubectl top pods --all-namespaces --sort-by=memory | head -20
```"""
    ))

    examples.append(msg_kubectl(
        "restart all pods in the api deployment without downtime",
        """```bash
kubectl rollout restart deployment/api
kubectl rollout status deployment/api --timeout=120s
```"""
    ))

    examples.append(msg_kubectl(
        "find all pods running as root",
        """```bash
kubectl get pods --all-namespaces -o json | python3 -c "
import json,sys
for pod in json.load(sys.stdin)['items']:
  for c in pod['spec']['containers']:
    sc = c.get('securityContext',{})
    psc = pod['spec'].get('securityContext',{})
    if not sc.get('runAsNonRoot') and not psc.get('runAsNonRoot'):
      print(f\"{pod['metadata']['namespace']}/{pod['metadata']['name']}: {c['name']}\")
"
```"""
    ))

    examples.append(msg_kubectl(
        "add resource limits to all containers in the worker deployment",
        """```bash
kubectl patch deployment worker --type=json -p '[
  {"op":"add","path":"/spec/template/spec/containers/0/resources","value":{
    "requests":{"cpu":"100m","memory":"128Mi"},
    "limits":{"cpu":"500m","memory":"256Mi"}
  }}
]'
```"""
    ))

    examples.append(msg_kubectl(
        "check if argocd is managing the payments namespace",
        """```bash
kubectl get deployments -n payments -o jsonpath='{range .items[*]}{.metadata.name}: {.metadata.labels.app\.kubernetes\.io/instance}{"\n"}{end}'
# If it returns an app name, ArgoCD manages it — fix in git, not kubectl
```"""
    ))

    examples.append(msg_kubectl(
        "create a network policy that allows the api pod to talk to the database pod on port 5432 and nothing else",
        """```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Egress
  egress:
    # Allow database access
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
    # MUST include DNS or nothing resolves
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
```bash
kubectl apply -f api-to-database-netpol.yaml
```"""
    ))

    examples.append(msg_kubectl(
        "show me all secrets that haven't been rotated in 90 days",
        """```bash
kubectl get secrets --all-namespaces -o json | python3 -c "
import json,sys
from datetime import datetime, timezone, timedelta
cutoff = datetime.now(timezone.utc) - timedelta(days=90)
for s in json.load(sys.stdin)['items']:
  if s['type'] == 'kubernetes.io/service-account-token': continue
  created = datetime.fromisoformat(s['metadata']['creationTimestamp'].replace('Z','+00:00'))
  if created < cutoff:
    age = (datetime.now(timezone.utc) - created).days
    print(f\"{s['metadata']['namespace']}/{s['metadata']['name']}: {age} days old\")
"
```"""
    ))

    return examples


def main():
    all_examples = []

    generators = [
        ("k8sgpt analysis responses", generate_k8sgpt_responses),
        ("kubectl-ai command generation", generate_kubectl_ai_responses),
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
        generator="generate_tool_integration.py",
        domain="CKA",
    )


if __name__ == "__main__":
    main()
