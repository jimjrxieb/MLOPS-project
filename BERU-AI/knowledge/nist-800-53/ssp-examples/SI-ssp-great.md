# System Security Plan — System and Information Integrity (SI) Family

## Links-Matrix Platform — GREAT VERSION

> **Reviewer note:** This SSP would pass a FedRAMP readiness review with zero major
> findings. SI-2 has automated post-patch rollout verification confirming every pod runs
> the patched digest within the SLA window. SI-3 has Falco rules tuned to each workload's
> expected syscall profile and a Falco response plugin that automatically terminates
> compromised pods — detection is integrated with response, not just alerting. SI-4 has
> a MITRE ATT&CK detection coverage table mapping 12 specific techniques to named tools,
> east-west anomaly detection via Falco NetworkActivity rules covering lateral movement,
> and quarterly false-positive reduction reviews. SI-7 closes the unsigned-image gap with
> Cosign signing at build and a Kyverno admission policy that blocks any unsigned image
> from running in production — SLSA Level 2 provenance attestations provide supply chain
> traceability from source commit to running pod.

---

**System Name:** Links-Matrix Platform
**System Owner:** Platform Engineering Lead
**ISSO:** Information System Security Officer
**Prepared By:** Security Team
**Date:** 2026-05-01
**Status:** Approved — Active Authorization

> **Control chain:** SI-2 remediates what RA-5 finds. SI-3 detects and blocks malicious
> code that SI-2 hasn't patched yet. SI-4 detects behavioral anomalies that neither
> scanning nor signatures catch. SI-7 verifies that what RA-5, SI-3, and SI-4 approved
> is actually what is running. Together these controls close the integrity loop from
> detection through remediation through runtime verification.

---

## SI-2 — Flaw Remediation

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Remediation SLAs

| Severity | FedRAMP Maximum | LM Organizational SLA | CISA KEV Override | Auto-Escalation |
| -------- | --------------- | --------------------- | ----------------- | --------------- |
| Critical | 30 days | 15 days | 48 hours | ISSO alert at 10 days |
| High | 30 days | 30 days | 48 hours | Team lead alert at 21 days |
| Medium | 90 days | 90 days | N/A | Team lead alert at 75 days |
| Low | 180 days | 180 days or risk-accept | N/A | Quarterly review |

A GitHub Actions workflow (`sla-breach-check.yaml`) runs daily, querying the Jira
`SEC-VULN` project for findings where `(today - discovery_date) > escalation_threshold`
and `status != Closed`. Matches create a PagerDuty event routed to the relevant owner.
This means SLA breach alerting is automated — the weekly triage meeting confirms
compliance rather than discovering breaches.

### Container Image Patching with Rollout Verification

When a vulnerability is identified in a base image or dependency, the remediation
pipeline is:

1. **Patch:** Base image digest updated in `platform-gitops/dockerfiles/` or dependency
   bumped in `lm-app/go.sum` / `requirements.txt`
2. **Scan gate:** CI pipeline runs Trivy against the patched image — must return zero
   Critical/High for the previously identified CVE-ID. CI fails if the CVE remains.
3. **Build and push:** Patched image pushed to ECR with new digest
4. **Deploy:** ArgoCD detects digest change, initiates rolling update
5. **Rollout verification (automated):** A GitHub Actions workflow (`patch-verify.yaml`)
   triggers on the ArgoCD sync event. It queries `kubectl get pods -A -o json` and
   verifies that every pod for the patched workload is running the new digest within
   2 hours of the sync event. If any pod is still running the old digest after 2 hours,
   a Jira `SEC-VULN` ticket is re-opened and the ISSO is alerted.
6. **Closure:** Ticket is auto-closed by `patch-verify.yaml` on successful rollout
   confirmation, with the verification timestamp and new digest recorded in the ticket.

This means ticket closure is evidence of remediation — not just a declaration of intent.

### SLA Compliance Metrics

| Quarter | Critical Opened | Critical Closed on Time | Critical Overdue | Avg Days to Remediate (Critical) |
| ------- | --------------- | ----------------------- | ---------------- | -------------------------------- |
| 2025-Q2 | 6 | 6 | 0 | 11 days |
| 2025-Q3 | 3 | 3 | 0 | 8 days |
| 2025-Q4 | 2 | 2 | 0 | 6 days |
| 2026-Q1 | 1 | 1 | 0 | 4 days |

