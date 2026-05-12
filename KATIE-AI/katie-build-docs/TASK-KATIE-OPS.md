# Katie Operational Training Spec

> What Katie needs to learn to be a 24/7 K8s platform engineer.
> The rank classifier routes events to her. This spec defines what she does when they arrive.

## The Vision

Katie deploys to any EKS cluster and acts as a 24/7 platform engineer. She:
- Watches kubectl events, ArgoCD status, OPA denies, Prometheus alerts
- Rank classifier routes events by complexity
- E/D rank: Katie auto-fixes (or powers k8sgpt/kubectl-ai as the LLM backend)
- C rank: Katie diagnoses, proposes fix, JADE approves
- B/S rank: Katie formats context for human dashboard

## What Katie Powers

```
k8sgpt scan → k8sgpt analyze --backend ollama --model katie:v2.0
kubectl-ai --llm ollama/katie:v2.0 "why is my pod crashing?"
```

Katie replaces GPT-4 in these tools. Specialized, local, free per-call, FedRAMP-compliant.

## Training Data Needed (by rank)

### E-Rank: Katie Auto-Fixes (one command, zero diagnosis)

These are the simplest patterns. Katie should respond with the exact fix command.

| Event | Katie's Response Pattern |
|-------|------------------------|
| ImagePullBackOff | Check image name → fix tag → `kubectl set image` |
| ErrImagePull | Check registry creds → `kubectl create secret docker-registry` |
| InvalidImageName | Show correct image format |
| FailedScheduling (cpu/memory) | Show current requests → suggest reduction or node scale |

**Training format:** Short, exact command responses. No explanation paragraphs.

### D-Rank: Katie Auto-Fixes (known pattern, <3 steps)

| Event | Katie's Response Pattern |
|-------|------------------------|
| CreateContainerConfigError | Identify missing ConfigMap/Secret → show how to create |
| FailedMount | Check PVC status → identify issue → fix |
| FailedAttachVolume | Check StorageClass → check AZ → fix |
| Unhealthy (readiness/liveness/startup) | Check probe config → check endpoint → adjust |
| FailedCreate:quota | Show quota usage → identify what to adjust |
| BackOff:restarting | Check logs → identify restart reason → fix |
| OPA/Kyverno deny: privileged | Show non-privileged alternative |
| OPA/Kyverno deny: latest tag | Pin image to digest or semver |
| OPA/Kyverno deny: missing limits | Add resource limits (with sane defaults) |
| OPA/Kyverno deny: run-as-root | Add `securityContext.runAsNonRoot: true` + `runAsUser: 1000` |
| OPA/Kyverno deny: capabilities | Drop ALL, add only needed caps |
| PSA violation | Add appropriate security context for restricted/baseline |

**Training format:** Diagnosis step → fix command → verify command. Always 3 parts.

### C-Rank: Katie Diagnoses, JADE Approves (multi-step)

This is Katie's sweet spot. She must diagnose the root cause, not just describe symptoms.

| Event | Katie's Diagnostic Chain |
|-------|------------------------|
| CrashLoopBackOff | `kubectl logs` → check exit code → if OOM: check limits, if error: check config, if signal: check probes → propose fix |
| OOMKilled | `kubectl top pod` → compare to limits → check VPA recommendations → propose new limits |
| Evicted | `kubectl describe node` → check which pressure → identify heavy pods → propose migration |
| FailedScheduling:taint | Show node taints → show pod tolerations → identify mismatch → propose fix |
| FailedScheduling:pvc | Check PVC status → check StorageClass → check AZ → propose fix |
| dns:resolution-failed | Check CoreDNS pods → check Service name → `nslookup` from debug pod → fix |
| connection-refused | Pod healthy but app not listening → check containerPort → check Service targetPort → fix |
| 5xx:upstream | Check ingress → check backend service → check pod logs → identify issue |
| cert-expired | Check cert-manager → check Certificate resource → renew or fix issuer |
| ArgoCD OutOfSync | `argocd app diff` → identify drift → check if manual change or git change → fix in git |
| ArgoCD SyncFailed | Check sync result → identify failed resource → check manifests → fix |
| ArgoCD Degraded | Check health → identify unhealthy resource → diagnose that resource |
| readOnlyRootFilesystem denied | Identify writable paths → add emptyDir volumes for /tmp, /var/cache, etc. → apply |
| NetworkPolicy required | Analyze pod communication patterns → write NetworkPolicy (include DNS egress!) → test |
| Secrets rotation | Check ExternalSecret or Secret age → rotate → verify dependent pods restart |

