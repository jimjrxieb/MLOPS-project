---
family: SC
family_name: System and Communications Protection
id: SC-7
name: Boundary Protection
---

question: "Are network boundaries enforced so traffic can only flow where it is explicitly authorized?"

description: >
  The information system monitors and controls communications at external boundaries and key
  internal boundaries; implements subnetworks for publicly accessible system components that
  are physically or logically separated from internal networks; and connects to external networks
  only through managed interfaces with boundary protection devices. In cloud-native environments,
  boundary protection operates at multiple layers simultaneously — VPC, subnet, security group,
  NetworkPolicy, and service mesh. Each layer catches what the one above it misses. A gap at
  any layer is an uncontrolled communication path.

enhancements:
  - id: SC-7(3)
    name: Access Points
    description: >
      The organization limits the number of external network connections to the system.
      Fewer egress and ingress points mean fewer places to monitor and fewer opportunities
      for unauthorized communication. A single ingress controller and a single NAT gateway
      per environment is a stronger posture than distributed, untracked access points.
  - id: SC-7(4)
    name: External Telecommunications Services
    description: >
      The organization implements a managed interface for each external communication service;
      establishes a traffic flow policy for each managed interface; protects the confidentiality
      and integrity of transmitted information; documents each exception and the need for the
      exception. Every external API call from a workload crosses a boundary — those calls must
      be authorized, logged, and egress-filtered.
  - id: SC-7(5)
    name: Deny by Default — Allow by Exception
    description: >
      The information system denies network communications traffic by default and allows
      network communications traffic by exception. Default-deny NetworkPolicy in K8s and
      default-deny Security Groups in AWS satisfy this. Anything not explicitly permitted
      is blocked.
  - id: SC-7(8)
    name: Route Traffic to Authenticated Proxy Servers
    description: >
      The information system routes internal communications traffic to external networks
      through authenticated proxy servers at managed interfaces. Egress proxy or NAT gateway
      with logging — workloads cannot establish direct arbitrary outbound connections.

HITRUST_map:
  - "09.m — Network Controls"
  - "09.n — Security of Network Services"
  - "01.a — Access Control Policy"

evidence:
  what_to_look_for:
    - Default-deny NetworkPolicy in every namespace with explicit allow rules for required traffic
    - VPC/subnet architecture diagram showing DMZ, private, and data tiers with traffic flow controls
    - Security Group rules showing deny-by-default with minimum required ingress/egress
    - Ingress controller as sole entry point — no NodePort or LoadBalancer services bypassing the boundary
    - Egress filtering — outbound traffic restricted to known endpoints, not open to internet
    - Network flow logs showing boundary traffic is captured for review
  ask_for:
    - "Show me your default NetworkPolicy in the production namespace — what traffic is denied by default and what is explicitly allowed?"
    - "Show me your VPC architecture — how are public, private, and data subnets separated and what controls traffic between them?"
    - "Show me your egress controls — can a pod in production make an arbitrary outbound connection to the internet?"
    - "Show me your ingress architecture — how many external entry points exist and are they all going through the same controlled interface?"
  tools:
    generic:
      - kubectl (`kubectl get networkpolicies -A` — verify default-deny per namespace)
      - Cilium / Calico network policy visualization
      - nmap (external boundary scan — verify only intended ports reachable from outside)
      - Istio (service mesh egress gateway — control and log outbound traffic)
    aws:
      - VPC Security Groups (verify default deny — no 0.0.0.0/0 ingress except load balancer)
      - VPC Network ACLs (stateless subnet-level boundary enforcement)
      - AWS Network Firewall (managed boundary inspection and filtering)
      - VPC Flow Logs (all boundary traffic captured)
      - AWS Config (rule: restricted-ssh, vpc-default-security-group-closed)
    microsoft:
      - Azure Network Security Groups (deny-all default with explicit inbound/outbound rules)
      - Azure Firewall (centralized boundary inspection and FQDN-based egress filtering)
      - Azure DDoS Protection (external boundary resilience)
      - Azure Virtual Network (subnet segmentation and peering controls)

failure_to_implement:
  - No default-deny NetworkPolicy — any compromised pod can reach any other pod or internal service in the cluster.
  - NodePort services exposed directly on worker node IPs — bypasses ingress controller and boundary controls.
  - Egress unrestricted — a compromised workload can exfiltrate data to any external host without detection.
  - Security Groups allow broad CIDR ranges inherited from a default VPC — never reviewed or tightened.
  - Network flow logs not enabled — boundary crossing events are invisible during incident investigation.

related:
  - CM-7
  - SC-8
  - AC-3
  - SI-4

chain: null
