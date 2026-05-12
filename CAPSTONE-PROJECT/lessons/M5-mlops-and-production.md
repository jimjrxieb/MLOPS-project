# M5 — MLOps and Production

> **Goal:** Get BERU out of a Python script and into a running service with tracked experiments and CI gates.
> **Build:** Ollama model registered, FastAPI `/api/beru` endpoint, MLflow eval tracking, GitHub Actions gate.
> **Gate:** CI passes on every push. Endpoint responds. MLflow shows the eval run.

---

## What MLOps Actually Is

MLOps is the practices that keep ML systems alive after they ship. Regular software has DevOps — CI/CD, monitoring, deployment pipelines. ML adds a layer: model versions, training pipelines, eval gates, data drift. MLOps is the union.

Without MLOps, a model is a file on someone's laptop. With MLOps:
- Every training run is tracked (MLflow)
- Promotion only happens if eval passes (CI gate)
- The running model is versioned and auditable
- Quality drift triggers alerts

**The analogy:** MLOps is quality control at a manufacturing plant. Every batch of product (model version) is tested before it ships. Failed batches are logged and don't leave the factory. The production line (training pipeline) has checkpoints at each stage. Nothing goes to customers that didn't pass inspection.

For BERU, this matters because it's a compliance tool. A BERU that ships a wrong finding is worse than no BERU — it creates false confidence. The eval gate is the inspector at the factory door.

---

## Concept 1 — Ollama and the Modelfile

Ollama is the local model server. You register a model with a Modelfile and Ollama serves it via HTTP on port 11434.

```bash
# Register BERU
ollama create beru:v1.0 -f BERU-AI/Modelfile_beru3b

# List registered models
ollama list

# Run BERU interactively
ollama run beru:v1.0

# Call BERU via HTTP (same API as OpenAI)
curl http://localhost:11434/api/chat -d '{
  "model": "beru:v1.0",
  "messages": [{"role": "user", "content": "Assess: SI-2 — no patch management documented"}],
  "stream": false
}'
```

### Model versioning with Ollama

When you fine-tune a new version:
1. Convert weights to GGUF: `python3 1-data-pipeline/convert_gguf.py`
2. Update `Modelfile_beru3b` to point `FROM ./beru-llama3b-v1.1.gguf`
3. `ollama create beru:v1.1 -f BERU-AI/Modelfile_beru3b`
4. Run eval suite against `beru:v1.1`
5. If it passes → promote. `ollama tag beru:v1.1 beru:latest`

Old version stays available (`beru:v1.0`) for rollback. Never delete a model that's passed eval until you're sure the new one works in production.

---

## Concept 2 — FastAPI Endpoint

FastAPI is the web framework. The GP-API already runs on port 8000. You're adding one route: `/api/beru`.

Look at the existing JADE route as the pattern: `GP-INFRA/GP-API/routes/jade.py`. BERU's route follows the same shape.

```python
# GP-INFRA/GP-API/routes/beru.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx

router = APIRouter(prefix="/api/beru", tags=["beru"])

class BeruRequest(BaseModel):
    scanner: str          # "trivy" | "kube-bench" | "prowler" | ...
    input: str            # raw scanner output
    system_name: Optional[str] = "unknown"
    run_id: Optional[str] = None

class BeruResponse(BaseModel):
    findings: list
    poam_draft: str
    ciso_summary: str
    hitl_pending: list    # queue IDs of B/S findings
    run_id: str

@router.post("/assess", response_model=BeruResponse)
async def assess(request: BeruRequest):
    """Run BERU assessment on scanner output."""
    try:
        # Call the BERU agent
        result = run_beru_agent(
            scanner=request.scanner,
            raw_input=request.input,
            system_name=request.system_name,
        )
        return BeruResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    # Check Ollama has beru:v1.0 loaded
    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:11434/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]
    beru_loaded = any("beru" in m for m in models)
    return {"status": "ok" if beru_loaded else "degraded", "beru_model": beru_loaded}
```

### Wiring it into main.py

