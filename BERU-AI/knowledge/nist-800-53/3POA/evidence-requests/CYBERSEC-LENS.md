# Evidence Request — CYBERSEC-LENS

```
TO:   SOC / Security Engineer / Cloud Security / GRC Lead (CYBERSEC-LENS)
FROM: 3POA Assessor / CISO Internal Audit
RE:   NIST 800-53 Evidence Collection — Container + Cloud + Compliance Controls
DUE:  48 hours before assessment call
```

This request covers controls implemented in:

- `GP-CONSULTING/CYBERSEC-LENS/03-RUNTIME-SECURITY/` — Container runtime detection (Falco)
- `GP-CONSULTING/CYBERSEC-LENS/04-CLOUD-SECURITY/` — Cloud posture (Prowler, GuardDuty, IAM)
- `GP-CONSULTING/CYBERSEC-LENS/05-COMPLIANCE-READY/` — FedRAMP evidence pipeline
- `GP-CONSULTING/CYBERSEC-LENS/09-CSF-LENS/` — CSF 2.0 IDENTIFY/PROTECT assessments

---

## AC — Access Control

### AC-2 — Account Management (Cloud Layer)

**What to provide**:

- IAM Access Analyzer report for the production AWS account
- Evidence no root access keys exist
- Evidence IAM users have MFA enabled
- Access review for service roles (last 90 days)

**Validation command**:

```bash
# Check root access keys (should return empty):
aws iam get-account-summary --query 'SummaryMap.AccountAccessKeysPresent'
# Run Prowler IAM checks:
prowler aws -c iam_no_root_access_key_task,iam_root_mfa_enabled,iam_user_mfa_enabled_console_access -M json 2>/dev/null
# IAM Access Analyzer findings:
aws accessanalyzer list-findings --analyzer-arn $(aws accessanalyzer list-analyzers --query 'analyzers[0].arn' --output text) \
  --query 'findings[?status==`ACTIVE`].[id,resource,action]' --output table
```

**Evidence artifact**: Prowler JSON output + IAM Access Analyzer findings export

---

### AC-3 — Access Enforcement (Cloud Layer)

**What to provide**:

- AWS SCP (Service Control Policies) for the organization or account
- GuardDuty finding evidence of privilege escalation detection
- Evidence IAM policies follow least privilege (no wildcards on sensitive resources)

**Validation command**:

```bash
# Check for overly permissive IAM policies:
prowler aws -c iam_policy_no_statements_with_admin_access,iam_no_inline_policy_attached -M json 2>/dev/null | \
  python3 -c "import json,sys; data=json.load(sys.stdin); fails=[r for r in data if r.get('status')=='FAIL']; print(f'{len(fails)} failures')"
```

**Evidence artifact**: IAM policy audit + Prowler PASS/FAIL report

---

## AU — Audit and Accountability

### AU-2 — Event Logging (Cloud + Runtime)

**What to provide**:

- CloudTrail trail configuration (all regions, S3 logging enabled, CloudWatch integration)
- Falco alert configuration showing which event types are captured
- Evidence logs are being actively written (sample log entries)

**Validation command**:

```bash
# Verify CloudTrail is active in all regions:
aws cloudtrail get-trail-status --name $(aws cloudtrail list-trails --query 'trailList[0].Name' --output text) \
  --query '[IsLogging, LatestDeliveryTime]'
# Verify Falco is generating events:
journalctl -u falco --since "1 hour ago" | tail -20
# Or from Splunk:
# index=gp_security source=falco | stats count by rule | sort -count | head 10
```

**Evidence artifact**: CloudTrail trail config + sample Falco JSONL alerts

---

### AU-3 — Content of Records

**What to provide**:

- Sample audit log entries showing: timestamp, user/account, action, resource, outcome
- Evidence Splunk captures all required fields
- Evidence logs are searchable and indexed

**Validation command**:

