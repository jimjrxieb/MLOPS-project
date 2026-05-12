#!/usr/bin/env python3
"""
generate_platform_eng_eval.py — Eval questions for junior platform engineer skills.

Covers everything a junior touches daily that's NOT already in the K8s eval suites:
- Python (bandit errors, pip audit, venv, debugging)
- Bash/Linux (scripting, systemctl, journalctl, troubleshooting)
- Git (merge conflicts, rebase, bisect, workflow)
- GitHub Actions (workflow YAML, secrets, debugging failing runs)
- Terraform (plan/apply, state, modules, drift)
- OPA/Rego (deny messages, policy writing, conftest)
- Helm (values, templates, upgrade, rollback)
- Docker (Dockerfile, multi-stage, layer optimization)
- AWS CLI (iam, s3, eks, sts, ssm)

Output: JSONL eval questions → 4-eval-clarify/2-test-data/evaluation/
"""

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "4-eval-clarify" / "2-test-data" / "evaluation"


def eval_q(id, category, subcategory, rank, question, expected_keywords, expected_fix_contains=None):
    """Build an eval question in the standard format."""
    q = {
        "id": id,
        "category": category,
        "subcategory": subcategory,
        "rank": rank,
        "question": question,
        "expected_keywords": expected_keywords,
        "grading": {
            "keywords_required": min(3, len(expected_keywords)),
            "fix_required": expected_fix_contains is not None,
            "workflow_required": False,
        },
    }
    if expected_fix_contains:
        q["expected_fix_contains"] = expected_fix_contains
    return q


def generate_python_eval():
    """Python/SAST eval — bandit errors, pip audit, debugging."""
    return [
        eval_q("py-sast-001", "python", "bandit", "D",
               "Bandit flagged B602: subprocess call with shell=True. How do you fix it?",
               ["subprocess", "shell=False", "shlex", "list", "Popen"],
               "shell=False"),
        eval_q("py-sast-002", "python", "bandit", "D",
               "Bandit flagged B106: hardcoded password in function argument. What's the fix?",
               ["environment variable", "os.environ", "secrets", "keyring", "vault"],
               "os.environ"),
        eval_q("py-sast-003", "python", "bandit", "D",
               "Bandit flagged B301: pickle.loads detected. Why is this dangerous and what's the alternative?",
               ["deserialization", "arbitrary code", "json", "yaml.safe_load", "untrusted"]),
        eval_q("py-sast-004", "python", "bandit", "D",
               "Bandit flagged B105: hardcoded password string detected in config.py. How do you remediate?",
               ["environment", "os.environ", ".env", "secrets manager", "remove"],
               "os.environ"),
        eval_q("py-deps-001", "python", "pip-audit", "D",
               "pip-audit found CVE-2024-1234 in requests==2.28.0 with fix available in 2.31.0. Walk through the fix.",
               ["pip install", "requirements.txt", "2.31.0", "pin", "test"]),
        eval_q("py-deps-002", "python", "pip-audit", "D",
               "pip-audit shows 3 vulnerabilities but 'no fix available' for one of them. What do you do?",
               ["upgrade", "available", "alternative", "suppress", "risk accept", "monitor"]),
        eval_q("py-venv-001", "python", "venv", "E",
               "How do you create a Python virtual environment, activate it, and install requirements?",
               ["python3 -m venv", "source", "activate", "pip install", "requirements.txt"]),
        eval_q("py-debug-001", "python", "debugging", "D",
               "A Python app crashes with 'ModuleNotFoundError: No module named requests'. The Dockerfile doesn't install deps. Fix it.",
               ["RUN pip install", "requirements.txt", "COPY requirements", "Dockerfile"],
               "pip install -r requirements.txt"),
        eval_q("py-yaml-001", "python", "yaml", "D",
               "Bandit flagged B506: yaml.load() is unsafe. How do you fix it?",
               ["yaml.safe_load", "Loader=SafeLoader", "untrusted", "code execution"],
               "safe_load"),
        eval_q("py-random-001", "python", "crypto", "D",
               "Bandit flagged B311: random.random() used for security token generation. What's the fix?",
               ["secrets", "secrets.token_hex", "secrets.token_urlsafe", "os.urandom", "cryptographic"],
               "secrets"),
    ]


