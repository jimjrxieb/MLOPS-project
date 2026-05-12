#!/usr/bin/env python3
"""
Foundational Knowledge Training Data Generator
================================================
Deep "how stuff works" knowledge that makes security click.

Like studying for Security+ — understanding networking makes
securing networks intuitive. Understanding SQL makes SQL injection obvious.

Categories:
1. Linux fundamentals (namespaces, cgroups, capabilities, syscalls)
2. Networking fundamentals (OSI model, TCP/IP, DNS, TLS, mTLS)
3. Container fundamentals (what a container actually IS)
4. Kubernetes internals (how scheduling, networking, storage actually work)
5. Cryptography basics (hashing, encryption, signing, certificates)
6. Database & application fundamentals (SQL, HTTP, APIs, auth)
7. Cloud fundamentals (IAM, VPC, shared responsibility)

Output: 1-data-pipeline/01-raw-data-lake/
"""
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "1-data-pipeline" / "01-raw-data-lake"
OUTPUT_FILE = OUTPUT_DIR / "foundational_knowledge.jsonl"

SYSTEM_PROMPT = "You are JADE, a security educator who teaches by building understanding from fundamentals. Explain how things work at a deep level — not just definitions, but mechanisms. When you understand how something works, you understand how to break it and how to defend it."


def msg(user, assistant):
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant}
    ]}


