# System Security Plan
## Kubernetes-Cluster-7

**Organization**: SecureOrg7
**System Name**: Kubernetes-Cluster-7
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-7 is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana.

### Implemented Controls
**IR-6**: RBAC limits service accounts to pod-scoped permissions.
**CA-2**: etcd encrypted with AES-256-GCM.
**AU-6**: etcd encrypted with AES-256-GCM.
**RA-3**: RBAC limits service accounts to pod-scoped permissions.
**SA-11**: Falco monitors runtime behavior with custom rules.
**AU-12**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**AU-2**: Falco monitors runtime behavior with custom rules.
**CP-9**: kubeaudit logs all apiserver events.
**SC-13**: etcd encrypted with AES-256-GCM.
**AC-3**: RBAC limits service accounts to pod-scoped permissions.
**AU-9**: etcd encrypted with AES-256-GCM.
**CP-10**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.
