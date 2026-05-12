#!/usr/bin/env python3
"""
generate_admission_deny_fixes.py — D-rank admission controller deny responses.

When OPA/Gatekeeper/Kyverno/PSA denies a deployment, Katie tells you exactly
what to change in the manifest to make it pass. These are D-rank because the
fix is always "change the manifest" — no diagnosis needed, just compliance.

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""

import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "admission_deny_fixes.jsonl"

SYSTEM_PROMPT = (
    "You are Katie, a CKS-certified Kubernetes security engineer. "
    "When an admission controller denies a deployment, you provide the exact YAML fix "
    "to make the manifest compliant. Always show the before (denied) and after (compliant) YAML."
)

def msg(user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]}


def generate_privileged_denies():
    examples = []

    examples.append(msg(
        "Kyverno denied: 'Validation rule disallow-privileged failed. Container must not be privileged.'",
        """**Denied because:** `securityContext.privileged: true` is set on the container.

**Before (denied):**
```yaml
containers:
  - name: app
    image: myapp:v1
    securityContext:
      privileged: true
```

**After (compliant):**
```yaml
containers:
  - name: app
    image: myapp:v1
    securityContext:
      privileged: false            # Or remove entirely (defaults to false)
      allowPrivilegeEscalation: false
      runAsNonRoot: true
      capabilities:
        drop: ["ALL"]
```

If the app needs specific capabilities (e.g., NET_BIND_SERVICE for port <1024):
```yaml
      capabilities:
        drop: ["ALL"]
        add: ["NET_BIND_SERVICE"]  # Only add what's actually needed
```

**Apply:** `kubectl apply -f deployment.yaml`"""
    ))

    return examples


def generate_latest_tag_denies():
    examples = []

    examples.append(msg(
        "Gatekeeper denied: 'Container image must not use :latest tag. Use a specific version or SHA digest.'",
        """**Denied because:** Image uses `:latest` tag which is mutable and non-reproducible.

**Before (denied):**
```yaml
containers:
  - name: api
    image: myregistry.io/api:latest
```

**After (compliant) — Option A: Semver tag:**
```yaml
containers:
  - name: api
    image: myregistry.io/api:v2.1.3
```

**After (compliant) — Option B: SHA digest (strongest):**
```yaml
containers:
  - name: api
    image: myregistry.io/api@sha256:a1b2c3d4e5f6...
```

**Get the digest for your current image:**
```bash
# From the registry
docker inspect --format='{{index .RepoDigests 0}}' myregistry.io/api:latest
# Or from crane
crane digest myregistry.io/api:latest
```

**Apply:** `kubectl apply -f deployment.yaml`"""
    ))

    return examples


def generate_resource_limit_denies():
    examples = []

    examples.append(msg(
        "Kyverno denied: 'Validation rule require-resource-limits failed. All containers must have CPU and memory limits.'",
        """**Denied because:** Container is missing `resources.limits` for CPU and/or memory.

**Before (denied):**
```yaml
containers:
  - name: worker
    image: worker:v1.2
    # No resources section at all
```

**After (compliant):**
```yaml
containers:
  - name: worker
    image: worker:v1.2
    resources:
      requests:
        cpu: "100m"          # What the scheduler reserves
        memory: "128Mi"
      limits:
        cpu: "500m"          # Max burst
        memory: "256Mi"      # Hard ceiling (OOMKilled if exceeded)
```

**How to pick values:**
```bash
# Check actual usage if the pod ran before
kubectl top pod -l app=worker --containers
# Requests = P50 usage, Limits = P99 usage with 50% headroom
```

**Common defaults by workload type:**
| Type | CPU req/limit | Memory req/limit |
|------|--------------|-----------------|
| API server | 100m/500m | 128Mi/512Mi |
| Worker | 250m/1000m | 256Mi/1Gi |
| Cache (Redis) | 100m/250m | 128Mi/256Mi |
| Database | 500m/2000m | 512Mi/2Gi |

**Apply:** `kubectl apply -f deployment.yaml`"""
    ))

    return examples


def generate_nonroot_denies():
    examples = []

    examples.append(msg(
        "PSA violation: 'pods \"api-5f7d8c\" is forbidden: violates PodSecurity \"restricted:latest\": runAsNonRoot must be true'",
        """**Denied because:** Pod Security Admission (PSA) at `restricted` level requires `runAsNonRoot: true` and a non-root `runAsUser`.

