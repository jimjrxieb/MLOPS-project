# Claude Fix Session: Falco JSON Output + Local Splunk + Ansible Local Tooling
**Date:** 2026-04-07
**Packages:** 03-RUNTIME-SECURITY, 06-OPTIMIZE
**Cluster:** Portfolio (k3s, Tailscale 100.116.11.56)

---

## Fix 1: Falco JSON Output — Wrong Helm Key (CRITICAL)

**Problem:** Falco on Portfolio was outputting plaintext, not JSON. All SIEM forwarders and dashboards received no data.

**Root cause:** Helm chart 8.0.1 (Falco 0.43.0) uses snake_case config keys. The deploy script used `falco.jsonOutput` (camelCase) which was silently ignored — Falco fell back to `json_output: false` default.

**Fix:**
- `deploy.sh`: Changed `falco.jsonOutput=true` → `falco.json_output=true`
- `deploy.sh`: Changed `falco.httpOutput` → `falco.http_output` (same issue)
- Playbook `02-deploy-falco.md`: Documented snake_case requirement

**Impact:** Without this fix, no scanner data reaches Splunk. Zero SIEM visibility.

**Training signal:** When Helm chart docs use camelCase but the underlying app config uses snake_case, the chart template may not translate — always verify the actual ConfigMap output.

---

## Fix 2: Falco Container Plugin Double-Registration (CRITICAL)

**Problem:** After fixing JSON output, Falco pod CrashLoopBackOff with: `Runtime error: cannot register plugin /usr/share/falco/plugins/libcontainer.so in inspector: found another plugin with name container. Aborting.`

**Root cause:** Two sources loading the container plugin:
1. `falco.yaml` has `load_plugins: [container]` (chart template auto-appends it)
2. `config.d/falco.container_plugin.yaml` baked into the Docker image also loads it

When `falcoctl.artifact.install.enabled=true`, the init container properly handles this. When disabled (e.g., air-gap/no GitHub access), the conflict crashes Falco.

**Fix:** Override `falco.config_files` to skip the problematic config.d file:
```yaml
falco:
  config_files:
    - /etc/falco/config.d/falco.iso8601_timeformat.yaml
    # Exclude: falco.container_plugin.yaml (double-registers plugin)
```

**Impact:** Falco won't start without this when falcoctl is disabled.

**Training signal:** Chart version + image version can have baked-in config that conflicts with Helm-generated config. Always check `config.d/` contents.

---

## Fix 3: falco-siem-forwarder.sh — Subshell Counter Bug

**Problem:** Forwarder reported "Found 13 alerts" but "Forwarded: 0, Errors: 0".

**Root cause:** `echo "$ALERTS" | while read` — the pipe creates a subshell. `FORWARDED` and `ERRORS` variables incremented inside the subshell are lost when it exits.

**Fix:** Changed from pipe to heredoc:
```bash
# Before (broken):
echo "$ALERTS" | while IFS= read -r alert; do ...

# After (fixed):
while IFS= read -r alert; do ...
done <<< "$ALERTS"
```

**Training signal:** Classic Bash gotcha. Never increment counters inside a piped `while` loop.

---

## Fix 4: falco-siem-forwarder.sh — Wrong Index and Sourcetype

**Problem:** Events forwarded to `index: "main"` with `sourcetype: "falco"` — dashboards query `index=idx_gp_security sourcetype="falco:alert"` and find nothing.

**Fix:**
- `index: "main"` → `index: "idx_gp_security"`
- `sourcetype: "falco"` → `sourcetype: "falco:alert"`

**Training signal:** Forwarder output format must match dashboard SPL queries exactly.

---

## Fix 5: Ansible `dry_run` String vs Boolean

**Problem:** Running `ansible-playbook -e dry_run=true` caused: `Conditional result (True) was derived from value of type 'str'`

**Root cause:** CLI `-e` passes strings, not booleans. Ansible strict mode rejects `when: dry_run` when the value is `"true"` (string).

**Fix:** All conditionals changed:
- `when: not dry_run` → `when: not (dry_run | bool)`
- `when: dry_run` → `when: dry_run | bool`

Applied across 4 roles: local_dast, local_splunk, local_loadtest, chaos_mesh.

**Training signal:** Always use `| bool` filter for variables that may come from CLI `-e`.

---

## Fix 6: Ansible `splunk_hec_token` Variable Collision

**Problem:** Local Splunk role's `splunk_hec_token` defaulted to `"gp-local-hec-token-2026"` in role defaults, but `group_vars/all/main.yml` had `splunk_hec_token: ""` (for the remote Splunk integration). Group vars override role defaults → token was always empty.

**Fix:** Renamed role variable to `local_splunk_hec_token` to avoid collision with existing group_vars.

**Training signal:** Ansible variable precedence: group_vars > role defaults. Namespace role-specific variables.

---

## Fix 7: Splunk HEC Uses HTTPS by Default

**Problem:** HEC verify/send tasks used `http://localhost:8088` but Splunk HEC has SSL enabled by default.

**Fix:** All HEC URLs changed to `https://localhost:8088` with `validate_certs: false` (self-signed cert).

**Training signal:** Splunk HEC defaults to HTTPS even in Docker dev containers.

---

## Fix 8: Splunk Dashboard XML — Bare Ampersand

**Problem:** Runtime Security dashboard returned 400 Bad Request: `XML Syntax Error: EntityRef: expecting ';'`

**Root cause:** `MITRE ATT&CK` in a `<title>` element — `&` is invalid in XML without being escaped.

**Fix:** `ATT&CK` → `ATT&amp;CK` in title, and `ATT&CK` → `ATT and CK` in XML comment.

**Training signal:** Always escape `&` in XML content. Even in comments, `&` can break some parsers.

---

## New Ansible Roles Built This Session

### 03-RUNTIME-SECURITY
- `local_splunk` — Splunk Docker container with 5 GP indexes + HEC pre-configured
- `local_dast` — ZAP + Nuclei install locally, runs DAST against cluster endpoint

### 06-OPTIMIZE (full Ansible structure created)
- `preflight` — kubectl, helm, cluster connectivity
- `local_loadtest` — k6/Locust install locally, runs load tests
- `chaos_mesh` — Chaos Mesh/LitmusChaos deploy in-cluster

### Portfolio Inventory
- `03-RUNTIME-SECURITY/ansible/inventories/portfolio.yml`
- `06-OPTIMIZE/ansible/inventories/portfolio.yml`

---

## Working Falco Values for Portfolio k3s (chart 8.0.1)

```yaml
driver:
  kind: modern_ebpf
falco:
  json_output: true
  json_include_output_property: true
  json_include_tags_property: true
  http_output:
    enabled: false
  config_files:
    - /etc/falco/config.d/falco.iso8601_timeformat.yaml
falcoctl:
  artifact:
    install:
      enabled: false
    follow:
      enabled: false
```

## End-to-End Flow (verified working)

```
Portfolio Falco (JSON) → kubectl logs → falco-siem-forwarder.sh → Splunk HEC (localhost:8088) → idx_gp_security → Runtime Security Dashboard
```