def generate_linux_fundamentals():
    """Linux kernel concepts that make container security intuitive."""
    return [
        msg("What are Linux namespaces and why do containers need them?",
            """Linux namespaces are a kernel feature that creates isolated views of system resources. Each namespace type isolates a different resource:

**The 7 namespace types:**

| Namespace | Isolates | Why containers need it |
|-----------|----------|----------------------|
| **PID** | Process IDs | Container sees only its own processes (PID 1 = its entrypoint) |
| **NET** | Network stack | Container gets its own IP, ports, routing table |
| **MNT** | Filesystem mounts | Container sees only its own filesystem tree |
| **UTS** | Hostname | Container can have its own hostname |
| **IPC** | Inter-process communication | Shared memory, semaphores isolated |
| **USER** | User/group IDs | UID 0 inside container ≠ UID 0 on host (with user namespaces) |
| **CGROUP** | Cgroup root | Container sees only its own resource limits |

**How it works:**
```bash
# A container is just a process in multiple namespaces
# When Docker runs a container, it calls:
unshare --pid --net --mnt --uts --ipc --user /bin/sh

# The process thinks it's alone on the machine
# But it's still running on the same kernel as the host
```

**Why this matters for security:**
- `privileged: true` in Kubernetes disables namespace isolation → container can see host processes, network, filesystem
- `hostPID: true` shares the PID namespace → container can see and signal host processes
- `hostNetwork: true` shares the NET namespace → container uses the host's IP and ports
- Breaking out of a container = escaping these namespaces back to the host

**The key insight:** A container is NOT a VM. It's a process with restricted views. The kernel is shared. That's why kernel exploits are the #1 container escape vector."""),

        msg("What are Linux capabilities and why do we drop ALL of them in Kubernetes?",
            """Linux capabilities split root's power into ~40 individual permissions. Instead of "all or nothing" root, a process can have specific capabilities.

**Common capabilities and what they allow:**

| Capability | What it allows | Security risk |
|-----------|---------------|---------------|
| `CAP_NET_RAW` | Raw sockets, packet sniffing | Network eavesdropping, ARP spoofing |
| `CAP_SYS_ADMIN` | Mount filesystems, set hostname, load kernel modules | Near-root access, container escape |
| `CAP_SYS_PTRACE` | Trace/debug other processes | Read memory of other containers |
| `CAP_NET_BIND_SERVICE` | Bind to ports below 1024 | Usually harmless, often needed |
| `CAP_CHOWN` | Change file ownership | Modify protected files |
| `CAP_SETUID` | Change user ID | Privilege escalation |
| `CAP_DAC_OVERRIDE` | Bypass file permission checks | Read/write any file |
| `CAP_KILL` | Send signals to any process | Kill other containers' processes |

**Why "drop ALL" is the standard:**
```yaml
securityContext:
  capabilities:
    drop:
    - ALL
    add:
    - NET_BIND_SERVICE  # Only add back what's needed
```

By default, Docker gives containers 14 capabilities including `CAP_NET_RAW`, `CAP_CHOWN`, `CAP_SETUID`. These are attack vectors:
- `CAP_NET_RAW` → attacker can ARP spoof within the pod network
- `CAP_SYS_PTRACE` → attacker can read secrets from other containers' memory
- `CAP_SETUID` → attacker can escalate to root inside the container

**The principle:** Start with zero capabilities, add back only what the application needs. Most applications need zero additional capabilities. A web server might need `NET_BIND_SERVICE` for port 80 — that's it.

**How to check what a running container has:**
```bash
kubectl exec <pod> -- cat /proc/1/status | grep Cap
# CapEff shows effective capabilities as a hex bitmap
# Decode with: capsh --decode=<hex>
```"""),

        msg("What are Linux cgroups and how do they enforce resource limits in Kubernetes?",
            """Cgroups (control groups) are a Linux kernel feature that limits, accounts for, and isolates resource usage (CPU, memory, I/O, network) of processes.

**How cgroups work:**
```
/ (root cgroup)
├── kubepods/
│   ├── burstable/
│   │   ├── pod-abc123/
│   │   │   ├── container-1/ → limits: 500m CPU, 256Mi memory
│   │   │   └── container-2/ → limits: 200m CPU, 128Mi memory
│   │   └── pod-def456/
│   └── guaranteed/
│       └── pod-ghi789/ → requests == limits (QoS: Guaranteed)
└── system.slice/
    ├── kubelet.service
    └── containerd.service
```

**What Kubernetes resource limits actually do:**
```yaml
resources:
  requests:
    cpu: 100m      # Scheduler uses this to find a node with capacity
    memory: 128Mi  # Scheduler reservation, also sets cgroup minimum
  limits:
    cpu: 500m      # Kernel throttles beyond this (CPU is compressible)
    memory: 256Mi  # Kernel OOM-kills if exceeded (memory is NOT compressible)
```

- `requests.cpu` → `cpu.shares` in cgroup (proportional, not hard limit)
- `limits.cpu` → `cpu.cfs_quota_us` in cgroup (hard throttle)
- `limits.memory` → `memory.limit_in_bytes` in cgroup (OOM kill if exceeded)

**Why this matters for security:**
1. **Without limits, one pod can starve the node** — crypto miner uses 100% CPU, legitimate pods can't schedule
2. **Memory limits prevent OOM bombs** — a memory leak in one container can't crash the entire node
3. **QoS classes determine eviction order:**
   - Guaranteed (requests == limits) → evicted last
   - Burstable (requests < limits) → evicted second
   - BestEffort (no requests/limits) → evicted first

**The key insight:** Resource limits aren't just performance tuning — they're security boundaries. A ResourceQuota per namespace prevents one team from consuming all cluster resources. A LimitRange sets defaults so no pod runs without limits."""),

        msg("What is seccomp and how does it restrict system calls in containers?",
            """Seccomp (Secure Computing Mode) is a Linux kernel feature that restricts which system calls a process can make. System calls are the interface between userspace and the kernel — every file open, network connection, and process creation is a syscall.

**How it works:**
1. A seccomp profile defines a whitelist/blacklist of allowed syscalls
2. The kernel checks every syscall against the profile
3. Blocked syscalls return an error (or kill the process)

**Kubernetes seccomp profiles:**

```yaml
# RuntimeDefault — recommended baseline
securityContext:
  seccompProfile:
    type: RuntimeDefault
```

The `RuntimeDefault` profile blocks ~44 dangerous syscalls including:
- `mount` — prevents filesystem manipulation
- `ptrace` — prevents debugging other processes
- `init_module` / `delete_module` — prevents loading kernel modules
- `reboot` — prevents rebooting the host
- `clock_settime` — prevents time manipulation

**Why this matters:**
- A container exploit needs syscalls to escalate privileges
- `ptrace` → read other containers' memory
- `mount` → access host filesystem
- `init_module` → load a kernel backdoor
- Seccomp blocks the exploit chain at the kernel level

**The three levels:**
- `Unconfined` — no restrictions (dangerous, default before K8s 1.27)
- `RuntimeDefault` — blocks known-dangerous syscalls (recommended)
- `Localhost` — custom profile (maximum security, needs tuning)

**How Falco uses this:**
Falco monitors syscalls at the kernel level using eBPF. When a process makes a syscall that matches a FalcoRule condition (like `execve` for a shell), Falco generates an alert. Seccomp blocks the syscall entirely — they work together: Falco detects, seccomp prevents."""),

        msg("What is AppArmor and how does it differ from seccomp?",
            """AppArmor and seccomp are both Linux security modules, but they operate at different levels:

**Seccomp** = restricts WHICH system calls a process can make
**AppArmor** = restricts WHAT RESOURCES a process can access (files, network, capabilities)

Think of it like:
- Seccomp = "you can't use the `mount` verb at all"
- AppArmor = "you can read /etc/config but not write to /etc/shadow"

**AppArmor profiles work on paths:**
```
# /etc/apparmor.d/my-profile
profile my-container flags=(attach_disconnected) {
  # Allow reading app files
  /app/** r,

  # Allow writing to tmp only
  /tmp/** rw,

  # Deny everything in /etc except config
  deny /etc/shadow r,
  deny /etc/gshadow r,

  # Deny raw network (no packet sniffing)
  deny network raw,

  # Deny mount operations
  deny mount,
}
```

**Comparison:**

| Feature | Seccomp | AppArmor |
|---------|---------|----------|
| Controls | System calls (kernel API) | File paths, network, capabilities |
| Granularity | "Can you call mount()?" | "Can you read /etc/shadow?" |
| Default in K8s | RuntimeDefault since 1.27 | None (must configure) |
| Performance | Near-zero overhead (BPF) | Low overhead |
| Complexity | Simple (allow/deny syscalls) | Medium (path-based rules) |

**Defense in depth:**
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault          # Blocks dangerous syscalls
  appArmorProfile:
    type: Localhost
    localhostProfile: k8s-restrict # Blocks dangerous file access
  readOnlyRootFilesystem: true     # Blocks all filesystem writes
  capabilities:
    drop: [ALL]                    # Drops all Linux capabilities
```

Each layer catches what the others miss. Seccomp blocks the syscall. AppArmor blocks the file access. ReadOnlyRootFilesystem blocks the write. Capabilities block the privilege. An attacker has to bypass ALL of them."""),
    ]


