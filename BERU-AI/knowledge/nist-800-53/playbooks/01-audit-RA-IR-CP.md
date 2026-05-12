# BERU — RA / IR / CP / CA / IA / SA Audit Playbook

> Risk Assessment: RA-3, RA-5, RA-7
> Incident Response: IR-4, IR-8
> Contingency Planning: CP-9, CP-10
> Assessment & Monitoring: CA-2, CA-7
> Identity & Authentication: IA-2, IA-5
> System & Services Acquisition: SA-10, SA-11, SA-12
>
> Tools: Prowler, Trivy, Kubescape, Velero, cert-manager, cosign, Semgrep
> Audience: BERU (NIST-800-53 internal auditor)
> Read first: the relevant `../controls/<ID>.md` for each control you are assessing.

---

## Step 1 — Collect Evidence for All Families

```bash
EVIDENCE="GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/$(date +%Y-%m-%d)-RA-IR-CP-CA-IA-SA"
mkdir -p $EVIDENCE

# RA-5: Vulnerability scan — Prowler
prowler aws --output-formats json --output-filename $EVIDENCE/prowler-$(date +%Y%m%d) 2>&1

# RA-5: Kubescape vulnerability/misconfig scan
kubescape scan --format json --output $EVIDENCE/kubescape-all-$(date +%Y%m%d).json 2>&1

# CP-9 / CP-10: Velero backup status
velero backup get 2>&1 | tee $EVIDENCE/velero-backups-$(date +%Y%m%d).txt
velero schedule get 2>&1 | tee $EVIDENCE/velero-schedules-$(date +%Y%m%d).txt
velero restore get 2>&1 | tee $EVIDENCE/velero-restores-$(date +%Y%m%d).txt

# CA-7: Continuous monitoring — Kubescape scheduled scan status
kubectl get cronjob -A | grep -i "kubescape\|monitor\|scan" 2>&1 | \
  tee $EVIDENCE/scheduled-scans-$(date +%Y%m%d).txt

# IA-2: cert-manager certificates (for workload identity)
kubectl get certificates -A -o json | \
  jq '.items[] | {namespace: .metadata.namespace, name: .metadata.name,
      ready: .status.conditions[]?.status, expiry: .status.notAfter}' \
  2>&1 | tee $EVIDENCE/certificates-ia-$(date +%Y%m%d).json

# IA-5: Check for default credentials or static tokens
kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | \
  grep -i "token-auth-file\|basic-auth-file" 2>&1 | \
  tee $EVIDENCE/apiserver-static-auth-$(date +%Y%m%d).txt

# SA-12: cosign supply chain verification
kubectl get pods -A -o json | jq -r '[.items[].spec.containers[].image] | unique[]' | \
  while read image; do
    echo -n "SA-12 $image → "
    cosign verify --certificate-identity-regexp ".*" \
      --certificate-oidc-issuer-regexp ".*" $image 2>&1 | head -1
  done 2>&1 | tee $EVIDENCE/sa12-cosign-$(date +%Y%m%d).txt

# SA-11: SAST/DAST coverage
semgrep --config=auto --output $EVIDENCE/sa11-semgrep-$(date +%Y%m%d).json \
  --json /path/to/app/source 2>&1

# IR-4: Falco responder scripts — do they exist?
ls -la GP-CONSULTING/CYBERSEC-LENS/03-RUNTIME-SECURITY/ 2>&1 | tee $EVIDENCE/ir4-responders-$(date +%Y%m%d).txt
```

---

## Step 2 — Assess RA-3 / RA-5 / RA-7: Risk Assessment

Read: `../controls/RA-3.md`, `../controls/RA-5.md`, `../controls/RA-7.md`

**RA-3 — Risk Assessment (documented)**

Questions:
1. Has a formal risk assessment been conducted and documented?
2. Are risks documented with likelihood, impact, and risk owner?
3. Is there a risk register or equivalent?

Assessment: Ask the CompO or CISO to provide:
- Last formal risk assessment document (date, scope, methodology)
- Current risk register (open risks, owners, target closure dates)
- Evidence that risks fed into POA&M items

**PASS:** Dated risk assessment ≤ 12 months old. Risk register maintained with owners. POA&M items trace to risk register.

**PARTIAL:** Risk assessment exists but > 12 months old. Risk register is informal or incomplete.

**FAIL:** No risk assessment document. No risk register. POA&M items with no traceability.

---

**RA-5 — Vulnerability Scanning**

