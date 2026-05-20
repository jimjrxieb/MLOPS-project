#!/usr/bin/env python3
"""
Katie 3B Corpus Curator — Clean, Filter, Deduplicate
=====================================================
Reads all trained chunks from 04-trained-data/v1.1-3b/ and produces a single
clean corpus file, filtering out known contamination patterns.

Katie's scope: CKA, CKS, CKAD, CNPA — autonomous Kubernetes & cloud networking engineer.

Filters applied:
  1. FORMAT: Only ChatML format (messages array). Drop Alpaca (instruction/input/output).
  2. GARBAGE: Raw JSON scan logs as assistant responses
  3. GARBAGE: [CORRECTION] / [NEEDS CORRECTION] / "Unable to provide specific correction"
  4. GARBAGE: Nested JSON inception (assistant outputs another training example)
  5. BLOAT: YouTube transcript fragments
  6. BLOAT: Chitchat / filler ("Nice work!", "I'm listening", "Appreciate that")
  7. BLOAT: "What is security analysis?" + JSON dump pattern
  8. BLOAT: Python GUI / unrelated programming tutorials
  9. DEDUP: Exact-match deduplication on user+assistant content
  10. DEDUP: Near-duplicate detection (same assistant response, different question phrasing)
  11. SCOPE: Flag examples outside CKA/CKS/CKAD/CNPA scope (kept in separate file)
  12. QUALITY: Drop examples with assistant response < 50 chars (stub answers)
  13. QUALITY: Drop examples where assistant starts with raw JSON '{' or '['

Usage:
    python3 tools/curate_corpus.py                        # Full run with stats
    python3 tools/curate_corpus.py --dry-run               # Preview without writing
    python3 tools/curate_corpus.py --output clean.jsonl     # Custom output path
    python3 tools/curate_corpus.py --skip-chunks 10,11,12   # Skip known-bad chunks
"""

import json
import hashlib
import re
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
TRAINED_DIR = BASE_DIR / "04-trained-data" / "v1.1-3b"
OUTPUT_DIR = BASE_DIR / "05-data-quality" / "curated"
REPORTS_DIR = Path("/home/jimmie/linkops-industries/GP-copilot/GP-S3/3-mlops-reports/4-curation")

# ── Chunks to skip entirely (audit verdict: DROP) ─────────────────────────
DROP_CHUNKS = {10, 11, 12, 21, 22, 23, 24, 27, 31, 32, 33, 37, 42, 43}

# ── Scope keywords for Katie's domain ─────────────────────────────────────
# CKA: cluster architecture, workloads, services, networking, storage, troubleshooting
CKA_KEYWORDS = [
    "etcd", "kubeadm", "kube-apiserver", "kube-scheduler", "kube-controller-manager",
    "kubelet", "kube-proxy", "static pod", "staticpod", "controlplane", "control plane",
    "control-plane", "worker node", "cluster upgrade", "kubeadm upgrade",
    "pv ", "pvc", "persistentvolume", "storageclass", "storage class",
    "statefulset", "daemonset", "deployment", "replicaset", "job ", "cronjob",
    "rolling update", "rollout", "drain", "cordon", "uncordon", "taint", "toleration",
    "affinity", "nodeaffinity", "podaffinity", "nodeselector", "node selector",
    "scheduler", "scheduling", "preemption", "priorityclass",
    "configmap", "secret", "serviceaccount", "service account",
    "clusterrole", "rolebinding", "kubectl", "jsonpath", "custom-columns",
    "etcd backup", "etcd restore", "etcd snapshot", "snapshot save", "snapshot restore",
    "certificate", "csr", "certificatesigningrequest", "openssl",
    "node notready", "not ready", "crashloopbackoff", "crashloop", "imagepullbackoff",
    "oomkilled", "pending", "evicted", "disk pressure", "diskpressure",
    "memory pressure", "pid pressure", "ephemeral", "debug container",
    "hpa", "horizontalpodautoscaler", "vpa", "metrics-server",
    "ingress", "ingressclass", "service type", "clusterip", "nodeport", "loadbalancer",
    "endpoint", "endpointslice", "coredns", "dns",
    "namespace", "resourcequota", "limitrange",
    "init container", "initcontainer", "sidecar", "multi-container",
    "volume", "emptydir", "hostpath", "projected volume", "downwardapi",
    "liveness", "readiness", "startup probe", "probe",
    "helm", "helm chart", "helm install", "helm upgrade", "values.yaml",
]

