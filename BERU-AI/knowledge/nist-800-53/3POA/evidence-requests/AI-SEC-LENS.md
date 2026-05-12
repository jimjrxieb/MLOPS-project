# Evidence Request — AI-SEC-LENS

```
TO:   AI Security Engineer / MLOps Lead (AI-SEC-LENS)
FROM: 3POA Assessor / CISO Internal Audit
RE:   NIST 800-53 + NIST AI 600-1 Evidence Collection — AI/ML Workload Controls
DUE:  48 hours before assessment call
```

This request covers controls implemented in:

- `GP-CONSULTING/AI-SEC-LENS/10-AI-SECURITY/` — Model supply chain, prompt injection,
  training data, inference security, adversarial testing
- `GP-MODEL-OPS/JADE-AI/` + `GP-MODEL-OPS/KATIE-AI/` — Deployed model artifacts
- `GP-MODEL-OPS/2-rag-ingestion/` — RAG pipeline + ChromaDB

**Note to assessor**: AI security controls span two frameworks. Part 1 covers NIST 800-53
controls where AI-specific tooling provides the implementation. Part 2 covers NIST AI 600-1
controls unique to AI/ML systems. Both are required for a complete AI workload assessment.

---

## Part 1 — NIST 800-53 (AI-Specific Implementation)

---

### AC-2 — Account Management (Model API Layer)

**What to provide**:

- Evidence model inference endpoints require authentication
- Service account inventory for ML workloads in the cluster
- Evidence model API keys are rotated on a schedule

**Validation command**:

```bash
# Check model API requires auth:
curl -s http://model-api:8000/api/jade/health
# Should return 401 without auth header, not 200
# Check RBAC for model service accounts:
kubectl get rolebindings,clusterrolebindings -A -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for b in data['items']:
    subs = [s for s in b.get('subjects', []) if 'jade' in s.get('name', '').lower() or 'katie' in s.get('name', '').lower()]
    if subs:
        role = b.get('roleRef', {}).get('name', 'unknown')
        print(f'{role}: {[s[\"name\"] for s in subs]}')
"
```

**Evidence artifact**: Model API auth test output + K8s RBAC for ML service accounts

---

### AC-6 — Least Privilege (Model API and RAG)

**What to provide**:

- Evidence ChromaDB requires authentication for queries (not open)
- Evidence MLflow server requires authentication
- Evidence inference endpoints return only what is needed (no debug output in production)

**Validation command**:

```bash
# ChromaDB auth check (should reject without token):
curl -s http://chromadb:8000/api/v1/collections
# Expected: auth error, not collection list

# MLflow auth check:
curl -s http://mlflow:5000/api/2.0/mlflow/experiments/list
# Expected: auth required

# Check OPA policies for model API:
ls GP-CONSULTING/AI-SEC-LENS/10-AI-SECURITY/03-inference-security/policies/
```

**Evidence artifact**: ChromaDB auth config + MLflow auth config + OPA policy YAML

---

### CA-2 — Control Assessments (Model Supply Chain)

**What to provide**:

- cosign verification output for production model artifacts (GGUF files)
- Evidence model artifacts are scanned before deployment
- Assessment report from last adversarial testing cycle

**Validation command**:

```bash
# Verify production model signature:
cosign verify-blob \
  --key GP-MODEL-OPS/3-model-registry/cosign.pub \
  --signature GP-MODEL-OPS/3-model-registry/jade-v1.0.sig \
  GP-MODEL-OPS/3-model-registry/jade-v1.0.gguf
# Show SHA256 chain:
sha256sum GP-MODEL-OPS/3-model-registry/jade-v1.0.gguf
```

**Evidence artifact**: cosign verification output + SHA256 hash chain for all production models

---

### CM-3 — Configuration Change Control (Model Versioning)

**What to provide**:

- MLflow experiment run history for production model
- Evidence Modelfile changes are version-controlled in git
- Evidence model promotions require review (not direct push to production)

**Validation command**:

```bash
# Show MLflow experiment runs:
mlflow experiments list
mlflow runs list --experiment-id 1 --output json | python3 -c "
import json, sys
runs = json.load(sys.stdin)
for r in runs[:5]:
    print(f'{r[\"info\"][\"run_id\"][:8]}: {r[\"info\"][\"status\"]} - {r[\"info\"][\"end_time\"]}')
"
# Show Modelfile history:
git log --oneline GP-MODEL-OPS/3-model-registry/ | head -10
```

**Evidence artifact**: MLflow run history export + Modelfile git history

---

### RA-5 — Vulnerability Scanning (LLM Surface)

**What to provide**:

- garak scan report against production model endpoint
- Evidence scan runs before model is promoted to production
- Evidence findings from garak are triaged and addressed

**Validation command**:

```bash
python3 -m garak --version
# Show last garak scan results:
ls GP-S3/6-seclab-reports/ai-sec-evidence/garak/
cat GP-S3/6-seclab-reports/ai-sec-evidence/garak/*.jsonl 2>/dev/null | python3 -c "
import json, sys
total = passed = 0
for line in sys.stdin:
    try:
        r = json.loads(line.strip())
        total += 1
        if r.get('passed'):
            passed += 1
    except Exception:
        pass
print(f'Total probes: {total}, Passed: {passed}, Failed: {total - passed}')
"
```

**Evidence artifact**: garak JSONL report + probe category summary

---

### SI-4 — System Monitoring (Inference Monitoring)

**What to provide**:

- MLflow metrics showing model performance over time
- Evidence inference latency and error rates are monitored
- Evidence anomalous inference patterns trigger alerts

**Validation command**:

```bash
# Show MLflow metrics:
mlflow runs list --experiment-id 1 --output json | python3 -c "
import json, sys
runs = json.load(sys.stdin)
for r in runs[:3]:
    metrics = r.get('data', {}).get('metrics', {})
    print(f'Run {r[\"info\"][\"run_id\"][:8]}: {metrics}')
"
# Check Prometheus metrics for inference:
curl -s http://prometheus:9090/api/v1/query?query=jade_inference_duration_seconds | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data.get('data', {}).get('result', [])
print(f'Inference metrics: {len(results)} series')
"
```

**Evidence artifact**: MLflow metrics export + Prometheus inference metric sample

---

### SI-7 — Software Integrity (Model Integrity)

**What to provide**:

- SHA256 hash chain for model checkpoints from training to production
- Evidence model weights are not modified post-signing
- cosign transparency log entries for all production models

**Validation command**:

```bash
# Show checkpoint hash chain:
cat GP-MODEL-OPS/3-model-registry/training_state.json | python3 -c "
import json, sys
state = json.load(sys.stdin)
for ckpt in state.get('checkpoints', [])[:5]:
    print(f'{ckpt[\"chunk\"]}: {ckpt.get(\"sha256\", \"NO HASH\")}')
"
# Verify current GGUF hash matches registry:
sha256sum GP-MODEL-OPS/3-model-registry/jade-v1.0.gguf
cat GP-MODEL-OPS/3-model-registry/hashes.sha256 | grep jade-v1.0.gguf
```

**Evidence artifact**: Hash chain JSON + cosign transparency log URLs

---

## Part 2 — NIST AI 600-1

---

### GOVERN 1.1 — Risk Management Framework

**What to provide**:

- Model card for each production model (JADE, KATIE)
- Evidence risk categories are documented for each model
- Organizational AI risk policy

**Validation command**:

```bash
# Show model cards:
ls GP-MODEL-OPS/6-model-cards/
cat GP-MODEL-OPS/6-model-cards/jade-model-card.md 2>/dev/null | head -40
cat GP-MODEL-OPS/6-model-cards/katie-model-card.md 2>/dev/null | head -40
```

**Evidence artifact**: Model cards + AI risk policy document

---

### GOVERN 1.2 — Roles and Responsibilities

**What to provide**:

- AI authority chain documentation (matches `CLAUDE.md` authority chain)
- Evidence human oversight is documented for B/S rank decisions
- Evidence JADE max authority is C-rank (hardcoded, not policy-only)

**Validation command**:

```bash
# Show authority chain config:
grep -A10 "Rank Boundaries\|KATIE max authority\|JADE max authority" \
  GP-copilot/.claude/rules/architecture-laws.md
# Show rank enforcement in code:
grep -r "C-rank\|B-rank\|S-rank\|authority" GP-MODEL-OPS/JADE-AI/ | grep -v ".pyc" | head -10
```

**Evidence artifact**: Authority chain documentation + rank boundary code reference

---

### GOVERN 1.5–1.6 — Bias Testing and Fairness Assessment

**What to provide**:

- Fairlearn or equivalent bias assessment results
- Evidence bias testing runs before model promotion
- Documented bias thresholds and what happens when they are exceeded

**Validation command**:

```bash
# Show bias test results:
ls GP-MODEL-OPS/4-eval-clarify/
# Run a bias check if Fairlearn is installed:
python3 -c "
from fairlearn.metrics import MetricFrame, selection_rate
print('Fairlearn available')
" 2>/dev/null || echo "Fairlearn not installed — manual bias review required"
# Show eval results:
ls GP-MODEL-OPS/4-eval-clarify/results/ 2>/dev/null | head -10
```

**Evidence artifact**: Eval results directory + bias assessment output (or documented manual process)

---

### MAP 2.1–2.3 — Training Data Quality, Documentation, and Lineage

**What to provide**:

- Presidio PII scan results for training data
- Evidence training data sources are documented
- Evidence data lineage is tracked (what went in, what was rejected)

**Validation command**:

```bash
# Show training data lineage:
cat GP-MODEL-OPS/1-local-pipeline/data_lineage.json 2>/dev/null | python3 -c "
import json, sys
lineage = json.load(sys.stdin)
print(f'Tracked sources: {len(lineage.get(\"sources\", []))}')
"
# Run Presidio on a sample:
python3 -c "
from presidio_analyzer import AnalyzerEngine
engine = AnalyzerEngine()
# Test with sample text:
results = engine.analyze(text='Patient John Doe, SSN 123-45-6789', language='en')
print(f'PII entities detected: {[r.entity_type for r in results]}')
"
# Show RAG ingestion log:
ls GP-S3/3-mlops-reports/1-rag-staging/ | head -5
```

**Evidence artifact**: Presidio scan log + RAG ingestion report + data lineage JSON

---

### MAP 3.1–3.5 — API Security and Inference Lifecycle

**What to provide**:

- GP-API authentication configuration (`GP-INFRA/GP-API/main.py`)
- Evidence rate limiting is configured on inference endpoints
- Evidence input validation rejects malformed prompts
- Inference request/response logging configuration

**Validation command**:

```bash
# Check GP-API auth middleware:
grep -A10 "auth\|token\|bearer\|rate_limit" GP-INFRA/GP-API/main.py | head -30
# Check rate limiting:
grep -r "rate.limit\|slowapi\|RateLimiter" GP-INFRA/GP-API/ | head -10
# Test auth:
curl -s http://localhost:8000/api/jade/health
# Expected: 401 without token
```

**Evidence artifact**: GP-API config + rate limit config + auth test output

---

### MEASURE 2.1–2.3 — Adversarial Robustness Testing

**What to provide**:

- counterfit attack report against production model
- ART perturbation test results
- Evidence adversarial testing runs before each model release

**Validation command**:

```bash
# Verify counterfit is available:
python3 -c "import counterfit; print(f'counterfit {counterfit.__version__}')" 2>/dev/null || echo "counterfit not installed"
# Verify ART is available:
python3 -c "from art.attacks.evasion import FastGradientMethod; print('ART OK')" 2>/dev/null || echo "ART not installed"
# Show last adversarial test results:
ls GP-S3/6-seclab-reports/ai-sec-evidence/ | grep -E "adversarial|counterfit|art"
```

**Evidence artifact**: counterfit report + ART perturbation results in `GP-S3/6-seclab-reports/ai-sec-evidence/`

---

### MEASURE 2.7–2.8 — RAG Data Integrity and Quality

**What to provide**:

- ChromaDB collection statistics (document count, last updated)
- Evidence ChromaDB requires authentication (not open to anonymous queries)
- Evidence RAG documents are validated before ingestion

**Validation command**:

```bash
# Show ChromaDB collection stats:
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='GP-MODEL-OPS/2-rag-ingestion/05-ragged-data/chroma/')
for collection in client.list_collections():
    print(f'{collection.name}: {collection.count()} documents')
"
# Verify ChromaDB auth setting:
grep -r "auth\|token\|CHROMA_SERVER_AUTH" GP-MODEL-OPS/2-rag-ingestion/ | grep -v ".pyc" | head -10
```

**Evidence artifact**: ChromaDB collection list + ingestion report from `GP-S3/3-mlops-reports/1-rag-staging/`

---

### MANAGE 2.1–2.4 — Model Provenance, Integrity, and Secure Configuration

**What to provide**:

- Modelfile for each production model (JADE, KATIE)
- cosign signature for each production GGUF
- Evidence Ollama model server has access controls (not open)

**Validation command**:

```bash
# Show production Modelfiles:
cat GP-MODEL-OPS/3-model-registry/Modelfile.jade 2>/dev/null | head -20
cat GP-MODEL-OPS/3-model-registry/Modelfile.katie 2>/dev/null | head -20
# Verify Ollama binding (should be localhost only, not 0.0.0.0):
ss -tlnp | grep 11434
# Should show 127.0.0.1:11434, not 0.0.0.0:11434
# Show signed models:
ls GP-MODEL-OPS/3-model-registry/*.sig 2>/dev/null
```

**Evidence artifact**: Modelfile contents + cosign signature files + Ollama binding config

---

### MANAGE 2.4–2.6 — Prompt Injection Mitigation

**What to provide**:

- garak scan report with injection probe results
- Evidence prompt injection defense is in place (input sanitization or prompt guard)
- Evidence that jailbreak attempts are logged

**Validation command**:

```bash
# Show last garak injection scan:
ls GP-S3/6-seclab-reports/ai-sec-evidence/garak/*.jsonl 2>/dev/null | head -3
# Run targeted injection probe (non-destructive):
python3 -m garak -m rest -g ollama --probes dan.Dan_6_2 --report_prefix /tmp/garak-injection-test 2>/dev/null
ls /tmp/garak-injection-test*.jsonl 2>/dev/null
```

**Evidence artifact**: garak injection probe results (JSONL) + promptfoo test results if available

---

### MANAGE 3.1–3.2 — MLOps Pipeline Security and Experiment Integrity

**What to provide**:

- MLflow server configuration showing authentication is required
- Evidence training pipeline uses pinned dependency versions
- Evidence experiment artifacts are immutable after logging

**Validation command**:

```bash
# Show MLflow auth config:
grep -r "MLFLOW_TRACKING_USERNAME\|MLFLOW_TRACKING_PASSWORD\|auth" GP-MODEL-OPS/JADE-AI/ | grep -v ".pyc" | head -10
# Show pinned requirements:
cat GP-MODEL-OPS/1-local-pipeline/requirements.txt | head -20
# Verify no unpinned versions:
grep -E ">=|~=|[^=]=[^=]" GP-MODEL-OPS/1-local-pipeline/requirements.txt | grep -v "#"
```

**Evidence artifact**: requirements.txt (pinned versions) + MLflow auth config + experiment artifact list

---

## Risk Summary Template

After the assessment call, complete this for each AI system assessed:

```
System: [JADE / KATIE / BERU]
Model: [base model + version]
Deployment: [Ollama local / SageMaker / other]

GOVERN: [PASS / PARTIAL / FAIL]
MAP:    [PASS / PARTIAL / FAIL]
MEASURE: [PASS / PARTIAL / FAIL]
MANAGE: [PASS / PARTIAL / FAIL]

OWASP LLM Top 10 Coverage:
  LLM01 (Prompt Injection): [covered by garak]
  LLM02 (Insecure Output Handling): [covered by output validation]
  LLM06 (Sensitive Information Disclosure): [covered by Presidio + access controls]
  LLM10 (Model Theft): [covered by API auth + rate limiting]

MITRE ATLAS Gaps:
  AML.T0046 (Streaming inference monitoring): NOT COVERED — open source gap
  AML.T0049 (Membership inference at scale): PARTIAL — ART covers offline testing

Overall Risk: [Low / Medium / High / Critical]
POA&M Items: [count]
```