Zero critical findings exceeded the 15-day SLA in the trailing 12 months. Average
time to remediate is decreasing — evidence of process maturity.

### Dependency Update Automation

Renovate Bot (`platform-gitops/renovate.json`, `lm-app/renovate.json`) automatically
creates PRs for dependency updates with: CVE description (if applicable), CVSS score,
and link to the advisory. PRs are auto-assigned to the owning DevSecOps engineer.
Critical/High CVE dependency updates are auto-labeled `priority:critical` and appear
at the top of the weekly triage queue.

**Responsible Role:** DevSecOps (Trivy CI, Renovate, patch-verify workflow, sla-breach-check), Cloud Security Engineer (Inspector, CISA KEV integration, weekly triage), ISSO (SLA oversight, escalation authority)

**Parameters:**
- Critical SLA: 15 days; CISA KEV override: 48 hours
- Rollout verification: Automated within 2 hours of ArgoCD sync
- SLA breach detection: Daily automated check (`sla-breach-check.yaml`)
- Metrics reporting: Quarterly (ISSO to AO briefing)

**Evidence / Artifacts:**
- `sla-breach-check.yaml` workflow (`platform-gitops/.github/workflows/`)
- `patch-verify.yaml` workflow (`platform-gitops/.github/workflows/`)
- Jira `SEC-VULN` project — finding history with discovery and closure timestamps
- SLA compliance metrics (Confluence: LM-SECURITY / SI / SLA-Metrics-2026-Q1.pdf)
- Renovate configuration (`platform-gitops/renovate.json`)

**Enhancements Addressed:**
- **SI-2(2):** Amazon Inspector provides continuous scanning. `sla-breach-check.yaml`
  provides automated flaw remediation status reporting — the state of every finding's
  SLA compliance is queryable on demand from Jira.
- **SI-2(3):** Discovery-to-closure timestamps are captured automatically. `patch-verify.yaml`
  confirms actual pod rollout rather than relying on ticket closure as a proxy. Quarterly
  metrics table shows zero SLA breaches for 12 consecutive months.

---

## SI-3 — Malicious Code Protection

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Defense-in-Depth: Five Malicious Code Protection Layers

| Layer | Mechanism | Tool | Response |
| ----- | --------- | ---- | -------- |
| 1 — Supply chain | Image scanning pre-push | Trivy CI (Critical/High blocks merge) | Build fails; PR blocked |
| 2 — Admission | Image source enforcement | Kyverno `allow-only-ecr-images` (Enforce) | Pod rejected |
| 3 — Admission | Image signature verification | Kyverno `require-cosign-signature` (Enforce) | Unsigned pod rejected |
| 4 — Runtime | Behavioral anomaly detection | Falco (tuned ruleset, DaemonSet) | PagerDuty alert + `kill-pod` response plugin |
| 5 — Threat intelligence | Cloud-layer threat detection | GuardDuty (EKS + Malware Protection) | Security Hub finding → IR ticket |

Layer 3 (Cosign signature verification) is detailed in SI-7. Layer 4 (Falco) is the
primary runtime malicious code detection — described below.

### Falco Runtime Detection (Tuned)

Falco DaemonSet is deployed on all EKS worker nodes with a tuned rule set maintained
in `platform-gitops/falco/rules/`. Beyond the default Falco rules, the following
Links-Matrix-specific rules are active:

| Rule Name | Trigger | ATT&CK Technique | Severity |
| --------- | ------- | ---------------- | -------- |
| `lm_unexpected_outbound` | Any network connection to IP not in approved CIDR (aligned with SC-7 firewall allowlist) | T1071 — Application Layer Protocol | Critical |
| `lm_binary_exec_in_container` | Execution of binary not in the container's approved binary list | T1059 — Command and Scripting Interpreter | Critical |
| `lm_write_to_etc` | Write to `/etc` in any running container | T1565.001 — Stored Data Manipulation | High |
| `lm_crypto_mining_cpu` | CPU syscall pattern matching crypto mining workloads | T1496 — Resource Hijacking | High |
| `lm_kubectl_exec_prod` | `kubectl exec` into a pod in `lm-production` namespace | T1609 — Container Administration Command | High |
| `lm_secret_env_read` | Process reading from `KUBECONFIG`, `AWS_SECRET_ACCESS_KEY` env var | T1552.007 — Container API | High |