```bash
# Sample CloudTrail record (shows required fields):
aws cloudtrail lookup-events --max-results 5 --query 'Events[*].[EventTime,Username,EventName,Resources[0].ResourceName]' --output table
# Sample Falco record (shows MITRE-tagged events):
cat /var/log/falco/falco_events.json 2>/dev/null | python3 -c "
import json, sys
for line in sys.stdin:
    try:
        e = json.loads(line.strip())
        print(f'{e.get(\"time\")}: [{e.get(\"rule\")}] {e.get(\"output\", \"\")[:80]}')
    except Exception:
        pass
" | head -10
```

**Evidence artifact**: CloudTrail event sample + Falco JSONL with full field set

---

### AU-9 — Audit Record Protection

**What to provide**:

- Evidence CloudTrail S3 bucket has MFA Delete and Object Lock enabled
- Evidence log bucket has no public access
- Evidence audit logs cannot be deleted by the same accounts that generate them

**Validation command**:

```bash
BUCKET=$(aws cloudtrail get-trail --name <trail-name> --query 'Trail.S3BucketName' --output text)
# Check Object Lock:
aws s3api get-object-lock-configuration --bucket $BUCKET
# Check public access block:
aws s3api get-public-access-block --bucket $BUCKET
# Check bucket ACL:
aws s3api get-bucket-acl --bucket $BUCKET
```

**Evidence artifact**: S3 bucket Object Lock config + public access block settings

---

### AU-12 — Audit Record Generation

**What to provide**:

- Falco exporter configuration (metrics export to Prometheus)
- Evidence audit events from all sources reach Splunk
- Splunk source count showing multi-source ingestion

**Validation command**:

```bash
# Check Falco metrics are being scraped:
curl -s http://falco-exporter:9376/metrics | grep falco_events_total
# Check Splunk has multi-source ingestion:
# SPL: index=gp_security | stats count by source | sort -count
```

**Evidence artifact**: Prometheus falco_events_total metric + Splunk source breakdown

---

## CA — Assessment, Authorization, and Monitoring

### CA-7 — Continuous Monitoring

**What to provide**:

- GuardDuty detector configuration and finding statistics
- Prowler scheduled scan configuration
- Splunk dashboard showing real-time security posture

**Validation command**:

```bash
# GuardDuty detector status:
aws guardduty get-detector --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)
# Finding counts by severity:
aws guardduty list-findings --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text) \
  --finding-criteria '{"Criterion": {"severity": {"Gte": 7}}}' --query 'length(FindingIds)'
```

**Evidence artifact**: GuardDuty finding statistics + Prowler HTML/JSON report

---

### CA-8 — Penetration Testing

**What to provide**:

- kube-hunter report from last penetration test
- nuclei DAST scan results
- Evidence that findings were remediated or risk-accepted

**Validation command**:

```bash
# Run kube-hunter (passive mode — no network changes):
kube-hunter --remote <cluster-endpoint> --report json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data.get('vulnerabilities', []):
    print(f'[{v.get(\"severity\",\"?\")}] {v.get(\"vulnerability\",\"?\")} - {v.get(\"description\",\"\")[:60]}')
"
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/artifacts/2026-04-13/` kube-hunter output

---

## CP — Contingency Planning

### CP-10 — System Recovery and Reconstitution

**What to provide**:

- Velero backup schedule configuration
- Evidence of a successful restore test (date, what was restored, result)
- RPO/RTO targets and evidence they were met in the test

**Validation command**:

```bash
velero backup get
velero schedule get
# Show last backup status:
velero backup describe $(velero backup get --output json | python3 -c "import json,sys; bs=json.load(sys.stdin)['items']; print(bs[0]['metadata']['name']) if bs else print('none')") 2>/dev/null
```

**Evidence artifact**: Velero backup log + restore test result (date, status, objects restored)

---

## IA — Identification and Authentication

### IA-2 — Identification and Authentication

**What to provide**:

- OIDC/Dex configuration for Kubernetes API server
- Evidence MFA is required for all human access
- IdP integration configuration (Okta, Azure AD, or Keycloak)

**Validation command**:

```bash
# Check OIDC is configured on kube-apiserver:
kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | grep -E "oidc-issuer-url|oidc-client-id"
# Verify Dex is running:
kubectl get pods -n dex 2>/dev/null || kubectl get pods -n auth | grep dex
```

