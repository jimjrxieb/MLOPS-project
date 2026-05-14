# BERU GRC Analyst API — slim FastAPI image.
#
# This image contains ONLY the inference path: FastAPI + LangGraph agent +
# Ollama HTTP client. It does NOT contain torch/transformers/unsloth — those
# are training-only. The model itself runs in a separate `ollama` container
# (see docker-compose.yml).
#
# Build:   docker build -t beru-api:1.4 .
# Run:     docker compose up   (preferred — wires ollama + this together)

FROM python:3.11-slim AS base

# Non-root user
RUN groupadd --gid 1000 beru && useradd --uid 1000 --gid beru --create-home beru

WORKDIR /app

# Security baseline: upgrade wheel + jaraco.context before requirements install.
# wheel: CVE-2026-24049 (priv-esc); jaraco.context: CVE-2026-23949 (path traversal).
# These are pre-installed/transitive deps that won't upgrade via requirements.txt alone.
RUN pip install --no-cache-dir --upgrade "wheel>=0.46.2" "jaraco.context>=6.1.0"

# Deps (layer cache — comes after security baseline so the cache busts on CVE pins)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# App source — agent, api, core, tools, providers, mlops, knowledge/.
# .dockerignore strips training-data/, mlruns/, *.gguf, caches.
# knowledge/ (the bundled NIST 800-53 corpus + AI RMF frameworks, ~2 MB) IS
# included — that's what makes the agent self-contained, no mounts needed.
COPY --chown=beru:beru . /app/

# MLflow file-store dir. In compose this is a bind mount; create it here so
# standalone `docker run` also gets working tracking instead of degrading.
RUN mkdir -p /app/mlruns && chown -R beru:beru /app/mlruns

# No BERU_NIST_DIR / BERU_CROSSWALK_PATH here — the agent's defaults point at
# the bundled /app/knowledge/ copy. Override those env vars only if you want it
# to read a different (e.g. canonical GP-CONSULTING) checkout.
ENV BERU_MODEL=beru:v1.4 \
    OLLAMA_HOST=http://ollama:11434 \
    MLFLOW_BERU_TRACKING_URI=file:///app/mlruns \
    PYTHONUNBUFFERED=1

USER beru
EXPOSE 8088

# Health endpoint the compose healthcheck hits.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=4 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8088/api/beru/health').status==200 else 1)" || exit 1

ENTRYPOINT ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8088"]