def generate_networking_fundamentals():
    """Networking concepts that make network security intuitive."""
    return [
        msg("Explain the OSI model and why it matters for Kubernetes security.",
            """The OSI model has 7 layers. Each layer is a potential attack surface:

```
Layer 7: Application  (HTTP, gRPC, DNS)     ← WAF, API gateway, SAST
Layer 6: Presentation (TLS, encoding)       ← Certificate management, mTLS
Layer 5: Session      (connections)          ← Session hijacking, timeouts
Layer 4: Transport    (TCP, UDP)            ← NetworkPolicy, port filtering
Layer 3: Network      (IP, routing)         ← CNI, pod CIDR, node CIDR
Layer 2: Data Link    (MAC, ARP)            ← ARP spoofing (CAP_NET_RAW)
Layer 1: Physical     (cables, radio)       ← Physical access, air-gapped
```

**In Kubernetes, here's where security controls live:**

**Layer 3-4 (Network/Transport):**
- NetworkPolicy operates at L3/L4 — filters by IP, namespace, port, protocol
- Calico/Cilium CNI plugins implement the actual packet filtering
- kube-proxy manages iptables/IPVS rules for Service routing

**Layer 6-7 (TLS/Application):**
- mTLS (Istio PeerAuthentication) encrypts and authenticates at L6
- Ingress controllers terminate TLS at L7
- Service mesh provides L7 routing (path-based, header-based)

**Why this matters:**
- NetworkPolicy can block traffic by IP/port (L4) but can't inspect HTTP headers (L7)
- An attacker inside the cluster network can reach any pod on any port unless NetworkPolicy blocks it at L3/L4
- mTLS prevents eavesdropping even if the attacker is on the same network (L6)
- A WAF (Web Application Firewall) inspects L7 (HTTP content) — catches SQL injection, XSS

**The key insight:** Security must operate at every layer. NetworkPolicy alone won't stop SQL injection (L7 attack). A WAF alone won't stop port scanning (L3/L4 attack). Defense in depth = controls at every OSI layer."""),

        msg("How does DNS work in Kubernetes? Why is it a security concern?",
            """Every pod in Kubernetes gets DNS resolution via CoreDNS. Understanding the flow reveals the attack surface:

**DNS resolution path:**
```
1. Pod makes DNS query for "api-service.production.svc.cluster.local"
2. Pod's /etc/resolv.conf points to CoreDNS ClusterIP (usually 10.96.0.10)
3. CoreDNS receives the query
4. CoreDNS checks its cache, then the Kubernetes API for Service/Endpoints
5. Returns the ClusterIP (for Service) or Pod IPs (for headless Service)
6. Pod connects to the returned IP
```

**The /etc/resolv.conf in every pod:**
```
nameserver 10.96.0.10           # CoreDNS ClusterIP
search production.svc.cluster.local svc.cluster.local cluster.local
ndots: 5                        # Try appending search domains for names with < 5 dots
```

**Service DNS names:**
- `api-service` → searches `api-service.production.svc.cluster.local`
- `api-service.other-ns` → cross-namespace access
- `api-service.production.svc.cluster.local` → fully qualified (FQDN)

**Security concerns:**

1. **DNS is unencrypted by default** — any pod on the network can see DNS queries. An attacker knows which services a pod talks to.

2. **DNS spoofing** — without DNSSEC, a compromised CoreDNS or man-in-the-middle can return fake IPs, redirecting traffic to a malicious pod.

3. **Cross-namespace access** — by default, any pod can resolve any Service in any namespace. DNS doesn't enforce access control. You need NetworkPolicy to block the actual connection.

4. **External DNS exfiltration** — an attacker can encode data in DNS queries to a domain they control (DNS tunneling). Egress NetworkPolicy blocking all egress except DNS doesn't help because the exfiltration IS DNS.

5. **CoreDNS is a single point of failure** — if CoreDNS goes down, no pod can resolve names. DDoS on CoreDNS takes down the cluster.

**Mitigations:**
- NetworkPolicy with egress rules (restrict which pods can talk to which services)
- mTLS via service mesh (even if DNS is spoofed, TLS handshake fails)
- DNS logging (CoreDNS can log all queries for audit)
- Limit external DNS (egress NetworkPolicy restricting port 53 to CoreDNS only)"""),

        msg("How does TLS work? Explain the handshake and why mTLS adds mutual authentication.",
            """TLS (Transport Layer Security) encrypts communication between two parties. The handshake establishes trust and encryption keys.

**TLS handshake (simplified):**
```
Client                              Server
  |                                    |
  |--- ClientHello (supported ciphers) -->|
  |                                    |
  |<-- ServerHello (chosen cipher) ----|
  |<-- Server Certificate (public key) |
  |<-- ServerHelloDone ---------------|
  |                                    |
  |  Client verifies server cert       |
  |  against trusted CA                |
  |                                    |
  |--- ClientKeyExchange (encrypted) ->|
  |--- ChangeCipherSpec ------------->|
  |--- Finished (encrypted) --------->|
  |                                    |
  |<-- ChangeCipherSpec --------------|
  |<-- Finished (encrypted) ----------|
  |                                    |
  |====== Encrypted communication =====|
```

**What each step does:**
1. Client says "I support these encryption algorithms"
2. Server picks one and sends its certificate (contains public key)
3. Client checks: Is this certificate signed by a CA I trust?
4. Client generates a random session key, encrypts it with server's public key
5. Both sides now have the same session key → symmetric encryption begins

**One-way TLS (standard HTTPS):**
- Server proves identity to client (certificate check)
- Client is anonymous to server
- Fine for web browsers → web servers

**mTLS (mutual TLS) — both sides prove identity:**
```
Client                              Server
  |--- ClientHello ------------------>|
  |<-- ServerHello + Server Cert -----|
  |<-- CertificateRequest ------------|  ← Server asks for client cert
  |                                    |
  |--- Client Certificate ----------->|  ← Client proves identity too
  |--- ClientKeyExchange ------------>|
  |--- CertificateVerify ------------>|  ← Client signs with private key
  |                                    |
  |====== Both sides authenticated ===|
```

**Why mTLS matters in Kubernetes:**
- In a cluster, any pod can talk to any other pod by default
- One-way TLS: "I'm talking to the real api-service" (but api-service doesn't know who's calling)
- mTLS: "I'm talking to the real api-service AND api-service knows I'm the real frontend-service"
- Prevents: impersonation, man-in-the-middle, unauthorized service-to-service calls

**Istio mTLS:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: strict-mtls
  namespace: production
spec:
  mtls:
    mode: STRICT  # Both sides MUST present valid certificates
```

Istio's sidecar proxy (Envoy) handles the mTLS handshake automatically. Certificates are issued by istiod and rotated every 24 hours. The application code doesn't need to change."""),

        msg("How do iptables work and why does Kubernetes use them for Service routing?",
            """iptables is the Linux kernel's packet filtering framework. Kubernetes uses it (via kube-proxy) to implement Service routing — when a pod connects to a Service ClusterIP, iptables rules redirect the traffic to a healthy backend pod.

**How iptables chains work:**
```
Incoming packet
    ↓
PREROUTING chain (NAT)  ← kube-proxy adds DNAT rules here
    ↓
FORWARD chain (filter)  ← NetworkPolicy rules go here (Calico/Cilium)
    ↓
POSTROUTING chain (NAT) ← Source NAT for outbound
    ↓
Destination pod
```

**What kube-proxy does:**
When you create a Service:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  clusterIP: 10.96.100.50
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: web
```

kube-proxy creates iptables rules:
```bash
# Simplified — real rules are more complex
-A KUBE-SERVICES -d 10.96.100.50/32 -p tcp --dport 80 -j KUBE-SVC-WEB
-A KUBE-SVC-WEB -m statistic --mode random --probability 0.333 -j KUBE-SEP-POD1
-A KUBE-SVC-WEB -m statistic --mode random --probability 0.500 -j KUBE-SEP-POD2
-A KUBE-SVC-WEB -j KUBE-SEP-POD3
-A KUBE-SEP-POD1 -p tcp -j DNAT --to-destination 10.244.1.5:8080
-A KUBE-SEP-POD2 -p tcp -j DNAT --to-destination 10.244.2.8:8080
-A KUBE-SEP-POD3 -p tcp -j DNAT --to-destination 10.244.3.3:8080
```

This load-balances traffic across 3 pods using DNAT (Destination NAT).

**How NetworkPolicy uses iptables (Calico):**
```bash
# Default deny ingress for a namespace
-A cali-tw-<endpoint> -j DROP

# Allow from specific source
-A cali-tw-<endpoint> -s 10.244.1.0/24 -p tcp --dport 8080 -j ACCEPT
```

**Why this matters for security:**
1. Service ClusterIPs are virtual — they don't exist on any interface. They're iptables DNAT rules. Port scanning a ClusterIP tells you nothing about the backend.
2. NetworkPolicy is implemented as iptables FILTER rules. If the CNI doesn't support NetworkPolicy (like Flannel), there are NO filter rules — all traffic is allowed.
3. kube-proxy runs on every node. If kube-proxy is compromised, an attacker can redirect Service traffic to a malicious pod.
4. IPVS mode (alternative to iptables) uses kernel-level load balancing — faster but same security model.

**Checking iptables rules on a node:**
```bash
sudo iptables -t nat -L KUBE-SERVICES -n | head -20
sudo iptables -t filter -L FORWARD -n | head -20
```"""),
    ]


