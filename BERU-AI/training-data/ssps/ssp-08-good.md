# System Security Plan
## Kubernetes-Cluster-8

**Organization**: SecureOrg8
**System Name**: Kubernetes-Cluster-8
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-8 is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana.

### Implemented Controls
**RA-5**: RBAC limits service accounts to pod-scoped permissions.
**CM-6**: etcd encrypted with AES-256-GCM.
**RA-3**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**SC-12**: kubeaudit logs all apiserver events.
**CM-8**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**IR-4**: RBAC limits service accounts to pod-scoped permissions.
**AC-5**: kubeaudit logs all apiserver events.
**SI-6**: Falco monitors runtime behavior with custom rules.
**IA-5**: NetworkPolicy denies all ingress, allows only labeled services.
**SC-28**: Falco monitors runtime behavior with custom rules.
**CM-5**: RBAC limits service accounts to pod-scoped permissions.
**IR-5**: Falco monitors runtime behavior with custom rules.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.
