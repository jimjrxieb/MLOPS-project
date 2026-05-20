# Tool Justification Matrix

**Purpose**: Every tool in GP-Copilot was chosen because it satisfies a specific NIST 800-53
control or enhancement — not because it was new, popular, or recommended by a vendor.
This matrix is the answer to "why are you running this tool?" and
"how do you know it's configured correctly?"

Read this before a CISO briefing, an audit, or any conversation where someone asks
"why not just use [Enterprise Tool X]?"

---

## How to Use This Document

Each entry answers four questions:

1. **What controls does it satisfy?** — The base control and specific enhancements
2. **Why this tool and not the obvious alternative?** — The non-obvious reason
3. **How do you know it's configured correctly?** — The validation command
4. **What evidence does it produce?** — The artifact the auditor will ask for

---

## DEVOPS-LENS Tools

---

### Semgrep

**Lens**: DEVOPS | **Category**: SAST

**Controls**: SA-10(1) · SI-3(1) · RA-5(1) · CM-5

**Enhancements addressed**:

- SA-10(1): Software, Firmware, and Information Integrity — developer security testing
- SI-3(1): Malicious Code Protection — central management of protection mechanisms

**Why this tool, not Checkmarx/Veracode/SonarQube**:
Semgrep scans infrastructure-as-code, Kubernetes manifests, Dockerfiles, AND
application source in the same pipeline pass with the same rule format. Enterprise
SAST tools are language-specific — you pay for each language license. Semgrep's
community rules cover OWASP Top 10 at no cost. The GP-Copilot custom ruleset
(`01-APP-SEC/01-scanners/semgrep-rules/`) adds K8s-specific patterns no commercial
tool covers out of the box.

**Configuration validation**:

```bash
semgrep --validate --config=GP-CONSULTING/DEVOPS-LENS/01-APP-SEC/01-scanners/semgrep-rules/
semgrep --config=p/owasp-top-ten --test
# Expected: rules validated, 0 parse errors
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/semgrep-results.json`

---

### Bandit

**Lens**: DEVOPS | **Category**: SAST (Python)

**Controls**: SI-3 · RA-5 · SA-10

**Enhancements addressed**:

- SI-3(2): Malicious Code Protection — automatic updates on detection of threats

**Why this tool, not Semgrep for Python**:
Bandit uses Python AST (Abstract Syntax Tree) parsing — it understands Python semantics
that regex-based tools miss. It catches `subprocess.call(shell=True)` and
`yaml.load()` (unsafe) where pattern-matching tools produce false negatives. Used
alongside Semgrep, not instead of it — complementary coverage.

**Configuration validation**:

```bash
bandit --version
bandit -r . -f json -o /tmp/bandit-test.json --exit-zero
cat /tmp/bandit-test.json | python3 -c "import json,sys; r=json.load(sys.stdin); print(f'{len(r[\"results\"])} findings')"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/bandit-results.json`

---

### Trivy

**Lens**: DEVOPS + CYBERSEC | **Category**: Image + IaC + SBOM scanner

**Controls**: CM-7 · RA-5(3)(5) · SA-12 · SI-2(2) · SC-12

**Enhancements addressed**:

- RA-5(3): Breadth of coverage — scans multiple target types in one run
- RA-5(5): Privileged access — identifies OS and package vulnerabilities with remediation guidance
- SA-12(3): Trustworthiness — supply chain risk via SBOM generation
- SI-2(2): Automated flaw remediation reporting

**Why this tool, not Prisma Cloud/Aqua/Snyk**:
Trivy scans container images, git repositories, filesystems, Kubernetes clusters,
Terraform, and Helm charts in a single binary. Prisma Cloud and Aqua are the same
scope at $100–300K/yr. Snyk covers application dependencies but not the full
container/IaC surface. Trivy's SBOM output (`--format cyclonedx`) is accepted by
FedRAMP assessors and DoD SBOM mandates.

**Configuration validation**:

```bash
trivy --version
trivy image --severity HIGH,CRITICAL --exit-code 0 --format json alpine:latest | jq '.Results[].Vulnerabilities | length'
trivy fs --scanners vuln,secret,config . --exit-code 0
# Expected: output shows scan types, no config errors
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/trivy-results.json`

---

### Gitleaks