def generate_bash_eval():
    """Bash/Linux eval — scripting, troubleshooting, system admin."""
    return [
        eval_q("bash-001", "bash", "scripting", "D",
               "Write a bash script that checks if a file exists, and exits with error code 1 if it doesn't.",
               ["if", "-f", "exit 1", "fi", "then"]),
        eval_q("bash-002", "bash", "scripting", "D",
               "How do you set a bash script to exit on any error, undefined variable, or pipe failure?",
               ["set -e", "set -u", "set -o pipefail", "errexit", "nounset"],
               "set -euo pipefail"),
        eval_q("bash-003", "bash", "piping", "D",
               "Find all .yaml files in the current directory recursively that contain 'privileged: true'.",
               ["find", "grep", "-r", "*.yaml", "privileged"]),
        eval_q("linux-001", "bash", "systemd", "D",
               "A service 'nginx' is failing to start. Walk through the troubleshooting commands.",
               ["systemctl status", "journalctl -u", "systemctl restart", "journalctl -xe"]),
        eval_q("linux-002", "bash", "disk", "D",
               "A node reports disk full. How do you find what's using the space?",
               ["df -h", "du -sh", "sort", "find", "ncdu"]),
        eval_q("linux-003", "bash", "networking", "D",
               "How do you check which process is listening on port 8080?",
               ["ss -tlnp", "lsof", "netstat", "8080", "PID"]),
        eval_q("linux-004", "bash", "permissions", "E",
               "A script fails with 'Permission denied'. How do you make it executable?",
               ["chmod", "+x", "chmod 755", "ls -l"]),
        eval_q("linux-005", "bash", "processes", "D",
               "How do you find and kill a zombie process consuming 100% CPU?",
               ["ps aux", "top", "kill", "kill -9", "PID"]),
        eval_q("bash-jq-001", "bash", "jq", "D",
               "Extract all pod names from kubectl get pods -o json output using jq.",
               ["jq", ".items[].metadata.name", "kubectl get pods", "-o json"]),
        eval_q("bash-curl-001", "bash", "curl", "D",
               "How do you test if an HTTP endpoint returns 200 and show only the status code?",
               ["curl", "-s", "-o /dev/null", "-w", "%{http_code}", "200"]),
    ]


def generate_git_eval():
    """Git eval — merge conflicts, rebase, workflow."""
    return [
        eval_q("git-001", "git", "merge-conflict", "D",
               "You pulled and got a merge conflict in deployment.yaml. Walk through resolving it.",
               ["git status", "<<<<<<<", "=======", ">>>>>>>", "git add", "git commit"]),
        eval_q("git-002", "git", "rebase", "C",
               "Your feature branch is 10 commits behind main. How do you rebase it?",
               ["git fetch", "git rebase", "origin/main", "force-push", "git push"]),
        eval_q("git-003", "git", "bisect", "C",
               "A bug was introduced sometime in the last 20 commits. How do you find which commit?",
               ["git bisect", "start", "bad", "good", "git bisect reset"]),
        eval_q("git-004", "git", "secrets", "D",
               "You accidentally committed a .env file with secrets. How do you remove it from history?",
               ["git filter-branch", "BFG", "git-filter-repo", ".gitignore", "force-push", "rotate"]),
        eval_q("git-005", "git", "workflow", "E",
               "How do you create a new branch, make a change, and open a PR using the gh CLI?",
               ["git checkout -b", "git add", "git commit", "git push", "gh pr create"]),
        eval_q("git-006", "git", "stash", "E",
               "You need to switch branches but have uncommitted changes. How do you save them?",
               ["git stash", "git stash pop", "git stash list", "git stash apply"]),
    ]