**Evidence artifact**: kube-apiserver OIDC config + IdP MFA policy screenshot

---

### IA-5 — Authenticator Management

**What to provide**:

- cert-manager certificate rotation schedule
- Evidence service accounts use projected service account tokens (not static)
- Evidence no static bearer tokens exist in production

**Validation command**:

```bash
# Check for expiring certificates:
kubectl get certificates -A -o json | python3 -c "
import json, sys, datetime
data = json.load(sys.stdin)
for c in data['items']:
    exp = c.get('status', {}).get('notAfter', 'unknown')
    name = c['metadata']['name']
    ns = c['metadata']['namespace']
    print(f'{ns}/{name}: expires {exp}')
"
# Verify projected service account tokens:
kubectl get pod -n production -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data['items']:
    for v in p['spec'].get('volumes', []):
        if v.get('projected'):
            print(f'{p[\"metadata\"][\"name\"]}: projected token OK')
            break
"
```

**Evidence artifact**: cert-manager cert expiry report + service account token config

---

## IR — Incident Response

### IR-4 — Incident Handling

**What to provide**:

- Falco responder scripts and their automation rank (E/D/C)
- Evidence at least one automated response was triggered in the last 30 days
- Incident response playbook reference (03-RUNTIME-SECURITY responders)

**Validation command**:

```bash
# List active responders:
ls GP-CONSULTING/CYBERSEC-LENS/03-RUNTIME-SECURITY/responders/
cat GP-CONSULTING/CYBERSEC-LENS/03-RUNTIME-SECURITY/responders/CAPABILITIES.md
# Show recent Falco-triggered response log:
cat /var/log/falco-responder.log 2>/dev/null | tail -20
```

**Evidence artifact**: Responder script inventory + triggered response log entries

---

### IR-5 — Incident Monitoring

**What to provide**:

- Splunk dashboard for incident tracking
- GuardDuty finding trends (30-day graph)
- Evidence incidents are tracked from detection to closure

**Validation command**:

```bash
# GuardDuty active findings:
aws guardduty list-findings --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text) \
  --query 'length(FindingIds)' --output text
# Splunk: index=gp_security | timechart count by severity span=1d
```

**Evidence artifact**: GuardDuty findings export + Splunk timechart screenshot

---

### IR-6 — Incident Reporting

**What to provide**:

- Chain-of-custody documentation for the last incident
- Evidence incident reports were sent to the required parties
- Incident log with dates, actions taken, and outcome

**Validation command**:

```bash
# Show chain-of-custody template:
cat GP-S3/6-seclab-reports/cybersec-evidence/incident-response/chain-of-custody.md
# List forensic collection artifacts:
ls GP-S3/6-seclab-reports/cybersec-evidence/incident-response/
```

**Evidence artifact**: Completed chain-of-custody form for last incident

---

## RA — Risk Assessment

### RA-2 — Security Categorization

**What to provide**:

- scan-and-map.py output showing control-to-finding mapping
- Evidence the system has a documented FIPS 199 categorization (if FedRAMP)
- Risk categorization for each finding type

**Validation command**:

```bash
python3 GP-CONSULTING/CYBERSEC-LENS/05-COMPLIANCE-READY/tools/scan-and-map.py \
  --input GP-S3/6-seclab-reports/devops-evidence/scans/ \
  --output /tmp/ra2-control-map.json
cat /tmp/ra2-control-map.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Controls with findings: {len(data)}')
for ctrl, findings in list(data.items())[:5]:
    print(f'  {ctrl}: {len(findings)} findings')
"
```

**Evidence artifact**: scan-and-map.py JSON output

---

### RA-5 — Vulnerability Scanning (Cloud Layer)

**What to provide**:

- Prowler scan results with PASS/FAIL counts
- Evidence that FAIL items are tracked in POA&M
- Evidence that scanning runs on a schedule (not just once)

**Validation command**:

```bash
prowler aws -M json --output-filename /tmp/ra5-prowler.json 2>/dev/null &
# While running, show last scan stats:
ls -la /tmp/prowler*.json 2>/dev/null | head -5
```

**Evidence artifact**: Prowler JSON report in `GP-S3/6-seclab-reports/cybersec-evidence/`