**Lens**: DEVOPS | **Category**: Secret detection

**Controls**: SC-12(1) · AC-6(9) · CM-5

**Enhancements addressed**:

- SC-12(1): Cryptographic key management — establishes and manages cryptographic keys
- AC-6(9): Log use of privileged functions — secrets in git constitute implicit credential exposure

**Why this tool, not GitHub Advanced Security/Trufflehog**:
Gitleaks scans the **entire git history**, not just the working tree. A secret committed
12 months ago and "deleted" in a subsequent commit is still in the history and still
compromised. GitHub Advanced Security requires GitHub Enterprise ($21/user/month).
Trufflehog is an alternative — GP-Copilot uses Gitleaks because its `.gitleaks.toml`
allowlist format is simpler to maintain and its CI exit codes are clean for pipeline integration.

**Configuration validation**:

```bash
gitleaks version
gitleaks detect --source . --report-format json --report-path /tmp/gitleaks-test.json --exit-code 0
# Expected: scan completes, report written
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/gitleaks-results.json`

---

### cosign (Container and Model Signing)

**Lens**: DEVOPS + AI-SEC | **Category**: Supply chain integrity

**Controls**: SA-12(3)(10) · SI-7(1)(6) · SC-12 · CM-5

**Enhancements addressed**:

- SA-12(3): Trustworthiness — validates software before use
- SA-12(10): Validate Software — verifies cryptographic signatures
- SI-7(1): Integrity checks using cryptographic mechanisms
- SI-7(6): Cryptographic protection

**Why this tool, not Notary/Docker Content Trust**:
cosign is the Sigstore standard — backed by Linux Foundation, supported by Google,
Red Hat, and VMware. Attestations are stored in the OCI registry alongside the image,
so there is no separate signature server to maintain. `cosign verify` is a one-command
audit step any assessor can run. Notary v2 is the emerging alternative but cosign is
production-ready now. Docker Content Trust (DCT) is Docker Hub-specific.

**Configuration validation**:

```bash
cosign version
# Verify a signed image:
cosign verify --certificate-identity-regexp=".*" --certificate-oidc-issuer-regexp=".*" <image>
# Verify model artifact:
cosign verify-blob --key cosign.pub --signature model.sig model.gguf
```

**Evidence artifact**: Cosign signature transparency log entries + `cosign verify` output

---

### Kyverno

**Lens**: DEVOPS | **Category**: Admission control

**Controls**: AC-3(7) · AC-4 · AC-6 · CM-7(5) · SC-6

**Enhancements addressed**:

- AC-3(7): Access Enforcement — role-based access control
- CM-7(5): Least Functionality — unauthorized software prohibition
- SC-6: Resource availability protection

**Why this tool, not OPA/Gatekeeper**:
Kyverno uses native Kubernetes YAML syntax — no Rego to learn. A platform engineer
can write and read a Kyverno policy without learning a new policy language. GP-Copilot
runs both Kyverno (workload policies) and Gatekeeper (infrastructure constraints)
because they have complementary strengths: Kyverno handles mutation (auto-adding
security contexts), Gatekeeper handles complex validation logic via Rego.

**Configuration validation**:

```bash
kubectl get clusterpolicies -A
kubectl get policyreport -A | grep -E "FAIL|WARN"
kyverno test GP-CONSULTING/DEVOPS-LENS/02-CLUSTER-HARDEN/01-policies/kyverno/
# Expected: 15 ClusterPolicies, test results show all pass
```

**Evidence artifact**: `kubectl get policyreport -A -o json` output

---

### kube-bench

**Lens**: DEVOPS | **Category**: CIS Benchmark

**Controls**: CM-2 · CM-6(1) · CM-7

**Enhancements addressed**:

- CM-6(1): Automated Central Management — automated benchmark verification

**Why this tool**:
kube-bench is the **CIS Kubernetes Benchmark** automated check tool — it IS the
standard. FedRAMP assessors and DoD RMF reviewers recognize kube-bench output as
authoritative CIS evidence. No alternative produces the same benchmark-numbered
output that maps directly to FedRAMP control requirements. Running any other tool
for CIS compliance requires manual mapping back to benchmark IDs.

**Configuration validation**:

