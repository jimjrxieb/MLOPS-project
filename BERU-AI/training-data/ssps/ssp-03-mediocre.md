# System Security Plan
## Kubernetes-Cluster-3

**Organization**: SecureOrg3
**System Name**: Kubernetes-Cluster-3
**Classification**: MODERATE
**Last Updated**: 2026-05-08

### System Description
The Kubernetes-Cluster-3 is deployed on AWS EKS with network policies and RBAC controls.

### Implemented Controls
**AU-12**: NetworkPolicy restricts.
**SC-12**: NetworkPolicy restricts.
**SC-6**: RBAC limits access to.
**AU-2**: Kyverno policies enforce.
**SA-11**: NetworkPolicy restricts.
**AC-6**: RBAC limits access to.
**CM-8**: NetworkPolicy restricts.
**IA-2**: RBAC limits access to.
**IR-6**: Kyverno policies enforce.
**AC-3**: RBAC limits access to.

### Key Assets
- Kubernetes API Server
- etcd cluster (3-node)
- Containerized microservices (Python/Go/Node.js)
- PostgreSQL database with encryption at rest
- Redis cache with TLS

### Risk Assessment
Conducted gap analysis against CIS Kubernetes Benchmark v1.6.1 (82 pass, 18 fail).
