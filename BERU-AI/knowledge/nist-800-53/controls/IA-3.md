---
family: IA
family_name: Identification and Authentication
id: IA-3
name: Device Identification and Authentication
---

question: "Are devices and non-human systems required to prove their identity before connecting?"

description: >
  The information system uniquely identifies and authenticates devices before establishing
  connections — whether local, remote, or network connections. In cloud-native environments
  this means workload identity: pods, services, and nodes must authenticate to each other
  and to external systems using cryptographic credentials, not shared secrets or implicit
  network trust. Service-to-service calls without mutual authentication are a IA-3 gap.

enhancements:
  - id: IA-3(1)
    name: Cryptographic Bidirectional Authentication
    description: >
      The information system authenticates devices before establishing connections using
      bidirectional authentication that is cryptographically based. mTLS between services
      satisfies this — a service mesh (Istio, Linkerd) is a common implementation.
      One-way TLS (server-only certificate) does not satisfy bidirectional authentication.

HITRUST_map:
  - "01.x — Mobile Computing and Communications"
  - "09.m — Network Controls"
  - "09.n — Security of Network Services"

evidence:
  what_to_look_for:
    - mTLS configuration in service mesh (PeerAuthentication policies set to STRICT mode)
    - Node bootstrap credentials (K8s node joining process — kubeadm bootstrap token lifecycle)
    - Device certificates issued by a PKI (certificates with device identity in Subject/SAN)
    - Workload identity configuration (SPIFFE/SPIRE, AWS IAM Roles for Service Accounts, Workload Identity Federation)
    - Evidence that unauthenticated device connections are rejected at the network layer
  ask_for:
    - "Show me your service mesh PeerAuthentication policy — is mTLS set to STRICT or PERMISSIVE across namespaces?"
    - "Show me how a new worker node authenticates to the cluster API server during bootstrap."
    - "Show me how your pods authenticate to AWS/Azure services — are they using workload identity or long-lived static credentials?"
    - "Show me if any service-to-service call bypasses mTLS — are there any PERMISSIVE mode exceptions and why?"
  tools:
    generic:
      - Istio (`kubectl get peerauthentication -A` — verify STRICT mTLS)
      - Linkerd (`linkerd check` — verify mTLS mesh coverage)
      - SPIFFE/SPIRE (workload identity attestation)
      - kubectl (`kubectl get nodes` — check node certificate expiry via `openssl s_client`)
    aws:
      - IAM Roles for Service Accounts (IRSA) — verify OIDC federation configured for EKS
      - AWS Certificate Manager Private CA (device certificate issuance)
      - AWS IoT Core (device certificates for IoT-adjacent workloads)
      - CloudTrail (AssumeRoleWithWebIdentity — verify service identity assertions)
    microsoft:
      - Entra ID Workload Identity Federation (replace client secrets with federated credentials)
      - Azure Kubernetes Service Workload Identity (pod-level managed identity)
      - Microsoft Defender for IoT (device identity and authentication for OT/IoT)
      - Azure Certificate Services (device certificate management)

failure_to_implement:
  - Services authenticate to each other based on network location alone — lateral movement from one pod compromises all services on the subnet.
  - Long-lived static credentials (API keys, service account tokens) stored in environment variables are trivially exfiltrated.
  - mTLS configured in PERMISSIVE mode — appears compliant but silently accepts unauthenticated connections.
  - Worker nodes join the cluster with bootstrap tokens that are never revoked after initial join.
  - No workload identity means cloud service authentication relies on credentials baked into container images or mounted secrets.

related:
  - IA-2
  - IA-5
  - SC-8
  - SC-12

chain: null
