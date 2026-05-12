---
family: CM
family_name: Configuration Management
id: CM-3
name: Configuration Change Control
---

question: "Is every configuration change reviewed, approved, tested, and documented before it reaches production?"

description: >
  The organization determines types of changes to the system that are configuration-controlled;
  reviews proposed changes and approves or disapproves them with explicit consideration for
  security impact; documents decisions; implements approved changes; retains records; and
  audits activities associated with configuration changes. Configuration change control is
  the process that prevents unauthorized changes from reaching production and ensures every
  change has a documented owner, a security review, and an approval chain. In GitOps
  environments, this is implemented through branch protection, required PR reviews, and
  CI/CD gates — the process is the pipeline.

enhancements:
  - id: CM-3(1)
    name: Automated Documentation, Notification, and Prohibition of Changes
    description: >
      The organization employs automated mechanisms to document proposed changes, notify
      defined approval authorities, and prohibit implementation of changes without approval.
      CI/CD pipeline enforcement (required status checks, protected branches, required
      reviewers) is the standard implementation. Changes that bypass the pipeline are
      policy violations regardless of their content.
  - id: CM-3(2)
    name: Testing, Validation, and Documentation of Changes
    description: >
      The organization tests, validates, and documents changes prior to implementation on
      the production system. Automated test suites, staging environment validation, and
      security scans in the pipeline are the evidence. A change that passes tests but
      never ran a security scan is a CM-3(2) gap.
  - id: CM-3(4)
    name: Security Representative
    description: >
      The organization requires a security representative to be a member of the
      organization-defined configuration change control board. Security review is a
      required gate, not an optional review. For high-impact changes, this means
      explicit security team sign-off, not just a passing pipeline.

HITRUST_map:
  - "10.k — Change Control Procedures"
  - "10.l — Control of Technical Vulnerabilities"
  - "09.ab — Monitoring System Use"

evidence:
  what_to_look_for:
    - Branch protection rules requiring minimum number of reviewers before merge to main
    - CI/CD pipeline configuration showing required security gates (SAST, image scan, policy check) before production deploy
    - Change management records linking commits or deployments to approved tickets
    - Security review participation records for high-impact configuration changes
    - Post-deployment validation steps documented in pipeline or runbook
    - Audit log of who approved each production deployment and when
  ask_for:
    - "Show me your branch protection configuration — what checks are required before a PR can merge to main?"
    - "Show me your CI/CD pipeline for a production deployment — at what point does security scanning run, and can it be bypassed?"
    - "Show me a recent high-impact configuration change — what was the approval chain, who reviewed it for security impact, and how is that documented?"
    - "Show me how an emergency hotfix bypasses normal change control — what compensating controls exist for expedited changes?"
  tools:
    generic:
      - GitHub / GitLab branch protection settings (required reviewers, required status checks, no force push)
      - GitHub Actions / GitLab CI (pipeline definition — security gates as required jobs)
      - ArgoCD sync policy (manual sync for production — prevents auto-apply without approval)
      - git log (full audit trail of who committed and who approved each merge)
    aws:
      - AWS Systems Manager Change Manager (formal change request and approval workflow)
      - AWS CodePipeline (approval actions — manual approval gate before production deploy)
      - CloudTrail (records who triggered each pipeline execution and deployment action)
      - AWS Config (detect configuration changes that occurred outside the approved pipeline)
    microsoft:
      - Azure DevOps Pipeline (approval gates and checks before production stage)
      - Azure DevOps Branch Policies (required reviewers, linked work items, comment resolution)
      - Azure Resource Manager deployment history (who deployed, when, with what template)
      - Microsoft Defender for Cloud (detect configuration changes made outside IaC)

failure_to_implement:
  - Developers can push directly to main or deploy manually to production — no technical enforcement of change control.
  - Security scanning exists in the pipeline but is a warning, not a blocking gate — failures are ignored.
  - Emergency hotfix procedure has no compensating controls — bypasses change control with no after-action documentation.
  - Configuration changes to cloud resources are made via console (click-ops) and never reflected in IaC — audit trail is incomplete.
  - Change management records exist in a ticketing system but are never linked to actual commits or deployments — approval cannot be verified.

related:
  - CM-2
  - CM-6
  - SI-7

chain: null
