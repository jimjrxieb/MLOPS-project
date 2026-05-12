# System Security Plan
## Kubernetes-Cluster-2

**Organization**: SecureOrg2
**System Name**: Kubernetes-Cluster-2
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-2 is deployed on AWS EKS with network policies and RBAC controls.

### Implemented Controls
**AC-17**: Kyverno policies enforce.
**RA-5**: NetworkPolicy restricts.
**CM-2**: NetworkPolicy restricts.
**SI-4**: Kyverno policies enforce.
**IA-5**: RBAC limits access to.
**SI-2**: Kyverno policies enforce.
**SA-10**: NetworkPolicy restricts.
**CM-8**: Kyverno policies enforce.
**SC-17**: RBAC limits access to.
**CA-8**: Kyverno policies enforce.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Conducted gap analysis against CIS Kubernetes Benchmark v1.6.1 (82 pass, 18 fail).
