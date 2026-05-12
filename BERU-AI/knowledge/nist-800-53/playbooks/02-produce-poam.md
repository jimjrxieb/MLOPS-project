# BERU — Produce POA&M Items

> Input: completed BERU findings (PARTIAL or FAIL status)
> Output: `GP-S3/6-seclab-reports/cybersec-evidence/poam/POAM-YYYY-MM.md`
> Template: `../templates/poam-item.md`
> Audience: BERU (writes the item) + JADE/DevSecOps (executes remediation) + J (approves B/S closures)

---

## When to Run This Playbook

Run after every family audit playbook that produces a PARTIAL or FAIL finding.
Every PARTIAL or FAIL must have a corresponding POA&M item before the audit session closes.

---

## Step 1 — Collect All PARTIAL and FAIL Findings

```bash
POAM_DIR="GP-S3/6-seclab-reports/cybersec-evidence/poam"
mkdir -p $POAM_DIR

# List findings that need POA&M items
ls GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/ | \
  xargs -I{} grep -l "STATUS: PARTIAL\|STATUS: FAIL" \
  GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/{}
```

---

## Step 2 — Assign POA&M IDs

Use sequential IDs within each month: `POAM-YYYY-MM-001`, `POAM-YYYY-MM-002`, etc.

Check the current highest ID in the active POAM file:
```bash
grep "^POAM-ID:" $POAM_DIR/POAM-$(date +%Y-%m).md 2>/dev/null | tail -1
```

---

## Step 3 — Fill the POA&M Template for Each Finding

For each PARTIAL or FAIL finding, open `../templates/poam-item.md` and fill:

**WEAKNESS:** One to three sentences. Name the specific resource, policy, or artifact that is missing.
- Bad: "AC-6 is not fully implemented."
- Good: "Three production service accounts (api-server, worker, scheduler) are bound to the cluster-admin ClusterRole, granting full cluster access. Least privilege scoping to required verbs and resources is not implemented."

**SYSTEM AFFECTED:** Be specific — `cluster: jsa-staging`, `namespace: production`, `AWS account: 123456789`.

**DETECTION DATE:** Use today's date if found during this audit. Use the scanner run date if from automated output.

**DETECTION METHOD:** Exact command that surfaced the finding:
```bash
kubectl get clusterrolebindings -o json | jq '.items[] | select(.roleRef.name == "cluster-admin")'
```

**EVIDENCE PATH:** Where is the evidence file?
```text
GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/2026-05-06-AC/cluster-admin-bindings-20260506.json
```

**SCHEDULED COMPLETION:** Use these guidelines:

| Rank | Max Completion Timeline |
| --- | --- |
| E | 24 hours (auto-fix) |
| D | 72 hours (auto-fix + log) |
| C | 14 days (JADE proposes, human approves) |
| B | 30 days (human decides) |
| S | 90 days (strategy decision) |

**MILESTONES:** Break C-rank and above into 2-3 milestones. First milestone should be within 48-72 hours (scoping or initial action). Last milestone is the validation that BERU confirms.

Example milestones for AC-6 finding:
```text
M1: 2026-05-08 PlatEng scopes cluster-admin SA list, identifies which SAs need it
M2: 2026-05-13 JADE proposes scoped ClusterRole YAML PRs for each SA, J approves
M3: 2026-05-20 PRs merged, BERU re-runs rbac-lookup, confirms zero SAs with cluster-admin
```

**REMEDIATION APPROACH:** Tell JADE or DevSecOps what to do. Reference the fixer script if one exists.

```text
JADE to scope each service account to the minimum verbs required:
  api-server: get, list, watch on pods, services, endpoints
  worker: get, list, watch on nodes, pods
  scheduler: get, list, watch on pods, nodes, persistentvolumeclaims

Fixer: DEVOPS-LENS/02-CLUSTER-HARDEN/02-fixers/rbac/scope-service-account-rbac.sh
Apply via git PR to cluster config repo. ArgoCD will sync.
```

**VALIDATION COMMAND:**
```bash
# After fix is applied:
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.subjects[]?.kind == "ServiceAccount") |
      select(.roleRef.name == "cluster-admin") | .metadata.name'
# Expected output: empty (no service accounts with cluster-admin)
```

---

## Step 4 — Write the POA&M File

Append each new item to the monthly POA&M file:

```bash
cat >> $POAM_DIR/POAM-$(date +%Y-%m).md << 'ITEM'
## POA&M Item [N]
[filled template content]
---
ITEM
```

---

## Step 5 — Route to Remediation Owner

After writing the POA&M item:

1. **D-rank**: Note in finding that auto-fixer will handle. No routing needed.
2. **C-rank**: Route to JADE. Include the POAM-ID and fixer script path.
3. **B-rank**: Package the finding + POA&M item. Escalate to J for decision.
4. **S-rank**: Package for CISO. Do not recommend action. Provide options and risk.

Route format:
```text
JADE: POAM-2026-05-001 is ready for remediation.
  Control: AC-6 — Least Privilege
  Finding: cluster-admin service accounts in production
  Rank: C
  Fixer: DEVOPS-LENS/02-CLUSTER-HARDEN/02-fixers/rbac/scope-service-account-rbac.sh
  Completion target: 2026-05-20
  Validation: see POA&M item POAM-2026-05-001 validation command
```

---

## Step 6 — Close a POA&M Item (BERU Re-Validates)

A POA&M item is CLOSED only after BERU confirms the fix.

```bash
# 1. Re-run the original detection command (from the POA&M DETECTION METHOD)
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.subjects[]?.kind == "ServiceAccount") |
      select(.roleRef.name == "cluster-admin") | .metadata.name'

# 2. Capture the clean output as closure evidence
[command] 2>&1 | tee GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/POAM-2026-05-001-closure-$(date +%Y%m%d).txt

# 3. Update the POA&M status
# STATUS HISTORY:
# 2026-05-06  OPEN — cluster-admin bound to 3 service accounts
# 2026-05-13  IN PROGRESS — PRs submitted for api-server and worker SAs
# 2026-05-20  CLOSED — kubectl confirms zero service accounts with cluster-admin
#             Closure evidence: ...beru-findings/POAM-2026-05-001-closure-20260520.txt
```

---

## POA&M Writing Rules

```text
NEVER leave WEAKNESS vague. Name the resource.
NEVER set SCHEDULED COMPLETION without milestones.
NEVER close a POA&M without running the VALIDATION COMMAND and saving the output.
NEVER mark CLOSED for B/S findings without J sign-off.
NEVER use "TBD" for REMEDIATION OWNER — name the role from control-owner-matrix.md.
```