Assessment commands:
```bash
# Prowler finding summary
cat $EVIDENCE/prowler-$(date +%Y%m%d).json | python3 -c "
import sys, json
data = json.load(sys.stdin)
findings = data.get('findings', data) if isinstance(data, dict) else data
severity_counts = {}
for f in findings:
    sev = f.get('Severity', f.get('severity', 'UNKNOWN'))
    severity_counts[sev] = severity_counts.get(sev, 0) + 1
for sev, count in sorted(severity_counts.items()):
    print(f'{sev}: {count}')
" 2>&1 | tee $EVIDENCE/prowler-summary-$(date +%Y%m%d).txt

# Kubescape risk score
cat $EVIDENCE/kubescape-all-$(date +%Y%m%d).json | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
score = data.get('riskScore', data.get('complianceScore', 'N/A'))
print(f'Kubescape risk score: {score}')
" 2>&1 | tee $EVIDENCE/kubescape-score-$(date +%Y%m%d).txt
```

Ask the SecEng: "How often do you run vulnerability scans? What is your SLA for remediating CRITICAL findings from Prowler?"

**PASS:** Prowler runs on schedule (weekly minimum). Kubescape continuous monitoring enabled. CRITICAL findings remediated within SLA. Scan results retained for 90 days.

**PARTIAL:** Scans run manually. No automated schedule. Some findings addressed but no formal SLA.

**FAIL:** No vulnerability scanning of cloud or cluster. No remediation tracking. Scan results older than 90 days.

---

**RA-7 — Risk Response**

Questions:
1. Is there a documented process for responding to RA-5 findings?
2. Are CRITICAL findings automatically creating tickets/alerts?
3. Is there evidence of risk response activity (closed tickets, POA&M updates)?

**PASS:** CRITICAL Prowler/Trivy findings auto-create Jira/GitHub issues. Risk response SLA documented. Recent evidence of closed findings.

**PARTIAL:** Response process exists informally. Critical findings tracked but not automatically.

**FAIL:** No response process. CRITICAL findings accumulate without action.

---

## Step 3 — Assess IR-4 / IR-8: Incident Response

Read: `../controls/IR-4.md`

**IR-4 — Incident Handling**

Questions:
1. Is there a Falco → alert → response automation chain?
2. Are responder scripts deployed and tested?
3. Is there an incident timeline in Splunk for recent events?

Assessment commands:
```bash
# Check responder scripts exist and are executable
ls -la GP-CONSULTING/CYBERSEC-LENS/03-RUNTIME-SECURITY/responders/ 2>&1 | \
  tee $EVIDENCE/ir4-responder-scripts-$(date +%Y%m%d).txt

# Check if responders are wired to Falco
kubectl get configmap -n falco falco-rules -o yaml | grep -i "program_output\|http_output" \
  2>&1 | tee $EVIDENCE/falco-output-config-$(date +%Y%m%d).txt

# Last incident evidence — check Splunk or ticket system
# (Splunk query: index=gp_security sourcetype=falco priority=CRITICAL | head 10)
```

**PASS:** Falco rules → Splunk pipeline confirmed. Automated responders deployed and tested within 90 days. Incident response plan documented. Post-incident review evidence.

**PARTIAL:** Responder scripts exist but not automated. Incidents reviewed manually. Plan exists but not tested.

**FAIL:** No incident response plan. No automated detection-to-response path. Falco alerts silently dropped.

---

**IR-8 — Incident Response Plan**

Ask to see: The written IR plan document. When was it last reviewed? When was the last tabletop?

**PASS:** Written IR plan dated ≤ 12 months ago. Tabletop exercise evidence within 12 months. Plan covers GP-Copilot tool stack (Falco, Splunk, Kubescape).

**PARTIAL:** IR plan exists but predates GP-Copilot tools. No tabletop evidence.

**FAIL:** No IR plan. No tabletop. No documented escalation path.

---

## Step 4 — Assess CP-9 / CP-10: Contingency Planning

Read: `../controls/CP-9.md`, `../controls/CP-10.md`

**CP-9 — System Backup**