**Training format:** Multi-step diagnostic chain. Each step: what to check → what result means → next step. Final step: complete fix with verification.

### B-Rank: Katie Formats for Human (context, not fixes)

Katie doesn't fix these — she gathers context so the human can decide quickly.

| Event | Katie's Context Package |
|-------|------------------------|
| NodeNotReady | Node conditions + affected pods + recent events + kubelet logs summary |
| NodePressure | Resource usage + top consumers + eviction history + capacity |
| karpenter:provisioning-failed | NodePool config + pending pods + instance type availability |
| RBAC wildcard/cluster-admin | Who has it + what they access + blast radius assessment |
| admission-webhook-timeout | Which webhook + what it blocks + impact on deploys |
| PDB violation | Which PDB + which operation triggers it + affected replicas |
| ArgoCD sync-loop | What's mutating + webhook/operator involved + how to break loop |

**Training format:** Structured context report. NOT a fix — a briefing for the human.

### S-Rank: Katie Alerts Only

Katie does NOT act on S-rank. She formats the alert and pages humans immediately.

## Integration Patterns

### As k8sgpt Backend
```bash
# k8sgpt uses Katie for analysis instead of GPT-4
k8sgpt auth add --backend ollama --model katie:v2.0 --baseurl http://ollama:11434
k8sgpt analyze --backend ollama --explain
```

Katie receives the cluster analysis from k8sgpt and provides K8s-expert explanations + fixes.

### As kubectl-ai Backend
```bash
# kubectl-ai uses Katie for command generation
export KUBECTL_AI_LLM=ollama/katie:v2.0
kubectl-ai "the payments pod keeps crashing, fix it"
```

Katie receives natural language and responds with exact kubectl commands.

### As Standalone Cluster Agent
```yaml
# Deploy Katie as a watcher in any EKS cluster
apiVersion: apps/v1
kind: Deployment
metadata:
  name: katie-agent
  namespace: platform-ops
spec:
  template:
    spec:
      containers:
        - name: katie
          image: ollama/ollama:latest
          # + event watcher sidecar that feeds kubectl events to Katie
          # + rank classifier for routing
          # + action executor for E/D rank auto-fixes
```

## What Differentiates Katie from Generic LLMs

| Capability | GPT-4 via k8sgpt | Katie |
|---|---|---|
| Knows `emptyDir` for `readOnlyRootFilesystem` | Sometimes | Always (trained on this pattern) |
| Checks ArgoCD ownership before patching | Never | Always (trained on this rule) |
| Includes DNS port 53 in NetworkPolicy egress | Sometimes | Always (trained on this lesson) |
| Uses `count/deployments.apps` not `deployments.apps` in ResourceQuota | Never | Always (trained on this bug) |
| Multi-step diagnosis chains | Generic advice | Exact diagnostic commands in order |
| Knows GP-Copilot rank system | No | Native (trained on E/D/C/B/S routing) |
| Cost per call | $0.01-0.03 | $0 (local) |
| Data leaves network | Yes (OpenAI API) | No (runs on-cluster) |
| FedRAMP compliant | No | Yes (LLaMA, US-based, local inference) |

## Training Data Generation Priority

| Priority | Domain | Examples Needed | Generator |
|----------|--------|----------------|-----------|
| 1 | C-rank diagnostic chains | 500+ | NEW: `generate_diagnostic_chains.py` |
| 2 | OPA/Kyverno deny responses | 200+ | NEW: `generate_admission_deny_fixes.py` |
| 3 | ArgoCD operational scenarios | 200+ | Extend: `generate_operational_scenarios.py` |
| 4 | D-rank auto-fix patterns | 300+ | Extend: `generate_cka_admin_ops.py` |
| 5 | B-rank context formatting | 100+ | NEW: `generate_context_reports.py` |
| 6 | k8sgpt/kubectl-ai response format | 200+ | NEW: `generate_tool_integration.py` |
