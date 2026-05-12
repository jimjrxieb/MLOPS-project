---
family: SC
family_name: System and Communications Protection
id: SC-8
name: Transmission Confidentiality and Integrity
---

question: "Is all data in transit encrypted and protected from tampering?"

description: >
  The information system implements cryptographic mechanisms to prevent unauthorized disclosure
  of information and detect changes to information during transmission. Data in transit must
  be protected at every hop — from client to ingress, from service to service inside the
  cluster, and from the cluster to external APIs and data stores. TLS is the minimum bar;
  mutual TLS (mTLS) is expected for service-to-service communication in high-assurance
  environments. Unencrypted protocols (HTTP, plain LDAP, unencrypted gRPC) on any
  production path are SC-8 violations.

enhancements:
  - id: SC-8(1)
    name: Cryptographic Protection
    description: >
      The information system implements cryptographic mechanisms to prevent unauthorized
      disclosure of information and detect changes during transmission. TLS 1.2 minimum,
      TLS 1.3 preferred. Cipher suite restrictions to eliminate weak algorithms (RC4, 3DES,
      NULL ciphers). Certificate validity enforced — expired or self-signed certs in
      production without a documented exception are a violation.
  - id: SC-8(2)
    name: Pre/Post Transmission Handling
    description: >
      The information system maintains the confidentiality and integrity of information
      during preparation for transmission and reception. Data is protected at the point
      of serialization — not just during the network hop. Encryption applied before
      the network layer (application-layer encryption) satisfies defense in depth
      where TLS termination happens at an intermediate proxy.

HITRUST_map:
  - "10.f — Policy on the Use of Cryptographic Controls"
  - "10.g — Key Management"
  - "09.m — Network Controls"
  - "09.n — Security of Network Services"

evidence:
  what_to_look_for:
    - TLS configuration on all ingress endpoints — cipher suites, protocol versions, certificate validity
    - mTLS enforcement in service mesh (Istio PeerAuthentication in STRICT mode cluster-wide)
    - Internal service communication audit — no HTTP-only services in production
    - Certificate management configuration (cert-manager issuer, ACM, or equivalent) with automated renewal
    - TLS on all data store connections (database, Redis, message queue, object storage)
    - Evidence that weak protocols (TLS 1.0, TLS 1.1, SSL) are disabled
  ask_for:
    - "Show me your ingress TLS configuration — what protocol versions and cipher suites are allowed, and show me the certificate expiry monitoring."
    - "Show me your Istio PeerAuthentication policy — is mTLS set to STRICT across all namespaces or are there PERMISSIVE exceptions?"
    - "Show me how your application connects to the database — is TLS enforced on the connection string, or is it optional?"
    - "Show me how internal HTTP services are handled — is there any plain HTTP traffic on service-to-service paths inside the cluster?"
  tools:
    generic:
      - testssl.sh (comprehensive TLS configuration audit — protocol versions, cipher suites, cert validity)
      - sslyze (automated TLS scanning)
      - Istio (`kubectl get peerauthentication -A` — verify STRICT mTLS)
      - cert-manager (`kubectl get certificates -A` — verify certificate status and expiry)
      - openssl s_client (verify TLS handshake details for specific endpoints)
    aws:
      - AWS Certificate Manager (certificate lifecycle and expiry monitoring)
      - ACM (enforce TLS on ALB — verify HTTPS-only listener, HTTP redirect)
      - AWS Config (rule: alb-http-to-https-redirection-check, elb-tls-https-listeners-only)
      - AWS Security Hub (TLS configuration findings)
      - RDS encryption in transit (verify `ssl-ca` parameter set on DB parameter group)
    microsoft:
      - Azure Application Gateway (TLS policy — minimum TLS 1.2, cipher suite restriction)
      - Azure Key Vault Certificates (certificate lifecycle management and renewal)
      - Azure Policy (deny creation of resources without HTTPS-only configuration)
      - Microsoft Defender for Cloud (TLS configuration recommendations)
      - Azure Front Door (TLS offload with minimum version enforcement)

failure_to_implement:
  - Service-to-service communication inside the cluster over plain HTTP — network-level attacker can read and modify traffic.
  - TLS 1.0 or 1.1 still accepted on external endpoints — vulnerable to POODLE and BEAST attacks.
  - mTLS in PERMISSIVE mode — silently accepts unauthenticated connections while appearing compliant.
  - Database connections without TLS — credentials and query results transmitted in plaintext over the network.
  - Certificate expires in production — service outage with no warning because expiry monitoring was never configured.

related:
  - SC-7
  - SC-12
  - SC-13
  - IA-3

chain: null
