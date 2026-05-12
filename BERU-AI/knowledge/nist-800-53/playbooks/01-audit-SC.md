# BERU — SC Family Audit Playbook

> System and Communications Protection: SC-7, SC-8, SC-12, SC-13, SC-28
> Tools: kubectl, Istio, NetworkPolicy, cert-manager, KMS, Trivy
> Audience: BERU (NIST-800-53 internal auditor)
> Read first: `../controls/SC-7.md`, `../controls/SC-8.md`, `../controls/SC-12.md`, `../controls/SC-13.md`, `../controls/SC-28.md`

---

## Inputs That Route Here

- Trivy network policy scan
- cert-manager certificate status
- kubectl NetworkPolicy dump
- AWS KMS / CloudTrail crypto events
- Gitleaks / secret scan finding (routes to SC-12)
- Manual request: "Is our data protected in transit and at rest?"

---

## Step 1 — Collect Data Protection Evidence

```bash
EVIDENCE="GP-S3/6-seclab-reports/cybersec-evidence/beru-findings/$(date +%Y-%m-%d)-SC"
mkdir -p $EVIDENCE

# 1a. NetworkPolicy inventory — all namespaces
kubectl get networkpolicies -A -o yaml 2>&1 | tee $EVIDENCE/networkpolicies-$(date +%Y%m%d).yaml

# 1b. Namespaces with NO default-deny NetworkPolicy (gap check)
kubectl get namespaces -o json | \
  jq -r '.items[].metadata.name' | while read ns; do
    count=$(kubectl get networkpolicies -n $ns 2>/dev/null | grep -c "default-deny\|deny-all" || echo 0)
    echo "Namespace: $ns → default-deny policies: $count"
  done 2>&1 | tee $EVIDENCE/namespace-netpol-coverage-$(date +%Y%m%d).txt

# 1c. Services with unexpected exposure (LoadBalancer / NodePort)
kubectl get services -A -o json | \
  jq '.items[] | select(.spec.type == "LoadBalancer" or .spec.type == "NodePort") |
      {namespace: .metadata.namespace, name: .metadata.name, type: .spec.type, ports: .spec.ports}' \
  2>&1 | tee $EVIDENCE/exposed-services-$(date +%Y%m%d).json

# 1d. cert-manager — certificate inventory
kubectl get certificates -A 2>&1 | tee $EVIDENCE/certificates-$(date +%Y%m%d).txt
kubectl get certificates -A -o json | \
  jq '.items[] | {namespace: .metadata.namespace, name: .metadata.name,
      ready: .status.conditions[]?.status, expiry: .status.notAfter}' \
  2>&1 | tee $EVIDENCE/cert-status-$(date +%Y%m%d).json

# 1e. Istio mTLS mode — if Istio is deployed
kubectl get peerauthentication -A -o yaml 2>&1 | tee $EVIDENCE/istio-mtls-$(date +%Y%m%d).yaml

# 1f. TLS configuration on Ingress objects
kubectl get ingress -A -o json | \
  jq '.items[] | {namespace: .metadata.namespace, name: .metadata.name,
      tls: .spec.tls, annotations: .metadata.annotations}' \
  2>&1 | tee $EVIDENCE/ingress-tls-$(date +%Y%m%d).json

# 1g. Secrets in git (Gitleaks)
gitleaks detect --source . --report-path $EVIDENCE/gitleaks-$(date +%Y%m%d).json 2>&1

# 1h. ExternalSecrets — is the operator deployed?
kubectl get externalsecret -A 2>&1 | tee $EVIDENCE/externalsecrets-$(date +%Y%m%d).txt
kubectl get secretstore -A 2>&1 | tee $EVIDENCE/secretstores-$(date +%Y%m%d).txt
```

For AWS:
```bash
# 1i. KMS key inventory
aws kms list-keys --output json 2>&1 | tee $EVIDENCE/kms-keys-$(date +%Y%m%d).json
aws kms describe-key --key-id <key-id> --output json 2>&1 | tee $EVIDENCE/kms-key-detail-$(date +%Y%m%d).json

# 1j. S3 encryption status
aws s3api get-bucket-encryption --bucket <bucket-name> \
  --output json 2>&1 | tee $EVIDENCE/s3-encryption-$(date +%Y%m%d).json

# 1k. EKS secrets encryption (envelope encryption)
aws eks describe-cluster --name <cluster-name> --query 'cluster.encryptionConfig' \
  --output json 2>&1 | tee $EVIDENCE/eks-encryption-$(date +%Y%m%d).json

# 1l. RDS encryption
aws rds describe-db-instances --query 'DBInstances[*].{DB:DBInstanceIdentifier,Encrypted:StorageEncrypted}' \
  --output json 2>&1 | tee $EVIDENCE/rds-encryption-$(date +%Y%m%d).json
```

---

## Step 2 — Assess SC-7: Boundary Protection

Read: `../controls/SC-7.md`

Questions to answer:
1. Is there a default-deny NetworkPolicy in every production namespace?
2. Are inter-namespace communications explicitly allowed, not open by default?
3. Are external-facing services intentionally exposed, not accidentally?

