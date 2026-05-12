# Playbook 02a — Kubeflow on Docker Desktop (WSL2 + GPU)

> Complete setup guide for running KFP training pipelines with GPU on Docker Desktop.
> Covers every fix and adjustment discovered during initial deployment.
> **When:** Before Playbook 02 on a Docker Desktop environment
> **Time:** 1-2 hours (including image pulls)

---

## Prerequisites

- [ ] Windows 11 with WSL2
- [ ] Docker Desktop installed with Kubernetes enabled
- [ ] NVIDIA GPU with Windows driver installed (Game Ready or Studio)
- [ ] `kubectl` and `helm` available in WSL2

---

## Phase 1: Enable GPU for Docker Desktop K8s

Docker Desktop supports GPU via the NVIDIA Container Toolkit, but K8s pods need extra config.

### 1a. Install NVIDIA Container Toolkit in WSL2

```bash
# Add NVIDIA package repo
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
```

### 1b. Set NVIDIA as Default Runtime

**Docker Desktop → Settings → Docker Engine** — replace the JSON with:

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
```

Click **Apply & Restart**.

> **Important:** Add the `default-runtime` and `runtimes` keys INSIDE the existing JSON block.
> Docker Desktop will revert manual edits to `~/.docker/daemon.json` — you MUST use the UI editor.

### 1c. Verify GPU in Docker

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
# Should show your GPU (e.g., RTX 5080)
```

### 1d. Why No NVIDIA Device Plugin?

WSL2 uses `/dev/dxg` (DirectX Graphics) instead of `/dev/nvidia*`. The NVIDIA K8s device plugin requires `/dev/nvidia*` for NVML device enumeration, so it reports "No devices found" on WSL2.

**This is fine.** Since `default-runtime: nvidia` is set, every pod gets GPU access automatically. You just can't use `resources.limits: nvidia.com/gpu: 1` in pod specs — the GPU is implicitly available.

On EKS or bare metal, deploy the device plugin and use explicit GPU requests.

---

## Phase 2: Switch kubectl Context

Docker Desktop creates its own context. Make sure you're on it:

```bash
kubectl config use-context docker-desktop
kubectl get nodes
# NAME             STATUS   ROLES           AGE   VERSION
# docker-desktop   Ready    control-plane   ...   v1.34.1
```

---

## Phase 3: Deploy KFP

```bash
# Use the deploy script (kustomize-based, not Helm)
bash tools/deploy-kubeflow.sh --namespace kubeflow
```

**What happens:**
1. Creates `kubeflow` namespace
2. Applies CRDs (Argo Workflows, KFP)
3. Deploys 14 pods: API server, UI, Argo, MySQL, SeaweedFS, metadata, cache

**First deploy takes 5-10 minutes** as images pull. Expect `CrashLoopBackOff` on `metadata-grpc` and `ml-pipeline` while MySQL starts — they self-heal.

```bash
# Watch until all 14 pods are Running
kubectl get pods -n kubeflow -w
```

---

## Phase 4: Access KFP

```bash
# KFP UI
kubectl port-forward svc/ml-pipeline-ui -n kubeflow 8888:80 &
# → http://localhost:8888

# KFP API (for Python SDK)
kubectl port-forward svc/ml-pipeline -n kubeflow 8887:8888 &

# SeaweedFS S3 (for uploading training data)
kubectl port-forward svc/seaweedfs -n kubeflow 8333:8333 &

# Verify API
curl http://localhost:8887/apis/v2beta1/healthz
```

**Install Python SDK:**
```bash
pip install kfp==2.16.0
```

---

## Phase 5: Build CUDA Training Image

KFP lightweight components use `base_image` + `packages_to_install`. The training step needs CUDA + Python:

```bash
# Build local image (16 seconds, ~400MB)
cat << 'EOF' | docker build -t kfp-cuda-python:v1 -f - .
FROM nvidia/cuda:12.1.0-base-ubuntu22.04
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip && \
    rm -rf /var/lib/apt/lists/* && \
    ln -s /usr/bin/python3 /usr/bin/python
EOF
```

> **Critical:** Tag with a version (`:v1`), NOT `:latest`. K8s uses `IfNotPresent` pull policy for tagged images, `Always` for `:latest`. Since this is a local-only image, `:latest` causes `ImagePullBackOff`.