def generate_container_fundamentals():
    """What containers actually are — makes escape/hardening intuitive."""
    return [
        msg("What is a container, really? How is it different from a VM?",
            """A container is a regular Linux process with three kernel features applied:

1. **Namespaces** — isolated view of system resources (PID, network, filesystem)
2. **Cgroups** — resource limits (CPU, memory, I/O)
3. **Union filesystem** — layered read-only image + writable top layer

**Container vs VM:**
```
VM:                                Container:
┌─────────────────────┐           ┌─────────────────────┐
│ Application          │           │ Application          │
├─────────────────────┤           ├─────────────────────┤
│ Guest OS (full)      │           │ Libraries only       │
├─────────────────────┤           ├─────────────────────┤
│ Hypervisor           │           │ Container runtime    │
├─────────────────────┤           ├─────────────────────┤
│ Host OS              │           │ Host OS (shared)     │
├─────────────────────┤           ├─────────────────────┤
│ Hardware             │           │ Hardware             │
└─────────────────────┘           └─────────────────────┘
```

**The critical difference:** VMs have their own kernel. Containers share the host kernel.

**Why this matters for security:**
- **Kernel exploits** — a vulnerability in the Linux kernel affects ALL containers on that host. A VM kernel exploit only affects that VM.
- **Container escape** — escaping a container = escaping namespaces. The attacker is now a process on the host with access to all other containers.
- **`privileged: true`** disables ALL namespace isolation → container IS the host.
- **`hostPID: true`** → container can see all host processes (ps aux shows everything)
- **`hostNetwork: true`** → container uses host's network (can sniff all traffic)

**What a container image actually is:**
```
Layer 4 (top): Your application code (read-write in running container)
Layer 3: pip install / npm install (read-only)
Layer 2: apt-get install dependencies (read-only)
Layer 1: Base OS (ubuntu:22.04 or alpine:3.19) (read-only)
```

`readOnlyRootFilesystem: true` makes the top layer read-only too. An attacker can't write malware to the filesystem. They'd need to write to a mounted volume (emptyDir for /tmp).

**The key insight:** Containers are isolation by convention, not by hardware. The kernel trusts the container runtime to enforce boundaries. That's why seccomp, AppArmor, capabilities, and securityContext all exist — they're defense-in-depth for when namespace isolation isn't enough."""),

        msg("How does a container image get built and why do layers matter for security?",
            """A Dockerfile creates an image layer by layer. Each instruction creates a new read-only layer:

```dockerfile
FROM ubuntu:22.04          # Layer 1: base OS (200MB)
RUN apt-get update         # Layer 2: package lists (30MB)
RUN apt-get install -y gcc # Layer 3: compiler (150MB)
COPY . /app                # Layer 4: your code (5MB)
RUN gcc -o myapp main.c    # Layer 5: compiled binary (1MB)
```

**Total image: 386MB.** But the compiled binary is only 1MB.

**Why layers matter for security:**

1. **Every layer is stored permanently.** Even if you delete a file in a later layer, it's still in the previous layer. Secrets committed in Layer 3 and "deleted" in Layer 4 are still extractable:
```bash
docker history myimage
docker save myimage | tar -xf -
# Each layer is a tar file — secrets are in the old layer
```

2. **Multi-stage builds solve this:**
```dockerfile
# Stage 1: Build (has gcc, secrets, source code)
FROM ubuntu:22.04 AS builder
RUN apt-get install -y gcc
COPY . /app
RUN gcc -o myapp main.c

# Stage 2: Runtime (has ONLY the binary)
FROM alpine:3.19
COPY --from=builder /app/myapp /myapp
USER 10001
CMD ["/myapp"]
```
Runtime image: ~6MB. No compiler, no source code, no build secrets.

3. **Image scanning works per-layer.** Trivy scans each layer for known CVEs in installed packages. Fewer layers with fewer packages = fewer vulnerabilities.

4. **Image digest = SHA256 of all layers.** If any layer changes, the digest changes. Pinning by digest guarantees the exact image:
```yaml
image: myapp@sha256:abc123...  # Immutable
image: myapp:v1.0              # Mutable (someone can push a new image with same tag)
```

5. **Cosign signs the digest, not the tag.** Signature verification ensures the image hasn't been tampered with since it was signed."""),
    ]