def generate_github_actions_eval():
    """GitHub Actions eval — workflow YAML, debugging, secrets."""
    return [
        eval_q("gha-001", "github-actions", "workflow", "D",
               "Write a GitHub Actions workflow that runs pytest on push to main.",
               ["on:", "push:", "branches:", "main", "runs-on:", "ubuntu", "pip install", "pytest"],
               "pytest"),
        eval_q("gha-002", "github-actions", "secrets", "D",
               "How do you use a secret called AWS_ACCESS_KEY in a GitHub Actions workflow step?",
               ["secrets.AWS_ACCESS_KEY", "${{", "env:", "secrets"]),
        eval_q("gha-003", "github-actions", "debugging", "C",
               "A GitHub Actions workflow fails with 'Error: Process completed with exit code 1' and no other output. How do you debug?",
               ["ACTIONS_STEP_DEBUG", "set -x", "run:", "verbose", "gh run view", "logs"]),
        eval_q("gha-004", "github-actions", "matrix", "D",
               "How do you run tests against Python 3.10, 3.11, and 3.12 in parallel using matrix strategy?",
               ["strategy:", "matrix:", "python-version:", "3.10", "3.11", "3.12"]),
        eval_q("gha-005", "github-actions", "caching", "D",
               "How do you cache pip dependencies in GitHub Actions to speed up CI?",
               ["actions/cache", "pip", "hashFiles", "requirements.txt", "restore-keys"]),
        eval_q("gha-006", "github-actions", "security", "D",
               "A GitHub Action uses a third-party action pinned to @main. What's the security risk and fix?",
               ["pin", "sha", "@", "digest", "supply chain", "actions/checkout@v4"]),
        eval_q("gha-007", "github-actions", "artifacts", "D",
               "How do you upload test results as artifacts in GitHub Actions?",
               ["actions/upload-artifact", "path:", "name:", "retention-days"]),
        eval_q("gha-008", "github-actions", "workflow-dispatch", "D",
               "How do you create a manually-triggered workflow with input parameters?",
               ["workflow_dispatch:", "inputs:", "description:", "required:", "type:"]),
    ]


def generate_terraform_eval():
    """Terraform/IaC eval — plan, state, modules, drift."""
    return [
        eval_q("tf-001", "terraform", "plan", "D",
               "terraform plan shows 3 resources to destroy that shouldn't be destroyed. What happened and how do you fix it?",
               ["terraform state", "drift", "refresh", "import", "terraform plan", "target"]),
        eval_q("tf-002", "terraform", "state", "C",
               "A resource was created manually in AWS. How do you bring it under Terraform management?",
               ["terraform import", "resource address", "state", "write the resource block"]),
        eval_q("tf-003", "terraform", "modules", "D",
               "What's wrong with this module source: `source = \"git::https://github.com/org/modules\"` without a ref?",
               ["pin", "ref=", "tag", "version", "reproducible", "?ref=v1.0"]),
        eval_q("tf-004", "terraform", "security", "D",
               "tfsec flagged: S3 bucket has no encryption configured. Show the Terraform fix.",
               ["aws_s3_bucket_server_side_encryption_configuration", "AES256", "aws:kms", "rule"],
               "server_side_encryption_configuration"),
        eval_q("tf-005", "terraform", "state-lock", "C",
               "terraform apply fails with 'Error acquiring the state lock'. What do you do?",
               ["terraform force-unlock", "DynamoDB", "state lock", "lock ID", "another process"]),
        eval_q("tf-006", "terraform", "drift", "C",
               "terraform plan shows changes you didn't make. How do you investigate and resolve drift?",
               ["terraform refresh", "terraform state show", "AWS console", "manual change", "import"]),
        eval_q("tf-007", "terraform", "variables", "E",
               "How do you pass a variable to terraform apply without hardcoding it?",
               ["TF_VAR_", "-var", "terraform.tfvars", ".auto.tfvars", "environment variable"]),
        eval_q("tf-008", "terraform", "backend", "D",
               "How do you configure Terraform to store state in S3 with DynamoDB locking?",
               ["backend", "s3", "bucket", "key", "dynamodb_table", "encrypt"]),
    ]


