#!/usr/bin/env python3
"""
Policy RAG Generator - Creates graph-like structured RAG data from Rego policies

Produces JSONL with:
1. Policy code + rich metadata
2. Q&A pairs teaching how to write each policy
3. Field path mappings (critical for JADE)
4. Relationships between policies
5. Common mistakes to avoid
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Field path knowledge graph
FIELD_PATHS = {
    # Pod-level fields (NOT in containers)
    "hostPID": {
        "path": "input.request.object.spec.hostPID",
        "level": "pod",
        "description": "Share host PID namespace",
        "common_mistake": "Looking in containers[_].securityContext.hostPID (WRONG)"
    },
    "hostIPC": {
        "path": "input.request.object.spec.hostIPC",
        "level": "pod",
        "description": "Share host IPC namespace",
        "common_mistake": "Looking in containers[_].securityContext.hostIPC (WRONG)"
    },
    "hostNetwork": {
        "path": "input.request.object.spec.hostNetwork",
        "level": "pod",
        "description": "Share host network namespace",
        "common_mistake": "Looking in containers[_].securityContext.hostNetwork (WRONG)"
    },
    "automountServiceAccountToken": {
        "path": "input.request.object.spec.automountServiceAccountToken",
        "level": "pod",
        "description": "Auto-mount SA token",
        "common_mistake": "Looking in containers[_].automountServiceAccountToken (WRONG - field doesn't exist there)"
    },
    "volumes": {
        "path": "input.request.object.spec.volumes[_]",
        "level": "pod",
        "description": "Pod volumes definition"
    },
    "sysctls": {
        "path": "input.request.object.spec.securityContext.sysctls[_]",
        "level": "pod",
        "description": "Kernel sysctls tuning",
        "common_mistake": "Looking in containers[_].securityContext.sysctls (WRONG)"
    },
    "fsGroup": {
        "path": "input.request.object.spec.securityContext.fsGroup",
        "level": "pod",
        "description": "Filesystem group for volumes"
    },
    "shareProcessNamespace": {
        "path": "input.request.object.spec.shareProcessNamespace",
        "level": "pod",
        "description": "Share process namespace between containers"
    },
    # Container-level fields
    "privileged": {
        "path": "containers[_].securityContext.privileged",
        "level": "container",
        "description": "Run container in privileged mode"
    },
    "allowPrivilegeEscalation": {
        "path": "containers[_].securityContext.allowPrivilegeEscalation",
        "level": "container",
        "description": "Allow privilege escalation in container"
    },
    "runAsUser": {
        "path": "containers[_].securityContext.runAsUser",
        "level": "container",
        "description": "Container user ID",
        "note": "Also available at pod-level: spec.securityContext.runAsUser"
    },
    "runAsGroup": {
        "path": "containers[_].securityContext.runAsGroup",
        "level": "container",
        "description": "Container group ID"
    },
    "runAsNonRoot": {
        "path": "containers[_].securityContext.runAsNonRoot",
        "level": "container",
        "description": "Require non-root user"
    },
    "readOnlyRootFilesystem": {
        "path": "containers[_].securityContext.readOnlyRootFilesystem",
        "level": "container",
        "description": "Read-only root filesystem"
    },
    "capabilities": {
        "path": "containers[_].securityContext.capabilities",
        "level": "container",
        "description": "Linux capabilities (add/drop)"
    },
    "procMount": {
        "path": "containers[_].securityContext.procMount",
        "level": "container",
        "description": "Proc mount type (Default/Unmasked)"
    },
    "seccompProfile": {
        "path": "containers[_].securityContext.seccompProfile",
        "level": "container",
        "description": "Seccomp profile",
        "note": "Also at pod-level: spec.securityContext.seccompProfile"
    },
    "image": {
        "path": "containers[_].image",
        "level": "container",
        "description": "Container image reference"
    },
    "resources": {
        "path": "containers[_].resources",
        "level": "container",
        "description": "Resource limits and requests"
    },
    "livenessProbe": {
        "path": "containers[_].livenessProbe",
        "level": "container",
        "description": "Container liveness probe"
    },
    "readinessProbe": {
        "path": "containers[_].readinessProbe",
        "level": "container",
        "description": "Container readiness probe"
    },
    # AppArmor (special - annotations)
    "apparmor": {
        "path": 'input.request.object.metadata.annotations["container.apparmor.security.beta.kubernetes.io/<container-name>"]',
        "level": "annotation",
        "description": "AppArmor profile (per-container annotation)",
        "common_mistake": "Looking in securityContext.appArmorProfile (WRONG - it's an annotation)"
    },
    # Namespace
    "namespace": {
        "path": "input.request.object.metadata.namespace",
        "level": "metadata",
        "description": "Pod namespace"
    }
}

# Terraform field paths
TERRAFORM_PATHS = {
    "aws_s3_bucket": "input.resource.aws_s3_bucket[name]",
    "aws_s3_bucket_acl": "input.resource.aws_s3_bucket_acl[name]",
    "aws_s3_bucket_versioning": "input.resource.aws_s3_bucket_versioning[name].versioning_configuration[_].status",
    "aws_s3_bucket_logging": "input.resource.aws_s3_bucket_logging[name]",
    "aws_s3_bucket_encryption": "input.resource.aws_s3_bucket_server_side_encryption_configuration[name]",
    "aws_s3_bucket_public_access_block": "input.resource.aws_s3_bucket_public_access_block[name]",
    "aws_db_instance": "input.resource.aws_db_instance[name]",
    "aws_security_group": "input.resource.aws_security_group[name]",
    "aws_instance": "input.resource.aws_instance[name]",
    "aws_iam_policy": "input.resource.aws_iam_policy[name]",
    "aws_lambda_function": "input.resource.aws_lambda_function[name]",
    # Plan JSON format
    "resource_changes": "input.resource_changes[_]"
}


def parse_rego_file(file_path: Path) -> Dict:
    """Parse a Rego file and extract structured metadata."""
    content = file_path.read_text()

    result = {
        "filename": file_path.name,
        "package": "",
        "description": "",
        "severity": "MEDIUM",
        "category": "",
        "resources": [],
        "code": content,
        "deny_rules": [],
        "warn_rules": [],
        "helper_functions": [],
        "field_paths": [],
        "input_structure": "kubernetes",  # or "terraform"
        "compliance_refs": []
    }

    # Extract package
    pkg_match = re.search(r'^package\s+(\S+)', content, re.MULTILINE)
    if pkg_match:
        result["package"] = pkg_match.group(1)
        if "terraform" in result["package"].lower():
            result["input_structure"] = "terraform"

    # Extract header comments
    header_comments = re.findall(r'^#\s*(.+)$', content, re.MULTILINE)
    for comment in header_comments[:10]:
        if "Description:" in comment:
            result["description"] = comment.split("Description:")[-1].strip()
        elif "Severity:" in comment:
            result["severity"] = comment.split("Severity:")[-1].strip()
        elif "Category:" in comment:
            result["category"] = comment.split("Category:")[-1].strip()
        elif "Resources:" in comment:
            result["resources"] = [r.strip() for r in comment.split("Resources:")[-1].split(",")]

    # Extract compliance references (PCI-DSS, CIS, etc.)
    compliance_refs = re.findall(r'(PCI-DSS\s+[\d.]+|CIS\s+AWS\s+[\d.]+|CIS\s+[\d.]+)', content)
    result["compliance_refs"] = list(set(compliance_refs))

    # Extract deny rules
    deny_matches = re.findall(r'deny\[msg\]\s*\{([^}]+)\}', content, re.DOTALL)
    result["deny_rules"] = [d.strip() for d in deny_matches]

    # Extract warn rules
    warn_matches = re.findall(r'warn\[msg\]\s*\{([^}]+)\}', content, re.DOTALL)
    result["warn_rules"] = [w.strip() for w in warn_matches]

    # Extract helper functions
    helper_matches = re.findall(r'^(\w+)\([^)]*\)\s*\{([^}]+)\}', content, re.MULTILINE | re.DOTALL)
    for name, body in helper_matches:
        if name not in ["deny", "warn"]:
            result["helper_functions"].append({"name": name, "body": body.strip()})

    # Detect field paths used
    for field, info in FIELD_PATHS.items():
        if field in content.lower() or info["path"].split(".")[-1] in content:
            result["field_paths"].append({
                "field": field,
                "level": info["level"],
                "path": info["path"]
            })

    return result


def generate_qa_pairs(policy: Dict) -> List[Dict]:
    """Generate Q&A training pairs from a policy."""
    qa_pairs = []

    filename = policy["filename"]
    code = policy["code"]
    package = policy["package"]

    # Q1: How to write this policy
    policy_name = filename.replace(".rego", "").replace("-", " ").replace("_", " ")
    qa_pairs.append({
        "instruction": f"Write an OPA Rego policy to {policy_name}",
        "input": f"Package: {package}, Input structure: {policy['input_structure']}",
        "output": code,
        "metadata": {
            "type": "policy-generation",
            "domain": "opa-rego",
            "skill_level": "C-rank",
            "source": filename,
            "compliance": policy["compliance_refs"]
        }
    })

    # Q2: Field path explanation
    for fp in policy["field_paths"]:
        field_info = FIELD_PATHS.get(fp["field"], {})
        qa_pairs.append({
            "instruction": f"Where is the {fp['field']} field located in a Kubernetes pod?",
            "input": "OPA Rego policy field path",
            "output": f"The {fp['field']} field is at {fp['level']}-level.\n\nField path: `{fp['path']}`\n\nDescription: {field_info.get('description', 'N/A')}\n\n" +
                     (f"COMMON MISTAKE: {field_info.get('common_mistake', '')}\n" if field_info.get('common_mistake') else ""),
            "metadata": {
                "type": "field-knowledge",
                "domain": "kubernetes-opa",
                "skill_level": "C-rank",
                "field_level": fp["level"]
            }
        })

    # Q3: What does this policy check?
    if policy["description"]:
        qa_pairs.append({
            "instruction": f"What does the {filename} OPA policy check for?",
            "input": "",
            "output": f"Policy: {filename}\nPackage: {package}\n\nDescription: {policy['description']}\n\nSeverity: {policy['severity']}\nCategory: {policy['category']}\nResources: {', '.join(policy['resources'])}\n\nCompliance references: {', '.join(policy['compliance_refs']) if policy['compliance_refs'] else 'N/A'}",
            "metadata": {
                "type": "policy-explanation",
                "domain": "opa-rego",
                "skill_level": "D-rank"
            }
        })

    return qa_pairs


def generate_relationship_entries(policies: List[Dict]) -> List[Dict]:
    """Generate entries showing relationships between policies."""
    entries = []

    # Group by category
    by_category = {}
    for p in policies:
        cat = p.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(p["filename"])

    for category, filenames in by_category.items():
        if len(filenames) > 1:
            entries.append({
                "instruction": f"What OPA policies relate to {category}?",
                "input": "List related security policies",
                "output": f"Related policies in the '{category}' category:\n\n" +
                         "\n".join([f"- {f}" for f in filenames]),
                "metadata": {
                    "type": "policy-relationship",
                    "domain": "opa-rego",
                    "category": category
                }
            })

    # Group by field level
    pod_level = [p["filename"] for p in policies if any(fp["level"] == "pod" for fp in p.get("field_paths", []))]
    container_level = [p["filename"] for p in policies if any(fp["level"] == "container" for fp in p.get("field_paths", []))]

    if pod_level:
        entries.append({
            "instruction": "Which Kubernetes security policies check pod-level fields?",
            "input": "Fields at spec.* not containers[_].*",
            "output": "Pod-level security policies (fields at spec.*, NOT containers[].*):\n\n" +
                     "\n".join([f"- {f}" for f in pod_level]) +
                     "\n\nThese fields include: hostPID, hostIPC, hostNetwork, automountServiceAccountToken, sysctls, volumes",
            "metadata": {
                "type": "field-level-mapping",
                "domain": "kubernetes-opa",
                "level": "pod"
            }
        })

    return entries


def generate_terraform_knowledge() -> List[Dict]:
    """Generate Terraform-specific knowledge entries."""
    entries = []

    # Input structure difference
    entries.append({
        "instruction": "What is the input structure difference between Kubernetes OPA and Terraform Conftest policies?",
        "input": "Comparing OPA input.request vs Terraform input.resource",
        "output": """## Kubernetes Admission (OPA/Gatekeeper)