Each rule's approved binary list is maintained in `platform-gitops/falco/profiles/<workload>.yaml`,
built from the known-good container manifest at deploy time. A process not in the
profile triggers `lm_binary_exec_in_container`.

### Automated Response: Falco Response Plugin

Falco `kill-pod` response plugin is deployed (`platform-gitops/falco/plugins/kill-pod/`).
For Critical-severity Falco rules, the plugin:
1. Captures the event (pod name, namespace, process, timestamp)
2. Issues `kubectl delete pod <pod-name> -n <namespace> --grace-period=0`
3. Applies the IR isolation NetworkPolicy (`ir/isolate-namespace.yaml`) to the namespace
4. Creates a PagerDuty P1 incident with the Falco event details
5. Writes a forensic event record to the `lm-log-archive` S3 bucket (Object Lock Compliance)

For High-severity rules, the plugin alerts without killing — human decision required
for pod termination (consistent with the IR-4 authority chain).

### Falco Alert History and Tuning

| Quarter | Total Alerts | True Positive | False Positive | FP Rate | Actions Taken |
| ------- | ------------ | ------------- | -------------- | ------- | ------------- |
| 2025-Q3 | 47 | 12 | 35 | 74% | Tuned 4 rules; reduced FP rate |
| 2025-Q4 | 28 | 14 | 14 | 50% | Tuned 3 rules; added workload profiles |
| 2026-Q1 | 19 | 16 | 3 | 16% | Tuned 2 rules |

False positive rate declining from 74% → 16% over three quarters — evidence that
rule tuning is sustained, not one-time. A quarterly tuning review is scheduled by
the Cloud Security Engineer after each quarter's alert review.

**Responsible Role:** DevSecOps (Trivy CI, Falco deployment and tuning), Cloud Security Engineer (GuardDuty, Kyverno registry and signature policies, Falco response plugin), Platform Engineer (workload profiles, node access for Falco DaemonSet)

**Parameters:**
- Runtime detection: Falco DaemonSet, all nodes
- Tuned environment-specific rules: 6 named rules + workload binary profiles
- Automated response: Critical = pod kill + namespace isolation; High = alert only
- GuardDuty: EKS Protection + Malware Protection enabled
- Quarterly tuning review: Cloud Security Engineer after each quarter

**Evidence / Artifacts:**
- Falco DaemonSet and rules (`platform-gitops/falco/`)
- Falco workload profiles (`platform-gitops/falco/profiles/`)
- Falco response plugin (`platform-gitops/falco/plugins/kill-pod/`)
- Falco alert history and tuning log (Confluence: LM-SECURITY / SI / Falco-Tuning)
- Kyverno `allow-only-ecr-images` policy (`platform-gitops/kyverno-policies/`)
- GuardDuty findings (Security Hub)

**Enhancements Addressed:**
- **SI-3(1):** Falco and GuardDuty are centrally deployed via ArgoCD. Rule updates are
  PR-reviewed and deployed to all nodes on merge — no per-node manual configuration.
- **SI-3(2):** GuardDuty threat intelligence updated automatically by AWS. Falco rules
  updated via ArgoCD on merge to `platform-gitops`. Workload binary profiles regenerated
  at each container image build.
- **SI-3(7):** Falco behavioral detection (syscall-level) catches process and network
  anomalies without signatures. `lm_binary_exec_in_container` detects novel malware that
  is not in any signature database if it executes a binary not in the workload profile.

---

## SI-4 — System Monitoring

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### MITRE ATT&CK Detection Coverage Map

The Links-Matrix Platform monitoring stack is mapped to MITRE ATT&CK for Containers
and Enterprise (Cloud sub-techniques). The table below shows current detection coverage:

| ATT&CK Technique | Name | Detecting Tool | Alert Destination | Coverage |
| ---------------- | ---- | -------------- | ----------------- | -------- |
| T1078.004 | Cloud account compromise | GuardDuty `UnauthorizedAccess:IAMUser/*` | Security Hub → IR ticket | Full |
| T1098.001 | IAM key added to account | CloudTrail → OpenSearch `iam-key-add` rule | PagerDuty `lm-security-p1` | Full |
| T1133 | External remote services | Falco `lm_unexpected_outbound` | PagerDuty P1 | Full |
| T1525 | Implant container image | Cosign admission policy + ECR scan | Pod rejected at admission | Full |
| T1609 | Container admin command | Falco `lm_kubectl_exec_prod` | PagerDuty High | Full |
| T1059 | Command and scripting interpreter | Falco `lm_binary_exec_in_container` | PagerDuty P1 | Full |
| T1552.001 | Credentials in files | GuardDuty `CredentialAccess:Kubernetes/*` | Security Hub | Full |
| T1486 | Data encrypted for impact (ransomware) | Falco abnormal file write volume + GuardDuty | PagerDuty P1 | Partial |
| T1071 | Application layer protocol (C2) | Network Firewall + Falco `lm_unexpected_outbound` | Blocked + alert | Full |
| T1046 | Network service discovery | Falco `lm_unexpected_outbound` + VPC Flow Logs | OpenSearch alert | Partial |
| T1190 | Exploit public-facing application | GuardDuty + OWASP ZAP DAST findings | Security Hub | Partial |
| T1496 | Resource hijacking (crypto mining) | Falco `lm_crypto_mining_cpu` + CloudWatch CPU alarm | PagerDuty High | Full |

Coverage gaps (Partial): T1486 ransomware detection relies on behavioral heuristics
(abnormal file write volume) — no dedicated ransomware signature detection. T1046
network discovery is partially covered by NetworkPolicy blocking but not actively
detected in all scenarios.

### East-West Traffic Anomaly Detection

Falco NetworkActivity rules monitor pod-to-pod communication for anomalies beyond
what NetworkPolicy blocks:

- `lm_unexpected_eastwest`: Fires when a pod makes a successful TCP connection to
  another pod that does not match the workload's approved egress profile
  (`platform-gitops/falco/profiles/<workload>-network.yaml`). Network profiles are
  built from the NetworkPolicy allow rules at deploy time.
- `lm_dns_lateral_discovery`: Fires on DNS queries for pod names or service names
  inconsistent with the workload's normal DNS pattern — a common lateral discovery
  technique.

These rules cover the lateral movement gap (SI-4(11)) that NetworkPolicy alone does
not address — NetworkPolicy blocks unauthorized traffic, but Falco can detect an
attacker who compromises a pod that has legitimate access to another service and
uses it for enumeration.

### Alert Routing Matrix

| Alert Source | Severity | PagerDuty Service | On-Call Role | Acknowledgment SLA |
| ------------ | -------- | ----------------- | ------------ | ------------------ |
| Falco Critical | P1 | `lm-security-p1` | SOC on-call + ISSO | 5 minutes |
| Falco High | P2 | `lm-security-p2` | SOC on-call | 15 minutes |
| GuardDuty High/Critical | P1/P2 | `lm-security-p1` | SOC on-call | 5 minutes |
| SLA breach (SI-2) | P2 | `lm-security-p2` | DevSecOps lead | 1 hour |
| CloudTrail IAM anomaly | P1 | `lm-security-p1` | Cloud Security + ISSO | 5 minutes |
| Prometheus critical | P1 | `lm-platform-alerts` | Platform on-call | 5 minutes |
| Break-glass use | P1 | `lm-security-p1` | ISSO immediate | 5 minutes |

### Quarterly False-Positive Review

A quarterly false-positive review meeting (Cloud Security + DevSecOps + SOC lead)
reviews the previous quarter's alert volume, classifies each alert as TP or FP,
tunes rules that produced FPs, and documents changes in `platform-gitops/falco/TUNING.md`.
The Falco FP rate reduction (74% → 16% over 3 quarters) is the output of this process.

### Multi-Region Monitoring

GuardDuty, CloudTrail, and VPC Flow Logs are enabled in both `us-east-1` (primary)
and `us-west-2` (DR). Security Hub aggregates findings from both regions into a single
view. Falco DaemonSet is deployed to both EKS clusters. Monitoring coverage is not
limited to the primary region.

**Responsible Role:** Cloud Security Engineer (GuardDuty, Security Hub, CloudTrail, ATT&CK coverage mapping), DevSecOps (Falco east-west rules, network profiles, quarterly tuning), SOC (on-call, alert triage, investigation records)

**Parameters:**
- ATT&CK techniques monitored: 12 (9 full coverage, 3 partial)
- East-west anomaly detection: Falco `lm_unexpected_eastwest` + `lm_dns_lateral_discovery`
- Alert routing: 7-row matrix by source and severity
- Quarterly FP review: Cloud Security + DevSecOps + SOC
- Multi-region: Both us-east-1 and us-west-2

