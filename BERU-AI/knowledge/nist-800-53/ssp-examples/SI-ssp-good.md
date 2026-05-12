# System Security Plan — System and Information Integrity (SI) Family

## Links-Matrix Platform — GOOD VERSION

> **Reviewer note:** This SSP would pass a readiness review with 4-5 clarification items.
> Trivy CI, Amazon Inspector, Falco, GuardDuty, and OpenSearch are named with specific
> configurations. SLAs match FedRAMP thresholds and are tracked in Jira. Falco alerts
> route to PagerDuty with an on-call rotation. readOnlyRootFilesystem is enforced on
> most production containers. Gaps: no image signing or Cosign verification at admission,
> Falco uses mostly default rules without environment-specific tuning, running containers
> are not automatically restarted after base image patches (gap in remediation closure
> verification), and east-west traffic anomaly detection is not implemented — lateral
> movement inside the cluster generates no dedicated alert.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Final Draft — Pending ISSO Signature

---

## SI-2 — Flaw Remediation

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

Flaw remediation on the Links-Matrix Platform is managed through a defined pipeline
from discovery to verified closure. SI-2 is the remediation arm of RA-5 scanning —
findings from Trivy, Amazon Inspector, kube-bench, and Prowler flow into Jira
(`SEC-VULN` project) and are tracked to closure.

**Remediation SLAs:**

| Severity | FedRAMP Maximum | Links-Matrix SLA | Escalation |
| -------- | --------------- | ---------------- | ---------- |
| Critical | 30 days | 15 days | Auto-escalates to ISSO at 10 days if unassigned |
| High | 30 days | 30 days | Reviewed at weekly vuln triage |
| Medium | 90 days | 90 days | Reviewed at monthly vuln triage |
| Low | 180 days | 180 days or risk-accept | Quarterly review |

**Container image patching process:**
When a vulnerability is identified in a base image, the remediation process is:
1. Update base image tag in Dockerfile (or pin to patched digest)
2. CI pipeline builds and scans the new image (Trivy — must pass zero Critical/High)
3. CI pushes new image digest to ECR
4. ArgoCD detects image update and syncs the deployment (rolling update)
5. Jira ticket closed with link to the ArgoCD sync event and new image digest

*(Note: the link between ticket closure and confirmed pod restart is manual — the
engineer closes the ticket after confirming the deployment rolled, but there is no
automated verification that all pods in production are running the patched digest.
A pod on an old ReplicaSet that failed to roll would not be automatically detected.)*

**Dependency updates:**
Dependabot is configured on the `platform-gitops` and `lm-app` repositories. It
auto-creates PRs for dependency updates with CVE context. PRs are reviewed weekly
by the DevSecOps team.

**Responsible Role:** DevSecOps (Trivy CI, Dependabot, ticket triage), Cloud Security Engineer (Inspector findings, weekly triage), ISSO (SLA oversight, escalation)

**Parameters:**
- Critical SLA: 15 days (FedRAMP: 30 days)
- High SLA: 30 days (FedRAMP: 30 days)
- Weekly vuln triage: DevSecOps + Cloud Security Engineer
- Finding tracker: Jira `SEC-VULN` project

**Evidence / Artifacts:**
- Jira `SEC-VULN` project — finding age and status (last 90 days)
- Trivy CI workflow (`platform-gitops/.github/workflows/pr-checks.yaml`)
- Amazon Inspector findings (AWS Security Hub)
- Dependabot configuration (`.github/dependabot.yml`)
- ArgoCD deployment history (ArgoCD UI — sync events linked from Jira tickets)

**Enhancements Addressed:**
- **SI-2(2):** Amazon Inspector provides continuous automated scanning. Jira `SEC-VULN`
  tracks finding status with discovery date visible — SLA compliance is reportable on demand.
- **SI-2(3):** Discovery-to-remediation timestamps are captured: Inspector/Trivy sets the
  discovery timestamp; Jira ticket closure records the remediation date. Weekly triage
  meeting reviews findings approaching SLA. *(Gap: automated SLA breach alerting is not
  implemented — the ISSO checks manually at weekly triage rather than being notified when
  a finding crosses its SLA threshold.)*

---

## SI-3 — Malicious Code Protection

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

Malicious code protection on the Links-Matrix Platform operates at three layers:
supply chain (CI image scanning), admission (registry allowlist enforcement), and
runtime (Falco behavioral detection and GuardDuty threat intelligence).

**Supply chain (CI scanning):**
Trivy runs on every PR to `platform-gitops` and `lm-app`. A Critical or High CVE
finding blocks merge. Images are scanned before being pushed to ECR.