def generate_opa_eval():
    """OPA/Rego eval — deny messages, policy writing, conftest."""
    return [
        eval_q("opa-001", "opa", "deny-message", "D",
               "Conftest fails with 'FAIL - deployment.yaml - Containers must not run as privileged'. How do you fix the manifest?",
               ["privileged: false", "securityContext", "remove privileged", "conftest test"]),
        eval_q("opa-002", "opa", "rego", "C",
               "Write an OPA Rego policy that denies any Deployment without resource limits.",
               ["deny", "input.spec.template.spec.containers", "resources", "limits", "violation"],
               "deny"),
        eval_q("opa-003", "opa", "conftest", "D",
               "How do you run conftest against Kubernetes manifests in a CI pipeline?",
               ["conftest test", "--policy", ".rego", "deployment.yaml", "exit code"]),
        eval_q("opa-004", "opa", "gatekeeper", "C",
               "A Gatekeeper ConstraintTemplate is deployed but the Constraint isn't matching any resources. How do you debug?",
               ["kubectl get constraint", "describe", "match", "kinds", "namespaceSelector", "audit"]),
        eval_q("opa-005", "opa", "kyverno", "D",
               "A Kyverno policy is in audit mode and logging violations. How do you switch it to enforce?",
               ["validationFailureAction", "Enforce", "Audit", "kubectl edit", "ClusterPolicy"]),
        eval_q("opa-006", "opa", "testing", "C",
               "How do you write unit tests for OPA Rego policies?",
               ["opa test", "test_", "with input as", "mock", ".rego"]),
    ]


def generate_helm_eval():
    """Helm eval — values, templates, upgrade, rollback."""
    return [
        eval_q("helm-001", "helm", "values", "D",
               "How do you override a Helm chart value at install time without editing the values.yaml?",
               ["--set", "--values", "-f", "helm install", "helm upgrade"]),
        eval_q("helm-002", "helm", "template", "D",
               "helm template renders but helm install fails. How do you debug?",
               ["helm template", "helm install --dry-run", "--debug", "kubectl apply --dry-run"]),
        eval_q("helm-003", "helm", "rollback", "D",
               "A helm upgrade broke the app. How do you rollback to the previous release?",
               ["helm rollback", "helm history", "REVISION", "helm rollback <release> <revision>"]),
        eval_q("helm-004", "helm", "hooks", "C",
               "A Helm pre-install hook job keeps failing and blocking the install. How do you fix it?",
               ["helm.sh/hook", "pre-install", "hook-delete-policy", "Job", "backoffLimit"]),
        eval_q("helm-005", "helm", "dependencies", "D",
               "How do you add a dependency chart (e.g., PostgreSQL) to your Helm chart?",
               ["Chart.yaml", "dependencies:", "repository:", "version:", "helm dependency update"]),
        eval_q("helm-006", "helm", "secrets", "C",
               "How do you manage secrets in Helm without committing them to git?",
               ["helm-secrets", "sops", "sealed-secrets", "external-secrets", "encrypt"]),
    ]


def generate_docker_eval():
    """Docker eval — Dockerfile, multi-stage, optimization."""
    return [
        eval_q("docker-001", "docker", "dockerfile", "D",
               "This Dockerfile installs deps before copying source code, so every code change rebuilds deps. Fix the layer ordering.",
               ["COPY requirements.txt", "RUN pip install", "COPY . .", "layer cache", "before"],
               "COPY requirements.txt"),
        eval_q("docker-002", "docker", "multi-stage", "D",
               "How do you use a multi-stage Dockerfile to build a Go binary without including the compiler in the final image?",
               ["FROM golang", "AS builder", "FROM alpine", "COPY --from=builder", "scratch"]),
        eval_q("docker-003", "docker", "security", "D",
               "Hadolint warns: 'DL3002 Last USER should not be root'. How do you fix it?",
               ["USER", "useradd", "adduser", "non-root", "1000"],
               "USER"),
        eval_q("docker-004", "docker", "security", "D",
               "Hadolint warns: 'DL3007 Using latest is prone to errors'. Fix the FROM line.",
               ["FROM", "pin", "tag", "sha256", "digest", "version"],
               ":"),
        eval_q("docker-005", "docker", "optimization", "D",
               "Your Docker image is 1.2GB. How do you reduce it?",
               ["multi-stage", "alpine", "slim", ".dockerignore", "rm -rf", "layer"]),
        eval_q("docker-006", "docker", "healthcheck", "E",
               "Add a HEALTHCHECK to a Dockerfile that checks if the app responds on port 8080.",
               ["HEALTHCHECK", "CMD", "curl", "wget", "8080", "--interval"]),
    ]