**Evidence / Artifacts:**
- ATT&CK coverage map (`platform-gitops/security/attack-coverage.md`)
- Falco east-west rules and network profiles (`platform-gitops/falco/rules/eastwest.yaml`)
- Alert routing matrix (Confluence: LM-SECURITY / SI / Alert-Routing.md)
- Quarterly tuning log (`platform-gitops/falco/TUNING.md`)
- PagerDuty service configuration (all six services)
- GuardDuty multi-region configuration (`infra-iac/guardduty/`)
- SOC alert investigation records (Jira `SEC-IR` — last 90 days)

**Enhancements Addressed:**
- **SI-4(2):** GuardDuty, Falco, and CloudTrail provide real-time automated detection.
  Alert routing via PagerDuty ensures human acknowledgment within 5–15 minutes of detection.
- **SI-4(4):** Network Firewall + GuardDuty DNS Protection covers north-south inbound/outbound.
  Falco `lm_unexpected_eastwest` covers east-west interior traffic.
- **SI-4(5):** Named alert routing table with 7 source/severity combinations, named PagerDuty
  services, named on-call roles, and acknowledgment SLAs. No alert goes to an unmonitored queue.
- **SI-4(11):** Falco `lm_unexpected_eastwest` and `lm_dns_lateral_discovery` detect
  anomalous interior communications that NetworkPolicy does not block.

---

## SI-7 — Software, Firmware, and Information Integrity

**Implementation Status:** Implemented

**Control Origination:** System-Specific

**Implementation Description:**

### Image Signing and Admission Verification

All container images produced by Links-Matrix CI pipelines are signed using Cosign
(Sigstore ecosystem) with the `lm-cosign-key` (ECDSA P-384, stored in AWS Secrets
Manager). Signing occurs in the CI pipeline immediately after the image is pushed
to ECR:

```bash
# In .github/workflows/build-push.yaml (after docker push)
cosign sign --key awssm://lm-cosign-key \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/lm-api@sha256:${IMAGE_DIGEST}
```

A Kyverno ClusterPolicy `require-cosign-signature` (Enforce mode) verifies the
Cosign signature on every pod admission request in the `lm-production` and
`lm-staging` namespaces:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-cosign-signature
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-image-signature
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: [lm-production, lm-staging]
      verifyImages:
        - imageReferences: ["123456789012.dkr.ecr.us-east-1.amazonaws.com/*"]
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      (lm-cosign-key public key)
                      -----END PUBLIC KEY-----
```

Any image not signed by `lm-cosign-key` — including a compromised image pushed to
ECR by an attacker who has ECR push access but not access to `lm-cosign-key` — is
rejected at admission. The private signing key is in AWS Secrets Manager, not in
the CI runner environment.

### SLSA Level 2 Provenance

All production image builds generate SLSA Level 2 provenance attestations using
the GitHub Actions SLSA provenance generator reusable workflow
(`platform-gitops/.github/workflows/build-push.yaml`, step: `generate-provenance`).
Attestations are stored as OCI artifacts in ECR alongside the image.

The provenance attestation records: source repository, branch, commit SHA, build
trigger, and build workflow. This allows post-incident forensics to answer:
"Was the image running in production built from the expected commit on the expected
branch?" — without relying on human-written records.

```bash
# Verify provenance for a running image
cosign verify-attestation \
  --type slsaprovenance \
  --key awssm://lm-cosign-key \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/lm-api@sha256:${IMAGE_DIGEST} \
  | jq '.payload | @base64d | fromjson | .predicate'
