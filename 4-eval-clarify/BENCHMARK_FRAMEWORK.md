# JADE Evaluation Framework

> **Testing JADE before merge: Domain knowledge + Task performance**

---

## Two Types of Testing

| Type | What It Measures | How |
|------|------------------|-----|
| **Domain Knowledge** | Does JADE know the subject? | Q&A benchmarks |
| **Task Performance** | Can JADE DO the work? | Input -> Output validation |

Most people only test the first. The second is where the money is.

---

## The 7 Domain Knowledge Categories

```
+-----------------------------------------------------------------------------+
|                    JADE KNOWLEDGE BENCHMARK CATEGORIES                       |
+-----------------------------------------------------------------------------+
|                                                                              |
|  1. CLOUD (AWS/Azure/GCP)                                                   |
|     +-- IAM policies & least privilege                                      |
|     +-- Network security (VPC, SGs, NACLs)                                  |
|     +-- Encryption (KMS, at-rest, in-transit)                               |
|     +-- Service-specific security (S3, RDS, Lambda)                         |
|     +-- Multi-account architecture                                          |
|                                                                              |
|  2. KUBERNETES SECURITY (CKS)                                               |
|     +-- Pod Security Standards/Policies                                     |
|     +-- RBAC & ServiceAccounts                                              |
|     +-- Network Policies                                                    |
|     +-- Secrets management                                                  |
|     +-- Admission control (Gatekeeper/Kyverno)                              |
|     +-- Runtime security (Falco, seccomp, AppArmor)                         |
|                                                                              |
|  3. DEVSECOPS                                                               |
|     +-- SAST/DAST tooling                                                   |
|     +-- Dependency scanning (SCA)                                           |
|     +-- Container image scanning                                            |
|     +-- CI/CD pipeline security                                             |
|     +-- Secrets in code detection                                           |
|     +-- IaC scanning (Checkov, tfsec)                                       |
|                                                                              |
|  4. COMPLIANCE & AUDITING                                                   |
|     +-- CIS Benchmarks (AWS, K8s, Docker)                                   |
|     +-- SOC2 controls                                                       |
|     +-- PCI-DSS requirements                                                |
|     +-- HIPAA safeguards                                                    |
|     +-- FedRAMP/NIST 800-53                                                 |
|     +-- Evidence collection & audit trails                                  |
|                                                                              |
|  5. HARDENING                                                               |
|     +-- OS hardening (Linux, containers)                                    |
|     +-- Network segmentation                                                |
|     +-- Attack surface reduction                                            |
|     +-- Defense in depth                                                    |
|     +-- Zero trust principles                                               |
|                                                                              |
|  6. INCIDENT RESPONSE                                                       |
|     +-- Triage methodology                                                  |
|     +-- Containment strategies                                              |
|     +-- Forensic preservation                                               |
|     +-- Communication templates                                             |
|     +-- Post-incident review                                                |
|                                                                              |
|  7. THREAT MODELING                                                         |
|     +-- STRIDE methodology                                                  |
|     +-- Attack trees                                                        |
|     +-- Crown jewels identification                                         |
|     +-- Risk scoring                                                        |
|     +-- Mitigation prioritization                                           |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## The 5 Task Performance Categories

This is **the real test** - can JADE produce working output?

```
+-----------------------------------------------------------------------------+
|                    JADE TASK BENCHMARK CATEGORIES                            |
+-----------------------------------------------------------------------------+
|                                                                              |
|  1. CODE GENERATION                                                         |
|     +-- Terraform modules (valid HCL?)                                      |
|     +-- Kubernetes YAML (applies clean?)                                    |
|     +-- Python scripts (runs without error?)                                |
|     +-- Bash scripts (shellcheck passes?)                                   |
|     +-- OPA/Rego policies (compiles?)                                       |
|                                                                              |
|  2. FIX GENERATION                                                          |
|     +-- Given: Checkov finding -> Output: Fixed Terraform                   |
|     +-- Given: Trivy CVE -> Output: Patched Dockerfile                      |
|     +-- Given: Semgrep alert -> Output: Secure code                         |
|     +-- Given: CrashLoopBackOff -> Output: Diagnosis + fix                  |
|     +-- Given: RBAC violation -> Output: Minimal permission                 |
|                                                                              |
|  3. POLICY GENERATION                                                       |
|     +-- Natural language -> Gatekeeper ConstraintTemplate                   |
|     +-- Natural language -> Kyverno ClusterPolicy                           |
|     +-- Natural language -> OPA Rego                                        |
|     +-- Natural language -> AWS SCP                                         |
|     +-- Natural language -> Network Policy                                  |
|                                                                              |
|  4. EXPLANATION & DOCS                                                      |
|     +-- Finding -> Plain English for client                                 |
|     +-- Fix -> Change documentation                                         |
|     +-- Compliance control -> Implementation guidance                       |
|     +-- Incident -> Executive summary                                       |
|                                                                              |
|  5. CLASSIFICATION & ROUTING                                                |
|     +-- Finding -> Correct rank (E/D/C/B/S)                                 |
|     +-- Finding -> Correct JSA agent                                        |
|     +-- Finding -> Correct compliance mapping                               |
|     +-- Request -> Correct task decomposition                               |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## ML Engineer Evaluation Metrics