# CKS: cluster setup, system hardening, minimize microservice vulns, supply chain, monitoring, runtime
CKS_KEYWORDS = [
    "networkpolicy", "network policy", "podsecuritypolicy", "psp",
    "podsecuritystandard", "pss", "podsecurityadmission", "psa",
    "securitycontext", "security context", "runasnonroot", "runasuser",
    "readonlyrootfilesystem", "readonly root", "allowprivilegeescalation",
    "capabilities", "drop all", "seccomp", "apparmor", "selinux",
    "rbac", "role-based", "clusterrole", "rolebinding", "least privilege",
    "audit", "audit policy", "audit log", "audit.log",
    "falco", "runtime security", "syscall", "behavioral",
    "trivy", "grype", "cosign", "notary", "sbom", "image signing", "image digest",
    "opa", "rego", "gatekeeper", "kyverno", "admission controller", "validatingwebhook",
    "mutatingwebhook", "admission webhook",
    "cis benchmark", "kube-bench", "kubescape", "polaris",
    "encryption at rest", "encryptionconfiguration", "etcd encryption",
    "tls", "mtls", "certificate", "secret management",
    "pod security", "container security", "image security", "supply chain",
    "sandbox", "gvisor", "kata", "runtimeclass",
    "cilium", "calico", "network plugin",
    "serviceaccount token", "automountserviceaccounttoken",
    "privilege escalation", "privileged", "hostpid", "hostipc", "hostnetwork",
    "hostpath", "docker.sock",
    "vulnerability scan", "cve", "sast", "dast",
    "distroless", "scratch", "nonroot", "user 1000",
    "restrict", "baseline", "privileged",
]

# CKAD: app design, build, deploy, observe, services/networking
CKAD_KEYWORDS = [
    "deployment strategy", "recreate", "rolling update", "blue-green", "canary",
    "multi-container", "sidecar", "ambassador", "adapter",
    "configmap", "secret", "env var", "envfrom", "volumemount",
    "liveness probe", "readiness probe", "startup probe", "httpget", "tcpsocket", "exec",
    "resource request", "resource limit", "requests.cpu", "limits.memory",
    "job ", "cronjob", "completions", "parallelism", "backofflimit",
    "label", "selector", "annotation", "matchlabels",
    "service", "clusterip", "nodeport", "loadbalancer", "headless",
    "ingress", "ingressclass", "path type", "pathtype",
    "pvc", "persistentvolumeclaim", "accessmodes", "storageclassname",
    "helm", "chart", "values", "template",
    "kubectl create", "kubectl run", "kubectl expose", "kubectl set image",
    "kubectl rollout", "kubectl scale", "kubectl autoscale",
    "dockerfile", "containerport", "workdir", "entrypoint", "cmd",
    "observability", "logging", "monitoring", "tracing",
    "pod design", "pod lifecycle", "restartpolicy",
    "networkpolicy", "port", "targetport",
    "securitycontext", "serviceaccount",
    "custom resource", "crd", "operator",
    "emptydir", "projected", "downward api",
]

