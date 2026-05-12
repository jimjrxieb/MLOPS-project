# BERU — AU Family Audit Playbook

> Audit and Accountability: AU-2, AU-3, AU-6, AU-7, AU-9, AU-12
> Tools: kubectl, Falco, Splunk, CloudTrail, kube-bench
> Audience: BERU (NIST-800-53 internal auditor)
> Read first: `../controls/AU-2.md`, `../controls/AU-3.md`, `../controls/AU-6.md`, `../controls/AU-9.md`, `../controls/AU-12.md`

---

## Inputs That Route Here

- Falco alert log
- kube-apiserver audit log sample
- Splunk dashboard export
- kube-bench output (checks 3.2.x)
- CloudTrail export
- Manual request: "Is our logging compliant?"

---

## Step 1 — Collect Audit Logging Evidence

```bash
EVIDENCE="GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/$(date +%Y-%m-%d)-AU"
mkdir -p $EVIDENCE

# 1a. kube-apiserver audit policy — does it exist?
kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | \
  grep -i "audit" 2>&1 | tee $EVIDENCE/apiserver-audit-config-$(date +%Y%m%d).txt

# 1b. kube-bench audit logging checks
kube-bench run --check 3.2.1,3.2.2 2>&1 | tee $EVIDENCE/kubebench-3.2-$(date +%Y%m%d).txt

# 1c. Audit policy file — if accessible on node
# (k3s: /etc/rancher/k3s/audit-policy.yaml | kubeadm: /etc/kubernetes/audit-policy.yaml)
cat /etc/kubernetes/audit-policy.yaml 2>&1 | tee $EVIDENCE/audit-policy-$(date +%Y%m%d).yaml

# 1d. Falco rules — are they enabled and deployed?
kubectl get daemonset -n falco 2>&1 | tee $EVIDENCE/falco-daemonset-$(date +%Y%m%d).txt
kubectl get configmap -n falco falco-rules -o yaml 2>&1 | tee $EVIDENCE/falco-rules-$(date +%Y%m%d).yaml

# 1e. Splunk — is the GP-Copilot integration running?
kubectl get pods -n splunk 2>&1 | tee $EVIDENCE/splunk-pods-$(date +%Y%m%d).txt

# 1f. Sample audit log entries (last 50 lines)
# Location varies: /var/log/kubernetes/audit.log or K8s DaemonSet log
kubectl logs -n kube-system -l component=kube-apiserver --tail=50 2>&1 | \
  tee $EVIDENCE/apiserver-log-sample-$(date +%Y%m%d).txt
```

For AWS:
```bash
# 1g. CloudTrail — is it enabled in all regions?
aws cloudtrail describe-trails --output json 2>&1 | tee $EVIDENCE/cloudtrail-trails-$(date +%Y%m%d).json

# 1h. Is CloudTrail logging to S3 with integrity validation?
aws cloudtrail get-trail-status --name <trail-name> --output json 2>&1 | \
  tee $EVIDENCE/cloudtrail-status-$(date +%Y%m%d).json
```

---

## Step 2 — Assess AU-2: Event Logging

Read: `../controls/AU-2.md`

Questions to answer:
1. Is an audit policy defined on the kube-apiserver?
2. Does the policy capture the required event types (RequestResponse, Metadata, None by resource)?
3. Are Falco runtime events configured to capture the GP-Copilot event categories?

Assessment criteria from the evidence:
```bash
# From audit-policy.yaml — check for these required rule levels:
# - RequestResponse for secrets, configmaps, serviceaccounts
# - Metadata for all other resources
# - None for health checks (/healthz, /readyz, /livez)

grep -E "level|resources|verbs" $EVIDENCE/audit-policy-$(date +%Y%m%d).yaml
```

Expected structure for PASS:
```yaml
# Must have these at minimum:
- level: RequestResponse
  resources:
  - group: ""
    resources: ["secrets", "configmaps", "serviceaccounts"]
- level: Metadata
  resources:
  - group: ""
    resources: ["*"]
```

**PASS criteria:** Audit policy file exists. RequestResponse level for sensitive resources. Falco DaemonSet running in all nodes. CloudTrail enabled multi-region.

**PARTIAL criteria:** Audit policy exists but uses `level: None` too broadly. Falco deployed but some rules disabled. CloudTrail enabled but not all regions.

**FAIL criteria:** No audit-policy.yaml. kube-bench 3.2.1 FAIL. No Falco. CloudTrail disabled.

---

## Step 3 — Assess AU-3: Content of Audit Records

Read: `../controls/AU-3.md`

Questions to answer:
1. Do audit records contain: who, what, when, where, outcome?
2. Are user identities captured (not just service accounts)?
3. Are source IPs recorded?

Assessment commands:
```bash
# Sample an audit log entry and verify required fields
# Required: user, verb, resource, namespace, responseStatus, requestReceivedTimestamp, sourceIPs
head -5 $EVIDENCE/apiserver-log-sample-$(date +%Y%m%d).txt | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        entry = json.loads(line)
        fields = ['user', 'verb', 'objectRef', 'responseStatus', 'requestReceivedTimestamp', 'sourceIPs']
        for f in fields:
            present = f in entry
            print(f'{f}: {\"PRESENT\" if present else \"MISSING\"}')
        break
    except:
        print('Could not parse log entry as JSON')
"
```