Assessment commands:
```bash
# Velero backup schedule
cat $EVIDENCE/velero-schedules-$(date +%Y%m%d).txt

# Last successful backup
cat $EVIDENCE/velero-backups-$(date +%Y%m%d).txt | grep -i "completed\|partial\|failed" | head -10

# Backup age — last backup timestamp
velero backup get --output json 2>&1 | \
  python3 -c "
import sys, json, datetime
data = json.load(sys.stdin)
backups = sorted(data.get('items', []), key=lambda x: x.get('status', {}).get('completionTimestamp', ''), reverse=True)
if backups:
    last = backups[0]
    print(f\"Last backup: {last['metadata']['name']}\")
    print(f\"Status: {last['status'].get('phase', 'unknown')}\")
    print(f\"Completed: {last['status'].get('completionTimestamp', 'never')}\")
" 2>&1 | tee $EVIDENCE/velero-last-backup-$(date +%Y%m%d).txt

# RDS automated backups
aws rds describe-db-instances \
  --query 'DBInstances[*].{DB:DBInstanceIdentifier,BackupRetention:BackupRetentionPeriod}' \
  --output json 2>&1 | tee $EVIDENCE/rds-backups-$(date +%Y%m%d).json
```

**PASS:** Velero schedule runs daily. Last backup completed successfully < 24 hours ago. RDS retention ≥ 7 days. Recovery tested within 90 days (show restore log).

**PARTIAL:** Backups scheduled but last run shows PARTIAL status. RDS retention configured. No recent restore test.

**FAIL:** No Velero schedule. Backups more than 7 days old or FAILED status. RDS `BackupRetentionPeriod: 0`.

---

**CP-10 — System Recovery and Reconstitution**

Questions:
1. Has a restore been tested from Velero backup?
2. Is the RTO/RPO documented?
3. Is there a runbook for recovery?

Assessment commands:
```bash
# Check restore history
cat $EVIDENCE/velero-restores-$(date +%Y%m%d).txt

# If no restores ever run — that is a FAIL for CP-10
```

**PASS:** At least one successful restore from backup within 90 days. RTO/RPO documented. Recovery runbook exists.

**PARTIAL:** Backup exists but no restore test. RTO/RPO informal.

**FAIL:** No restore ever run. No RTO/RPO. No recovery runbook.

---

## Step 5 — Assess CA-2 / CA-7: Assessment and Continuous Monitoring

**CA-2 — Control Assessments**

Questions:
1. Is this the first assessment or is there a prior assessment to compare against?
2. Are assessments scheduled (annual minimum for most baselines)?
3. Does the assessment cover all three lenses?

**PASS:** Annual assessment documented. Prior findings tracked. This assessment covers DEVOPS + CYBERSEC + AI-SEC lenses.

**PARTIAL:** Assessment run but covers only one or two lenses. No prior baseline to compare.

**FAIL:** No prior assessment. No assessment schedule. Single ad-hoc scan not representative.

---

**CA-7 — Continuous Monitoring**

Assessment commands:
```bash
# Is Kubescape running on a schedule?
cat $EVIDENCE/scheduled-scans-$(date +%Y%m%d).txt

# Is Prowler scheduled?
aws events list-rules --query 'Rules[?contains(Name, `prowler`)]' --output json 2>&1 | \
  tee $EVIDENCE/prowler-schedule-$(date +%Y%m%d).json

# Falco + Splunk = continuous monitoring for runtime
kubectl get daemonset -n falco 2>&1 | tee $EVIDENCE/falco-ca7-$(date +%Y%m%d).txt
```

**PASS:** Kubescape scheduled weekly. Prowler scheduled. Falco running. Splunk receiving events. Results reviewed on cadence.

**PARTIAL:** Some tools scheduled, some manual. Review cadence informal.

**FAIL:** All scans manual. No continuous monitoring. Results not reviewed until an incident.

---

## Step 6 — Assess IA-2 / IA-5: Identity and Authentication

**IA-2 — Multi-Factor Authentication**

Questions:
1. Is MFA required for all human access to the cluster (kubectl, AWS console)?
2. Are service account tokens short-lived (projected service account tokens)?

Assessment commands:
```bash
# Check for static token auth on API server (bad)
cat $EVIDENCE/apiserver-static-auth-$(date +%Y%m%d).txt

# Check projected service account token volume mounts
kubectl get pods -A -o json | \
  jq '.items[] | select(.spec.volumes[]?.projected.sources[]?.serviceAccountToken != null) |
      {namespace: .metadata.namespace, name: .metadata.name}' \
  2>&1 | tee $EVIDENCE/projected-tokens-$(date +%Y%m%d).json

# AWS MFA enforcement
aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled' \
  --output text 2>&1 | tee $EVIDENCE/aws-mfa-$(date +%Y%m%d).txt
```

**PASS:** No static token auth on API server. AWS console access requires MFA (IAM policy). Service accounts use projected tokens with short expiry. No `--token-auth-file` on apiserver.

**PARTIAL:** MFA required for AWS console but not enforced by IAM policy. Service accounts mix static and projected tokens.