# CNPA: Cloud Native Platform Associate — networking, CNI, service mesh, platform eng, IaC, observability
CNPA_KEYWORDS = [
    "vpc", "subnet", "cidr", "routing table", "route table",
    "security group", "nacl", "network acl", "firewall rule",
    "nat gateway", "internet gateway", "transit gateway", "vpc peering",
    "privatelink", "private link", "endpoint service",
    "load balancer", "alb", "nlb", "elb", "target group",
    "dns", "route53", "coredns", "external-dns", "corefile",
    "cni", "calico", "cilium", "flannel", "weave", "multus",
    "ebpf", "iptables", "ipvs", "nftables", "conntrack",
    "service mesh", "istio", "linkerd", "envoy", "sidecar proxy",
    "mTLS", "mutual tls", "zero trust network",
    "gateway api", "gatewayclass", "httproute", "tcproute",
    "network policy", "networkpolicy", "ingress rule", "egress rule",
    "pod-to-pod", "pod to pod", "cluster networking", "pod networking",
    "kube-proxy", "ipvs mode", "iptables mode",
    "bandwidth", "latency", "throughput", "qos",
    "cloud networking", "aws networking", "gcp networking", "azure networking",
    "vxlan", "geneve", "wireguard", "ipsec", "tunnel",
    "bgp", "bird", "routing", "peering",
    "ingress controller", "nginx ingress", "traefik", "haproxy",
    "ssl termination", "tls termination", "certificate manager", "cert-manager",
    "network troubleshoot", "tcpdump", "nslookup", "dig", "traceroute",
    "network debug", "connectivity", "packet",
    # Platform engineering (broader CNPA scope)
    "backstage", "kratix", "crossplane", "xrd", "composition",
    "platform engineering", "internal developer", "idp", "golden path",
    "keda", "knative", "dapr", "score",
    "cluster api", "vcluster", "rancher", "multi-cluster",
    "terraform", "pulumi", "cdk", "kustomize", "helmfile",
    "applicationset", "app of apps",
    # Observability
    "prometheus", "grafana", "loki", "tempo", "opentelemetry", "otel",
    "alertmanager", "promql", "servicemonitor", "podmonitor",
    "jaeger", "zipkin", "distributed tracing",
    # Container runtime
    "containerd", "cri-o", "oci", "buildkit", "podman",
    # Storage
    "csi", "rook", "ceph", "longhorn", "volume snapshot",
]

# Operational (keep — Katie needs this for 2AM autonomy)
OPS_KEYWORDS = [
    "argocd", "argo cd", "gitops", "self-heal", "app sync",
    "rank", "e-rank", "d-rank", "c-rank", "b-rank", "s-rank",
    "incident", "2am", "2 am", "on-call", "oncall", "pager",
    "remediat", "remediation", "auto-fix", "autofix",
    "finding", "scan result", "triage", "escalat",
    "drift", "ownership", "kubectl patch",
    "playbook", "runbook", "sop",
    "falco alert", "runtime alert",
    "jsa", "jade", "katie",
]

# Out-of-scope patterns (flag for separate file)
OUT_OF_SCOPE_PATTERNS = [
    r"sql injection",
    r"xss|cross.site.script",
    r"phishing",
    r"social engineering",
    r"penetration test",
    r"bug bounty",
    r"web application firewall|waf",
    r"oauth|openid|saml",  # unless K8s OIDC
    r"python full course",
    r"javascript|react|angular|vue\.js",
    r"machine learning|neural network|deep learning",
    r"blockchain|cryptocurrency",
    r"gdpr|privacy",
]

# ── Garbage detection patterns ─────────────────────────────────────────────
GARBAGE_PATTERNS = [
    r'^\s*\{["\']timestamp["\']',           # Raw JSON scan logs
    r'^\s*\{["\']cycle_id["\']',            # Operational cycle logs
    r'^\s*\{["\']messages["\']',            # Nested training example
    r'^\s*\{["\']instruction["\']',         # Nested Alpaca format
    r'\[CORRECTION\]',                       # Correction placeholders
    r'\[NEEDS CORRECTION\]',                 # Needs correction placeholders
    r'Unable to provide specific correction', # Failed corrections
    r'CORRECTION NEEDED',                    # Another correction variant
]

YOUTUBE_PATTERNS = [
    r'discord\s+(channel|link|server)',
    r'make sure to (join|subscribe|like)',
    r'cubesimplif',
    r'exam\s+cram',
    r'screenshot',
    r'click\s+on',
    r'let me just',
    r'own fingers your own keyboard',
    r'in the next (video|lesson|module)',
    r'patreon|buymeacoffee|ko-fi',
    # Additional transcript markers from spot-check
    r'little container timmy',
    r'we did a six or seven hour',
    r'\d+\s*000 stars on github',
    r'docker (pools|pulls)',
    r'vendor agnostic it doesn.t focus',
    r'let\'s go ahead and',
    r'so basically what happens is',
    r'i\'m gonna show you',
]