```python
# GP-INFRA/GP-API/main.py — add one line
from routes import jade, beru  # add beru

app.include_router(jade.router)
app.include_router(beru.router)  # add this
```

Test it:
```bash
# Start the API
cd GP-INFRA && uvicorn GP-API.main:app --reload --port 8000

# Call BERU
curl -X POST http://localhost:8000/api/beru/assess \
  -H "Content-Type: application/json" \
  -d '{"scanner": "trivy", "input": "{...}", "system_name": "NovaSec Cloud"}'
```

---

## Concept 3 — MLflow Experiment Tracking

MLflow records every training and eval run so you can compare model versions, reproduce results, and answer the auditor question: "Why did you promote this version over the last one?"

### The pattern (same as JADE-AI uses)

```python
import mlflow

with mlflow.start_run(run_name="beru-eval-v1.0"):
    # Log what you tested with
    mlflow.log_param("model", "beru:v1.0")
    mlflow.log_param("eval_questions", 30)
    mlflow.log_param("eval_suite", "grc-30q-v1")

    # Run your eval
    results = run_eval_suite("beru:v1.0", questions)

    # Log what you got
    mlflow.log_metric("overall_accuracy", results["overall"])
    mlflow.log_metric("ac_family_accuracy", results["AC"])
    mlflow.log_metric("si_family_accuracy", results["SI"])
    mlflow.log_metric("hallucinated_ids", results["hallucinations"])

    # Log the full results as an artifact
    mlflow.log_artifact("eval_results.json")
```

### Starting the MLflow UI

```bash
mlflow ui --backend-store-uri file:///home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/JADE-AI/mlruns/
# Open http://localhost:5000
```

You'll see every run, params, metrics, and the promotion decision. This is what you show the auditor.

**The experiment name for BERU:** `beru-eval`. Every run goes into this experiment so you can compare v1.0 vs v1.1 side-by-side.

---

## Concept 4 — GitHub Actions Eval Gate

The eval gate runs automatically on every push to `main`. If BERU's eval score drops below the threshold, the push is blocked.

```yaml
# .github/workflows/beru-eval.yml
name: BERU Eval Gate

on:
  push:
    branches: [main]
    paths:
      - 'GP-MODEL-OPS/BERU-AI/**'  # only run when BERU changes

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r GP-MODEL-OPS/BERU-AI/requirements.txt

      - name: Run data quality gate
        run: |
          cd GP-MODEL-OPS
          python3 -m pytest 8-tests/test_data_quality.py -v

      - name: Run BERU core tests
        run: |
          cd GP-MODEL-OPS
          python3 -m pytest 8-tests/test_beru_core.py 8-tests/test_beru_tools.py -v

      # Full eval suite requires Ollama GPU — run separately on self-hosted runner
      # or as a scheduled job, not on every push
```

**Why the full eval isn't on every push:** The eval suite needs Ollama + beru:v1.0 loaded, which requires a GPU runner. GitHub's free runners don't have GPUs. The compromise: run the unit/integration tests on every push, run the full eval suite on a schedule or self-hosted runner.

---

## Concept 5 — Docker and Kubernetes Basics (for the resume)

You don't need to build a full K8s deployment for BERU today — `jsa-kubestar` is already deployed on the cluster. But you need to be able to talk about it.

### What a BERU Dockerfile would look like

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (Docker layer caching)
COPY GP-MODEL-OPS/BERU-AI/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY GP-MODEL-OPS/BERU-AI/ ./BERU-AI/

# Non-root user (security-standards.md rule 17)
RUN useradd -r -u 1000 beru
USER beru

# Ollama is a sidecar — BERU calls it via HTTP, doesn't contain it
ENV OLLAMA_URL=http://ollama:11434

CMD ["python3", "BERU-AI/agent.py", "--serve"]
```

### K8s minimal manifest for BERU

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: beru
spec:
  replicas: 1
  selector:
    matchLabels:
      app: beru
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: beru
          image: gp-copilot/beru:v1.0
          resources:
            requests: { cpu: "500m", memory: "512Mi" }
            limits: { cpu: "2", memory: "2Gi" }
          livenessProbe:
            httpGet:
              path: /api/beru/health
              port: 8000
```