---

## Phase 6: Upload Training Data to SeaweedFS

KFP pods can't access your local filesystem. Training data must be in SeaweedFS (S3-compatible):

```python
import boto3

s3 = boto3.client('s3',
    endpoint_url='http://localhost:8333',
    aws_access_key_id='minio',         # default KFP creds
    aws_secret_access_key='minio123',
    region_name='us-east-1',
)

# Create bucket
s3.create_bucket(Bucket='ml-artifacts')

# Upload training chunk
s3.upload_file('1-data-pipeline/03-chunked-untrained/chunk_0005_10k.jsonl',
               'ml-artifacts', 'training-data/chunk_0005_10k.jsonl')
```

**SeaweedFS creds:** `minio` / `minio123` (from `mlpipeline-minio-artifact` secret in kubeflow namespace).

---

## Phase 7: Submit Training Pipeline

```bash
python3 02-training-pipeline/kfp/train_chunk5_kfp.py
# → View at http://localhost:8888/#/runs/details/<run-id>
```

The pipeline DAG in the UI shows:
1. **download_training_data** — pulls from SeaweedFS
2. **validate_data** — quality gates (format, scope, content)
3. **etl_and_chunk** — dedup, shuffle, split holdout
4. **train_lora** — LoRA fine-tune on GPU (Unsloth, 4-bit quantized)

Each step logs metrics visible in the KFP UI (click a step → Metrics tab).

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Unsloth cannot find any torch accelerator` | Base image has no CUDA libs | Use `kfp-cuda-python:v1` (CUDA + Python) |
| `ImagePullBackOff` on local image | `:latest` tag forces pull from registry | Tag with version: `kfp-cuda-python:v1` |
| `exit status 127` | Base image has no `python3` | Use `kfp-cuda-python:v1`, not `nvidia/cuda:*-base-*` |
| `libnvidia-ml.so.1: cannot open shared object` | WSL2 NVIDIA libs not mounted | Set `default-runtime: nvidia` in Docker Engine settings |
| Port-forward dies | Docker Desktop restart / pod recycling | Re-run `kubectl port-forward` commands |
| `CrashLoopBackOff` on metadata-grpc | MySQL not ready yet | Wait 2-3 min — self-heals when MySQL starts |
| `No devices found` from device plugin | WSL2 uses `/dev/dxg`, not `/dev/nvidia*` | Don't use device plugin on WSL2 — GPU is implicit |
| KFP UI shows stale data | Browser cache | Hard refresh (Ctrl+Shift+R) |

---

## What's Different from EKS

| Aspect | Docker Desktop WSL2 | EKS |
|--------|---------------------|-----|
| GPU access | Implicit (`default-runtime: nvidia`) | Explicit (`nvidia.com/gpu: 1` resource request) |
| Device plugin | Not needed (won't work on WSL2) | Required (NVML enumeration) |
| S3 storage | SeaweedFS in-cluster | AWS S3 with IRSA |
| MySQL | In-cluster (KFP-managed) | RDS recommended |
| Training image | Local `kfp-cuda-python:v1` | ECR or nvcr.io/nvidia/pytorch |
| Node scaling | Single node (your laptop) | Karpenter spot `g5.xlarge` |
| Image pull | Local Docker store | ECR / nvcr.io registry |

---

## Verified Configuration

| Component | Version/Detail |
|-----------|---------------|
| Docker Desktop | 4.x with WSL2 backend |
| Kubernetes | v1.34.1 |
| GPU | NVIDIA GeForce RTX 5080 (16GB) |
| KFP | v2.16.0 (kustomize deploy) |
| KFP SDK | kfp==2.16.0 |
| Training image | `kfp-cuda-python:v1` (CUDA 12.1 + Python 3.10) |
| Artifact storage | SeaweedFS (S3-compatible, in-cluster) |
| Creds | `minio` / `minio123` |

---

## Next Steps

| Done | Next |
|------|------|
| KFP + GPU verified | Playbook `02` — Create experiments, submit pipelines |
| Training pipeline works | Playbook `05` — Full training lifecycle |
| Want model serving | Playbook `08` — KServe + vLLM |
