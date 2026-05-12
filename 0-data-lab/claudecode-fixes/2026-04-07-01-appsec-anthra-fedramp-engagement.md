# Claude Fix Session: 01-APP-SEC Engagement Against Anthra-FedRAMP
**Date:** 2026-04-07
**Package:** 01-APP-SEC
**Target:** GP-PROJECTS/01-instance/slot-3/Anthra-FedRAMP
**Output:** GP-S3/5-consulting-reports/01-instance/slot-3/01-package/

---

## Fix 1: understand-target.sh pipefail crash (CRITICAL)

**Problem:** Script died at step 4/8 with no error message.
**Root cause:** `find ... -exec grep -l ... | wc -l` — grep returns exit 1 when no matches. With `set -euo pipefail`, the pipeline fails silently.
**Fix:** Added `|| true` to CloudFormation and Kubernetes detection find|grep pipelines.
**Training signal:** Any `grep` in a pipeline under `set -eo pipefail` needs `|| true` if zero matches is a valid outcome.

## Fix 2: Output directory structure — unique tags

**Problem:** Multiple scans per day overwrote each other (all named `baseline-YYYYMMDD`).
**Fix:** Added auto-incrementing tag: `{label}-{YYYYMMDD}-{NNN}` (e.g., `01-20260407-001`). Changed `_scanner-common.sh` `setup_output()` to scan for existing dirs and increment.
**Training signal:** Date-only naming fails when running iterative scan-fix-rescan cycles.

## Fix 3: JSON outputs to json-outputs/ subdirectory

**Problem:** Scanner JSONs mixed with markdown reports in same directory.
**Fix:** Added `$JSON_OUTPUT_DIR` variable pointing to `json-outputs/` subdir. Updated all scanner scripts to write there. Updated `auto-fix.sh` to detect `json-outputs/` subdir (backward-compatible with flat structure).
**Training signal:** Separate data (JSON) from reports (markdown) for cleaner engagement artifacts.

## Fix 4: run-all-scanners.sh split output directories

**Problem:** `run-all-scanners.sh` called src + infra scanners which each auto-routed their own output dir, creating two separate directories.
**Fix:** Compute output dir in `run-all-scanners.sh` FIRST, then pass `-o "$OUTPUT_DIR"` to both sub-scripts.

## Fix 5: auto-fix.sh subshell counter bug (REPEAT)

**Problem:** Same piped `while read` subshell bug as falco-siem-forwarder. Counters showed 0 despite fixes applied.
**Fix:** Recount from FIX-REPORT.md file using grep at summary time instead of relying on in-loop counters.

## Fix 6: auto-fix.sh --plan flag doesn't exist

**Problem:** `run-all-scanners.sh` next steps said `--plan` but `auto-fix.sh` uses `--scan-dir`.
**Fix:** Updated the output prompt.

## Fix 7: GP-Copilot/OSS-Copilot artifacts not excluded

**Problem:** Scanners and auto-fix kept processing engagement artifacts (60+ files) as client code.
**Fix:** Added excludes to all scanner scripts (Semgrep, Trivy, Grype, Checkov) and skip logic in auto-fix.sh for `GP-Copilot/`, `OSS-Copilot/`, `MSSP/` paths.

## Fix 8: add-security-context.sh incomplete patching

**Problem:** Fixer reported "FIXED" but only added `allowPrivilegeEscalation: false`. Missing `readOnlyRootFilesystem: true` and `capabilities.drop: [ALL]`. Subsequent runs saw `securityContext:` exists and skipped.
**Fix:** Rewrote container-level logic to check for each required field individually and add what's missing, instead of all-or-nothing.

## Fix 9: kube-bench removed from 01-APP-SEC

**Problem:** kube-bench is a live cluster scanner, not a static code scanner. Errors when run against a repo.
**Fix:** Removed from `run-infra-scanners.sh`. Belongs in 02-CLUSTER-HARDEN.

## Fix 10: tune-falco.sh YAML validation too strict

**Problem:** Falco rule files use `[=]` syntax that Python `yaml.safe_load` rejects as invalid.
**Fix:** Catch `ConstructorError` specifically and allow it (Falco-specific syntax).

## Fix 11: Playbook JSON paths updated

**Problem:** All specialty playbooks (04-05b) referenced `<scan-output>/gitleaks.json` but JSONs now live in `json-outputs/`.
**Fix:** Updated all 6 playbooks to use `<scan-output>/json-outputs/*.json`.

## Fix 12: git-purge-secret.sh missing --force

**Problem:** `git filter-repo` refused to run on non-fresh clone.
**Fix:** Added `--force` flag to the `git filter-repo` command.

## Fix 13: bump-cves.sh github-action support

**Problem:** Script didn't support `github-action` package manager type.
**Fix:** Added `github-action` case that finds workflow files via grep, backs up, and updates the `uses:` version tag.

## Fix 14: Playbook restructure — 05a moved to 06c

**Problem:** 05a-add-conftest-policy was an "add" playbook mixed in with "fix" playbooks.
**Fix:** Renamed to 06c-add-conftest-policy. 05b-fix-supply-chain renamed to 05a-fix-supply-chain.

## New fixers created

- `02-fixers/dockerfile/fix-apt-pin-versions.sh` — DL3008
- `02-fixers/dockerfile/fix-pip-pin-versions.sh` — DL3013

## Playbook updates

- 04-fix-secrets.md — Step 1.5 (live vs history), Step 3 (mapping table)
- 04c-fix-dockerfiles.md — DL3008/DL3013 moved from manual to automated
- 05-fix-k8s-manifests.md — Step 7 (init containers), Step 7a (cross-package escalation table)
- run-all-scanners.sh — Next steps point to specialty playbooks, not auto-fix loop

## Final state: Anthra-FedRAMP 01-APP-SEC

- Source: 25 client findings (git history + .terraform FPs)
- Infra: 134 client findings (mostly CKV_AWS → 04-CLOUD-SECURITY, CKV_K8S → 02-CLUSTER-HARDEN)
- GP-Copilot artifacts: 6 (not client code)
- All auto-fixable 01-APP-SEC findings resolved
- Remaining escalate to other packages
