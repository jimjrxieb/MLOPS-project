# System Security Plan
## Kubernetes-Cluster-9

**Organization**: SecureOrg9
**System Name**: Kubernetes-Cluster-9
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-9 is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana.

### Implemented Controls
**SI-7**: Falco monitors runtime behavior with custom rules.
**RA-3**: Falco monitors runtime behavior with custom rules.
**AU-3**: ArgoCD AppProject restricts deployment sources to trusted repos.
**AC-2**: kubeaudit logs all apiserver events.
**AC-6**: RBAC limits service accounts to pod-scoped permissions.
**CM-7**: etcd encrypted with AES-256-GCM.
**RA-2**: NetworkPolicy denies all ingress, allows only labeled services.
**SC-6**: etcd encrypted with AES-256-GCM.
**AC-17**: etcd encrypted with AES-256-GCM.
**CA-8**: ArgoCD AppProject restricts deployment sources to trusted repos.
**CM-6**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**CM-5**: NetworkPolicy denies all ingress, allows only labeled services.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.
