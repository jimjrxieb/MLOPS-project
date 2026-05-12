#!/usr/bin/env python3
"""
CKA Admin Operations Training Data Generator
==============================================
Priority 2: Control plane admin ops Katie can't do.

Targets: kubeadm, etcd backup/restore, kubelet troubleshooting,
drain/uncordon, journalctl, systemctl, cluster upgrades.

Output: ChatML JSONL → 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "cka_admin_ops.jsonl"

SYSTEM_PROMPT = "You are JADE, a CKA-certified Kubernetes administrator. Provide exact commands for cluster administration. Use canonical tool names: kubeadm, etcdctl, kubectl, kubelet, systemctl, journalctl. Always show the full command with all required flags."

def msg(system, user, assistant):
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}

def generate_etcd_examples():
    examples = []
    scenarios = [
        {
            "q": "How do you backup etcd in a kubeadm-managed cluster?",
            "a": """Backup etcd using etcdctl snapshot save:

```bash
# Find etcd pod and get cert paths
kubectl get pods -n kube-system -l component=etcd

# Backup etcd (using certs from the etcd StaticPod)
ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-backup.db \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify the backup
ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-backup.db --write-out=table
```

The `--cacert`, `--cert`, and `--key` flags are required for TLS authentication. These paths come from the kube-apiserver StaticPod manifest at `/etc/kubernetes/manifests/kube-apiserver.yaml` (look for `--etcd-cafile`, `--etcd-certfile`, `--etcd-keyfile`).

Store backups off-cluster. Automate with a CronJob or systemd timer."""
        },
        {
            "q": "How do you restore etcd from a snapshot backup?",
            "a": """Restore etcd using etcdctl snapshot restore:

```bash
# Stop the kube-apiserver (move the StaticPod manifest)
sudo mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/

# Stop etcd
sudo mv /etc/kubernetes/manifests/etcd.yaml /tmp/

# Restore the snapshot to a new data directory
ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-backup.db \\
  --data-dir=/var/lib/etcd-restored \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key

# Update the etcd StaticPod to use the new data directory
# Edit /tmp/etcd.yaml: change --data-dir=/var/lib/etcd to --data-dir=/var/lib/etcd-restored
# Also update the hostPath volume to point to /var/lib/etcd-restored

# Move StaticPod manifests back
sudo mv /tmp/etcd.yaml /etc/kubernetes/manifests/
sudo mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/

# Wait for kubelet to restart the StaticPod containers
# Verify cluster state
kubectl get nodes
kubectl get pods -A
```

Critical: The `--data-dir` must be a NEW directory (not the existing one). The kubelet will automatically restart the etcd StaticPod when the manifest is placed back."""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_kubeadm_upgrade_examples():
    examples = []
    versions = [("1.28", "1.29"), ("1.29", "1.30"), ("1.30", "1.31")]

    for old, new in versions:
        q = f"Upgrade a kubeadm cluster from {old} to {new}. Show all commands."
        a = f"""Upgrade kubeadm cluster from {old} to {new}:

**Step 1: Upgrade the control plane node**
```bash
# Update kubeadm
sudo apt-get update
sudo apt-get install -y kubeadm={new}.0-1.1

# Verify upgrade plan
sudo kubeadm upgrade plan

# Apply the upgrade (control plane first)
sudo kubeadm upgrade apply v{new}.0

# Drain the control plane node
kubectl drain <control-plane-node> --ignore-daemonsets --delete-emptydir-data

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet={new}.0-1.1 kubectl={new}.0-1.1
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Uncordon the control plane node
kubectl uncordon <control-plane-node>
```

**Step 2: Upgrade each worker node**
```bash
# On the worker node:
sudo apt-get update
sudo apt-get install -y kubeadm={new}.0-1.1
sudo kubeadm upgrade node

# On the control plane — drain the worker node:
kubectl drain <worker-node> --ignore-daemonsets --delete-emptydir-data

# On the worker node — upgrade kubelet and kubectl:
sudo apt-get install -y kubelet={new}.0-1.1 kubectl={new}.0-1.1
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# On the control plane — uncordon the worker node:
kubectl uncordon <worker-node>
```

