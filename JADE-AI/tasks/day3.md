*Wednesday morning. Sprint planning just ended. Your backlog grew, but at least you have context.*

---

## DAY 3 - Wednesday Morning

*Post-standup. Tech Lead drops by your desk with a sticky note.*

**Today's Structure:**
- 🏆 5 Golden Topics (must practice daily)
- 🎲 2 Random Tasks (varied skills)
- 🎤 3 Interview Questions (verbal practice)

---

# 🏆 GOLDEN TOPICS (5)

---

### TICKET-014 | 🔴 URGENT | Kubernetes | D-Rank
**From:** On-call Engineer (Chen)
**Channel:** #incident-medium

> Production deployment rollout is stuck. 3 of 5 replicas won't come up. The new pods keep failing readiness probes.
>
> ```
> kubectl get pods -n payments
> NAME                          READY   STATUS    RESTARTS   AGE
> payment-api-v2-abc123-x7k9p   1/1     Running   0          2d
> payment-api-v2-abc123-m3n2q   1/1     Running   0          2d
> payment-api-v2-def456-p9r8s   0/1     Running   0          8m
> payment-api-v2-def456-k2l4m   0/1     Running   0          8m
> payment-api-v2-def456-j5h6g   0/1     Running   0          8m
> ```
>
> ```yaml
> # New deployment readiness probe:
> readinessProbe:
>   httpGet:
>     path: /health
>     port: 8080
>   initialDelaySeconds: 5
>   periodSeconds: 10
>   failureThreshold: 3
> ```
>
> App logs show: `INFO: Server started on port 3000`
>
> Client wants to know ETA. Rollout is blocking their release.

**Deliverable:**
1. What's the root cause? (Be specific)
2. Two ways to fix this - quick fix vs proper fix
3. kubectl command to verify the fix worked
4. How would you prevent this in CI/CD?

---

### TICKET-015 | 🟡 Medium | OPA/Gatekeeper | C-Rank
**From:** Jira (Security Team)
**Project:** SEC-Audit-2026

> **Title:** Block privilege escalation in containers
>
> After the recent pentest, we need to enforce that NO container can set `allowPrivilegeEscalation: true` or run with `privileged: true`.
>
> Requirements:
> - Block at admission time (not just audit)
> - Clear error message for developers
> - Exclude `kube-system` namespace (some system pods need it)
> - Must work with both Deployments and raw Pods

**Deliverable:**
1. ConstraintTemplate with Rego logic
2. Constraint YAML with namespace exclusion
3. Example Pod that PASSES (proper security context)
4. Example Pod that FAILS (privileged container)
5. How would you roll this out safely to an existing cluster?

---

### TICKET-016 | 🟡 Medium | CI/CD Security | D-Rank
**From:** Client Success Manager (Jordan)
**Channel:** #client-securebank-support

> SecureBank is asking why their GitHub Actions workflow keeps failing with:
>
> ```
> Error: Process completed with exit code 1.
> ERROR: Gitleaks has detected sensitive information in your changes.
>
> Finding: Generic API Key
> Secret:  sk_live_******************
> File:    src/config/payment.ts
> Line:    42
> ```
>
> Developer says: "But I'm using environment variables! The secret is in GitHub Secrets!"
>
> Here's their code:
> ```typescript
> // src/config/payment.ts
> const STRIPE_KEY = process.env.STRIPE_KEY || "sk_live_defaultkey123456789";
> ```
>
> They want to know: Is Gitleaks broken? Should we add an exception?