def generate_crypto_fundamentals():
    """Cryptography basics that make certificate/signing/hash security click."""
    return [
        msg("Explain hashing, encryption, and signing. How are they different and when do you use each?",
            """Three cryptographic operations, three different purposes:

**Hashing (one-way fingerprint):**
```
Input: "password123"  → SHA256 → "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
Input: "password124"  → SHA256 → "completely different hash"
```
- **One-way:** Can't reverse the hash back to the input
- **Deterministic:** Same input always gives same hash
- **Use cases:** Password storage, file integrity, image digests
- **Security rule:** SHA256/SHA512 for security. Never MD5/SHA1 (collision attacks)

**Encryption (two-way, needs a key):**
```
Symmetric (same key):
  plaintext + key → AES → ciphertext → AES + same key → plaintext

Asymmetric (public/private key pair):
  plaintext + public key → RSA → ciphertext → RSA + private key → plaintext
```
- **Two-way:** Decrypt with the right key
- **Use cases:** TLS (data in transit), disk encryption (data at rest), secrets
- **Symmetric (AES):** Fast, same key both sides. Used for bulk data.
- **Asymmetric (RSA/ECDSA):** Slow, different keys. Used for key exchange and signing.

**Signing (prove authenticity):**
```
1. Hash the content → SHA256 → digest
2. Encrypt the digest with PRIVATE key → signature
3. Anyone with PUBLIC key can decrypt → gets the digest
4. They hash the content themselves → compare digests
5. Match = content hasn't been tampered with AND came from the private key holder
```
- **Use cases:** Image signing (Cosign), TLS certificates, code signing, JWT tokens
- **Cosign signs container images:** `cosign sign --key cosign.key myimage@sha256:abc`
- **Verification:** `cosign verify --key cosign.pub myimage@sha256:abc`

**How they work together in Kubernetes:**
- **etcd encryption at rest** → AES encrypts Secrets stored in etcd
- **TLS certificates** → asymmetric encryption + signing for API server communication
- **Image digests** → SHA256 hash ensures image integrity
- **Cosign** → signs image digests, Kyverno verifies signatures at admission
- **ServiceAccount tokens** → JWT signed by kube-apiserver, verified by kubelet"""),

        msg("What is a TLS certificate and how does certificate-based authentication work in Kubernetes?",
            """A TLS certificate is a signed document that binds a public key to an identity. It's how machines prove "I am who I say I am."

**Certificate structure:**
```
Certificate:
  Subject: CN=kube-apiserver          # Who this cert belongs to
  Issuer: CN=kubernetes-ca            # Who signed it (the CA)
  Public Key: RSA 2048-bit            # Server's public key
  Valid: 2026-01-01 to 2027-01-01     # Expiry
  SANs: kubernetes, kubernetes.default, 10.96.0.1, 192.168.1.100
  Signature: <CA's signature>         # Proof the CA vouches for this
```

**Trust chain:**
```
Root CA (self-signed, trusted by all nodes)
  ├── kube-apiserver cert (signed by CA)
  ├── etcd server cert (signed by CA)
  ├── kubelet client cert (signed by CA)
  ├── kube-scheduler cert (signed by CA)
  └── admin user cert (signed by CA)
```

**How Kubernetes uses certificates:**

1. **kube-apiserver ↔ etcd:** mTLS. Both present certs signed by the etcd CA.
```
API server flags:
  --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt
  --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key
  --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
```

2. **kubelet ↔ kube-apiserver:** mTLS. kubelet presents a client cert to prove its identity.
```
kubelet rotates its own cert automatically (--rotate-certificates=true)
```

3. **kubectl ↔ kube-apiserver:** Client cert in kubeconfig:
```yaml
users:
- name: admin
  user:
    client-certificate-data: <base64 cert>
    client-key-data: <base64 private key>
```

4. **ServiceAccount tokens:** JWT signed by the API server's private key. Pods verify with the public key.

**Why certificate expiry is critical:**
```bash
# Check expiry
sudo kubeadm certs check-expiration

# If expired, kubelet can't authenticate → node goes NotReady
# Fix:
sudo kubeadm certs renew all
sudo systemctl restart kubelet
```

**The key insight:** Kubernetes authentication IS certificate authentication. Every component proves its identity with a cert signed by the cluster CA. Compromising the CA private key = compromising the entire cluster."""),
    ]