```

### readOnlyRootFilesystem (Universal Enforcement)

Kyverno ClusterPolicy `require-readonly-rootfs` (Enforce mode) blocks pod admission
in **all namespaces** unless `securityContext.readOnlyRootFilesystem: true` is set.
System components that legitimately require a writable filesystem (certain kube-system
components) use a documented exemption list in the Kyverno policy — no blanket exclusions
for entire namespaces.

Any container that attempts to write outside its declared `emptyDir` or `PVC` mounts
is detected by Falco rule `detect_write_to_readonly_fs` (SI-3). If the write is by
a Critical-severity process, the Falco response plugin terminates the pod.

### Image Digest Pinning (Universal)

All ArgoCD Application manifests reference images by digest. Renovate Bot automatically
opens PRs to update digests when new images are pushed to ECR. Kyverno policy
`require-image-digest` (Enforce mode, all namespaces) blocks any pod that uses a
mutable tag (`:latest`, `:main`, `:v1.2`) rather than a content-addressable digest.
A mutable tag cannot satisfy SI-7 — the same tag can point to different image content
at different times.

### Integrity Violation Response

Integrity violation events trigger automated response, not just alerting:

| Event | Detection | Automated Response |
| ----- | --------- | ------------------ |
| Unsigned image presented at admission | Kyverno `require-cosign-signature` | Pod rejected; audit log entry |
| Unexpected binary executed in container | Falco `lm_binary_exec_in_container` (Critical) | Pod killed; namespace isolated; P1 alert |
| Write to read-only filesystem | Falco `detect_write_to_readonly_fs` (Critical) | Pod killed; forensic event written to S3 Object Lock |
| Image digest mismatch at deploy | ArgoCD health check + Kyverno | Sync failed; ISSO alert |
| Cosign key compromise suspected | Manual (ISSO trigger) | Key revoked in Secrets Manager; all unsigned images rejected; emergency re-sign initiated |

**Responsible Role:** DevSecOps (Cosign signing workflow, SLSA provenance, Renovate digest updates), Platform Engineer (Kyverno admission policies, readOnlyRootFilesystem enforcement), Cloud Security Engineer (Cosign key custody in Secrets Manager, Falco response plugin), ISSO (Cosign key compromise response authority)

**Parameters:**
- Image signing: Cosign + ECDSA P-384 (`lm-cosign-key` in AWS Secrets Manager)
- Admission signature verification: Kyverno `require-cosign-signature` (Enforce — production and staging)
- SLSA provenance: Level 2 (GitHub Actions reusable workflow, OCI artifact in ECR)
- readOnlyRootFilesystem: Enforce mode in all namespaces (exemptions documented per component)
- Image digest pinning: Enforce mode in all namespaces (Kyverno + Renovate)
- Integrity violation response: Automated kill for Critical events; alert for High

**Evidence / Artifacts:**
- Cosign signing step (`platform-gitops/.github/workflows/build-push.yaml`)
- Kyverno `require-cosign-signature` policy (`platform-gitops/kyverno-policies/`)
- Kyverno `require-readonly-rootfs` policy (`platform-gitops/kyverno-policies/`)
- Kyverno `require-image-digest` policy (`platform-gitops/kyverno-policies/`)
- SLSA provenance generator workflow step (`platform-gitops/.github/workflows/build-push.yaml`)
- Falco response plugin kill-pod (`platform-gitops/falco/plugins/kill-pod/`)
- Cosign key (`lm-cosign-key` in AWS Secrets Manager — public key in Kyverno policy)
- Sample provenance attestation query output (Confluence: LM-SECURITY / SI / Provenance-Sample)

**Enhancements Addressed:**
- **SI-7(1):** Kyverno admission policies check integrity at every pod creation event —
  not just at initial deployment. A digest change between deployments is caught on the
  next pod admission (restart, scale event, node eviction).
- **SI-7(6):** Cosign ECDSA P-384 signatures provide cryptographic tamper evidence.
  The private key never leaves AWS Secrets Manager — an attacker with ECR push access
  cannot forge a valid signature.
- **SI-7(7):** Integrity violations trigger automated pod termination and namespace
  isolation for Critical events — detection is integrated with the IR-4 response pipeline,
  not just logging to a queue.
- **SI-7(15):** Kyverno `require-cosign-signature` blocks any unsigned image from running
  in production or staging — code authentication is enforced at admission, before execution.

---

## Test Procedures

### SI-2 Test Procedure

```bash
# Verify sla-breach-check workflow ran today
gh run list --workflow=sla-breach-check.yaml --repo platform-gitops \
  --limit 1 --json conclusion,createdAt
# Expected: conclusion: "success", no SLA breach findings

# Verify a recently patched finding has rollout-verification closure
# (Manual: pick a closed SEC-VULN ticket from last 30 days)
# Expected: ticket comments include patch-verify.yaml run ID, new image digest, and timestamp
```

### SI-3 Test Procedure

```bash
# Verify Falco DaemonSet is running on all nodes
kubectl get ds falco -n falco -o jsonpath='{.status.numberReady}/{.status.desiredNumberScheduled}'
# Expected: equal values (e.g., 6/6)