Assessment commands:
```bash
# Which production namespaces have no NetworkPolicy at all?
kubectl get namespaces -o json | jq -r '.items[].metadata.name' | \
  grep -v "kube-\|cert-manager\|falco\|argocd\|splunk\|monitoring" | \
  while read ns; do
    count=$(kubectl get networkpolicies -n $ns 2>/dev/null | wc -l)
    echo "$ns: $count policies"
  done 2>&1 | tee $EVIDENCE/namespace-netpol-count-$(date +%Y%m%d).txt

# Check for the Istio PeerAuthentication STRICT mode (mTLS enforcement)
kubectl get peerauthentication -A -o json | \
  jq '.items[] | {namespace: .metadata.namespace, mode: .spec.mtls.mode}' \
  2>&1 | tee $EVIDENCE/peerauthentication-$(date +%Y%m%d).json
```

**PASS criteria:** Default-deny NetworkPolicy in all production namespaces (verified via namespace-netpol-coverage output). Istio PeerAuthentication STRICT mode enabled. All LoadBalancer services have an architectural justification documented.

**PARTIAL criteria:** Most namespaces have default-deny. 1-2 non-prod namespaces without policies. Istio in PERMISSIVE mode (not STRICT).

**FAIL criteria:** Production namespaces with no NetworkPolicy. Pods can communicate freely across namespaces. No boundary documentation.

---

## Step 3 — Assess SC-8: Transmission Confidentiality and Integrity

Read: `../controls/SC-8.md`