```bash
kube-bench run --targets node,master --json > /tmp/kube-bench-results.json
cat /tmp/kube-bench-results.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for test in data['Controls']:
    fails = [r for r in test['tests'] for x in r['results'] if x['status'] == 'FAIL']
    print(f'{test[\"id\"]}: {len(fails)} failures')
"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/scans/kubebench-results.json`

---

### Kubescape

**Lens**: DEVOPS | **Category**: K8s security posture

**Controls**: CA-2 · CM-6 · RA-5(4)

**Enhancements addressed**:

- RA-5(4): Discoverable information — identifies what an attacker could learn from misconfigurations

**Why this tool, not Falco/kube-bench**:
Kubescape runs NSA/CISA K8s Hardening Guidance, MITRE ATT&CK for Kubernetes, CIS,
and SOC 2 frameworks simultaneously. kube-bench only runs CIS. Falco is runtime
detection, not configuration assessment. Kubescape provides a risk score that maps
directly to MITRE ATT&CK technique IDs — an assessor can ask "what's your ATT&CK
coverage?" and Kubescape provides the answer numerically.

**Configuration validation**:

```bash
kubescape scan --submit=false --format json --output /tmp/kubescape-results.json
cat /tmp/kubescape-results.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Risk score: {data.get(\"riskScore\", \"N/A\")}')
"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/artifacts/kubescape/`

---

### Polaris

**Lens**: DEVOPS | **Category**: Workload best practices

**Controls**: CM-6 · CM-7 · SI-6

**Enhancements addressed**:

- SI-6: Security function verification — checks that security settings are applied to workloads

**Why this tool alongside kube-bench and Kubescape**:
kube-bench checks cluster configuration. Kubescape checks RBAC and network.
Polaris checks individual **workload** configuration — `securityContext`, resource limits,
health probes, image tags. It catches the things developers introduce every sprint.
The combination is: kube-bench (cluster) + Kubescape (ATT&CK posture) + Polaris (workload).

**Configuration validation**:

```bash
polaris audit --format=json > /tmp/polaris-results.json
cat /tmp/polaris-results.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Score: {data.get(\"score\", \"N/A\")}')
"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/artifacts/polaris/`

---

## CYBERSEC-LENS Tools

---

### Falco

**Lens**: CYBERSEC | **Category**: Runtime threat detection

**Controls**: AU-2(3) · AU-12(1)(3) · IR-4(1) · SI-3(1)(8) · SI-4(2)(4)(20) · CM-3(5) · AU-3

**Enhancements addressed**:

- AU-2(3): Compilation and correlation of audit records from multiple sources
- AU-12(1): System-wide and time-correlated audit trail
- IR-4(1): Automated incident handling processes
- SI-3(1): Central management of malicious code protection
- SI-4(2): Automated tools for real-time analysis
- SI-4(4): Inbound and outbound communications traffic monitoring
- SI-4(20): Privileged user monitoring

**Why this tool, not Sysdig Secure/Aqua Runtime/CrowdStrike Falcon**:
Falco provides kernel-level syscall monitoring via eBPF — the same visibility plane as
Sysdig Secure and CrowdStrike. Sysdig Secure is $120–200K/yr for the same detection.
Falco is the upstream open source project that Sysdig built their product on. The 66
rules in GP-Copilot are MITRE ATT&CK tagged — an assessor can ask "what ATT&CK
techniques does your runtime detection cover?" and the answer is a grep away.
No other open source tool provides kernel-level syscall monitoring at this coverage.

**Configuration validation**:

```bash
falco --validate /etc/falco/falco.yaml
falco --list | wc -l
# List all loaded rules with their MITRE tags:
grep -r "tags:" /etc/falco/rules.d/ | grep -c "mitre"
systemctl is-active falco
```

**Evidence artifact**: Falco alert JSON stream → Splunk `gp_security` index

---

### Prowler

**Lens**: CYBERSEC | **Category**: Cloud security posture

**Controls**: AC-2 · AC-3 · CA-7(1) · RA-5(1)(3) · CM-3

**Enhancements addressed**:

- CA-7(1): Independent assessment — runs 400+ checks against cloud APIs, not self-reported
- RA-5(3): Breadth of coverage across cloud services