What a REAL MLOps engineer measures:

| Metric | What It Means | How to Test |
|--------|---------------|-------------|
| **Accuracy** | Is the answer correct? | Compare to known-good answers |
| **Hallucination Rate** | Does it make stuff up? | Check for fake CIS controls, fake CVEs |
| **Consistency** | Same input = same output? | Run same prompt 10x, compare |
| **Latency** | How fast? | Time to first token, total response time |
| **Token Efficiency** | How verbose? | Tokens per useful output |
| **Retrieval Accuracy** | Does RAG find the right docs? | Check which chunks get pulled |
| **Task Success Rate** | Does generated code work? | Actually run/apply the output |

---

## Benchmark Directory Structure

```
2-test-data/
+-- evaluation-tests/
|   +-- 01-cloud-benchmark/
|   |   +-- aws-iam-questions.jsonl
|   |   +-- aws-networking-questions.jsonl
|   |   +-- gcp-questions.jsonl
|   |   +-- azure-questions.jsonl
|   |   +-- expected-answers.json
|   |
|   +-- 02-cks-benchmark/
|   |   +-- pod-security-questions.jsonl
|   |   +-- rbac-questions.jsonl
|   |   +-- network-policy-questions.jsonl
|   |   +-- admission-control-questions.jsonl
|   |   +-- expected-answers.json
|   |
|   +-- 03-devsecops-benchmark/
|   |   +-- sast-questions.jsonl
|   |   +-- sca-questions.jsonl
|   |   +-- cicd-questions.jsonl
|   |   +-- iac-scanning-questions.jsonl
|   |   +-- expected-answers.json
|   |
|   +-- 04-compliance-benchmark/
|   |   +-- cis-questions.jsonl
|   |   +-- soc2-questions.jsonl
|   |   +-- pci-questions.jsonl
|   |   +-- hipaa-questions.jsonl
|   |   +-- expected-answers.json
|   |
|   +-- 05-hardening-benchmark/
|   |   +-- os-hardening-questions.jsonl
|   |   +-- container-hardening-questions.jsonl
|   |   +-- network-segmentation-questions.jsonl
|   |   +-- expected-answers.json
|   |
|   +-- 06-incident-response-benchmark/
|   |   +-- triage-questions.jsonl
|   |   +-- containment-questions.jsonl
|   |   +-- forensics-questions.jsonl
|   |   +-- expected-answers.json
|   |
|   +-- 07-threat-modeling-benchmark/
|       +-- stride-questions.jsonl
|       +-- attack-tree-questions.jsonl
|       +-- risk-scoring-questions.jsonl
|       +-- expected-answers.json
|
+-- task-tests/
|   +-- fix-generation/
|   |   +-- checkov-findings/
|   |   |   +-- input-001.json      # Checkov finding
|   |   |   +-- expected-001.tf     # Correct fix
|   |   +-- trivy-findings/
|   |   +-- semgrep-alerts/
|   |
|   +-- policy-generation/
|   |   +-- gatekeeper/
|   |   |   +-- prompt-001.txt      # "Only allow images from gcr.io/approved"
|   |   |   +-- expected-001.yaml   # Working ConstraintTemplate
|   |   +-- kyverno/
|   |   +-- opa-rego/
|   |
|   +-- code-generation/
|   |   +-- terraform/
|   |   +-- kubernetes/
|   |   +-- python/
|   |
|   +-- classification/
|       +-- rank-classification/
|       |   +-- findings.jsonl      # 100 sample findings
|       |   +-- expected-ranks.json # Correct E/D/C/B/S
|       +-- agent-routing/
|           +-- requests.jsonl
|           +-- expected-agents.json
|
+-- scripts/
    +-- run_benchmarks.py
    +-- score_results.py
    +-- generate_report.py
```