**Admission control:**
Kyverno ClusterPolicy `allow-only-ecr-images` (Enforce mode) blocks any pod that
references an image not from `123456789012.dkr.ecr.us-east-1.amazonaws.com`. This
prevents workloads from pulling images from Docker Hub, ghcr.io, or other registries
that are not under the organization's control.

**Runtime (Falco):**
Falco is deployed as a DaemonSet on all EKS worker nodes (`platform-gitops/falco/`).
Falco monitors system calls and alerts on:
- Shell spawned in a container (`k8s_audit.yaml` rule: `Terminal shell in container`)
- Privilege escalation attempt (`Privilege Escalation Using Sudo`)
- Sensitive file read (`Read sensitive file below /etc`)
- Network connection from unexpected container

Falco alerts route to PagerDuty (`lm-security-falco` service) and to OpenSearch
(index: `falco-alerts`). P1-equivalent Falco alerts page the on-call SOC engineer.

**GuardDuty:**
Amazon GuardDuty is enabled in the `lm-prod` account with EKS Protection (K8s audit
log analysis) and Malware Protection (on-demand EBS volume scanning). GuardDuty findings
feed into Security Hub and high/critical findings create Jira `SEC-IR` tickets.

**Responsible Role:** DevSecOps (Trivy CI, Falco deployment), Cloud Security Engineer (GuardDuty, Kyverno registry policy), Platform Engineer (Falco DaemonSet, node access)

**Parameters:**
- CI scan threshold: Blocks merge on Critical or High finding
- Registry allowlist: ECR only (`allow-only-ecr-images`, Enforce mode)
- Runtime detection: Falco DaemonSet on all nodes
- GuardDuty: Enabled with EKS Protection and Malware Protection

**Evidence / Artifacts:**
- Kyverno `allow-only-ecr-images` policy (`platform-gitops/kyverno-policies/`)
- Falco DaemonSet manifest (`platform-gitops/falco/`)
- Falco alert history (OpenSearch index: `falco-alerts`, last 30 days)
- GuardDuty finding list (Security Hub — filter: ProductName = GuardDuty)

**Enhancements Addressed:**
- **SI-3(1):** Falco and GuardDuty are centrally deployed and managed — not per-node
  individual configuration. Falco rule updates are deployed via ArgoCD from `platform-gitops`.
- **SI-3(2):** Falco rule updates are deployed via ArgoCD on merge to `platform-gitops`.
  GuardDuty threat intelligence is automatically updated by AWS. ECR Enhanced Scanning
  updates CVE signatures continuously.
- **SI-3(7):** Falco behavioral detection catches process-level anomalies (shell in
  container, privilege escalation) without requiring malware signatures. *(Gap: Falco
  uses mostly default rule sets — environment-specific tuning for Links-Matrix workload
  profiles has not been done. Default rules generate false positives on normal workload
  behavior, creating alert fatigue risk.)*

---

## SI-4 — System Monitoring

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

System monitoring on the Links-Matrix Platform combines cloud-layer threat detection
(GuardDuty), runtime behavioral detection (Falco), Kubernetes control plane audit
logging, and metrics-based alerting (Prometheus/Alertmanager).

**Monitoring stack:**

| Tool | Coverage | Alert Destination | Cadence |
| ---- | -------- | ----------------- | ------- |
| Amazon GuardDuty | CloudTrail, VPC Flow Logs, DNS, EKS audit | Security Hub → Jira `SEC-IR` | Continuous |
| Falco | Pod/node syscall behavior, K8s audit events | PagerDuty `lm-security-falco` + OpenSearch | Real-time |
| CloudTrail | AWS API events (all services, all regions) | OpenSearch (index: `cloudtrail-*`) | Real-time |
| Prometheus/Alertmanager | Metrics anomalies (pod crash loops, resource spikes) | PagerDuty `lm-platform-alerts` | Real-time |
| OpenSearch Dashboards | Log aggregation and query (Fluent Bit → OpenSearch) | Human review (SOC daily review) | Batch |

**Alert routing:**
PagerDuty `lm-security-falco` escalation policy: P1 alerts page the on-call SOC
engineer within 5 minutes. If unacknowledged, escalates to ISSO within 15 minutes.
On-call rotation covers all hours (24/7 — two-person rotation, weekly shift).

**Kubernetes control plane monitoring:**
EKS control plane logging is enabled for: API server, audit, authenticator, controller
manager, scheduler. Logs ship to CloudWatch (`/aws/eks/lm-prod-cluster/cluster`) and
are forwarded to OpenSearch via Fluent Bit.

**Responsible Role:** Cloud Security Engineer (GuardDuty, Security Hub, CloudTrail), DevSecOps (Falco, Prometheus/Alertmanager, OpenSearch), SOC (on-call, alert triage)

**Parameters:**
- GuardDuty: Enabled with EKS Protection (control plane + data plane logs)
- On-call rotation: 24/7, two-person, weekly shift
- P1 acknowledgment SLA: 5 minutes
- P1 ISSO escalation: 15 minutes if unacknowledged

