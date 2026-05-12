---
family: AC
family_name: Access Control
id: AC-5
name: Separation of Duties
---

question: "Are critical functions divided so no single person can cause undetected harm?"

description: >
  The organization separates duties of individuals as necessary to prevent malevolent activity
  without collusion; documents separation of duties; and implements separation through assigned
  access authorizations. No single person should have the ability to both initiate and approve
  a high-impact action — whether a code deploy, an account creation, or a financial transaction.
  SoD is the architectural control that makes insider threat economically irrational.

enhancements: []

HITRUST_map:
  - "01.a — Access Control Policy"
  - "01.b — User Registration and De-registration"
  - "06.d — Information Security Incident Management"

evidence:
  what_to_look_for:
    - Role matrix documenting which roles have conflicting permissions and how conflicts are prevented
    - Branch protection rules requiring a second approver before merge to main/production
    - CI/CD pipeline configuration showing separate approval gates for deploy to production
    - Evidence that developers cannot self-approve pull requests or pipeline runs
    - RBAC showing that the role that can create accounts cannot also approve access requests
  ask_for:
    - "Show me your branch protection configuration — can a developer approve their own PR?"
    - "Show me how a code change reaches production — who approves each stage, and can the same person approve more than one stage?"
    - "Show me your role matrix — which roles have conflicting permissions, and how is that conflict controlled?"
    - "Show me if any single IAM user or K8s service account can both write policy and deploy workloads."
  tools:
    generic:
      - GitHub/GitLab branch protection settings (CODEOWNERS, required reviewers)
      - git log (verify multi-party approvals on merge commits)
      - CI/CD pipeline audit (GitHub Actions, ArgoCD, Tekton — approval gates)
    aws:
      - IAM policy analysis (identify overlapping critical permissions in roles)
      - AWS Organizations SCPs (prevent single-account ownership of critical actions)
      - CloudTrail (detect same principal performing initiation and approval actions)
    microsoft:
      - Azure DevOps branch policies (required reviewers)
      - Entra ID PIM (approval workflows for privileged role activation)
      - Azure Policy (enforce separation at resource level)

failure_to_implement:
  - A developer can write, approve, and deploy their own code to production with no second review.
  - A single administrator can create accounts and approve their own access requests.
  - Insider threat goes undetected because no split of authority exists to require collusion.
  - FedRAMP and SOC 2 Type II auditors cite SoD as a material weakness if pipeline approvals are absent.
  - Incident response reveals that a compromise was undetectable because one principal controlled the full action chain.

related:
  - AC-2
  - AC-3
  - AC-6

chain: null
