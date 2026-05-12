# BERU — SI Family Audit Playbook

> System and Information Integrity: SI-2, SI-3, SI-4, SI-7
> Tools: Trivy, Grype, Falco, cosign, Kyverno, Semgrep
> Audience: BERU (NIST-800-53 internal auditor)
> Read first: `../controls/SI-2.md`, `../controls/SI-3.md`, `../controls/SI-4.md`, `../controls/SI-7.md`

---

## Inputs That Route Here

- Trivy image scan output (CVEs → SI-2, unsigned images → SI-7)
- Grype scan output
- Falco alert (runtime event → SI-4)
- cosign verification failure (→ SI-7)
- Semgrep SAST finding
- kube-bench output referencing image policies

---

## Step 1 — Collect System Integrity Evidence

```bash
EVIDENCE="GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/$(date +%Y-%m-%d)-SI"
mkdir -p $EVIDENCE

# 1a. Trivy image scan — all running images
kubectl get pods -A -o json | \
  jq -r '[.items[].spec.containers[].image] | unique[]' | \
  while read image; do
    safe=$(echo $image | tr '/:' '--')
    trivy image --format json --output $EVIDENCE/trivy-$safe-$(date +%Y%m%d).json $image 2>&1
  done

# 1b. Trivy summary — HIGH and CRITICAL CVEs across all images
kubectl get pods -A -o json | jq -r '[.items[].spec.containers[].image] | unique[]' | \
  while read image; do
    result=$(trivy image --severity HIGH,CRITICAL --format table $image 2>&1)
    if echo "$result" | grep -q "Total:"; then
      echo "=== $image ==="
      echo "$result" | grep "Total:"
    fi
  done 2>&1 | tee $EVIDENCE/trivy-cve-summary-$(date +%Y%m%d).txt

# 1c. Image signature verification — cosign
kubectl get pods -A -o json | jq -r '[.items[].spec.containers[].image] | unique[]' | \
  while read image; do
    echo -n "Image: $image → "
    cosign verify --certificate-identity-regexp ".*" \
      --certificate-oidc-issuer-regexp ".*" $image 2>&1 | head -1
  done 2>&1 | tee $EVIDENCE/cosign-verify-$(date +%Y%m%d).txt

# 1d. Kyverno image signature policy — is it enforced?
kubectl get clusterpolicies -o json | \
  jq '.items[] | select(.metadata.name | test("image|signature|sign"; "i")) |
      {name: .metadata.name, mode: .spec.validationFailureAction}' \
  2>&1 | tee $EVIDENCE/kyverno-image-policies-$(date +%Y%m%d).json

# 1e. Falco — is it running and generating alerts?
kubectl get daemonset -n falco 2>&1 | tee $EVIDENCE/falco-status-$(date +%Y%m%d).txt
kubectl logs -n falco daemonset/falco --tail=50 2>&1 | tee $EVIDENCE/falco-recent-$(date +%Y%m%d).txt

# 1f. Falco rules coverage — how many rules are loaded?
kubectl get configmap -n falco falco-rules -o json | \
  jq -r '.data | to_entries[0].value' | grep -c "^- rule:" 2>&1 | \
  tee $EVIDENCE/falco-rule-count-$(date +%Y%m%d).txt

# 1g. Unpinned images (latest tag or no digest)
kubectl get pods -A -o json | \
  jq '.items[] | .spec.containers[] | select(.image | test(":latest$|^[^:]+$")) |
      {pod: .name, image: .image}' \
  2>&1 | tee $EVIDENCE/unpinned-images-$(date +%Y%m%d).json

# 1h. Semgrep SAST — run against application source if available
semgrep --config=auto --output $EVIDENCE/semgrep-$(date +%Y%m%d).json \
  --json /path/to/app/source 2>&1
```

---

## Step 2 — Assess SI-2: Flaw Remediation

Read: `../controls/SI-2.md`

