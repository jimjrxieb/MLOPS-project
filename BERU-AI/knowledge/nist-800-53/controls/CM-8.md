---
family: CM
family_name: Configuration Management
id: CM-8
name: System Component Inventory
---

question: "Do we have an accurate, current inventory of every component in the system — hardware, software, and services?"

description: >
  The organization develops and documents an inventory of system components that accurately
  reflects the current system; includes all components within the authorization boundary;
  is at a level of granularity deemed necessary for tracking and reporting; and reviews and
  updates the inventory on a defined frequency and whenever components are installed, removed,
  or changes occur. You cannot protect what you do not know exists. An incomplete inventory
  means unknown components — unpatched, unconfigured, and outside the security boundary —
  are running in production. Inventory is also the foundation for vulnerability management:
  RA-5 scans cannot be comprehensive without a complete component list.

enhancements:
  - id: CM-8(1)
    name: Updates During Installations and Removals
    description: >
      The organization updates the inventory of system components as an integral part of
      component installations, removals, and system updates. Inventory is not a periodic
      snapshot — it is a live record maintained by the deployment pipeline. Every deploy
      adds a record; every decommission removes one.
  - id: CM-8(2)
    name: Automated Maintenance
    description: >
      The organization employs automated mechanisms to help maintain an up-to-date, complete,
      accurate, and readily available inventory of system components. Automated discovery
      (K8s API, cloud provider APIs, CMDB integrations) ensures the inventory reflects
      reality rather than what someone last documented manually.
  - id: CM-8(3)
    name: Automated Unauthorized Component Detection
    description: >
      The organization employs automated mechanisms to detect unauthorized components and
      takes defined actions when discovered. Unknown components — containers from untracked
      images, cloud resources deployed outside IaC, shadow IT — are automatically flagged
      for investigation and remediation.

HITRUST_map:
  - "09.ab — Monitoring System Use"
  - "10.l — Control of Technical Vulnerabilities"
  - "09.m — Network Controls"

evidence:
  what_to_look_for:
    - Component inventory covering all K8s workloads (pods, deployments, daemonsets), services, and namespaces
    - Cloud resource inventory across all accounts and regions (EC2, RDS, Lambda, S3, etc.)
    - Software bill of materials (SBOM) for container images in production
    - Inventory update process showing new deployments are automatically registered
    - Unauthorized component detection capability — alert or scan that identifies resources outside IaC
    - Inventory review records showing the list was validated against live infrastructure
  ask_for:
    - "Show me your system component inventory — how is it maintained and how current is it?"
    - "Show me how you detect a cloud resource deployed outside your IaC pipeline — a rogue EC2 instance or manually created S3 bucket."
    - "Show me your SBOM for production container images — can you enumerate every package and version running in production right now?"
    - "Show me your inventory update process — if a new microservice is deployed today, when does it appear in the inventory and who is notified?"
  tools:
    generic:
      - kubectl (`kubectl get all -A` — live K8s component inventory)
      - Trivy SBOM generation (`trivy image --format cyclonedx` — software bill of materials)
      - Syft (SBOM generation for container images and filesystems)
      - Backstage (developer portal as component catalog — service inventory with ownership)
      - Kubescape (K8s resource inventory with security posture)
    aws:
      - AWS Config (resource inventory across all AWS accounts and regions)
      - AWS Systems Manager Inventory (detailed software and EC2 instance inventory)
      - AWS Service Catalog (approved components and their deployment records)
      - Amazon Inspector (inventory + vulnerability mapping — CVE per component)
      - AWS Config rule: ec2-instance-managed-by-systems-manager (detect unmanaged instances)
    microsoft:
      - Azure Resource Graph (`az graph query` — inventory all resources across subscriptions)
      - Microsoft Defender for Cloud (asset inventory with security coverage gaps)
      - Azure Arc (inventory hybrid and on-prem nodes alongside cloud resources)
      - Microsoft Defender for DevOps (container image inventory in registry)

failure_to_implement:
  - Shadow IT cloud resources — EC2 instances or S3 buckets created manually are never scanned or patched.
  - Inventory is a spreadsheet last updated six months ago — does not reflect current deployed state.
  - No SBOM means a critical CVE announcement triggers days of investigation to determine which services are affected.
  - Decommissioned components remain in the inventory — scoping and cost decisions are made against stale data.
  - Unauthorized container running in production (from a test deployment that was never cleaned up) is invisible to the security team.

related:
  - CM-2
  - CM-6
  - RA-5
  - SI-2

chain: null