**Evidence / Artifacts:**
- GuardDuty findings (Security Hub)
- Falco alert history (OpenSearch: `falco-alerts`)
- CloudTrail configuration (`infra-iac/cloudtrail/`)
- PagerDuty `lm-security-falco` escalation policy and on-call schedule
- EKS control plane logging configuration (`infra-iac/eks/main.tf`)

**Enhancements Addressed:**
- **SI-4(2):** GuardDuty and Falco provide real-time automated threat detection. PagerDuty
  ensures alerts reach humans within minutes, not hours.
- **SI-4(4):** GuardDuty monitors inbound (anomalous API calls) and outbound (DNS-based
  C2 detection via GuardDuty DNS Protection) traffic. VPC Flow Logs capture network-layer
  boundary events. *(Gap: east-west traffic between pods inside the cluster is not
  monitored for anomalies — lateral movement between services generates no dedicated alert.)*
- **SI-4(5):** PagerDuty escalation policy routes P1 Falco alerts to on-call SOC within
  5 minutes, escalating to ISSO at 15 minutes. Named personnel, not a distribution list.
- **SI-4(11):** *(Not fully implemented.)* VPC Flow Logs and GuardDuty cover north-south
  traffic. Interior east-west pod traffic anomaly detection is not implemented. Compensating
  control: NetworkPolicy restricts which pods can communicate at layer 4.

---

## SI-7 — Software, Firmware, and Information Integrity

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

**readOnlyRootFilesystem:**
Kyverno ClusterPolicy `require-readonly-rootfs` (Warn mode) flags any pod that does
not set `securityContext.readOnlyRootFilesystem: true`. Production workloads in
`lm-production` namespace enforce this context — the policy is in Enforce mode for
that namespace only. *(Note: `kube-system` and `cert-manager` namespaces are excluded
from the Enforce policy — some system components require writable filesystems.)*

**Image digest pinning:**
All production ArgoCD Application manifests reference images by digest rather than
mutable tag (e.g., `lm-api:sha256:abc123...`). Renovate automatically updates digests
on new image pushes to ECR. Tags (`:latest`, `:main`) are prohibited in production
manifests by Kyverno policy `require-image-digest` (Enforce mode for `lm-production`).

**Falco filesystem integrity:**
Falco rule `detect_write_to_readonly_fs` fires when any write syscall targets a path
not in the pod's defined `emptyDir` or `PVC` mounts. Alerts route to PagerDuty
`lm-security-falco`.

**Image admission:**
Kyverno policy `allow-only-ecr-images` (described in SI-3) ensures images come from
the organization's controlled registry. *(Gap: no cryptographic signature verification
at admission — an image pushed to ECR by a compromised CI pipeline would not be
rejected by admission control if it came from the correct registry.)*

**Responsible Role:** Platform Engineer (readOnlyRootFilesystem enforcement, Kyverno policies), DevSecOps (Renovate digest updates, Falco FIM rule)

**Parameters:**
- readOnlyRootFilesystem: Enforce in `lm-production`; Warn elsewhere
- Image digest pinning: Enforced in `lm-production` (Kyverno, Renovate)
- Falco FIM rule: `detect_write_to_readonly_fs` — PagerDuty alert

**Evidence / Artifacts:**
- Kyverno `require-readonly-rootfs` policy (`platform-gitops/kyverno-policies/`)
- Kyverno `require-image-digest` policy (`platform-gitops/kyverno-policies/`)
- Falco FIM rule (`platform-gitops/falco/rules/fim.yaml`)
- Production ArgoCD Application manifests with digest references

---

## What Makes This GOOD (But Not Great) — Examiner's Notes

| Control | Strengths | Gaps |
| ------- | --------- | ---- |
| SI-2 | SLAs tighter than FedRAMP minimum for Critical, Jira tracking with timestamps, container patching process documented | No automated verification that all pods are running the patched digest post-rollout; SLA breach alerting is manual (weekly triage review) |
| SI-3 | Falco DaemonSet on all nodes, ECR-only registry policy in Enforce mode, GuardDuty with EKS and Malware Protection | Falco default rules only — not tuned to workload profiles; false positive rate unknown; no automated response to Falco detections (alert only, no pod kill) |
| SI-4 | Named tools with specific coverage, 24/7 on-call via PagerDuty, EKS control plane logging enabled | East-west traffic anomaly detection not implemented — lateral movement between services generates no alert |
| SI-7 | Digest pinning enforced in production, readOnlyRootFilesystem enforced for production namespace, Falco FIM rule | No image signing or admission-time signature verification — compromised CI pipeline could push a malicious image to ECR and it would be admitted |