This shows you understand non-root containers, resource limits, and health probes — the three things reviewers look for in K8s manifests.

---

## Troubleshooting M5

| Symptom | Cause | Fix |
|---------|-------|-----|
| `404 Not Found` on `/api/beru/assess` | Route not registered in `main.py` | Add `app.include_router(beru.router)` |
| MLflow `Run not found` | Tracking URI wrong | Set `mlflow.set_tracking_uri("file:///...")` with absolute path |
| GitHub Actions fails on import | BERU-AI not in PYTHONPATH | Add `sys.path.insert(0, "GP-MODEL-OPS")` in the test file |
| Eval runs but accuracy is 0 | Model not loaded in Ollama | CI needs Ollama running — use `ollama serve &` before the eval step |
| FastAPI 500 on large scanner inputs | Context overflow | Truncate scanner output to ~4,000 tokens before sending to model |
| `ollama: command not found` in container | Ollama needs to be a sidecar | Don't install Ollama in the BERU container — it's a separate service on `localhost:11434` |

---

## What You Build

Four artifacts:
1. `ollama create beru:v1.0 -f BERU-AI/Modelfile_beru3b` — model registered
2. `GP-INFRA/GP-API/routes/beru.py` — FastAPI route, health check, assess endpoint
3. MLflow run logged under experiment `beru-eval` with the 30-question results
4. `.github/workflows/beru-eval.yml` — CI gate running unit + integration tests

**The demo test:**
```bash
curl http://localhost:8000/api/beru/health
# {"status": "ok", "beru_model": true}

curl -X POST http://localhost:8000/api/beru/assess \
  -H "Content-Type: application/json" \
  -d '{"scanner": "trivy", "input": "...", "system_name": "NovaSec Cloud"}'
# {"findings": [...], "poam_draft": "...", "ciso_summary": "..."}
```

**3PAO question this answers:** "How do you know BERU v1.0 is better than the base model? How do you prevent a bad version from reaching production?"
Your answer: "Every model version runs the 30-question eval suite, logged in MLflow. The GitHub Actions workflow blocks merges if the test suite fails. We have eval scores for every promoted version going back to the beginning."

---

## Control Traceability

> When an auditor asks "how do you know the model in production is the one you evaluated?" — point here.

**NIST 800-53:**

| Control | What it maps to in M5 | Audit answer |
|---------|----------------------|--------------|
| **AU-3** — Content of Audit Records | MLflow logs model version, eval score, training data hash, and timestamp for every promoted model | "Every BERU version has an MLflow run ID. The run contains: eval scores, data version, hyperparams, and the artifact sha256. Nothing is inferred." |
| **SI-7** — Software, Firmware, and Information Integrity | `EvidencePackager` generates sha256 checksums for every artifact in the evidence ZIP — the manifest is tamper-evident | "The evidence package for every assessment run includes a `manifest.json` with sha256 for each file. The archive itself has a detached `.sha256` checksum." |
| **CM-3** — Configuration Change Control | GitHub Actions `beru-eval.yml` blocks merge if the test suite fails — no version ships without passing the gate | "The CI pipeline enforces the eval gate. A PR that breaks the test suite or drops coverage below threshold cannot be merged." |
| **CA-7** — Continuous Monitoring | MLflow inference tracking logs every BERU API call in production — latency, model version, rank decision | "Production BERU logs every inference to MLflow. We can see if response quality drops after a model update without waiting for an audit." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **MANAGE-4.1** — Post-deployment risk monitoring | MLflow inference tracker captures model version, latency, and rank distribution in production — regressions are visible | "Post-deployment monitoring is live from day one. MLflow shows if BERU starts producing more B-rank escalations than expected." |
| **MEASURE-4.1** — Measurable performance metrics tracked over time | Eval score history in `5-experiments/` lets us compare every deployed version on the same benchmark | "We have a baseline eval score from M1 (base 3B model) and a post-training score from M3. Every future version is measured against the same 30 questions." |
