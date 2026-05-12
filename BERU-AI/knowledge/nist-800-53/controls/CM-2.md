---
family: CM
family_name: Configuration Management
id: CM-2
name: Baseline Configuration
---

question: "Is there a documented, approved baseline for how every system component should be configured?"

description: >
  The organization develops, documents, and maintains a current baseline configuration of
  the information system and reviews and updates it as part of component installations and
  upgrades, and whenever required by organization-defined events. A baseline configuration
  is the known-good state of a system — the configuration that has been reviewed, approved,
  and declared secure. Without a documented baseline, there is no way to detect drift,
  enforce policy, or demonstrate to an auditor that the current state matches the intended state.
  In K8s environments, the baseline is the sum of Helm values, Kyverno policies, OPA rules,
  and IaC manifests in version control.

enhancements:
  - id: CM-2(1)
    name: Reviews and Updates
    description: >
      The organization reviews and updates the baseline configuration when required by
      system changes, when vulnerabilities are identified that affect the baseline, and
      on an organization-defined frequency. A baseline that is never updated becomes a
      liability — it documents what the system used to look like, not what it is.
  - id: CM-2(2)
    name: Automation Support for Accuracy and Currency
    description: >
      The organization employs automated mechanisms to maintain an up-to-date, complete,
      accurate, and readily available baseline configuration of the system. GitOps with
      ArgoCD or Flux satisfies this — the desired state is always the current state of
      the main branch, and drift from that state is automatically detected and reported.
  - id: CM-2(3)
    name: Retention of Previous Configurations
    description: >
      The organization retains previous versions of baseline configurations to support
      rollback and recovery. Git history provides this automatically when configuration
      is managed as code — every prior baseline is a tagged commit or release.

HITRUST_map:
  - "09.ab — Monitoring System Use"
  - "10.l — Control of Technical Vulnerabilities"
  - "06.d — Information Security Incident Management"

evidence:
  what_to_look_for:
    - Documented baseline configuration in version control (Helm values, Kustomize overlays, Terraform state, IaC manifests)
    - Approval records for baseline changes (PR approvals, change management tickets linked to commits)
    - Baseline review cadence and records (annual review or event-triggered review documentation)
    - GitOps sync status showing desired state matches live state (ArgoCD app health, Flux reconciliation status)
    - CIS Benchmark or hardening guide adopted as the baseline reference for each component type
  ask_for:
    - "Show me your baseline configuration in git — where is the approved, current-state configuration for your K8s cluster stored?"
    - "Show me how a change to the baseline is approved — what's the PR process, and who must approve before merge?"
    - "Show me your ArgoCD or Flux sync status — are there any components showing drift from the baseline?"
    - "Show me the CIS Benchmark or hardening standard you use as your baseline reference — which version and what's your coverage?"
  tools:
    generic:
      - git (baseline configuration stored as code — `git log` shows full history)
      - ArgoCD (`argocd app list` — verify Synced status across all applications)
      - Flux (`flux get all` — reconciliation status)
      - Helm (`helm history <release>` — version and values history)
      - kube-bench (CIS Kubernetes Benchmark compliance check against baseline)
    aws:
      - AWS Config (configuration recorder captures current state — compare against baseline)
      - AWS Systems Manager State Manager (enforce baseline configuration on EC2)
      - CloudFormation / Terraform state (IaC as baseline for cloud resources)
      - AWS Config Conformance Packs (CIS AWS Foundations Benchmark)
    microsoft:
      - Azure Policy (enforce baseline via built-in and custom policy definitions)
      - Azure Blueprints / Bicep (IaC baseline for Azure resources)
      - Microsoft Defender for Cloud (secure score and recommendations vs. baseline)
      - Azure Arc (extend baseline configuration management to hybrid nodes)

failure_to_implement:
  - No documented baseline means an auditor cannot verify that the current configuration is intentional and approved.
  - Configuration exists only in living infrastructure — no version history means rollback after a bad change is manual and slow.
  - Baseline document exists but was last updated two years ago — does not reflect current architecture or hardening state.
  - Drift between baseline and live configuration goes undetected — the system has been running in an unapproved state for months.
  - CIS Benchmark adopted in name only — no controls mapped to actual configuration settings in the environment.

related:
  - CM-3
  - CM-6
  - CM-7
  - CM-8

chain: null
