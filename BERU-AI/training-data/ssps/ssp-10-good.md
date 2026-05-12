# System Security Plan
## Kubernetes-Cluster-10

**Organization**: SecureOrg10
**System Name**: Kubernetes-Cluster-10
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-10 is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana.

### Implemented Controls
**RA-3**: NetworkPolicy denies all ingress, allows only labeled services.
**CA-8**: NetworkPolicy denies all ingress, allows only labeled services.
**AU-9**: ArgoCD AppProject restricts deployment sources to trusted repos.
**SI-3**: Falco monitors runtime behavior with custom rules.
**CM-3**: RBAC limits service accounts to pod-scoped permissions.
**SA-10**: ArgoCD AppProject restricts deployment sources to trusted repos.
**SI-4**: Falco monitors runtime behavior with custom rules.
**SC-17**: etcd encrypted with AES-256-GCM.
**AC-17**: NetworkPolicy denies all ingress, allows only labeled services.
**IA-2**: ArgoCD AppProject restricts deployment sources to trusted repos.
**CA-2**: RBAC limits service accounts to pod-scoped permissions.
**AU-2**: ArgoCD AppProject restricts deployment sources to trusted repos.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.