**Deliverable:**
1. Explain why Gitleaks flagged this (it's not a false positive)
2. The secure fix for this code pattern
3. Should they add a `.gitleaksignore`? When is that appropriate?
4. Example `.gitleaks.toml` rule if they have legitimate test keys

---

### TICKET-017 | 🟢 Low | Scripting/Automation | C-Rank
**From:** Platform Team
**Channel:** #infrastructure

> We rotate our Kubernetes service account tokens monthly. Currently it's manual:
> 1. Generate new token
> 2. Update 12 different GitHub repos' secrets
> 3. Trigger deployments to pick up new token
> 4. Verify all services healthy
>
> Can you write a Python script to automate steps 2-4? We'll handle token generation separately.
>
> Requirements:
> - Input: new token value, list of repos
> - Use GitHub API to update secrets
> - Trigger workflow dispatch on each repo
> - Wait and verify deployment status
> - Output: success/failure report

**Deliverable:**
1. Python script with proper error handling
2. Example config file for repo list
3. How would you securely pass the token to this script?
4. What logging would you add for audit trail?

---

### TICKET-018 | 🟡 Medium | API Integration | D-Rank
**From:** Senior Consultant (Sarah)
**Channel:** #client-healthvault-support

> HealthVault's security dashboard stopped receiving findings from their Trivy scanner. The webhook integration was working yesterday.
>
> Error from their logs:
> ```
> POST /api/v1/findings HTTP/1.1 - 401 Unauthorized
> {"error": "Invalid API key", "code": "AUTH_FAILED"}
> ```
>
> They swear they haven't changed anything. The API key is stored in AWS Secrets Manager and injected as an env var.
>
> Their integration code:
> ```python
> import os
> import requests
>
> API_KEY = os.getenv("DASHBOARD_API_KEY")
>
> def send_findings(findings):
>     response = requests.post(
>         "https://security-dashboard.healthvault.io/api/v1/findings",
>         json=findings,
>         headers={"X-API-Key": API_KEY}
>     )
>     return response.status_code
> ```

**Deliverable:**
1. List 5 things you would check to debug this
2. How would you verify the API key is being loaded correctly?
3. What's your hypothesis for why it broke "without changes"?
4. How would you make this integration more resilient?

---

# 🎲 RANDOM TASKS (2)

---

### TICKET-019 | 🟢 Low | Helm Charts | E-Rank
**From:** Jira (from Sprint Planning)
**Project:** PLATFORM-Internal

> **Title:** Add resource limits to our internal Helm chart
>
> Our `jsa-cluster` Helm chart is missing resource requests/limits. Checkov is complaining.
>
> Current values.yaml has:
> ```yaml
> infrasec:
>   resources: {}
> ```
>
> Add sensible defaults for a security scanning agent that:
> - Runs periodic scans (CPU spikes during scans)
> - Holds scan results in memory temporarily
> - Should not be evicted during important scans

**Deliverable:**
1. Updated values.yaml snippet with resources
2. What's the difference between requests and limits?
3. How do you determine appropriate values for a new workload?

---

### TICKET-020 | 🟡 Medium | IAM Roles | C-Rank
**From:** Email from Client (forwarded by Tech Lead)
**Client:** TacticalNet (FedRAMP)

> "Our auditor is asking about our IAM role strategy. We have 47 roles and no one knows what half of them do. Can you help us:
>
> 1. Identify unused roles
> 2. Find overly permissive roles (wildcards)
> 3. Recommend a naming convention
>
> We need this documented for our FedRAMP package."

**Deliverable:**
1. AWS CLI commands to find unused roles (no recent activity)
2. AWS CLI or policy-analyzer approach to find `*` permissions
3. Recommended naming convention with examples
4. What ongoing process would prevent this sprawl?

---

# 🎤 INTERVIEW QUESTIONS (3)

*Answer these as if you're in an interview. Speak out loud or write as you would explain verbally. Structure matters.*

---

### INTERVIEW-01 | Explain a Concept
**Interviewer:** "Can you explain what Pod Security Standards are in Kubernetes and why they matter?"

**Your Task:**
- Explain PSS to someone who knows Kubernetes but not security
- Cover the three levels (Privileged, Baseline, Restricted)
- Give a real-world example of when you'd use each
- Mention how it relates to Pod Security Admission

**Format:** 2-3 minute verbal explanation (write it out as you'd say it)

---

### INTERVIEW-02 | Troubleshooting Scenario
**Interviewer:** "Walk me through how you would troubleshoot a Kubernetes pod that keeps getting OOMKilled."

**Your Task:**
- Describe your systematic approach
- What commands would you run first?
- How do you determine if it's a memory leak vs undersized limits?
- What's your fix strategy?

**Format:** Step-by-step walkthrough as you'd explain to an interviewer

---

### INTERVIEW-03 | Architecture Design
**Interviewer:** "If you were designing a secrets management strategy for a Kubernetes cluster, what would you consider?"

**Your Task:**
- Cover at least 3 different approaches (native secrets, external secrets, vault, etc.)
- Discuss trade-offs of each
- What would influence your recommendation?
- How would compliance requirements (HIPAA, PCI) affect your choice?

**Format:** Structured answer with clear reasoning

---

## ⏱️ Time Budget

| Section | Count | Time Each | Total |
|---------|-------|-----------|-------|
| Golden Topics | 5 | 20 min | 100 min |
| Random Tasks | 2 | 15 min | 30 min |
| Interview Questions | 3 | 10 min | 30 min |
| **Total** | **10** | - | **160 min** |

---

## ✅ Daily Checklist

### Golden Topics
- [ ] Kubernetes (TICKET-014)
- [ ] OPA/Gatekeeper (TICKET-015)
- [ ] CI/CD Security (TICKET-016)
- [ ] Scripting/Automation (TICKET-017)
- [ ] API Integration (TICKET-018)

### Random Tasks
- [ ] Helm Charts (TICKET-019)
- [ ] IAM Roles (TICKET-020)

### Interview Practice
- [ ] Explain: Pod Security Standards (INTERVIEW-01)
- [ ] Troubleshoot: OOMKilled pods (INTERVIEW-02)
- [ ] Design: Secrets Management (INTERVIEW-03)

---

*Chen is still waiting on that deployment fix. The rollout has been stuck for 15 minutes now.*

*Handle the urgent one first. Then work through the rest. The interview questions can be done on your lunch break.*

*Go.* 🎯
