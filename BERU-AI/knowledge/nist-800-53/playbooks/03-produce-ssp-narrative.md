# BERU — Produce SSP Narratives

> Input: completed BERU findings (any status — PASS, PARTIAL, FAIL)
> Output: great-tier SSP narrative per control family
> Reference: `../ssp-examples/<family>-ssp-great.md`
> Audience: BERU writes. ISSO reviews. CISO signs.

---

## When to Run This Playbook

Run when:
- A FedRAMP, NIST, or HIPAA audit requires SSP control narratives
- CISO asks for documented proof of control implementation
- A client requests SSP narrative for a specific control family
- After audit findings are resolved and controls move to PASS

---

## The Quality Standard

Read `../ssp-examples/<family>-ssp-great.md` before writing.

The three tiers:

```text
BAD:   "Access controls are implemented per policy."
       → Zero specificity. Auditor reads this and marks FAIL on documentation.

GOOD:  "Role-based access control is enforced via Kyverno ClusterPolicies that deny
        wildcard verbs and cluster-admin bindings to service accounts.
        Last reviewed: 2026-05-01."
       → Names the tool and the policy type. Has a date. Auditor can ask for evidence.

GREAT: "Kyverno ClusterPolicy deny-cluster-admin-sa (validationFailureAction: Enforce)
        prevents any ServiceAccount subject from being bound to the cluster-admin
        ClusterRole. rbac-lookup quarterly review on 2026-05-01 found 0 service accounts
        with cluster-admin binding. kube-bench 5.1.6: PASS. Evidence: kubescape RBAC scan
        at GP-S3/6-seclab-reports/cybersec-evidence/scans/kubescape-rbac-20260501.json."
       → Names the exact policy. Names the enforcement mode. Has a date. Names the
          evidence artifact. Auditor can validate every claim with a single command.
```

---

## Step 1 — Identify the Controls to Narrate

From your completed BERU findings, list the controls that need SSP narrative:

| Control | Status | Narrative Approach |
| --- | --- | --- |
| PASS | PASS | Document what is implemented and where the evidence is |
| PARTIAL | PARTIAL | Document what is implemented, acknowledge the gap, state the remediation plan |
| FAIL | FAIL | Document that the control is not yet implemented and reference the POA&M item |

---

## Step 2 — Write the Narrative for Each Control

Use this structure for every control narrative:

```text
[Control ID] — [Control Name]

Implementation: [PASS | PARTIAL | FAIL]

[One paragraph — great tier. Must include all of the following:]
  1. The specific tool or mechanism implementing the control
     (Kyverno policy name, AWS Config rule, cert-manager issuer, etc.)
  2. The enforcement mode (Enforce vs. Audit, Enabled vs. Monitoring)
  3. The last verification date and result
  4. The evidence artifact path in GP-S3

[If PARTIAL or FAIL — one additional sentence referencing the POA&M:]
  "Gap remediation is tracked in POAM-YYYY-MM-NNN, scheduled completion YYYY-MM-DD."
```

---

## Step 3 — Narrative Templates by Family

### AC — Access Control

Template (fill in the bracketed fields):

```text
AC-6 — Least Privilege

Implementation: PASS | PARTIAL | FAIL

Least privilege for Kubernetes workloads is enforced via Kyverno ClusterPolicy
[policy-name] (validationFailureAction: Enforce), which [what the policy does, e.g.,
"denies any ServiceAccount from being bound to the cluster-admin ClusterRole"].
rbac-lookup review on [DATE] confirmed [N] service accounts with cluster-admin binding.
RBAC policies are scoped to the minimum required verbs ([list]) and resources ([list])
for each workload. Kubescape RBAC framework scan on [DATE] returned risk score [N].
Evidence: [GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/DATE-AC/cluster-admin-bindings-DATE.json]
```

### AU — Audit and Accountability

```text
AU-2 / AU-12 — Event Logging and Audit Record Generation

Implementation: PASS | PARTIAL | FAIL

Kubernetes API server audit logging is enabled via audit-policy.yaml with
RequestResponse level for Secrets, ConfigMaps, and ServiceAccounts, and Metadata
level for all other resources. Log retention is [N] days per --audit-log-maxage setting.
kube-bench 3.2.1 and 3.2.2: [PASS/FAIL] on [DATE]. Falco DaemonSet ([N] rules loaded)
provides runtime event logging covering [N] MITRE ATT&CK techniques. Falco events are
forwarded to Splunk index gp_security. Evidence: [path to audit-policy and kubebench output]
```