def generate_aws_eval():
    """AWS CLI eval — iam, s3, eks, sts, ssm."""
    return [
        eval_q("aws-001", "aws", "iam", "D",
               "How do you list all IAM users that haven't logged in for 90 days?",
               ["aws iam", "generate-credential-report", "get-credential-report", "password_last_used"]),
        eval_q("aws-002", "aws", "s3", "E",
               "How do you sync a local directory to an S3 bucket?",
               ["aws s3 sync", "s3://", "--delete", "cp"]),
        eval_q("aws-003", "aws", "eks", "D",
               "How do you update your kubeconfig to connect to an EKS cluster?",
               ["aws eks update-kubeconfig", "--name", "--region", "kubeconfig"]),
        eval_q("aws-004", "aws", "sts", "D",
               "How do you assume an IAM role from the CLI and use it for subsequent commands?",
               ["aws sts assume-role", "--role-arn", "AccessKeyId", "SecretAccessKey", "SessionToken", "export"]),
        eval_q("aws-005", "aws", "ssm", "D",
               "How do you store and retrieve a secret using AWS Systems Manager Parameter Store?",
               ["aws ssm put-parameter", "get-parameter", "--type SecureString", "--with-decryption", "--name"]),
        eval_q("aws-006", "aws", "cloudwatch", "D",
               "How do you view the last 100 log events from a CloudWatch log group?",
               ["aws logs", "filter-log-events", "--log-group-name", "get-log-events", "--limit"]),
        eval_q("aws-007", "aws", "ecr", "D",
               "How do you authenticate Docker to push images to ECR?",
               ["aws ecr get-login-password", "docker login", "--password-stdin", "ECR registry URL"]),
        eval_q("aws-008", "aws", "vpc", "C",
               "An EKS pod can't reach an RDS instance in a different subnet. Walk through the networking troubleshooting.",
               ["security group", "subnet", "route table", "VPC peering", "CIDR", "port 5432"]),
    ]


def write_eval_suite(name, dirname, questions):
    """Write eval questions to a benchmark directory."""
    outdir = EVAL_DIR / dirname
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{name}_eval.jsonl"

    with open(outfile, "w") as f:
        for q in questions:
            f.write(json.dumps(q) + "\n")

    print(f"  {dirname}: {len(questions)} questions → {outfile.name}")
    return len(questions)


def main():
    print("Generating platform engineering eval suites...\n")

    total = 0
    total += write_eval_suite("python", "16-python-benchmark", generate_python_eval())
    total += write_eval_suite("bash", "17-bash-linux-benchmark", generate_bash_eval())
    total += write_eval_suite("git", "18-git-benchmark", generate_git_eval())
    total += write_eval_suite("github_actions", "19-github-actions-benchmark", generate_github_actions_eval())
    total += write_eval_suite("terraform", "20-terraform-benchmark", generate_terraform_eval())
    total += write_eval_suite("opa", "21-opa-rego-benchmark", generate_opa_eval())
    total += write_eval_suite("helm", "22-helm-benchmark", generate_helm_eval())
    total += write_eval_suite("docker", "23-docker-benchmark", generate_docker_eval())
    total += write_eval_suite("aws", "24-aws-cli-benchmark", generate_aws_eval())

    print(f"\nTotal: {total} new eval questions across 9 domains")
    print(f"Output: {EVAL_DIR}")


if __name__ == "__main__":
    main()