CHITCHAT_PATTERNS = [
    r'^(nice work|good job|appreciate that|i\'m listening|great question|sounds good)',
    r'^(sure thing|absolutely|you\'re welcome|no problem|happy to help)',
    r'^(let me know if|hope this helps|feel free to)',
]

# Mad-libs business template patterns (random dollar amounts, percentages)
TEMPLATE_MADLIBS_PATTERNS = [
    r'Budget:\s*\$\d+',
    r'ROI:\s*\d+%',
    r'estimated.*\$\d+.*million',
    r'compliance penalties.*\$\d+',
    r'downtime cost.*\$\d+',
    r'Duration:\s*\d+\s*minutes.*Impact:\s*\d+\s*affected',
]

# Docker docs page dumps
DOCS_DUMP_PATTERNS = [
    r'Table of contents.*\n.*Getting started',
    r'Docker (Desktop|Engine|Compose|Hub).*\n.*Docker (Desktop|Engine|Compose|Hub)',
    r'^\s*(Guides|Reference|Manuals)\s*\n\s*(Guides|Reference|Manuals)',
]

# ── Katie system prompt (replaces JADE/other prompts) ─────────────────────
KATIE_SYSTEM_PROMPT = (
    "You are Katie, a CKA/CKS/CKAD/CNPA-certified autonomous Kubernetes engineer "
    "for GP-Copilot. You diagnose and fix production issues at 2 AM without human "
    "intervention. You provide complete, working fixes with exact commands and YAML "
    "manifests. You check ArgoCD ownership before any fix. You route by rank "
    "(E/D/C/B/S). You reference real tools: kubectl, Falco, Trivy, Kubescape, "
    "Kyverno, OPA/Rego, Helm, ArgoCD. You never hallucinate commands."
)


def extract_chunk_number(filename: str) -> int:
    """Extract chunk number from filename like chunk_0008_10k.jsonl."""
    try:
        return int(filename.split("_")[1])
    except (IndexError, ValueError):
        return -1


def is_chatml_format(record: dict) -> bool:
    """Check if record is ChatML format with messages array."""
    if "messages" not in record:
        return False
    msgs = record["messages"]
    if not isinstance(msgs, list) or len(msgs) < 2:
        return False
    return all(isinstance(m, dict) and "role" in m and "content" in m for m in msgs)


def get_assistant_content(record: dict) -> str:
    """Extract assistant response from ChatML record."""
    for msg in record.get("messages", []):
        if msg.get("role") == "assistant":
            return msg.get("content", "")
    return ""


def get_user_content(record: dict) -> str:
    """Extract user question from ChatML record."""
    for msg in record.get("messages", []):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def content_hash(user: str, assistant: str) -> str:
    """Create a hash for deduplication."""
    combined = f"{user.strip().lower()}||{assistant.strip().lower()}"
    return hashlib.md5(combined.encode()).hexdigest()


def response_hash(assistant: str) -> str:
    """Hash just the response for near-dedup detection."""
    return hashlib.md5(assistant.strip().lower().encode()).hexdigest()


def is_garbage(assistant: str) -> str | None:
    """Check if assistant response matches garbage patterns. Returns reason or None."""
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, assistant, re.IGNORECASE):
            return f"garbage:{pattern[:30]}"
    return None


def is_youtube_transcript(text: str) -> bool:
    """Check if text contains YouTube transcript markers."""
    matches = sum(1 for p in YOUTUBE_PATTERNS if re.search(p, text, re.IGNORECASE))
    if matches >= 2:
        return True
    # Also catch raw speech patterns: no code blocks, no YAML, excessive lowercase
    if len(text) > 200:
        lowercase_ratio = sum(1 for c in text if c.islower()) / max(len(text), 1)
        has_code = "```" in text or "apiVersion" in text or "kubectl" in text
        has_sentences = text.count(". ") > 5
        # Raw speech: very high lowercase, no code, many short sentences
        if lowercase_ratio > 0.85 and not has_code and has_sentences and matches >= 1:
            return True
    return False