---

## Benchmark Entry Formats

### Knowledge Benchmark (JSONL)

```json
{
  "id": "cks-001",
  "category": "kubernetes",
  "subcategory": "pod-security",
  "rank": "D",
  "question": "A pod spec has 'privileged: true'. What is the security risk and how do you fix it?",
  "expected_keywords": ["root", "host", "escape", "securityContext", "privileged: false"],
  "expected_fix_contains": "privileged: false",
  "grading": {
    "keywords_required": 3,
    "fix_required": true,
    "workflow_required": false
  }
}
```

### Task Benchmark (Input/Output Pairs)

```json
// tasks/fix-generation/checkov-findings/input-001.json
{
  "id": "fix-001",
  "scanner": "checkov",
  "check_id": "CKV_AWS_19",
  "finding": "S3 bucket does not have encryption enabled",
  "resource": "aws_s3_bucket.data",
  "file": "main.tf",
  "severity": "HIGH"
}
```

```hcl
// tasks/fix-generation/checkov-findings/expected-001.tf
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

### Classification Benchmark

```json
{
  "id": "classify-001",
  "finding": {
    "scanner": "trivy",
    "severity": "CRITICAL",
    "vuln_id": "CVE-2024-1234",
    "description": "Remote code execution in express < 4.18.0",
    "package": "express",
    "fix_available": true
  },
  "expected_rank": "D",
  "expected_agent": "jsa-devsec",
  "expected_auto_fix": true
}
```

---

## Scorecard Template

```
+-----------------------------------------------------------------------------+
|                    JADE v1.x BENCHMARK RESULTS                               |
+-----------------------------------------------------------------------------+
|                                                                              |
|  DOMAIN KNOWLEDGE                           TASK PERFORMANCE                 |
|  ------------------                         ----------------                 |
|  Cloud (AWS):        __/100 (__%)           Fix Generation:    __/60 (__%)  |
|  Kubernetes (CKS):   __/100 (__%)           Policy Gen:        __/50 (__%)  |
|  DevSecOps:          __/100 (__%)           Code Gen:          __/70 (__%)  |
|  Compliance:         __/100 (__%)           Explanation:       __/50 (__%)  |
|  Hardening:          __/100 (__%)           Classification:    __/100(__%)  |
|  Incident Response:  __/100 (__%)                                           |
|  Threat Modeling:    __/100 (__%)                                           |
|                                                                              |
|  OVERALL: __% Knowledge, __% Task Success                                   |
|                                                                              |
|  QUALITY METRICS:                                                            |
|  Hallucination Rate: __%                                                    |
|  Consistency Score:  __%                                                    |
|  Avg Latency:        __ms                                                   |
|                                                                              |
|  RECOMMENDATIONS:                                                            |
|  - [Gap area 1]                                                             |
|  - [Gap area 2]                                                             |
|  - [Gap area 3]                                                             |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## Decision Criteria

| Accuracy | Action |
|----------|--------|
| 80%+ on tests | Merge/convert, monitor in prod |
| 60-80% accuracy | Add targeted training data for failure cases |
| <60% accuracy | Review training data quality, possible issues |

---

## Quick Reference: The 7 Categories

| # | Category | Tests Knowledge Of | Tests Ability To |
|---|----------|-------------------|------------------|
| 1 | **Cloud** | AWS/Azure services, IAM, networking | Generate Terraform, CloudFormation |
| 2 | **CKS** | K8s security concepts | Generate secure YAML, policies |
| 3 | **DevSecOps** | Scanner tools, CI/CD | Generate pipeline configs, fix code |
| 4 | **Compliance** | Frameworks (CIS, SOC2, PCI) | Map findings to controls, generate evidence |
| 5 | **Hardening** | Defense in depth, attack surface | Generate hardening configs |
| 6 | **Incident Response** | Triage, containment, forensics | Generate playbooks, summaries |
| 7 | **Threat Modeling** | STRIDE, risk analysis | Identify threats, prioritize mitigations |

---

*Last updated: January 2026*