**FAIL:** `--token-auth-file` present on API server. No MFA requirement for cloud console access. Long-lived static tokens in use.

---

**IA-5 — Authenticator Management**

Questions:
1. Are TLS certificates managed by cert-manager with automatic renewal?
2. Are any certificates expired or within 30 days of expiry?
3. Are secrets (passwords, tokens) rotated on schedule?

Assessment commands:
```bash
# Check cert expiry
cat $EVIDENCE/certificates-ia-$(date +%Y%m%d).json | python3 -c "
import sys, json
from datetime import datetime, timezone
data = [json.loads(line) for line in sys.stdin if line.strip()]
for cert in data:
    expiry = cert.get('expiry')
    if expiry:
        exp_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
        days_left = (exp_dt - datetime.now(timezone.utc)).days
        status = 'OK' if days_left > 30 else ('WARN' if days_left > 7 else 'CRITICAL')
        print(f\"{status}: {cert['namespace']}/{cert['name']} expires in {days_left} days\")
" 2>&1 | tee $EVIDENCE/cert-expiry-check-$(date +%Y%m%d).txt
```

**PASS:** All certificates managed by cert-manager. No certs expire within 30 days. Automatic renewal confirmed. Secrets rotation documented.

**PARTIAL:** Most certs managed by cert-manager. 1-2 manual certs with documented rotation. Some approaching expiry.

**FAIL:** Manual certificate management. Certs expired or < 7 days from expiry. No rotation schedule.

---

## Step 7 — Assess SA-10 / SA-11 / SA-12: System Acquisition

**SA-10 — Developer Configuration Management**

Questions:
1. Are security controls verified in the CI/CD pipeline before deployment?
2. Is there a conftest or OPA gate on manifests?

Assessment commands:
```bash
# Check CI pipeline for security gates
ls GP-CONSULTING/DEVOPS-LENS/01-APP-SEC/03-templates/ci-templates/ 2>&1 | \
  tee $EVIDENCE/sa10-ci-templates-$(date +%Y%m%d).txt

# Check conftest policies
ls GP-CONSULTING/DEVOPS-LENS/01-APP-SEC/01-scanners/conftest/ 2>&1 | \
  tee $EVIDENCE/sa10-conftest-$(date +%Y%m%d).txt
```

**SA-11 — Developer Security Testing**

Questions:
1. Is Semgrep or Bandit running in CI?
2. Are SAST findings reviewed before merge?

Assessment commands:
```bash
cat $EVIDENCE/sa11-semgrep-$(date +%Y%m%d).json | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
errors = data.get('errors', [])
print(f'Semgrep findings: {len(results)}, Errors: {len(errors)}')
high = [r for r in results if r.get('extra', {}).get('severity') in ['ERROR', 'WARNING']]
print(f'High/Error severity: {len(high)}')
" 2>&1 | tee $EVIDENCE/sa11-semgrep-summary-$(date +%Y%m%d).txt
```

**SA-12 — Supply Chain Risk Management**

Assessment commands:
```bash
# cosign verification (from Step 1 above)
cat $EVIDENCE/sa12-cosign-$(date +%Y%m%d).txt

# Trivy SBOM
kubectl get pods -A -o json | jq -r '[.items[].spec.containers[].image] | unique | .[0]' | \
  xargs -I{} trivy image --format cyclonedx --output $EVIDENCE/sa12-sbom-sample.json {} 2>&1
```

| Control | PASS Criteria | FAIL Indicator |
| --- | --- | --- |
| SA-10 | conftest policy gate in CI pipeline | No CI gate on manifests |
| SA-11 | Semgrep/Bandit in CI, findings reviewed | No SAST in pipeline |
| SA-12 | cosign verify passes all prod images | Any prod image unsigned |

---

## Step 8 — Fill BERU Findings

| Control Family | Control Owner | Fixer Route | Rank Range |
| --- | --- | --- | --- |
| RA-3, RA-7 | CompO + CISO | Risk register + SLA definition | B |
| RA-5 | SecEng | Prowler/Kubescape scheduling | C |
| IR-4, IR-8 | IRT + SOC | Responder deployment + IR plan update | C–B |
| CP-9, CP-10 | ITOps + PlatEng | Velero schedule + restore test | C |
| CA-2, CA-7 | CompO | Kubescape + Prowler scheduling | C |
| IA-2, IA-5 | ITOps + CloudSec | MFA policy + cert-manager | C |
| SA-10, SA-11, SA-12 | DevSecOps | CI gates + cosign | D–C |

Reference: `../ssp-examples/<family>-ssp-great.md` for SSP narrative quality.