def generate_database_app_fundamentals():
    """SQL, HTTP, auth fundamentals that make application security click."""
    return [
        msg("What is SQL injection and why does understanding SQL make the vulnerability obvious?",
            """SQL (Structured Query Language) is how applications talk to databases. Understanding SQL makes injection attacks obvious:

**Normal SQL query:**
```sql
SELECT * FROM users WHERE username = 'admin' AND password = 'secret123';
```

**How the application builds it (VULNERABLE):**
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

**What an attacker sends:**
```
username: admin' OR '1'='1' --
password: anything
```

**What the database executes:**
```sql
SELECT * FROM users WHERE username = 'admin' OR '1'='1' --' AND password = 'anything'
```

The `--` comments out the password check. `'1'='1'` is always true. The attacker bypasses authentication.

**Why it works:** The application treats user input as SQL code. The database can't tell the difference between the developer's SQL and the attacker's SQL.

**The fix — parameterized queries:**
```python
# SECURE — database knows this is DATA, not CODE
cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
```

With parameterized queries, the database treats `admin' OR '1'='1' --` as a literal string to match, not as SQL commands.

**Other injection types (same principle):**
- **Command injection:** `os.system("ping " + user_input)` → user sends `; rm -rf /`
- **LDAP injection:** same pattern with LDAP queries
- **XSS:** HTML/JavaScript injection into web pages

**The universal lesson:** Never mix user input with code. Use parameterized queries for SQL, subprocess with lists (not strings) for commands, template escaping for HTML. The data channel and the code channel must be separate."""),

        msg("How does Kubernetes RBAC work and why is 'least privilege' the core principle?",
            """RBAC (Role-Based Access Control) controls WHO can do WHAT to WHICH resources in Kubernetes.

**The four RBAC objects:**

```
Role / ClusterRole         = WHAT actions are allowed
  ↓ (bound by)
RoleBinding / ClusterRoleBinding = WHO gets those permissions
  ↓ (references)
Subject                    = User, Group, or ServiceAccount
```

**Example — allow a developer to view pods but not delete them:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: dev
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]  # Can read, NOT delete/create/update
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-pod-reader
  namespace: dev
subjects:
- kind: User
  name: alice
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**Namespace-scoped vs Cluster-scoped:**
- `Role` + `RoleBinding` = permissions in ONE namespace
- `ClusterRole` + `ClusterRoleBinding` = permissions cluster-wide

**Why least privilege matters:**

| Bad practice | Risk | Fix |
|---|---|---|
| `verbs: ["*"]` on `resources: ["*"]` | Full cluster admin | List specific verbs and resources |
| ServiceAccount with cluster-admin | Pod compromise = cluster compromise | Namespace-scoped Role with minimal verbs |
| Default ServiceAccount has permissions | Every pod in namespace gets them | Create dedicated ServiceAccounts per app |
| `automountServiceAccountToken: true` (default) | Token available to any process in pod | Set `automountServiceAccountToken: false` |

**How an attacker escalates via RBAC:**
1. Compromise a pod → read the mounted ServiceAccount token at `/var/run/secrets/kubernetes.io/serviceaccount/token`
2. Use the token to call the Kubernetes API
3. If the ServiceAccount has `create pods` permission → create a privileged pod → container escape
4. If it has `get secrets` → read all secrets in the namespace

**Check your RBAC:**
```bash
# What can this ServiceAccount do?
kubectl auth can-i --list --as=system:serviceaccount:production:my-app

# Who has cluster-admin?
kubectl get clusterrolebindings -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.subjects[*].name}{" "}{end}'
```

**The key insight:** RBAC is only as secure as the weakest ServiceAccount. One over-permissioned ServiceAccount in one namespace can be the entry point for a full cluster compromise."""),
    ]


