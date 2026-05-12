---
family: RA
family_name: Risk Assessment
id: RA-5
name: Vulnerability Monitoring and Scanning
---

question: "Are vulnerabilities scanned for continuously across the full system scope — and are findings tracked to closure?"

description: >
  The organization monitors and scans for vulnerabilities in the system and hosted applications
  at defined frequencies and when new vulnerabilities are identified; employs vulnerability
  monitoring tools and techniques; analyzes vulnerability scan reports and results; remediates
  legitimate vulnerabilities within defined timeframes; shares information obtained from
  vulnerability monitoring with defined personnel; and updates scanning tools as new
  vulnerabilities are identified. RA-5 is the detection half of the vulnerability management
  cycle — SI-2 is the remediation half. Together they form a closed loop: scan, find, fix,
  verify. A scan that produces findings no one acts on is not vulnerability management.

enhancements:
  - id: RA-5(2)
    name: Update Vulnerabilities to Be Scanned
    description: >
      The organization updates the system vulnerabilities scanned prior to a new scan and
      when new vulnerabilities are identified and reported. Scanning against a stale CVE
      database misses recently published vulnerabilities. Continuous feed updates —
      not weekly or monthly refresh cycles — are the expectation.
  - id: RA-5(3)
    name: Breadth and Depth of Coverage
    description: >
      The organization employs vulnerability scanning procedures that can demonstrate
      the breadth and depth of coverage. Breadth means every component in the authorization
      boundary is in scope — no exclusions without documented rationale. Depth means
      credential-based scanning where surface scanning would miss internal vulnerabilities.
  - id: RA-5(5)
    name: Privileged Access
    description: >
      The organization implements privileged access authorization to organizational systems
      for selected vulnerability scanning activities. Authenticated scanning produces
      materially more accurate results than unauthenticated scanning — finding counts
      are typically 5-10x higher with credentials.
  - id: RA-5(11)
    name: Public Disclosure Program
    description: >
      The organization establishes a public reporting channel for receiving reports of
      vulnerabilities in organizational systems. A coordinated vulnerability disclosure
      (CVD) policy and a security.txt file enables external researchers to report
      findings responsibly rather than publicly or silently.

HITRUST_map:
  - "10.l — Control of Technical Vulnerabilities"
  - "10.m — Control of Technical Vulnerabilities"
  - "03.b — Risk Assessment"

evidence:
  what_to_look_for:
    - Continuous or scheduled scan results covering all system components (containers, hosts, cloud services, applications)
    - Scan scope documentation confirming no components are excluded without documented rationale
    - Finding age tracking showing discovery timestamps and current remediation status per finding
    - Authenticated scan configuration (credentials used, scan depth)
    - Evidence of CVE database currency (scanner version and feed update timestamps)
    - Scan result trend over time — is the vulnerability count declining, stable, or growing?
  ask_for:
    - "Show me your current vulnerability scan results — what is the open critical and high count, and what is the oldest open finding?"
    - "Show me your scan scope — which components are included and are there any exclusions? What is the rationale for any exclusion?"
    - "Show me your scanner configuration — is it authenticated? How often does the CVE feed update?"
    - "Show me the trend over the last 90 days — is your vulnerability backlog decreasing?"
  tools:
    generic:
      - Trivy (container image, filesystem, IaC, and SBOM vulnerability scanning)
      - Grype (fast container image and SBOM vulnerability scanning)
      - Nuclei (web application and infrastructure vulnerability scanning)
      - OpenVAS / Greenbone (network and host vulnerability scanning)
      - OWASP ZAP (web application DAST scanning)
      - kube-bench (K8s component and configuration vulnerability assessment)
    aws:
      - Amazon Inspector (continuous EC2 and ECR scanning — no scan scheduling required)
      - AWS Config (configuration-level vulnerability detection via managed rules)
      - AWS Security Hub (aggregate Inspector, GuardDuty findings into prioritized view)
      - ECR Enhanced Scanning (Snyk-powered CVE scanning on image push and new CVE publication)
    microsoft:
      - Microsoft Defender for Containers (registry and runtime vulnerability assessment)
      - Microsoft Defender for Servers (VM vulnerability assessment via Qualys or Defender integration)
      - Microsoft Defender for Cloud (unified vulnerability findings across cloud estate)
      - Azure Container Registry Tasks (trigger scan on image push)

failure_to_implement:
  - Point-in-time scan quarterly — vulnerabilities published between scans go undetected for months.
  - Scans run but findings are not tracked — no one knows whether the same vulnerability has been open for a week or a year.
  - Scan scope excludes worker nodes or production namespaces "to avoid performance impact" — the most critical components are unscanned.
  - Unauthenticated scanning only — internal vulnerabilities accessible only with credentials are never surfaced.
  - Finding count is growing quarter over quarter — new vulnerabilities are introduced faster than existing ones are remediated.

related:
  - RA-3
  - RA-7
  - SI-2
  - CM-8

chain: null
