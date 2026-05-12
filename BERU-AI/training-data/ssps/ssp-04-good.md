# System Security Plan
## Kubernetes-Cluster-4

**Organization**: SecureOrg4
**System Name**: Kubernetes-Cluster-4
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-4 is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana.

### Implemented Controls
**SC-8**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**AC-6**: NetworkPolicy denies all ingress, allows only labeled services.
**AU-6**: RBAC limits service accounts to pod-scoped permissions.
**IR-5**: NetworkPolicy denies all ingress, allows only labeled services.
**IA-2**: Falco monitors runtime behavior with custom rules.
**SC-7**: kubeaudit logs all apiserver events.
**CA-8**: Falco monitors runtime behavior with custom rules.
**SA-12**: etcd encrypted with AES-256-GCM.
**AU-12**: ArgoCD AppProject restricts deployment sources to trusted repos.
**AC-17**: kubeaudit logs all apiserver events.
**AC-2**: ArgoCD AppProject restricts deployment sources to trusted repos.
**SC-23**: kubeaudit logs all apiserver events.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.