def generate_cloud_fundamentals():
    """Cloud concepts that make cloud security intuitive."""
    return [
        msg("What is the Shared Responsibility Model and why does it matter for Kubernetes on AWS?",
            """The Shared Responsibility Model defines who secures what between you and the cloud provider:

**AWS is responsible for security OF the cloud:**
- Physical data centers, hardware, hypervisors
- Managed service infrastructure (EKS control plane, RDS engine, S3 storage layer)
- Global network, edge locations

**You are responsible for security IN the cloud:**
- What you deploy (containers, applications, configurations)
- Network configuration (VPC, security groups, NACLs)
- Identity and access (IAM policies, RBAC)
- Data encryption (at rest and in transit)
- OS patching (on EC2 instances, EKS worker nodes)

**For EKS specifically:**

| Component | AWS manages | You manage |
|-----------|------------|------------|
| Control plane (API server, etcd, scheduler) | Yes (patched, HA, encrypted) | No |
| Worker nodes (EC2) | No | Yes (OS patches, AMI updates, kubelet) |
| Pod security (securityContext, RBAC) | No | Yes |
| Network (VPC, CNI, NetworkPolicy) | VPC infrastructure | Security groups, NetworkPolicy |
| Secrets | KMS infrastructure | Encryption config, rotation, access policies |
| Container images | ECR infrastructure | Image scanning, signing, vulnerability patching |

**Why this matters:**
- "We use EKS" does NOT mean "AWS secures our Kubernetes"
- AWS secures the control plane. YOU secure everything in it.
- A pod running as root on EKS is just as vulnerable as on bare metal
- AWS doesn't apply NetworkPolicy, securityContext, or RBAC for you

**The key insight:** Cloud providers secure the infrastructure. You secure the workloads. Most breaches happen in the "your responsibility" layer — misconfigured IAM, open security groups, pods without securityContext, unencrypted secrets."""),

        msg("What is a VPC and how does network isolation work in AWS?",
            """A VPC (Virtual Private Cloud) is your own private network within AWS. It's an isolated section of the AWS cloud where you control IP addressing, subnets, routing, and firewalls.

**VPC structure:**
```
VPC (10.0.0.0/16) — 65,536 IP addresses
├── Public Subnet (10.0.1.0/24) — 256 IPs
│   ├── Internet Gateway → internet access
│   ├── ALB (load balancer)
│   ├── NAT Gateway (for private subnet outbound)
│   └── Bastion host (SSH jump box)
│
├── Private Subnet (10.0.10.0/24) — 256 IPs
│   ├── Application servers (EC2, EKS nodes)
│   ├── Outbound via NAT Gateway only
│   └── No direct internet access
│
└── Database Subnet (10.0.20.0/24) — 256 IPs
    ├── RDS instances (publicly_accessible = false)
    ├── ElastiCache
    └── No internet route at all
```

**How traffic flows:**
```
Internet → Internet Gateway → Public Subnet → ALB
                                               ↓ (Security Group allows port 8080 from ALB only)
                                         Private Subnet → Application
                                               ↓ (Security Group allows port 5432 from App SG only)
                                         Database Subnet → RDS
```

**Three layers of network security:**

1. **Route tables** — control WHERE traffic can go
   - Public subnet: `0.0.0.0/0 → Internet Gateway`
   - Private subnet: `0.0.0.0/0 → NAT Gateway` (outbound only)
   - Database subnet: no default route (completely isolated)

2. **NACLs (Network ACLs)** — subnet-level firewall (stateless)
   - Allow/deny rules processed in order
   - Applied to ALL traffic entering/leaving the subnet

3. **Security Groups** — instance-level firewall (stateful)
   - Allow rules only (implicit deny)
   - Can reference other Security Groups as sources

**Why this matters for security:**
- Database in a public subnet with `publicly_accessible = true` → anyone on the internet can attempt connections
- Missing NAT Gateway → private subnet has no outbound (can't pull images, can't reach package repos)
- Security Group with `0.0.0.0/0` on SSH → brute-force target from anywhere
- No egress filtering → compromised instance can exfiltrate data freely

The VPC is your first line of defense. Get the network architecture right and many attack vectors disappear."""),
    ]


def main():
    all_examples = []

    sections = [
        ("Linux fundamentals", generate_linux_fundamentals),
        ("Networking fundamentals", generate_networking_fundamentals),
        ("Container fundamentals", generate_container_fundamentals),
        ("Cryptography fundamentals", generate_crypto_fundamentals),
        ("Database & application fundamentals", generate_database_app_fundamentals),
        ("Cloud fundamentals", generate_cloud_fundamentals),
    ]

    for name, gen_func in sections:
        examples = gen_func()
        print(f"  {name}: {len(examples)} examples")
        all_examples.extend(examples)

    random.shuffle(all_examples)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nTotal: {len(all_examples)} foundational knowledge examples")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