**Before (denied):**
```yaml
spec:
  containers:
    - name: api
      image: api:v3
      # No securityContext — runs as root by default
```

**After (compliant):**
```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000              # Any non-zero UID
    runAsGroup: 1000
    fsGroup: 1000
  containers:
    - name: api
      image: api:v3
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
      volumeMounts:
        - name: tmp
          mountPath: /tmp
  volumes:
    - name: tmp
      emptyDir: {}
```

**Common gotcha:** If the Dockerfile uses `USER root` or doesn't specify a USER, the image runs as root even with `runAsNonRoot: true` — the pod will fail with `container has runAsNonRoot and image will run as root`. Fix: add `USER 1000` to Dockerfile or set `runAsUser: 1000` in the pod spec.

**Apply:** `kubectl apply -f deployment.yaml`"""
    ))

    return examples


def generate_host_namespace_denies():
    examples = []

    examples.append(msg(
        "Kyverno denied: 'Validation rule disallow-host-namespaces failed. Host PID and host network are not allowed.'",
        """**Denied because:** Pod uses `hostPID: true`, `hostNetwork: true`, or `hostIPC: true`.

**Before (denied):**
```yaml
spec:
  hostNetwork: true
  hostPID: true
  containers:
    - name: monitor
      image: monitor:v1
```

**After (compliant):**
```yaml
spec:
  hostNetwork: false   # Or remove entirely
  hostPID: false       # Or remove entirely
  containers:
    - name: monitor
      image: monitor:v1
      ports:
        - containerPort: 8080    # Use containerPort instead of hostNetwork
```

**If you need host access (monitoring agents like Falco, node-exporter):**
These are legitimate exceptions. Create a PolicyException:
```yaml
apiVersion: kyverno.io/v2beta1
kind: PolicyException
metadata:
  name: allow-falco-host-access
  namespace: falco-system
spec:
  exceptions:
    - policyName: disallow-host-namespaces
      ruleNames:
        - host-namespaces
  match:
    any:
      - resources:
          namespaces: ["falco-system"]
          names: ["falco-*"]
```

**Apply:** `kubectl apply -f deployment.yaml`"""
    ))

    return examples


def generate_capability_denies():
    examples = []

    examples.append(msg(
        "Gatekeeper denied: 'container has a disallowed capability: NET_RAW. Only NET_BIND_SERVICE is allowed.'",
        """**Denied because:** Container has capabilities that aren't on the allow list.

**Before (denied):**
```yaml
containers:
  - name: app
    securityContext:
      capabilities:
        add: ["NET_RAW", "SYS_ADMIN"]
```

**After (compliant):**
```yaml
containers:
  - name: app
    securityContext:
      capabilities:
        drop: ["ALL"]
        # Only add back what you actually need:
        # add: ["NET_BIND_SERVICE"]   # Only if binding to port < 1024
```

**Common capabilities and when you need them:**
| Capability | When needed | Alternative |
|-----------|------------|-------------|
| NET_BIND_SERVICE | Binding to port <1024 | Use port >1024 and Service targetPort mapping |
| NET_RAW | Ping/traceroute from container | Almost never needed in production |
| SYS_ADMIN | Mount filesystems | Never use — security risk |
| CHOWN | Change file ownership | Set correct ownership in Dockerfile |
| SETUID/SETGID | Switch users | Set runAsUser in pod spec instead |

**Rule of thumb:** Start with `drop: ["ALL"]` and add nothing. Only add back a capability if the app crashes without it and you understand why.

**Apply:** `kubectl apply -f deployment.yaml`"""
    ))

    return examples


def main():
    all_examples = []

    generators = [
        ("Privileged denies", generate_privileged_denies),
        ("Latest tag denies", generate_latest_tag_denies),
        ("Resource limit denies", generate_resource_limit_denies),
        ("Non-root denies", generate_nonroot_denies),
        ("Host namespace denies", generate_host_namespace_denies),
        ("Capability denies", generate_capability_denies),
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
        generator="generate_admission_deny_fixes.py",
        domain="CKS",
    )


if __name__ == "__main__":
    main()