Questions to answer:
1. Is all traffic between services encrypted (mTLS via Istio, or TLS via cert-manager)?
2. Do Ingress resources enforce HTTPS, not HTTP?
3. Is the cert-manager issuer configured correctly (Let's Encrypt or internal CA)?

Assessment commands:
```bash
# Check Ingress for missing TLS or HTTP redirect
kubectl get ingress -A -o json | \
  jq '.items[] | select(.spec.tls == null or .spec.tls == []) |
      {namespace: .metadata.namespace, name: .metadata.name}' \
  2>&1 | tee $EVIDENCE/ingress-no-tls-$(date +%Y%m%d).json

# Check for insecure annotations (no ssl-redirect)
kubectl get ingress -A -o json | \
  jq '.items[] | select(
    .metadata.annotations["nginx.ingress.kubernetes.io/ssl-redirect"] == "false" or
    .metadata.annotations["nginx.ingress.kubernetes.io/force-ssl-redirect"] == null
  ) | {namespace: .metadata.namespace, name: .metadata.name}' \
  2>&1 | tee $EVIDENCE/ingress-no-ssl-redirect-$(date +%Y%m%d).json

# cert-manager issuer — is it production (not staging)?
kubectl get clusterissuer -o yaml 2>&1 | tee $EVIDENCE/clusterissuer-$(date +%Y%m%d).yaml
```

**PASS criteria:** All Ingress resources have TLS configured. ssl-redirect annotation enforced. Istio mTLS STRICT mode in production. All certs issued by production issuer (not staging/self-signed in prod).

**PARTIAL criteria:** Most services have TLS. 1-2 internal services HTTP-only with justification. Istio in PERMISSIVE mode.

**FAIL criteria:** Production endpoints serving HTTP without redirect. No cert-manager. No Istio mTLS. Self-signed certs in production without documented exception.

---

## Step 4 — Assess SC-12: Cryptographic Key Establishment and Management

Read: `../controls/SC-12.md`

Questions to answer:
1. Are application secrets stored in a secrets manager (AWS Secrets Manager, Vault, ExternalSecrets), not in K8s Secrets or ConfigMaps?
2. Are KMS keys rotated on schedule?
3. Are any secrets detected in git history?

Assessment commands:
```bash
# Check for secrets in ConfigMaps (common misconfiguration)
kubectl get configmaps -A -o json | \
  jq '.items[] | select(.data != null) |
      {namespace: .metadata.namespace, name: .metadata.name} |
      select(.name | test("secret|password|key|token|credential"; "i"))' \
  2>&1 | tee $EVIDENCE/configmaps-with-secrets-names-$(date +%Y%m%d).json

# Check actual ConfigMap values for secret patterns
kubectl get configmaps -A -o json | python3 -c "
import sys, json, re
data = json.load(sys.stdin)
secret_pattern = re.compile(r'(password|secret|key|token|credential|api_key)', re.IGNORECASE)
for item in data['items']:
    for k, v in (item.get('data') or {}).items():
        if secret_pattern.search(str(v)):
            print(f\"WARN: {item['metadata']['namespace']}/{item['metadata']['name']} key '{k}' may contain a secret\")
" 2>&1 | tee $EVIDENCE/configmap-secret-values-$(date +%Y%m%d).txt

# ExternalSecrets — are all secrets pulled from a backend?
cat $EVIDENCE/externalsecrets-$(date +%Y%m%d).txt

# Gitleaks results
cat $EVIDENCE/gitleaks-$(date +%Y%m%d).json | python3 -c "
import sys, json
findings = json.load(sys.stdin)
print(f'Total git secret findings: {len(findings)}')
for f in findings[:5]:
    print(f\"  {f.get('RuleID')}: {f.get('File')}:{f.get('StartLine')} — {f.get('Secret', '')[:20]}...\")
" 2>&1

# KMS rotation status
aws kms list-keys --output json | jq -r '.Keys[].KeyId' | \
  while read key; do
    rotation=$(aws kms get-key-rotation-status --key-id $key --query 'KeyRotationEnabled' --output text)
    echo "Key $key: rotation=$rotation"
  done 2>&1 | tee $EVIDENCE/kms-rotation-$(date +%Y%m%d).txt
```

**PASS criteria:** No secrets in ConfigMaps or git history. ExternalSecrets operator deployed and all K8s Secrets sourced from it. KMS rotation enabled. No Gitleaks findings.

**PARTIAL criteria:** Some secrets in K8s Secrets (not ConfigMaps). ExternalSecrets not yet fully migrated. No Gitleaks findings in current code (only old history).

**FAIL criteria:** Secrets in ConfigMaps or env vars. Gitleaks findings in active branches. No secrets manager. KMS rotation disabled.

---

## Step 5 — Assess SC-13: Cryptographic Protection

Read: `../controls/SC-13.md`

Questions to answer:
1. Are FIPS-approved cryptographic algorithms in use for TLS?
2. Is etcd encryption enabled?
3. Are EBS/RDS volumes using AES-256?

Assessment commands:
```bash
# Check etcd encryption at rest
kubectl get pod -n kube-system -l component=kube-apiserver -o yaml | \
  grep "encryption-provider-config" 2>&1 | tee $EVIDENCE/etcd-encryption-config-$(date +%Y%m%d).txt

# kube-bench 1.2.29 — encryption provider config
kube-bench run --check 1.2.29 2>&1 | tee $EVIDENCE/kubebench-1.2.29-$(date +%Y%m%d).txt

# TLS version check on API server
kube-bench run --check 1.2.31,1.2.32 2>&1 | tee $EVIDENCE/kubebench-tls-$(date +%Y%m%d).txt
```

**PASS criteria:** kube-bench 1.2.29 PASS (etcd encryption config). TLS 1.2+ enforced. AES-256 for storage. FIPS-compliant cipher suites if FedRAMP in scope.

**PARTIAL criteria:** etcd encryption config present but not verified working. TLS 1.2 allowed alongside TLS 1.0/1.1.

**FAIL criteria:** kube-bench 1.2.29 FAIL. No etcd encryption. TLS 1.0 or 1.1 in use.

---

## Step 6 — Assess SC-28: Protection of Information at Rest

Read: `../controls/SC-28.md`

Questions to answer:
1. Are PersistentVolumes encrypted (EBS encryption, StorageClass with encryption)?
2. Are S3 buckets encrypted (SSE-S3 or SSE-KMS)?
3. Are RDS databases using storage encryption?

Assessment commands:
```bash
# PersistentVolume encryption — check StorageClass
kubectl get storageclass -o yaml | grep -i "encrypt\|kms" 2>&1 | \
  tee $EVIDENCE/storageclass-encryption-$(date +%Y%m%d).txt

# Check existing PVs for encryption annotation
kubectl get pv -o json | \
  jq '.items[] | {name: .metadata.name, encrypted: (.metadata.annotations // {} | to_entries[] | select(.key | contains("encrypt")))}' \
  2>&1 | tee $EVIDENCE/pv-encryption-$(date +%Y%m%d).json

# S3 encryption (from Step 1)
cat $EVIDENCE/s3-encryption-$(date +%Y%m%d).json

# RDS encryption (from Step 1)
cat $EVIDENCE/rds-encryption-$(date +%Y%m%d).json
```

**PASS criteria:** EBS StorageClass has `encrypted: "true"` and `kmsKeyId` configured. All S3 buckets use SSE-KMS (not SSE-S3). All RDS instances have `StorageEncrypted: true`.

**PARTIAL criteria:** Most storage encrypted. Some legacy PVs not encrypted (under migration).

**FAIL criteria:** Default StorageClass without encryption. S3 buckets without encryption. RDS with `StorageEncrypted: false`.

---

## Step 7 — Fill BERU Findings

| Control | Control Owner | Fixer Route | Rank Range |
| --- | --- | --- | --- |
| SC-7 | PlatEng | NetworkPolicy generator + Istio PeerAuthentication | C |
| SC-8 | PlatEng + AppDev | cert-manager + Ingress TLS annotation | D–C |
| SC-12 | PlatEng + CloudSec | ExternalSecrets migration + KMS rotation | C–B |
| SC-13 | PlatEng | etcd encryption config (kube-apiserver PR) | C–B |
| SC-28 | CloudSec | StorageClass encryption + S3 SSE-KMS | C |

Reference: `../ssp-examples/SC-ssp-great.md` for SSP narrative quality standard.