**Key rules:**
- Always upgrade control plane first, then worker nodes
- Use `kubeadm upgrade plan` before `kubeadm upgrade apply`
- Always `drain` before upgrading kubelet, `uncordon` after
- Upgrade one minor version at a time (no skipping)
- Verify: `kubectl get nodes` — all should show v{new}.0 and Ready"""
        examples.append(msg(SYSTEM_PROMPT, q, a))

    return examples


def generate_kubelet_troubleshooting():
    examples = []
    scenarios = [
        {
            "q": "A node shows NotReady. How do you troubleshoot the kubelet?",
            "a": """Troubleshoot kubelet on a NotReady node:

**Step 1: Check node status from control plane**
```bash
kubectl describe node <node-name>
# Look for Conditions: Ready=False, MemoryPressure, DiskPressure, PIDPressure
# Look for Events section for recent errors
```

**Step 2: SSH to the node and check kubelet**
```bash
# Check kubelet service status
systemctl status kubelet

# Check kubelet logs
journalctl -u kubelet -f --no-pager -n 100

# Common errors to look for:
# - "certificate has expired" → rotate certs
# - "PLEG is not healthy" → container runtime issue
# - "failed to run Kubelet: unable to load" → config issue
# - "disk pressure" → node disk full
```

**Step 3: Check container runtime**
```bash
# For containerd
systemctl status containerd
crictl ps
crictl pods

# For Docker (legacy)
systemctl status docker
docker ps
```

**Step 4: Common fixes**
```bash
# Restart kubelet
sudo systemctl restart kubelet

# If certificate expired
sudo kubeadm certs renew all
sudo systemctl restart kubelet

# If disk pressure
df -h
sudo crictl rmi --prune
sudo journalctl --vacuum-size=500M

# If memory pressure
free -m
# Check for OOMKilled pods
kubectl get events --field-selector reason=OOMKilled
```

**Step 5: Verify recovery**
```bash
kubectl get nodes
# Node should transition back to Ready
```"""
        },
        {
            "q": "The kubelet is failing with PLEG errors. What does this mean and how do you fix it?",
            "a": """PLEG (Pod Lifecycle Event Generator) is the kubelet component that monitors pod state changes. PLEG errors mean the container runtime is not responding fast enough.

**Diagnose:**
```bash
# Check kubelet logs for PLEG
journalctl -u kubelet | grep -i "PLEG"

# Typical error:
# "PLEG is not healthy: pleg was last seen active 3m0s ago; threshold is 3m0s"

# Check container runtime health
systemctl status containerd
crictl info
```

**Common causes:**
1. **Overloaded node** — too many pods, container runtime can't keep up
2. **Slow container runtime** — containerd or Docker hanging
3. **Disk I/O saturation** — image pulls or log writes blocking
4. **Network issues** — image registry timeouts

**Fix:**
```bash
# Restart container runtime
sudo systemctl restart containerd
sudo systemctl restart kubelet

# If overloaded, drain some workloads
kubectl drain <node> --ignore-daemonsets

# Check disk I/O
iostat -x 1 5

# Clean up unused images
sudo crictl rmi --prune

# If persistent, check for pod count limits
kubectl get pods --field-selector spec.nodeName=<node> | wc -l
# Default max-pods is 110, check with:
journalctl -u kubelet | grep "max-pods"
```"""
        },
        {
            "q": "How do you drain a node safely before maintenance?",
            "a": """Use kubectl drain to safely evict workloads:

```bash
# Drain the node (evicts pods, respects PodDisruptionBudgets)
kubectl drain <node-name> \\
  --ignore-daemonsets \\
  --delete-emptydir-data \\
  --grace-period=60 \\
  --timeout=300s

# The node is now cordoned (unschedulable) and pods are evicted
kubectl get node <node-name>
# STATUS: Ready,SchedulingDisabled
```