**PASS criteria:** All 6 required fields present in sample entries. User.username is a named identity, not anonymous. sourceIPs captured.

**PARTIAL criteria:** Most fields present but sourceIPs missing or user is always system:serviceaccount.

**FAIL criteria:** Audit log entries missing who, what, or when. Entries are not parseable JSON.

---

## Step 4 — Assess AU-6: Audit Record Review, Analysis, and Reporting

Read: `../controls/AU-6.md`

Questions to answer:
1. Is someone (SOC, platform team) regularly reviewing audit logs?
2. Are Splunk dashboards configured to surface anomalies?
3. Is there a documented review cadence (daily, weekly)?

Evidence to request from SOC:
- Last Splunk saved search or alert configuration showing audit log review
- Documentation of review frequency
- Any tickets/incidents opened from audit log review in last 30 days

```bash
# Check Splunk searches are running
# (this requires Splunk CLI or REST API access)
curl -k -u admin:<password> https://localhost:8089/servicesNS/-/-/saved/searches \
  --get --data "search=index%3Dgp_security" 2>&1 | tee $EVIDENCE/splunk-searches-$(date +%Y%m%d).xml
```

**PASS criteria:** Documented weekly review. Splunk alerts configured on high-severity Falco rules. Evidence of review (tickets, reports) in last 30 days.

**PARTIAL criteria:** Splunk deployed but alerts undocumented. Review happens informally without cadence.

**FAIL criteria:** No log review process. Splunk not deployed. No evidence of any audit log review.

---

## Step 5 — Assess AU-9: Protection of Audit Information

Read: `../controls/AU-9.md`

Questions to answer:
1. Can a regular user or application delete audit logs?
2. Are audit logs stored separately from the system being audited?
3. Is CloudTrail log file validation enabled?

Assessment commands:
```bash
# Who has access to the audit log location?
# Check if any SA has write access to the node filesystem (bad sign)
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.subjects[]?.kind == "ServiceAccount") |
      {binding: .metadata.name, role: .roleRef.name}' 2>&1 | \
  tee $EVIDENCE/sa-clusterrole-bindings-$(date +%Y%m%d).json

# CloudTrail log file validation
aws cloudtrail get-trail-status --name <trail-name> --query 'LatestDeliveryAttemptSucceeded' \
  --output text 2>&1 | tee $EVIDENCE/cloudtrail-validation-$(date +%Y%m%d).txt

# Check S3 bucket policy on CloudTrail bucket (deny public, deny delete)
aws s3api get-bucket-policy --bucket <cloudtrail-bucket> \
  --output json 2>&1 | tee $EVIDENCE/cloudtrail-bucket-policy-$(date +%Y%m%d).json
```

**PASS criteria:** Audit logs in separate index/bucket. S3 bucket policy denies delete without MFA. CloudTrail log file validation enabled. No application SA has write to log locations.

**PARTIAL criteria:** Logs stored but no deletion protection. CloudTrail validation disabled.

**FAIL criteria:** Audit logs stored on the same node filesystem as applications. No write protection. Any application can delete logs.

---

## Step 6 — Assess AU-12: Audit Record Generation

Read: `../controls/AU-12.md`

Questions to answer:
1. Are audit records generated for all AU-2 required events?
2. Is the audit log pipeline continuous (no gaps)?
3. Does Falco actually generate alerts for the event categories it covers?

Assessment commands:
```bash
# kube-bench 3.2.2 — are audit logs being generated?
kube-bench run --check 3.2.2 2>&1 | tee $EVIDENCE/kubebench-3.2.2-$(date +%Y%m%d).txt

# Verify Falco is generating events (look for recent output)
kubectl logs -n falco daemonset/falco --tail=20 2>&1 | tee $EVIDENCE/falco-recent-$(date +%Y%m%d).txt

# Check for any Falco errors indicating dropped events
kubectl logs -n falco daemonset/falco | grep -i "error\|drop\|fail" 2>&1 | \
  tee $EVIDENCE/falco-errors-$(date +%Y%m%d).txt
```

**PASS criteria:** kube-bench 3.2.2 PASS. Falco generating events without drops. Audit log timestamps show continuous coverage (no gaps > 1 minute).

**PARTIAL criteria:** Audit log exists but Falco shows dropped events. Some time gaps in coverage.

**FAIL criteria:** kube-bench 3.2.2 FAIL. Falco not running. Audit log shows multi-hour gaps.

---

## Step 7 — Fill BERU Findings

| Control | Control Owner | Fixer Route | Rank Range |
| --- | --- | --- | --- |
| AU-2 | PlatEng + SOC | audit-policy.yaml PR | C |
| AU-3 | PlatEng | audit-policy content fix | C |
| AU-6 | SOC | Splunk alert config | D–C |
| AU-9 | PlatEng + CloudSec | S3 policy + MFA delete | C–B |
| AU-12 | PlatEng | Falco deployment fix | D–C |

Produce one finding per control using `../templates/beru-finding.md`.
POA&M items required for all PARTIAL and FAIL findings.

Reference: `../ssp-examples/AU-ssp-great.md` for SSP narrative quality standard.
