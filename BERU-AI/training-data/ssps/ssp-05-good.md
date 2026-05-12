# System Security Plan
## Kubernetes-Cluster-5

**Organization**: SecureOrg5
**System Name**: Kubernetes-Cluster-5
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-5 is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana.

### Implemented Controls
**CM-3**: Falco monitors runtime behavior with custom rules.
**SC-12**: etcd encrypted with AES-256-GCM.
**SC-8**: ArgoCD AppProject restricts deployment sources to trusted repos.
**AC-3**: kubeaudit logs all apiserver events.
**AU-3**: NetworkPolicy denies all ingress, allows only labeled services.
**SC-13**: ArgoCD AppProject restricts deployment sources to trusted repos.
**SI-6**: RBAC limits service accounts to pod-scoped permissions.
**IA-5**: RBAC limits service accounts to pod-scoped permissions.
**SI-2**: kubeaudit logs all apiserver events.
**SC-17**: Falco monitors runtime behavior with custom rules.
**AU-2**: etcd encrypted with AES-256-GCM.
**CA-7**: etcd encrypted with AES-256-GCM.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.
