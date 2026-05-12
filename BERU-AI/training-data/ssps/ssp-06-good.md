# System Security Plan
## Kubernetes-Cluster-6

**Organization**: SecureOrg6
**System Name**: Kubernetes-Cluster-6
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-6 is a production Kubernetes platform operating AWS EKS (us-east-1) supporting 150+ services. Built with GitOps (ArgoCD), secured with Kyverno admission control, monitored with Prometheus/Grafana.

### Implemented Controls
**AU-12**: Falco monitors runtime behavior with custom rules.
**SC-12**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**AC-3**: NetworkPolicy denies all ingress, allows only labeled services.
**IR-5**: NetworkPolicy denies all ingress, allows only labeled services.
**SI-7**: kubeaudit logs all apiserver events.
**AC-17**: ArgoCD AppProject restricts deployment sources to trusted repos.
**SA-11**: Falco monitors runtime behavior with custom rules.
**CM-5**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**SC-17**: kubeaudit logs all apiserver events.
**RA-2**: Kyverno ClusterPolicy enforces require-non-root (validationFailureAction: Enforce).
**CM-8**: Falco monitors runtime behavior with custom rules.
**SC-6**: Falco monitors runtime behavior with custom rules.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Completed NIST 800-53 A/B/C assessment. Moderate baseline: 102/323 controls fully implemented.