Questions to answer:
1. Are HIGH and CRITICAL CVEs tracked and remediated within an SLA?
2. Is there a documented patch cycle (e.g., CRITICAL ≤ 7 days, HIGH ≤ 30 days)?
3. Are node/OS packages patched?

Assessment commands:
```bash
# Count HIGH and CRITICAL CVEs by image
python3 - <<'EOF'
import os, json, glob
evidence_dir = "$EVIDENCE"
total_high = 0
total_critical = 0
images_with_issues = []

for f in glob.glob(f"{evidence_dir}/trivy-*-*.json"):
    try:
        with open(f) as fh:
            data = json.load(fh)
        for result in data.get('Results', []):
            for vuln in result.get('Vulnerabilities', []):
                if vuln.get('Severity') == 'CRITICAL':
                    total_critical += 1
                elif vuln.get('Severity') == 'HIGH':
                    total_high += 1
    except:
        pass

print(f"Total CRITICAL CVEs across all images: {total_critical}")
print(f"Total HIGH CVEs across all images: {total_high}")
EOF
```

Ask the control owner: "What is your SLA for remediating CRITICAL CVEs? Show me the last CRITICAL CVE that was fixed and the timeline from detection to remediation."

**PASS criteria:** Documented patch SLA (CRITICAL ≤ 7 days, HIGH ≤ 30 days). Trivy integrated in CI (blocks merge on CRITICAL). Zero unpatched CRITICAL CVEs older than 7 days. Evidence of recent patch activity.

**PARTIAL criteria:** Trivy runs but does not block merges. CRITICAL CVEs exist with remediation tickets showing progress. SLA documented but not enforced automatically.

**FAIL criteria:** No CVE scanning. CRITICAL CVEs older than 30 days with no remediation activity. No patch SLA. Images using `:latest` with no digest pinning.

---

## Step 3 — Assess SI-3: Malicious Code Protection

Read: `../controls/SI-3.md`

Questions to answer:
1. Is Falco deployed and protecting all nodes?
2. Are Falco rules tuned to detect the relevant threat categories?
3. Is the Falco → Splunk pipeline operational (alerts not silently dropping)?

Assessment commands:
```bash
# Verify Falco DaemonSet is running on all nodes
kubectl get daemonset -n falco -o json | \
  jq '{desired: .status.desiredNumberScheduled, ready: .status.numberReady}' \
  2>&1 | tee $EVIDENCE/falco-coverage-$(date +%Y%m%d).json

# Check Falco rule categories are loaded
kubectl exec -n falco daemonset/falco -- falco --list | grep -c "rule:" 2>&1 | \
  tee $EVIDENCE/falco-loaded-rules-$(date +%Y%m%d).txt

# Test Falco is alerting — trigger a known-safe test event
kubectl run test-falco --image=alpine --restart=Never -- \
  sh -c "cat /etc/shadow" 2>&1 || true
sleep 5
kubectl logs -n falco daemonset/falco --tail=10 | grep "test-falco" 2>&1 | \
  tee $EVIDENCE/falco-test-alert-$(date +%Y%m%d).txt
kubectl delete pod test-falco 2>/dev/null || true

# Check Splunk is receiving Falco events
# (query: index=gp_security source=falco | head 5)
```

**PASS criteria:** Falco DaemonSet: `desired == ready` on all nodes. Rule count > 50. Test event generates alert. Splunk shows recent Falco events (< 24 hours old).

**PARTIAL criteria:** Falco deployed but not on all nodes. Rules loaded but Splunk integration not confirmed. Alerts generated but not routed.

**FAIL criteria:** Falco not deployed. No runtime threat detection. Falco deployed but showing errors/dropped events. No path from alert to SOC.

---

## Step 4 — Assess SI-4: System Monitoring

Read: `../controls/SI-4.md`