---

## SC — System and Communications Protection

### SC-7 — Boundary Protection (Cloud Layer)

**What to provide**:

- VPC Security Group configuration for production
- Evidence no security group allows 0.0.0.0/0 ingress on sensitive ports
- Evidence AWS Network Firewall or equivalent is deployed

**Validation command**:

```bash
# Check for overly permissive security groups:
prowler aws -c ec2_securitygroup_allow_ingress_from_internet_to_all_ports,\
ec2_securitygroup_allow_ingress_from_internet_to_port_22,\
ec2_securitygroup_allow_ingress_from_internet_to_port_3389 -M json 2>/dev/null | head -30
```

**Evidence artifact**: Prowler security group check output + VPC flow log sample

---

### SC-8 — Transmission Confidentiality (Cloud Layer)

**What to provide**:

- AWS Certificate Manager certificate list
- Evidence all load balancers use HTTPS listeners
- Evidence S3 buckets have SSL enforcement bucket policy

**Validation command**:

```bash
# Check for HTTP listeners on ALBs:
prowler aws -c elb_ssl_listeners,elbv2_ssl_policy_configured -M json 2>/dev/null | head -20
# Check S3 SSL enforcement:
prowler aws -c s3_bucket_ssl_requests_only -M json 2>/dev/null | head -20
```

**Evidence artifact**: ACM certificate list + Prowler HTTPS check results

---

### SC-12 — Cryptographic Key Management (Cloud Layer)

**What to provide**:

- AWS KMS key configuration for production resources
- Evidence EKS secrets are encrypted with a customer-managed KMS key
- Evidence RDS/S3 encryption uses CMK (not AWS-managed)
- Key rotation policy (annual minimum)

**Validation command**:

```bash
# Check KMS key rotation:
aws kms list-keys --query 'Keys[*].KeyId' --output text | tr '\t' '\n' | while read key; do
  rotation=$(aws kms get-key-rotation-status --key-id $key --query 'KeyRotationEnabled' --output text 2>/dev/null)
  desc=$(aws kms describe-key --key-id $key --query 'KeyMetadata.Description' --output text 2>/dev/null)
  echo "$key ($desc): rotation=$rotation"
done
```

**Evidence artifact**: KMS key list with rotation status + EKS encryption config

---

### SC-17 — Public Key Infrastructure Certificates

**What to provide**:

- cert-manager ClusterIssuer configuration
- Evidence certificates are short-lived (90 days or less)
- Evidence certificate renewal is automated

**Validation command**:

```bash
kubectl get clusterissuer -A -o yaml
kubectl get certificates -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for c in data['items']:
    duration = c['spec'].get('duration', 'default')
    renew_before = c['spec'].get('renewBefore', 'default')
    print(f'{c[\"metadata\"][\"name\"]}: duration={duration}, renewBefore={renew_before}')
"
```

**Evidence artifact**: cert-manager Certificate manifests + renewal events from cert-manager logs

---

### SC-23 — Session Authenticity

**What to provide**:

- OIDC token expiry configuration
- Evidence sessions use short-lived tokens (not long-lived API keys)
- Evidence service-to-service auth uses workload identity (not static secrets)

**Validation command**:

```bash
# Check OIDC token TTL in Dex config:
kubectl get configmap -n dex dex-config -o yaml 2>/dev/null | grep -A5 expiry
# Check that no long-lived kubeconfig tokens exist in secrets:
kubectl get secrets -A -o json | python3 -c "
import json, sys, base64
data = json.load(sys.stdin)
for s in data['items']:
    if s['type'] == 'kubernetes.io/service-account-token':
        print(f'Static SA token: {s[\"metadata\"][\"namespace\"]}/{s[\"metadata\"][\"name\"]}')
" | head -10
```

**Evidence artifact**: OIDC token TTL config + Dex/IdP session policy

---

### SC-28 — Protection at Rest (Cloud Layer)

**What to provide**:

- Evidence all S3 buckets have default encryption
- Evidence RDS instances use encryption at rest
- Evidence EBS volumes are encrypted

**Validation command**:

```bash
prowler aws -c s3_bucket_default_encryption,\
rds_instance_storage_encrypted,\
ec2_ebs_default_encryption -M json 2>/dev/null | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data:
    if r.get('status') == 'FAIL':
        print(f'FAIL: {r.get(\"check_id\")} - {r.get(\"resource_arn\", r.get(\"resource_id\"))}')
"
```

**Evidence artifact**: Prowler encryption check output + KMS key usage report

---

## SI — System and Information Integrity

### SI-3 — Malicious Code Protection (Runtime)

**What to provide**:

- Falco rule file list showing coverage
- Evidence that malicious code detection events trigger alerts
- Splunk dashboard showing Falco detection statistics

**Validation command**:

```bash
# List all active Falco rule files and their count:
ls /etc/falco/rules.d/
grep -c "^- rule:" /etc/falco/rules.d/*.yaml 2>/dev/null | sort -t: -k2 -nr
# Total rules loaded:
falco --list 2>/dev/null | wc -l
```

**Evidence artifact**: Falco rule file list + count + sample alert events in Splunk

---

### SI-4 — System Monitoring (Cloud + Runtime)

**What to provide**:

- GuardDuty integration with Security Hub
- CloudWatch alarm configuration for security events
- Falco → Splunk pipeline configuration

**Validation command**:

```bash
# Security Hub enabled:
aws securityhub get-enabled-standards --query 'StandardsSubscriptions[*].StandardsSubscriptionArn' --output table
# GuardDuty → Security Hub integration:
aws securityhub list-enabled-product-subscriptions --query 'ProductSubscriptions' --output table
# CloudWatch security alarms:
aws cloudwatch describe-alarms --alarm-name-prefix Security --query 'MetricAlarms[*].[AlarmName,StateValue]' --output table
```

**Evidence artifact**: Security Hub standards list + GuardDuty finding counts + CloudWatch alarm config

---

### SI-7 — Software Integrity (Runtime)

**What to provide**:

- Falco rules for file integrity monitoring
- Evidence drift detection is running
- At least one integrity violation alert from the last 30 days (or evidence none occurred)

**Validation command**:

```bash
# Show Falco file integrity rules:
grep -r "write_below_etc\|modify_binary_dirs\|read_sensitive_file" /etc/falco/rules.d/ | head -10
# Check drift detection script:
cat GP-CONSULTING/CYBERSEC-LENS/03-RUNTIME-SECURITY/tools/drift-detector.sh 2>/dev/null | head -20
```

**Evidence artifact**: Falco FIM alert log + drift-detector.sh run output

---

### SI-10 — Information Input Validation

**What to provide**:

- WAF configuration if deployed
- Evidence input validation exists at API ingress
- Nuclei scan results for injection vulnerabilities

**Validation command**:

```bash
# AWS WAF rules:
aws wafv2 list-web-acls --scope REGIONAL --query 'WebACLs[*].[Name,DefaultAction]' --output table 2>/dev/null
# Recent nuclei DAST results:
ls GP-S3/6-seclab-reports/devops-evidence/artifacts/2026-04-14/dast/
```

**Evidence artifact**: `GP-S3/6-seclab-reports/devops-evidence/artifacts/2026-04-14/dast/` nuclei results

---

## FedRAMP Pipeline Validation

If this engagement is FedRAMP-scoped, run the full compliance pipeline and
provide the output tarball:

```bash
bash GP-CONSULTING/CYBERSEC-LENS/05-COMPLIANCE-READY/tools/run-fedramp-scan.sh
python3 GP-CONSULTING/CYBERSEC-LENS/05-COMPLIANCE-READY/tools/scan-and-map.py
python3 GP-CONSULTING/CYBERSEC-LENS/05-COMPLIANCE-READY/tools/gap-analysis.py
bash GP-CONSULTING/CYBERSEC-LENS/05-COMPLIANCE-READY/tools/package-evidence.sh
```

**Deliverable**: `/tmp/fedramp-evidence-<date>.tar.gz` — submit this to the assessor directly.
The tarball contains: scan results mapped to controls, gap analysis with risk scores, and
the CSF-LENS POA&M generated by `gap-to-poam.py`.