def is_madlibs_template(user: str, assistant: str) -> bool:
    """Check if example is a mad-libs business template with random numbers."""
    matches = sum(1 for p in TEMPLATE_MADLIBS_PATTERNS
                  if re.search(p, assistant, re.IGNORECASE))
    return matches >= 2


def is_docs_dump(assistant: str) -> bool:
    """Check if response is a raw documentation page dump."""
    for pattern in DOCS_DUMP_PATTERNS:
        if re.search(pattern, assistant, re.IGNORECASE | re.MULTILINE):
            return True
    # Also catch ToC-style content: many short lines that are just headings
    lines = assistant.strip().split("\n")
    if len(lines) > 10:
        short_lines = sum(1 for l in lines if 0 < len(l.strip()) < 40)
        if short_lines / len(lines) > 0.7:
            # Mostly short lines with no code = likely a ToC dump
            has_code = any("```" in l or "kubectl" in l or "apiVersion" in l for l in lines)
            if not has_code:
                return True
    return False


def is_chitchat(assistant: str) -> bool:
    """Check if response is chitchat/filler."""
    for pattern in CHITCHAT_PATTERNS:
        if re.search(pattern, assistant.strip(), re.IGNORECASE):
            return True
    return False


def is_stub(assistant: str) -> bool:
    """Check if response is too short to be useful."""
    return len(assistant.strip()) < 50


def starts_with_json(assistant: str) -> bool:
    """Check if response starts with raw JSON."""
    stripped = assistant.strip()
    if not stripped:
        return False
    if stripped[0] in ('{', '['):
        try:
            json.loads(stripped)
            return True  # It's a valid JSON blob, not prose
        except json.JSONDecodeError:
            # Only flag if it looks like a JSON log (has timestamp/cycle_id)
            return bool(re.match(r'^\s*[\{\[]\s*"(timestamp|cycle_id|scanner|messages|instruction)', stripped))
    return False


def classify_scope(user: str, assistant: str) -> list[str]:
    """Classify which cert domains this example covers."""
    combined = f"{user} {assistant}".lower()
    scopes = []

    for keyword in CKA_KEYWORDS:
        if keyword.lower() in combined:
            scopes.append("CKA")
            break

    for keyword in CKS_KEYWORDS:
        if keyword.lower() in combined:
            scopes.append("CKS")
            break

    for keyword in CKAD_KEYWORDS:
        if keyword.lower() in combined:
            scopes.append("CKAD")
            break

    for keyword in CNPA_KEYWORDS:
        if keyword.lower() in combined:
            scopes.append("CNPA")
            break

    for keyword in OPS_KEYWORDS:
        if keyword.lower() in combined:
            scopes.append("OPS")
            break

    return scopes


def is_out_of_scope(user: str, assistant: str) -> bool:
    """Check if example is clearly outside Katie's domain."""
    combined = f"{user} {assistant}".lower()

    # If it matches any K8s/cloud scope, it's in scope even if it also matches OOS
    scopes = classify_scope(user, assistant)
    if scopes:
        return False

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return True

    return False


