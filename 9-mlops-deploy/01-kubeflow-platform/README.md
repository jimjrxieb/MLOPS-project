# 01-Kubeflow Platform

Standalone KFP (Kubeflow Pipelines) deployment on Kubernetes. No full Kubeflow platform — just the components that matter.

## Contents

```
01-kubeflow-platform/
├── manifests/
│   ├── kfp-values.yaml                    ← KFP standalone Helm values (MySQL + S3)
│   ├── kserve-values.yaml                 ← KServe standalone Helm values (vLLM + KEDA)
│   └── nvidia-device-plugin-wsl2.yaml     ← NVIDIA device plugin for WSL2 (EKS only)
└── kfp-components/
    └── README.md                          ← How to write reusable pipeline components
```

## What Gets Deployed

| Component | Purpose | Namespace |
|-----------|---------|-----------|
| KFP (Kubeflow Pipelines) | Pipeline orchestration, experiment tracking, artifact lineage | `kubeflow` |
| Argo Workflows | Executes pipeline steps as K8s pods | `kubeflow` |
| MySQL | Metadata store (experiments, runs, artifacts) | `kubeflow` |
| SeaweedFS | S3-compatible artifact storage (replaces MinIO in KFP 2.16+) | `kubeflow` |
| NVIDIA device plugin | GPU visibility for K8s pods (EKS only — WSL2 uses default runtime) | `kube-system` |

## Deployed by

- `tools/deploy-kubeflow.sh` — KFP standalone install (kustomize, not Helm)
- Playbook `02-deploy-experiment-tracking.md`

## GPU Access

Two modes depending on environment:

### Docker Desktop + WSL2 (local dev)

GPU is available to ALL pods automatically — no device plugin or resource requests needed.

**Prerequisites:**
1. NVIDIA GPU driver installed on Windows (Game Ready or Studio)
2. Docker Desktop with WSL2 backend
3. NVIDIA Container Toolkit installed in WSL2:
   ```bash
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
     sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   ```
4. Docker Desktop → Settings → Docker Engine → set `default-runtime` to `nvidia`:
   ```json
   {
     "default-runtime": "nvidia",
     "runtimes": {
       "nvidia": {
         "path": "nvidia-container-runtime",
         "runtimeArgs": []
       }
     }
   }
   ```
5. Apply & Restart Docker Desktop

**Verify:** `docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi`

**Why no device plugin?** WSL2 uses `/dev/dxg` (DirectX Graphics) instead of `/dev/nvidia*`. The NVIDIA K8s device plugin requires `/dev/nvidia*` for NVML enumeration. Since `default-runtime: nvidia` makes the GPU available to every container, pods can use CUDA without requesting `nvidia.com/gpu` as a resource.

### EKS / bare-metal (production)

Use the NVIDIA device plugin so GPU is an allocatable K8s resource:

```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.17.0/deployments/static/nvidia-device-plugin.yml
```

Then KFP pipelines request GPU explicitly:
```python
train_task.set_accelerator_type("nvidia.com/gpu")
train_task.set_accelerator_limit(1)
```

## Verified On

- Docker Desktop 4.x + WSL2 + K8s v1.34.1 + RTX 5080 (16GB)
- KFP v2.16.0 (kustomize deploy, platform-agnostic)
- SeaweedFS for S3-compatible artifact storage
- 14 pods in `kubeflow` namespace