# Verify ECR-only registry admission control
kubectl run test-rejected --image=nginx:latest -n lm-production --dry-run=server 2>&1
# Expected: "Error from server: admission webhook denied: image not from approved registry"
```

### SI-4 Test Procedure

```bash
# Verify multi-region GuardDuty is active
for region in us-east-1 us-west-2; do
  aws guardduty list-detectors --region "$region" \
    --query 'DetectorIds[0]' --output text
done
# Expected: non-empty detector ID in both regions

# Verify east-west Falco rules are loaded
kubectl exec -n falco ds/falco -- falco --list-rules 2>/dev/null \
  | grep -E "lm_unexpected_eastwest|lm_dns_lateral_discovery"
# Expected: both rules listed as active
```

### SI-7 Test Procedure

```bash
# Verify unsigned image is rejected at admission
kubectl run unsigned-test \
  --image=123456789012.dkr.ecr.us-east-1.amazonaws.com/lm-api:unsigned-test \
  -n lm-production --dry-run=server 2>&1
# Expected: admission webhook denied — image signature verification failed

# Verify readOnlyRootFilesystem is enforced
kubectl run rwfs-test --image=busybox \
  --overrides='{"spec":{"containers":[{"name":"rwfs-test","image":"busybox","securityContext":{"readOnlyRootFilesystem":false}}]}}' \
  -n lm-production --dry-run=server 2>&1
# Expected: admission webhook denied — readOnlyRootFilesystem must be true

# Verify mutable tag is rejected
kubectl run tag-test --image=123456789012.dkr.ecr.us-east-1.amazonaws.com/lm-api:latest \
  -n lm-production --dry-run=server 2>&1
# Expected: admission webhook denied — image digest required

# Verify SLSA provenance exists for current production image
DIGEST=$(kubectl get deployment lm-api -n lm-production \
  -o jsonpath='{.spec.template.spec.containers[0].image}' | cut -d@ -f2)
cosign verify-attestation --type slsaprovenance \
  --key awssm://lm-cosign-key \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/lm-api@"${DIGEST}" \
  | jq '.payload | @base64d | fromjson | .predicate.buildType'
# Expected: "https://slsa.dev/provenance/v0.2"
```

**Pass criteria:** No SLA breaches, Falco DaemonSet ready on all nodes, unsigned/mutable/writable
pod rejected at admission, SLSA provenance verifiable for production images, GuardDuty
active in both regions, east-west Falco rules loaded.

---

## What Makes This GREAT — Examiner's Notes

| Control | What Elevates It |
| ------- | ---------------- |
| SI-2 | `patch-verify.yaml` closes the ticket-closure gap — closure is evidence of actual pod rollout, not an engineer's declaration. SLA breach alerting is automated daily, not discovered at weekly triage. 4-quarter metrics table shows zero SLA breaches. |
| SI-3 | 6 environment-specific Falco rules with workload binary profiles — detection is tuned to what Links-Matrix workloads actually do. Automated `kill-pod` response for Critical events means detection is integrated with response, not just alerting. FP rate from 74% → 16% over 3 quarters shows sustained tuning. |
| SI-4 | 12-technique ATT&CK coverage table tells auditors exactly what is and isn't detected — honest partial-coverage annotations for T1486 and T1046 are more credible than claiming full coverage. East-west Falco rules close the lateral movement visibility gap that NetworkPolicy cannot address. |
| SI-7 | Cosign signing at build + `require-cosign-signature` at admission closes the unsigned-image gap. The private key is in Secrets Manager — an attacker with ECR push access cannot forge a signature. SLSA Level 2 provenance provides post-incident traceability from running image digest back to source commit. |
| SI-7 | Three Kyverno Enforce-mode admission policies (signature, readOnlyRootFilesystem, digest) make integrity controls automatic, not aspirational. The test procedures prove all three reject invalid pods in real-time — auditors can run these commands themselves. |
| All | The SI family closes the loop: SI-2 proves flaws are remediated; SI-3 detects malicious code that SI-2 hasn't patched yet; SI-4 detects behavioral anomalies that neither scanning nor signatures catch; SI-7 verifies the integrity of what all three approved to run. The control chain comment at the top makes that relationship explicit — auditors see the architecture, not just the controls. |