def curate_corpus(dry_run: bool = False, skip_chunks: set = None,
                  output_path: Path = None) -> dict:
    """Main curation pipeline. Returns stats dict."""
    if skip_chunks is None:
        skip_chunks = DROP_CHUNKS

    if output_path is None:
        output_path = OUTPUT_DIR / "katie_v2_clean.jsonl"

    stats = {
        "total_read": 0,
        "dropped_format": 0,
        "dropped_garbage": 0,
        "dropped_youtube": 0,
        "dropped_madlibs": 0,
        "dropped_docs_dump": 0,
        "dropped_chitchat": 0,
        "dropped_stub": 0,
        "dropped_json_response": 0,
        "dropped_exact_dedup": 0,
        "dropped_response_dedup": 0,
        "dropped_skip_chunk": 0,
        "kept_in_scope": 0,
        "kept_out_of_scope": 0,  # Saved to separate file
        "system_prompts_replaced": 0,
        "scope_breakdown": Counter(),
        "per_chunk": {},
    }

    seen_content = set()      # Full content hashes
    seen_responses = {}       # Response hash -> count (cap at 3 per response)
    kept = []
    out_of_scope = []

    chunk_files = sorted(TRAINED_DIR.glob("chunk_*_10k.jsonl"))
    if not chunk_files:
        print(f"ERROR: No chunk files found in {TRAINED_DIR}")
        return stats

    print(f"Found {len(chunk_files)} chunk files")
    print(f"Skipping chunks: {sorted(skip_chunks)}")
    print()

    for chunk_file in chunk_files:
        chunk_num = extract_chunk_number(chunk_file.name)
        chunk_stats = {"read": 0, "kept": 0, "dropped": Counter()}

        if chunk_num in skip_chunks:
            with open(chunk_file) as f:
                line_count = sum(1 for _ in f)
            stats["dropped_skip_chunk"] += line_count
            stats["total_read"] += line_count
            chunk_stats["read"] = line_count
            chunk_stats["dropped"]["skip_chunk"] = line_count
            stats["per_chunk"][chunk_file.name] = chunk_stats
            print(f"  {chunk_file.name}: SKIPPED ({line_count} lines)")
            continue

        with open(chunk_file) as f:
            for line_num, line in enumerate(f, 1):
                stats["total_read"] += 1
                chunk_stats["read"] += 1

                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    stats["dropped_garbage"] += 1
                    chunk_stats["dropped"]["bad_json"] += 1
                    continue

                # Filter 1: Format check
                if not is_chatml_format(record):
                    stats["dropped_format"] += 1
                    chunk_stats["dropped"]["format"] += 1
                    continue

                assistant = get_assistant_content(record)
                user = get_user_content(record)

                # Filter 2: Garbage patterns
                garbage_reason = is_garbage(assistant)
                if garbage_reason:
                    stats["dropped_garbage"] += 1
                    chunk_stats["dropped"][garbage_reason] += 1
                    continue

                # Filter 3: Raw JSON response
                if starts_with_json(assistant):
                    stats["dropped_json_response"] += 1
                    chunk_stats["dropped"]["json_response"] += 1
                    continue

                # Filter 4: YouTube transcripts
                if is_youtube_transcript(assistant) or is_youtube_transcript(user):
                    stats["dropped_youtube"] += 1
                    chunk_stats["dropped"]["youtube"] += 1
                    continue

                # Filter 5: Mad-libs business templates
                if is_madlibs_template(user, assistant):
                    stats["dropped_madlibs"] += 1
                    chunk_stats["dropped"]["madlibs"] += 1
                    continue

                # Filter 6: Docs page dumps
                if is_docs_dump(assistant):
                    stats["dropped_docs_dump"] += 1
                    chunk_stats["dropped"]["docs_dump"] += 1
                    continue

                # Filter 7: Chitchat
                if is_chitchat(assistant):
                    stats["dropped_chitchat"] += 1
                    chunk_stats["dropped"]["chitchat"] += 1
                    continue

                # Filter 8: Stub responses
                if is_stub(assistant):
                    stats["dropped_stub"] += 1
                    chunk_stats["dropped"]["stub"] += 1
                    continue

                # Filter 9: Exact dedup
                ch = content_hash(user, assistant)
                if ch in seen_content:
                    stats["dropped_exact_dedup"] += 1
                    chunk_stats["dropped"]["exact_dedup"] += 1
                    continue
                seen_content.add(ch)

                # Filter 10: Response dedup (allow max 3 of same response)
                rh = response_hash(assistant)
                resp_count = seen_responses.get(rh, 0)
                if resp_count >= 3:
                    stats["dropped_response_dedup"] += 1
                    chunk_stats["dropped"]["response_dedup"] += 1
                    continue
                seen_responses[rh] = resp_count + 1

                # Classify scope
                scopes = classify_scope(user, assistant)

                if is_out_of_scope(user, assistant) and not scopes:
                    out_of_scope.append(record)
                    stats["kept_out_of_scope"] += 1
                    chunk_stats["dropped"]["out_of_scope"] += 1
                    continue

                # Replace system prompt to Katie's persona
                for msg in record["messages"]:
                    if msg["role"] == "system":
                        if "katie" not in msg["content"].lower():
                            msg["content"] = KATIE_SYSTEM_PROMPT
                            stats["system_prompts_replaced"] += 1
                        break
                else:
                    # No system message — add one
                    record["messages"].insert(0, {
                        "role": "system",
                        "content": KATIE_SYSTEM_PROMPT,
                    })
                    stats["system_prompts_replaced"] += 1

                # It's a keeper
                kept.append(record)
                stats["kept_in_scope"] += 1
                chunk_stats["kept"] += 1

                for s in scopes:
                    stats["scope_breakdown"][s] += 1

        stats["per_chunk"][chunk_file.name] = chunk_stats
        drop_pct = (1 - chunk_stats["kept"] / max(chunk_stats["read"], 1)) * 100
        print(f"  {chunk_file.name}: {chunk_stats['kept']}/{chunk_stats['read']} kept ({drop_pct:.0f}% dropped)")

    # Write output
    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            for record in kept:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"\nWrote {len(kept)} clean examples to {output_path}")

        # Write out-of-scope to separate file
        oos_path = output_path.with_name("katie_v2_out_of_scope.jsonl")
        with open(oos_path, "w") as f:
            for record in out_of_scope:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Wrote {len(out_of_scope)} out-of-scope examples to {oos_path}")

        # Write report
        report = generate_report(stats, kept, out_of_scope)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"curation-{timestamp}.md"
        with open(report_path, "w") as f:
            f.write(report)
        print(f"Wrote report to {report_path}")

        # Also save locally
        local_report = output_path.with_name("curation_report.md")
        with open(local_report, "w") as f:
            f.write(report)

    return stats