**Why this tool, not AWS Security Hub/Wiz/Orca**:
Prowler runs 400+ checks across AWS, GCP, and Azure in a single CLI. Security Hub
aggregates findings but doesn't run its own checks — it depends on GuardDuty,
Inspector, Config, and Macie. Wiz and Orca are excellent but cost $150–300K/yr.
Prowler is FedRAMP and CIS Level 1/2 aligned — its output maps check IDs to CIS
benchmark numbers and NIST controls, which is what a FedRAMP assessor needs.

**Configuration validation**:

```bash
prowler --version
prowler aws --quick-inventory 2>/dev/null | head -20
prowler aws -c iam_no_root_access_key_task -M json 2>/dev/null | tail -20
```

**Evidence artifact**: `GP-S3/6-seclab-reports/cybersec-evidence/` Prowler JSON output

---

### GuardDuty

**Lens**: CYBERSEC | **Category**: AWS threat detection

**Controls**: AU-2 · IR-4(1)(4) · IR-5 · CA-7(1)

**Enhancements addressed**:

- IR-4(1): Automated incident handling
- IR-4(4): Information correlation
- CA-7(1): Independent assessment (ML-based, not rule-based)

**Why this tool alongside Falco**:
Falco detects at the K8s layer — container syscalls, K8s API events, pod behaviors.
GuardDuty detects at the AWS layer — VPC Flow Logs, CloudTrail API calls, DNS queries,
EKS audit logs. They are **not redundant**: an attacker who compromises an IAM role
outside the cluster is invisible to Falco but visible to GuardDuty. Both are required
for complete coverage.

**Configuration validation**:

```bash
aws guardduty list-detectors
aws guardduty get-detector --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)
# Expected: Status: ENABLED, FindingPublishingFrequency set
```

**Evidence artifact**: GuardDuty findings exported to Security Hub → CloudWatch → Splunk

---

### Splunk (SIEM)

**Lens**: CYBERSEC | **Category**: SIEM / correlation

**Controls**: AU-3 · AU-6(1)(3) · AU-9(2) · IR-4(1) · IR-5 · IR-6

**Enhancements addressed**:

- AU-6(1): Automated process integrating audit review, analysis, and reporting
- AU-6(3): Correlate and analyze audit records from multiple tools
- AU-9(2): Store audit logs on separate system component

**Why this tool, not Elastic/Wazuh/Datadog**:
Splunk stores audit logs on a separate component from the systems being audited (AU-9(2)
requirement). Elastic and Wazuh can do this but require more configuration to separate
log storage from log sources. Splunk's SPL query language is familiar to SOC analysts
and produces the dashboards a CISO expects to see. The GP-Copilot integration
(`03-RUNTIME-SECURITY/05-splunk-integration/`) wires Falco + Prowler + GuardDuty +
K8s audit logs into named indexes that map to control families.

**Configuration validation**:

```bash
# From Splunk search head:
# index=gp_security | stats count by source
# index=gp_compliance | stats count by control_id
curl -k -u admin:changeme https://splunk:8089/services/data/inputs/all | grep -c "enabled"
```

**Evidence artifact**: Splunk dashboard exports in `gp_security`, `gp_compliance` indexes

---

### Checkov

**Lens**: CYBERSEC | **Category**: IaC static analysis

**Controls**: SA-10(1) · CM-3(4)(6) · CM-5

**Enhancements addressed**:

- CM-3(4): Security impact analysis during configuration change
- CM-3(6): Cryptography management in configuration changes

**Why this tool alongside Semgrep**:
Semgrep is language-agnostic SAST. Checkov is IaC-specific — it understands Terraform
resource graphs, CloudFormation dependencies, and ARM template structures. Checkov
catches "S3 bucket with public ACL where the bucket policy allows public access" —
a conditional misconfig that requires understanding resource relationships. Semgrep
would need a custom rule for each cloud provider's resource graph.

**Configuration validation**:

```bash
checkov --version
checkov -d . --framework terraform,cloudformation,kubernetes --compact --quiet
# Expected: Pass/Fail counts per framework
```

**Evidence artifact**: Checkov JSON output in CI pipeline logs

---

### cert-manager

**Lens**: CYBERSEC | **Category**: Certificate lifecycle

**Controls**: SC-17 · IA-5(2) · SC-8(1)

**Enhancements addressed**:

- IA-5(2): PKI-based authentication — certificate-based credentials
- SC-8(1): Cryptographic protection of data in transit

**Why this tool, not manual cert management**:
cert-manager automates certificate issuance, rotation, and expiration alerts.
Manual certificate management fails at scale — a single expired cert during an
incident is a critical finding. cert-manager's `Certificate` resource provides
an audit record of every cert issued, its expiry, and its renewal history.
This satisfies IA-5(2) and SC-17 with automated evidence.

**Configuration validation**:

```bash
kubectl get certificates -A
kubectl get certificaterequests -A | grep -v Approved
# Check for expiring certs:
kubectl get certificates -A -o json | python3 -c "
import json, sys, datetime
certs = json.load(sys.stdin)['items']
for c in certs:
    exp = c.get('status', {}).get('notAfter', 'unknown')
    print(f'{c[\"metadata\"][\"name\"]}: expires {exp}')
"
```

**Evidence artifact**: `kubectl get certificates -A -o yaml` + cert-manager controller logs

---

## AI-SEC-LENS Tools

---

### garak

**Lens**: AI-SEC | **Category**: LLM vulnerability scanner

**Controls**: RA-5(1)(5) · SI-4(2) · CA-2

**NIST AI 600-1**: MANAGE 2.4–2.6 (Prompt Injection) · MEASURE 2.1–2.3 (Adversarial)

**MITRE ATLAS**: AML.T0048 (Direct Prompt Injection) · AML.T0054 (LLM Jailbreak) · AML.T0056 (Adversarial Input)

**Why this tool, not manual red-teaming**:
garak runs 40+ automated probe types across an LLM endpoint — prompt injection,
jailbreak, data extraction, encoding attacks, hallucination injection. A human
red team cannot cover this volume systematically. garak maps results to OWASP LLM
Top 10 (2025) and MITRE ATLAS, which is what an AI security audit requires.
No enterprise equivalent exists at this price point. Hidden Layer's products perform
similar scans at $80–150K/yr.

**Configuration validation**:

```bash
python3 -m garak --version
python3 -m garak -m rest -g ollama --probes dan --report_prefix /tmp/garak-test
# Expected: probe runs, JSONL report written
ls /tmp/garak-test*.jsonl
```

**Evidence artifact**: `GP-S3/6-seclab-reports/ai-sec-evidence/garak/` JSONL reports

---

### Presidio

**Lens**: AI-SEC | **Category**: PII detection in training data

**Controls**: SC-28(1) · AU-2 · SI-10

**NIST AI 600-1**: MAP 2.1 (Data Quality) · MAP 2.2 (Data Documentation)

**Why this tool, not manual review/AWS Macie**:
Presidio scans unstructured text for 50+ PII entity types (SSN, credit card, health
data, email, phone) using NLP recognizers — faster and more complete than keyword
search. AWS Macie scans S3 objects but not arbitrary text files or training JSONL.
Presidio is embedded in the RAG ingestion pipeline before any document reaches
ChromaDB, so PII never enters the vector database.

**Configuration validation**:

```bash
python3 -c "
from presidio_analyzer import AnalyzerEngine
engine = AnalyzerEngine()
results = engine.analyze(text='Call John at 555-867-5309', language='en')
print(f'Entities found: {[r.entity_type for r in results]}')
"
# Expected: ['PHONE_NUMBER']
```

**Evidence artifact**: Presidio scan log per RAG ingestion run in `GP-MODEL-OPS/2-RagIngestion-Pipeline/`

---

### counterfit + ART (Adversarial Robustness Toolbox)

**Lens**: AI-SEC | **Category**: Adversarial ML testing

**Controls**: RA-3(1) · RA-5

**NIST AI 600-1**: MEASURE 2.1–2.3 (Adversarial Inputs)

**MITRE ATLAS**: AML.T0031 (Erode ML Model Integrity) · AML.T0043 (Craft Adversarial Data)

**Why these tools, not manual testing**:
counterfit (Microsoft) provides a CLI for running adversarial attacks against black-box
ML models without access to training code. ART (IBM) provides white-box attacks when
model weights are accessible. Together they cover the full threat model: an external
attacker who can only query the model (counterfit) and an insider who has model access
(ART). Neither requires knowing the model architecture in advance.

**Configuration validation**:

```bash
python3 -c "import counterfit; print(counterfit.__version__)"
python3 -c "from art.attacks.evasion import FastGradientMethod; print('ART OK')"
```

**Evidence artifact**: counterfit attack report + ART perturbation results in `GP-S3/6-seclab-reports/ai-sec-evidence/`

---

### MLflow (Hardened)

**Lens**: AI-SEC | **Category**: ML experiment tracking and audit trail

**Controls**: AU-2 · AU-12(1) · CA-7 · CM-3

**NIST AI 600-1**: MANAGE 3.1–3.2 (MLOps Pipeline Security) · GOVERN 1.3–1.4 (Performance Monitoring)

**Why this tool, not custom logging**:
MLflow provides an immutable audit trail for every training run: parameters, metrics,
artifacts, and the code version that produced them. Custom logging can be deleted.
MLflow runs with authentication enabled (`MLFLOW_TRACKING_USERNAME/PASSWORD` +
`mlflow.set_tracking_uri()`) so the audit trail is access-controlled. The
`mlruns/` directory is the evidence chain — an auditor can trace any deployed model
back to the exact training run that produced it.

**Configuration validation**:

```bash
mlflow --version
# Check auth is enabled:
curl -s http://localhost:5000/api/2.0/mlflow/experiments/list -H "Authorization: Bearer $MLFLOW_TOKEN" | python3 -c "import json,sys; print('Auth OK' if 'experiments' in json.load(sys.stdin) else 'FAIL')"
# Check runs exist:
mlflow experiments list
```

**Evidence artifact**: `GP-MODEL-OPS/JADE-AI/mlruns/` — immutable training run records

---

## Summary: Tool → Control Coverage

| Tool | Primary Controls | Enhancement Count | MITRE Coverage |
|------|-----------------|-------------------|---------------|
| Semgrep | SA-10, SI-3, RA-5 | SA-10(1), SI-3(1) | T1190, T1059 |
| Bandit | SI-3, RA-5, SA-10 | SI-3(2) | T1190 |
| Trivy | CM-7, RA-5, SA-12, SI-2, SC-12 | RA-5(3)(5), SA-12(3)(10), SI-2(2) | T1195, T1525 |
| Gitleaks | SC-12, AC-6, CM-5 | SC-12(1), AC-6(9) | T1552 |
| cosign | SA-12, SI-7, SC-12, CM-5 | SA-12(3)(10), SI-7(1)(6) | T1195.002 |
| Kyverno | AC-3, AC-4, AC-6, CM-7, SC-6 | AC-3(7), CM-7(5) | T1610, T1611, T1525 |
| kube-bench | CM-2, CM-6, CM-7 | CM-6(1) | T1610, T1611 |
| Kubescape | CA-2, CM-6, RA-5 | RA-5(4) | MITRE ATT&CK for K8s (full) |
| Polaris | CM-6, CM-7, SI-6 | — | T1525, T1610 |
| Falco | AU-2, AU-3, AU-12, IR-4, SI-3, SI-4, CM-3 | AU-2(3), AU-12(1)(3), IR-4(1), SI-4(2)(4)(20) | 11 ATT&CK tactics |
| Prowler | AC-2, AC-3, CA-7, RA-5 | CA-7(1), RA-5(1)(3) | T1078, T1530 |
| GuardDuty | AU-2, IR-4, IR-5, CA-7 | IR-4(1)(4), CA-7(1) | T1078, T1098, T1530 |
| Splunk | AU-3, AU-6, AU-9, IR-4, IR-5, IR-6 | AU-6(1)(3), AU-9(2) | All (correlation layer) |
| Checkov | SA-10, CM-3, CM-5 | CM-3(4)(6) | T1195, T1610 |
| cert-manager | SC-17, IA-5, SC-8 | IA-5(2), SC-8(1) | — |
| garak | RA-5, SI-4, CA-2 | RA-5(1)(5) | AML.T0048, AML.T0054 |
| Presidio | SC-28, AU-2, SI-10 | SC-28(1) | AML.T0011, AML.T0020 |
| counterfit + ART | RA-3, RA-5 | RA-3(1) | AML.T0031, AML.T0043 |
| MLflow | AU-2, AU-12, CA-7, CM-3 | AU-12(1), CA-7(1) | AML.T0010 |
