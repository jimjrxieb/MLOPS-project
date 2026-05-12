---
family: CM
family_name: Configuration Management
id: CM-7
name: Least Functionality
---

question: "Does every system component expose only the ports, protocols, services, and functions it actually needs?"

description: >
  The organization configures the system to provide only essential capabilities and prohibits
  or restricts the use of functions, ports, protocols, and services not required. Least
  functionality is the system-level analog to least privilege — just as AC-6 scopes what
  users can do, CM-7 scopes what the system itself is allowed to do. Attack surface is
  reduced by eliminating everything that is not operationally required. Unused services,
  open ports, and enabled features are all potential attack vectors that exist with zero
  operational benefit.

enhancements:
  - id: CM-7(1)
    name: Periodic Review
    description: >
      The organization reviews the system periodically to identify and eliminate unnecessary
      functions, ports, protocols, and services. The attack surface grows over time as
      features are enabled for temporary needs and never disabled. A periodic review
      forces explicit justification for everything that is running.
  - id: CM-7(2)
    name: Prevent Program Execution
    description: >
      The information system prevents the execution of programs in accordance with an
      organization-defined list of prohibited software, rules authorizing terms and conditions,
      or rules authorizing exceptions. Admission controllers (Kyverno, OPA) enforcing
      allowed image registries and blocking known-bad images satisfy this.
  - id: CM-7(5)
    name: Authorized Software — Allow-by-Exception
    description: >
      The organization identifies authorized software programs and employs a deny-all,
      permit-by-exception policy to allow the execution of authorized software. An
      approved image registry list enforced by admission control is the K8s implementation.
      Any image not on the approved list is rejected at admission.

HITRUST_map:
  - "09.ab — Monitoring System Use"
  - "09.m — Network Controls"
  - "10.l — Control of Technical Vulnerabilities"

evidence:
  what_to_look_for:
    - Network policy restricting pod-to-pod communication to only necessary paths (deny-all default, explicit allow rules)
    - Admission control policy restricting container images to approved registries
    - Node-level port scan results showing only authorized ports open
    - Service exposure audit — no NodePort or LoadBalancer services without documented justification
    - Disabled or removed system services, packages, and kernel modules not required for operation
    - Periodic functionality review records showing unused services were identified and removed
  ask_for:
    - "Show me your default NetworkPolicy — is it deny-all with explicit allows, or allow-all with explicit denies?"
    - "Show me how you enforce which container registries are allowed — what happens if someone tries to deploy from an unapproved registry?"
    - "Show me your exposed services — are there any NodePort or LoadBalancer services and are they all documented and justified?"
    - "Show me a recent least-functionality review — what services or ports were found to be unnecessary and how were they removed?"
  tools:
    generic:
      - kubectl (`kubectl get networkpolicies -A` — verify default-deny exists in all namespaces)
      - nmap (port scan cluster nodes and service endpoints — verify only authorized ports open)
      - Kyverno policy (restrict allowed image registries — block pull from untrusted sources)
      - Trivy (detect unnecessary packages and services in container images)
      - Falco (runtime detection of unexpected process execution in containers)
    aws:
      - AWS Security Groups (verify least-privilege port rules — no 0.0.0.0/0 ingress on non-public services)
      - VPC Network ACLs (subnet-level traffic restriction)
      - AWS Config (rule: restricted-ssh, restricted-common-ports)
      - AWS Inspector (network reachability findings — identifies unintended exposure)
    microsoft:
      - Azure Network Security Groups (verify inbound rules — no unrestricted access)
      - Azure Defender for Containers (runtime process and network activity anomalies)
      - Azure Policy (deny public IP assignment on resources that should be internal)
      - Microsoft Defender for Cloud (network exposure recommendations)

failure_to_implement:
  - Default allow-all NetworkPolicy means any compromised pod can reach every other pod in the cluster.
  - Debug service deployed for an incident and never removed — exposes an unauthenticated shell endpoint in production.
  - Container images pulled from Docker Hub without restriction — supply chain risk from unvetted public images.
  - SSH open on all worker nodes to 0.0.0.0/0 — left over from initial cluster setup, never locked down.
  - Periodic review never conducted — attack surface has grown continuously since initial deployment with no remediation.

related:
  - CM-2
  - CM-6
  - SC-7
  - SI-3

chain: null