def generate_report(stats: dict, kept: list, out_of_scope: list) -> str:
    """Generate markdown curation report."""
    total = stats["total_read"]
    kept_count = stats["kept_in_scope"]
    oos_count = stats["kept_out_of_scope"]
    dropped = total - kept_count - oos_count

    lines = [
        "# Katie v2 Corpus Curation Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Input**: {total:,} examples across {len(stats['per_chunk'])} chunks",
        f"**Output**: {kept_count:,} clean in-scope examples ({kept_count/max(total,1)*100:.1f}%)",
        f"**Out-of-scope**: {oos_count:,} examples (saved separately)",
        f"**Dropped**: {dropped:,} examples ({dropped/max(total,1)*100:.1f}%)",
        "",
        "## Drop Reasons",
        "",
        "| Reason | Count | % |",
        "|--------|-------|---|",
        f"| Skipped chunks (DROP verdict) | {stats['dropped_skip_chunk']:,} | {stats['dropped_skip_chunk']/max(total,1)*100:.1f}% |",
        f"| Wrong format (not ChatML) | {stats['dropped_format']:,} | {stats['dropped_format']/max(total,1)*100:.1f}% |",
        f"| Garbage patterns | {stats['dropped_garbage']:,} | {stats['dropped_garbage']/max(total,1)*100:.1f}% |",
        f"| Raw JSON response | {stats['dropped_json_response']:,} | {stats['dropped_json_response']/max(total,1)*100:.1f}% |",
        f"| YouTube transcripts | {stats['dropped_youtube']:,} | {stats['dropped_youtube']/max(total,1)*100:.1f}% |",
        f"| Mad-libs business templates | {stats['dropped_madlibs']:,} | {stats['dropped_madlibs']/max(total,1)*100:.1f}% |",
        f"| Docs page dumps | {stats['dropped_docs_dump']:,} | {stats['dropped_docs_dump']/max(total,1)*100:.1f}% |",
        f"| Chitchat/filler | {stats['dropped_chitchat']:,} | {stats['dropped_chitchat']/max(total,1)*100:.1f}% |",
        f"| Stub responses (<50 chars) | {stats['dropped_stub']:,} | {stats['dropped_stub']/max(total,1)*100:.1f}% |",
        f"| Exact duplicates | {stats['dropped_exact_dedup']:,} | {stats['dropped_exact_dedup']/max(total,1)*100:.1f}% |",
        f"| Response duplicates (>3 same) | {stats['dropped_response_dedup']:,} | {stats['dropped_response_dedup']/max(total,1)*100:.1f}% |",
        "",
        "## Scope Breakdown (in-scope examples)",
        "",
        "| Domain | Count | % of Kept |",
        "|--------|-------|-----------|",
    ]

    for scope in ["CKS", "CKA", "CKAD", "CNPA", "OPS"]:
        count = stats["scope_breakdown"].get(scope, 0)
        pct = count / max(kept_count, 1) * 100
        lines.append(f"| {scope} | {count:,} | {pct:.1f}% |")

    lines.extend([
        "",
        "*Note: Examples can match multiple scopes.*",
        "",
        f"**System prompts replaced to Katie persona**: {stats['system_prompts_replaced']:,}",
        "",
        "## Per-Chunk Results",
        "",
        "| Chunk | Read | Kept | Dropped | Keep % |",
        "|-------|------|------|---------|--------|",
    ])

    for chunk_name in sorted(stats["per_chunk"].keys()):
        cs = stats["per_chunk"][chunk_name]
        keep_pct = cs["kept"] / max(cs["read"], 1) * 100
        total_dropped = cs["read"] - cs["kept"]
        lines.append(f"| {chunk_name} | {cs['read']:,} | {cs['kept']:,} | {total_dropped:,} | {keep_pct:.0f}% |")

    lines.extend([
        "",
        "## Cert Coverage Gaps",
        "",
        "Target distribution for Katie v2:",
        "- CKS: 35% (pod security, RBAC, audit, runtime, supply chain)",
        "- CKA: 30% (cluster ops, workloads, storage, networking, troubleshooting)",
        "- CKAD: 20% (app design, deployment, services, config, observability)",
        "- CNPA: 10% (cloud networking, CNI, service mesh, DNS, VPC)",
        "- OPS: 5% (ArgoCD, rank routing, incident response, playbooks)",
        "",
        "## Next Steps",
        "",
        "1. Review scope breakdown — generate targeted data for underrepresented certs",
        "2. Feed `katie_v2_clean.jsonl` through ETL pipeline",
        "3. Train fresh from base model (single LoRA pass, NOT incremental chunks)",
        "4. Eval with cert-focused benchmarks",
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Katie 3B Corpus Curator")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--output", type=str, help="Custom output path")
    parser.add_argument("--skip-chunks", type=str,
                        help="Comma-separated chunk numbers to skip (adds to default DROP list)")
    parser.add_argument("--only-chunks", type=str,
                        help="Only process these chunk numbers (comma-separated)")
    args = parser.parse_args()

    print()
    print("=" * 65)
    print("  KATIE v2 CORPUS CURATOR")
    print("  Clean, Filter, Deduplicate — CKA/CKS/CKAD/CNPA scope")
    print("=" * 65)
    print()

    skip = set(DROP_CHUNKS)
    if args.skip_chunks:
        extra = {int(x.strip()) for x in args.skip_chunks.split(",")}
        skip |= extra
        print(f"Additional skip chunks: {sorted(extra)}")

    output_path = Path(args.output) if args.output else None

    stats = curate_corpus(
        dry_run=args.dry_run,
        skip_chunks=skip,
        output_path=output_path,
    )

    # Print summary
    total = stats["total_read"]
    kept = stats["kept_in_scope"]
    oos = stats["kept_out_of_scope"]
    dropped = total - kept - oos

    print()
    print("=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print(f"  Total read:       {total:>8,}")
    print(f"  In-scope kept:    {kept:>8,}  ({kept/max(total,1)*100:.1f}%)")
    print(f"  Out-of-scope:     {oos:>8,}  (saved separately)")
    print(f"  Dropped:          {dropped:>8,}  ({dropped/max(total,1)*100:.1f}%)")
    print()
    print("  Scope breakdown:")
    for scope in ["CKS", "CKA", "CKAD", "CNPA", "OPS"]:
        count = stats["scope_breakdown"].get(scope, 0)
        bar = "#" * (count // 200)
        print(f"    {scope:<6} {count:>6,}  {bar}")
    print("=" * 65)

    if args.dry_run:
        print("\n  [DRY RUN] No files written.")
    print()


if __name__ == "__main__":
    main()