Questions to answer:
1. Are Falco alerts routed to the SOC (Splunk)?
2. Are there automated responders for high-severity events?
3. Is there a documented monitoring scope (what is monitored, what is not)?

Assessment commands:
```bash
# Check for Falco responder scripts
ls GP-CONSULTING/CYBERSEC-LENS/03-RUNTIME-SECURITY/ 2>&1 | tee $EVIDENCE/responder-inventory-$(date +%Y%m%d).txt

# Check Splunk dashboard for GP-Copilot security events
# (Splunk REST API or GUI export)
# Expected: index=gp_security | stats count by source | table source, count

# Check if automated responder is deployed
kubectl get cronjob -A | grep -i "responder\|falco\|incident" 2>&1 | \
  tee $EVIDENCE/responder-cronjobs-$(date +%Y%m%d).txt

# Kubescape MITRE ATT&CK coverage — how well is the cluster monitored?
kubescape scan framework mitre --format json \
  --output $EVIDENCE/kubescape-mitre-$(date +%Y%m%d).json 2>&1
```

**PASS criteria:** Falco → Splunk pipeline confirmed with recent events. Automated responder deployed for at least CRITICAL alerts. MITRE ATT&CK coverage ≥ 60% via Kubescape. Monitoring scope documented.

**PARTIAL criteria:** Splunk deployed but not all Falco rules routed. Responder scripts exist but not automated (manual trigger only).

**FAIL criteria:** No SIEM integration. Falco alerts go nowhere. No automated response. No monitoring scope documentation.

---

## Step 5 — Assess SI-7: Software, Firmware, and Information Integrity

Read: `../controls/SI-7.md`

Questions to answer:
1. Are container images signed with cosign?
2. Does Kyverno enforce image signature verification at admission?
3. Are there unsigned images currently running in production?

Assessment commands:
```bash
# Check cosign verification results (from Step 1)
cat $EVIDENCE/cosign-verify-$(date +%Y%m%d).txt | grep -c "FAIL\|Error" 2>&1
cat $EVIDENCE/cosign-verify-$(date +%Y%m%d).txt | grep "FAIL\|Error" 2>&1

# Kyverno image signature policy enforcement mode
cat $EVIDENCE/kyverno-image-policies-$(date +%Y%m%d).json

# SI-7 kube-bench check (5.2.4 — images from authorized registries)
kube-bench run --check 5.2.4 2>&1 | tee $EVIDENCE/kubebench-5.2.4-$(date +%Y%m%d).txt

# Check all images come from an approved registry
kubectl get pods -A -o json | \
  jq -r '.items[].spec.containers[].image' | sort -u | \
  grep -v "^registry.k8s.io\|^gcr.io\|^docker.io/library\|^ghcr.io\|^<your-approved-registry>" \
  2>&1 | tee $EVIDENCE/unapproved-registry-images-$(date +%Y%m%d).txt
```

**PASS criteria:** cosign signatures verified on all production images. Kyverno image signature policy in Enforce mode. Zero images from unapproved registries in production. kube-bench 5.2.4 PASS.

**PARTIAL criteria:** cosign policy in Audit mode (not Enforce). Some production images unsigned but tracked. Registry allowlist policy exists.

**FAIL criteria:** No cosign or image signature verification. Kyverno image policy absent or in Audit mode. Images pulled from unapproved/unknown registries.

---

## Step 6 — Fill BERU Findings

| Control | Control Owner | Fixer Route | Rank Range |
| --- | --- | --- | --- |
| SI-2 | DevSecOps | Trivy CI gate + base image update PR | D–C |
| SI-3 | SecEng | Falco DaemonSet deployment | C |
| SI-4 | SOC + SecEng | Falco→Splunk pipeline + responders | C |
| SI-7 | DevSecOps + PlatEng | cosign + Kyverno image signature policy | C–B |

Reference: `../ssp-examples/SI-ssp-great.md` for SSP narrative quality standard.