**Perform maintenance:**
```bash
# SSH to the node
# Upgrade OS, kernel, kubelet, etc.
sudo apt-get update && sudo apt-get upgrade -y
sudo systemctl restart kubelet
```

**Return the node to service:**
```bash
# Uncordon the node (make it schedulable again)
kubectl uncordon <node-name>

# Verify
kubectl get node <node-name>
# STATUS: Ready
```

**Key flags:**
- `--ignore-daemonsets` — DaemonSet pods can't be evicted, skip them
- `--delete-emptydir-data` — allow eviction of pods with emptyDir volumes
- `--grace-period=60` — give pods 60s to shut down gracefully
- `--timeout=300s` — abort if drain takes longer than 5 minutes
- `--force` — evict pods not managed by a controller (standalone pods, NOT recommended)

**If drain hangs:** check PodDisruptionBudgets:
```bash
kubectl get pdb -A
# A PDB with maxUnavailable=0 will block drain forever
```"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_control_plane_examples():
    examples = []
    scenarios = [
        {
            "q": "What are the core Kubernetes control plane components?",
            "a": """The Kubernetes control plane consists of these core components:

**1. kube-apiserver**
- The API gateway for the entire cluster
- All `kubectl` commands go through the kube-apiserver
- Handles authentication, authorization (RBAC), and admission control
- Runs as a StaticPod at `/etc/kubernetes/manifests/kube-apiserver.yaml`

**2. etcd**
- Distributed key-value store that holds all cluster state
- Stores pod specs, ConfigMaps, Secrets, RBAC rules, node status
- Runs as a StaticPod at `/etc/kubernetes/manifests/etcd.yaml`
- Back up with: `etcdctl snapshot save`

**3. kube-scheduler**
- Assigns pods to nodes based on resource requests, taints, affinity, and constraints
- Watches for unscheduled pods via the kube-apiserver
- Runs as a StaticPod at `/etc/kubernetes/manifests/kube-scheduler.yaml`

**4. kube-controller-manager**
- Runs the core control loops: Deployment controller, ReplicaSet controller, Node controller, Job controller
- Ensures desired state matches actual state
- Runs as a StaticPod at `/etc/kubernetes/manifests/kube-controller-manager.yaml`

**5. cloud-controller-manager** (cloud environments only)
- Manages cloud-specific resources: load balancers, routes, node lifecycle
- Separates cloud logic from core Kubernetes code
- Runs as a Deployment or StaticPod depending on the cloud provider

**Worker node components:**
- **kubelet** — node agent, manages pod lifecycle, reports to kube-apiserver
- **kube-proxy** — manages network rules (iptables/IPVS) for Service routing
- **container runtime** — containerd or CRI-O, runs the actual containers"""
        },
        {
            "q": "Design a highly available Kubernetes control plane.",
            "a": """HA control plane requires multiple control plane nodes with load-balanced API access:

**Architecture:**
```
                    Load Balancer (L4/TCP)
                    ├── Control Plane 1 (kube-apiserver, etcd)
                    ├── Control Plane 2 (kube-apiserver, etcd)
                    └── Control Plane 3 (kube-apiserver, etcd)
```

**Key requirements:**

1. **Odd number of control plane nodes** — etcd requires quorum (majority)
   - 3 nodes tolerates 1 failure
   - 5 nodes tolerates 2 failures
   - Never use 2 (no quorum advantage over 1)

2. **Two topologies:**
   - **Stacked** — etcd runs on the same nodes as control plane (simpler, fewer servers)
   - **External etcd** — dedicated etcd cluster (better isolation, harder to manage)

3. **Load balancer** in front of all kube-apiserver instances
   - HAProxy, NGINX, or cloud LB (NLB on AWS)
   - Health check: TCP port 6443

**Setup with kubeadm:**
```bash
# Initialize first control plane
sudo kubeadm init \\
  --control-plane-endpoint "lb.example.com:6443" \\
  --upload-certs

# Join additional control plane nodes
sudo kubeadm join lb.example.com:6443 \\
  --token <token> \\
  --discovery-token-ca-cert-hash sha256:<hash> \\
  --control-plane \\
  --certificate-key <cert-key>

# Verify etcd cluster health
ETCDCTL_API=3 etcdctl member list \\
  --endpoints=https://127.0.0.1:2379 \\
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \\
  --cert=/etc/kubernetes/pki/etcd/server.crt \\
  --key=/etc/kubernetes/pki/etcd/server.key
```

**Verify HA:**
```bash
kubectl get nodes
# All control plane nodes should show Ready
# Stop one control plane — cluster should continue operating
```"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def generate_storage_examples():
    examples = []
    scenarios = [
        {
            "q": "Explain static vs dynamic PersistentVolume provisioning.",
            "a": """**Static provisioning** — admin creates PersistentVolume manually:

```yaml
# PV created manually by admin
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-static
spec:
  capacity:
    storage: 10Gi
  accessModes:
  - ReadWriteOnce
  storageClassName: manual
  hostPath:
    path: /data/pv-static
---
# PVC binds to the PV
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-static
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: manual
  resources:
    requests:
      storage: 10Gi
```

**Dynamic provisioning** — StorageClass creates PV automatically:

```yaml
# StorageClass with provisioner
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
reclaimPolicy: Delete
allowVolumeExpansion: true
---
# PVC triggers automatic PV creation
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-dynamic
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 20Gi
```

**Key differences:**
- Static: PV created manually before PVC. Good for pre-provisioned storage.
- Dynamic: StorageClass provisioner creates PV on demand. Standard for cloud.
- `reclaimPolicy: Retain` keeps data after PVC deletion (safe for production)
- `reclaimPolicy: Delete` removes the backing storage (default, use with caution)
- `allowVolumeExpansion: true` lets you grow PVCs without recreating them"""
        },
        {
            "q": "How do you expand a PVC that is already in use?",
            "a": """Expand a PVC in-place (requires StorageClass with `allowVolumeExpansion: true`):

**Step 1: Verify the StorageClass allows expansion**
```bash
kubectl get storageclass
# Check for ALLOWVOLUMEEXPANSION=true
```

If not enabled, patch it:
```bash
kubectl patch storageclass <name> -p '{"allowVolumeExpansion": true}'
```

**Step 2: Edit the PVC to increase storage**
```bash
kubectl edit pvc my-pvc
# Change spec.resources.requests.storage from 10Gi to 20Gi
```

Or patch directly:
```bash
kubectl patch pvc my-pvc -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

**Step 3: Restart the pod to pick up the expansion**
```bash
# Some CSI drivers support online expansion, but many require pod restart
kubectl delete pod <pod-using-pvc>
# The Deployment/StatefulSet will recreate the pod

# Verify
kubectl get pvc my-pvc
# CAPACITY should show 20Gi
kubectl exec <new-pod> -- df -h /mount-path
```

**Important:**
- PVC expansion only works if the StorageClass has `allowVolumeExpansion: true`
- You can only increase size, never decrease
- Some volume types require pod restart for the filesystem to expand
- EBS, GCE PD, and Azure Disk all support online expansion via CSI"""
        },
    ]
    for s in scenarios:
        examples.append(msg(SYSTEM_PROMPT, s["q"], s["a"]))
    return examples


def main():
    all_examples = []

    print("[1/5] Generating etcd backup/restore examples...")
    all_examples.extend(generate_etcd_examples())

    print("[2/5] Generating kubeadm upgrade examples...")
    all_examples.extend(generate_kubeadm_upgrade_examples())

    print("[3/5] Generating kubelet troubleshooting examples...")
    all_examples.extend(generate_kubelet_troubleshooting())

    print("[4/5] Generating control plane component examples...")
    all_examples.extend(generate_control_plane_examples())

    print("[5/5] Generating storage admin examples...")
    all_examples.extend(generate_storage_examples())

    random.shuffle(all_examples)

    from generate_utils import write_training_data
    write_training_data(
        examples=all_examples,
        output_file=OUTPUT_FILE,
        generator="generate_cka_admin_ops.py",
        domain="CKA",
    )


if __name__ == "__main__":
    main()