```rego
input.request.kind.kind == "Pod"
input.request.object.spec.containers[_]
input.request.object.metadata.namespace
```

## Terraform (Conftest)
```rego
# For HCL files directly:
input.resource.aws_s3_bucket[name]
input.resource.aws_db_instance[name]

# For terraform plan JSON:
resource := input.resource_changes[_]
resource.type == "aws_s3_bucket"
resource.change.after.bucket
```

CRITICAL: Never use `input.request.kind.kind` in Terraform policies - that's Kubernetes-only!""",
        "metadata": {
            "type": "input-structure",
            "domain": "opa-rego",
            "skill_level": "C-rank"
        }
    })

    # Terraform resource patterns
    for resource, path in TERRAFORM_PATHS.items():
        if "aws_s3" in resource:
            entries.append({
                "instruction": f"How do I access {resource} in a Terraform Conftest policy?",
                "input": "Terraform OPA Rego resource access",
                "output": f"Access {resource} using:\n\n```rego\n{resource.replace('aws_', '')} := {path}\n```\n\nPackage should be `package terraform.s3` or similar.",
                "metadata": {
                    "type": "terraform-resource",
                    "domain": "terraform-opa",
                    "resource": resource
                }
            })

    return entries


def main():
    """Main entry point."""
    # Paths
    input_dir = Path("/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/4-GP-CLARIFY/2-test-data/inference-tests/policies/all-policies")
    output_dir = Path("/home/jimmie/linkops-industries/GP-copilot/GP-OPENSEARCH/01-unprocessed")
    output_file = output_dir / f"policy_rag_structured_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    print(f"Parsing policies from: {input_dir}")

    # Parse all policies
    policies = []
    for rego_file in sorted(input_dir.glob("*.rego")):
        print(f"  Parsing: {rego_file.name}")
        policy = parse_rego_file(rego_file)
        policies.append(policy)

    print(f"\nParsed {len(policies)} policies")

    # Generate structured entries
    all_entries = []

    # 1. Q&A pairs for each policy
    for policy in policies:
        qa_pairs = generate_qa_pairs(policy)
        all_entries.extend(qa_pairs)

    # 2. Relationship entries
    relationship_entries = generate_relationship_entries(policies)
    all_entries.extend(relationship_entries)

    # 3. Terraform knowledge
    terraform_entries = generate_terraform_knowledge()
    all_entries.extend(terraform_entries)

    # 4. Field path master reference
    all_entries.append({
        "instruction": "What is the complete field path reference for Kubernetes OPA policies?",
        "input": "Pod-level vs container-level fields",
        "output": """# Kubernetes Field Path Reference for OPA Rego

## POD-LEVEL Fields (at spec.*, NOT containers[].*)
| Field | Path |
|-------|------|
| hostPID | `input.request.object.spec.hostPID` |
| hostIPC | `input.request.object.spec.hostIPC` |
| hostNetwork | `input.request.object.spec.hostNetwork` |
| automountServiceAccountToken | `input.request.object.spec.automountServiceAccountToken` |
| sysctls | `input.request.object.spec.securityContext.sysctls[_]` |
| volumes | `input.request.object.spec.volumes[_]` |
| fsGroup | `input.request.object.spec.securityContext.fsGroup` |
| shareProcessNamespace | `input.request.object.spec.shareProcessNamespace` |

## CONTAINER-LEVEL Fields (at containers[].*)
| Field | Path |
|-------|------|
| privileged | `containers[_].securityContext.privileged` |
| allowPrivilegeEscalation | `containers[_].securityContext.allowPrivilegeEscalation` |
| runAsUser | `containers[_].securityContext.runAsUser` |
| runAsGroup | `containers[_].securityContext.runAsGroup` |
| runAsNonRoot | `containers[_].securityContext.runAsNonRoot` |
| readOnlyRootFilesystem | `containers[_].securityContext.readOnlyRootFilesystem` |
| capabilities | `containers[_].securityContext.capabilities.add/drop` |
| procMount | `containers[_].securityContext.procMount` |
| seccompProfile | `containers[_].securityContext.seccompProfile` |
| image | `containers[_].image` |
| resources | `containers[_].resources.limits/requests` |

## SPECIAL: AppArmor (Annotation, not securityContext!)
```rego
annotation_key := sprintf("container.apparmor.security.beta.kubernetes.io/%s", [container.name])
profile := input.request.object.metadata.annotations[annotation_key]
```

## SPECIAL: Seccomp (securityContext, not annotation!)
```rego
# Pod-level
input.request.object.spec.securityContext.seccompProfile.type

# Container-level
containers[_].securityContext.seccompProfile.type
```

NEVER confuse AppArmor (annotations) with Seccomp (securityContext)!""",
        "metadata": {
            "type": "field-reference",
            "domain": "kubernetes-opa",
            "skill_level": "C-rank",
            "importance": "critical"
        }
    })

    # 5. Common mistakes
    all_entries.append({
        "instruction": "What are common mistakes when writing Kubernetes OPA policies?",
        "input": "OPA Rego troubleshooting",
        "output": """# Common OPA Rego Mistakes

## 1. Wrong Field Level
❌ WRONG: `containers[_].securityContext.hostPID`
✅ RIGHT: `input.request.object.spec.hostPID`

hostPID, hostIPC, hostNetwork are POD-level, not container-level.

## 2. AppArmor vs Seccomp Confusion
❌ WRONG: `securityContext.appArmorProfile`
✅ RIGHT: `metadata.annotations["container.apparmor.security.beta.kubernetes.io/name"]`

AppArmor is annotations. Seccomp is securityContext.

## 3. Terraform Input Structure
❌ WRONG: `input.request.kind.kind == "Bucket"` (Kubernetes syntax)
✅ RIGHT: `bucket := input.resource.aws_s3_bucket[name]` (Terraform syntax)

## 4. Namespace Check Inversion
❌ WRONG: `not input.request.namespace == "default"` (double negative)
✅ RIGHT: `input.request.object.metadata.namespace == "default"` (check positive)

## 5. Missing Field Existence Check
❌ WRONG: `container.securityContext.runAsUser > 10000`
✅ RIGHT: First check field exists, then compare value

## 6. Image Tag Checks
❌ WRONG: Checking only `:latest`
✅ RIGHT: Also check for NO tag (defaults to :latest) and missing `@sha256:` digest""",
        "metadata": {
            "type": "troubleshooting",
            "domain": "opa-rego",
            "skill_level": "C-rank"
        }
    })

    # Write output
    print(f"\nWriting {len(all_entries)} entries to: {output_file}")
    with open(output_file, 'w') as f:
        for entry in all_entries:
            f.write(json.dumps(entry) + '\n')

    print(f"\nDone! Created {len(all_entries)} structured RAG entries")

    # Summary
    by_type = {}
    for e in all_entries:
        t = e.get("metadata", {}).get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    print("\nBy type:")
    for t, count in sorted(by_type.items()):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