### CM — Configuration Management

```text
CM-6 / CM-7 — Configuration Settings / Least Functionality

Implementation: PASS | PARTIAL | FAIL

Cluster configuration is enforced via [N] Kyverno ClusterPolicies in validationFailureAction:
Enforce mode, preventing [list key restrictions: privileged containers, root execution,
hostPath mounts, wildcard RBAC]. kube-bench CIS Kubernetes Benchmark L1 run on [DATE]
showed [N PASS / N FAIL / N WARN] across [N] checks. Failing checks are tracked in
[POAM reference if any]. ArgoCD enforces git-based change control: [N] applications synced,
[N] OutOfSync at time of assessment. Evidence: [paths to kubebench output, polaris output,
kyverno PolicyReport]
```

### SC — System and Communications Protection

```text
SC-7 — Boundary Protection

Implementation: PASS | PARTIAL | FAIL

Default-deny NetworkPolicy is deployed in [N of N] production namespaces. [N] namespaces
lack a default-deny policy [reference POA&M if any]. Istio service mesh is [deployed in
STRICT mTLS mode / not deployed — justify]. Ingress TLS is enforced on [N of N] external
endpoints via cert-manager [issuer-name]. Evidence: [path to networkpolicies dump, cert
status output]

SC-12 — Cryptographic Key Management

Secrets are managed via ExternalSecrets Operator connected to [AWS Secrets Manager /
Vault]. [N] K8s Secrets are sourced via ExternalSecrets. Gitleaks scan on [DATE] found
[N findings / zero findings] in the active git history. KMS key rotation is [enabled /
disabled] with [N] active keys. Evidence: [paths to externalsecret inventory, gitleaks
output, kms rotation status]
```

### SI — System Integrity

```text
SI-2 — Flaw Remediation

Implementation: PASS | PARTIAL | FAIL

Container image vulnerability scanning is performed by Trivy in the CI pipeline on
every pull request, blocking merges with CRITICAL CVEs (since [DATE]). Trivy scan of
production images on [DATE] found [N CRITICAL / N HIGH] CVEs. CRITICAL CVE SLA is
[N days]. Prowler cloud scan on [DATE] found [N] CRITICAL and [N] HIGH cloud findings.
Evidence: [paths to trivy scan outputs, prowler output]

SI-7 — Software, Firmware, and Information Integrity

All production container images are signed using cosign with the GP-Copilot signing key
(keyless / key-based). Kyverno ClusterPolicy [require-image-signature] (validationFailureAction:
Enforce) prevents unsigned images from running in production namespaces. cosign verify on
[DATE] confirmed [N of N] images valid. Evidence: [path to cosign-verify output]
```

---

## Step 4 — Review Against the Quality Standard

Before finalizing any narrative, check each sentence against this checklist:

- [ ] Names the specific tool (not just "a tool" or "controls")
- [ ] Names the specific policy, rule, or config (not just "a policy")
- [ ] States the enforcement mode (Enforce vs. Audit, Enabled vs. Disabled)
- [ ] Has a date (last scan, last review, last verification)
- [ ] Points to an evidence artifact path in GP-S3
- [ ] For PARTIAL/FAIL: references the POA&M item number

If any checkbox is unchecked, the narrative is not great-tier. Rewrite before finalizing.

---

## Step 5 — Save the SSP Narrative

```bash
SSP_DIR="GP-S3/6-seclab-reports/cybersec-evidence/ssp-narratives"
mkdir -p $SSP_DIR

# One file per family per engagement
# Filename: YYYY-MM-DD-<client>-SSP-<family>.md
nano $SSP_DIR/$(date +%Y-%m-%d)-<client>-SSP-AC.md
```

---

## SSP Writing Hard Stops

```text
NEVER write "the organization implements access controls" — too vague to audit.
NEVER write a narrative for a FAIL finding without referencing the POA&M item.
NEVER claim PASS on a control that has an open POA&M item — that is PARTIAL at best.
NEVER omit the evidence artifact path — a claim without evidence is hearsay.
NEVER use dates older than 90 days as "current" evidence of an ongoing control.
```
