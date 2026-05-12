"""
JADE Tools Module
Provides capabilities for JADE to act as GP-Copilot's Jarvis

Tools:
- jsa_deployer: Deploy JSA (Junior Secure Agent) clones to clusters
- log_reader: Read and analyze logs from various sources
- cluster_manager: Manage Kubernetes clusters and deployments
- infra_provisioner: Generate infrastructure suggestions (Terraform)
"""

from .jsa_deployer import JSADeployer, deploy_jsa, list_jsa_instances, get_jsa_status
from .log_reader import LogReader, read_logs, tail_logs, search_logs
from .cluster_manager import ClusterManager, list_clusters, get_cluster_info
from .infra_provisioner import InfraProvisioner, create_infra_tool, get_infra_tools_for_llm

__all__ = [
    # JSA Deployment
    'JSADeployer',
    'deploy_jsa',
    'list_jsa_instances',
    'get_jsa_status',

    # Log Reading
    'LogReader',
    'read_logs',
    'tail_logs',
    'search_logs',

    # Cluster Management
    'ClusterManager',
    'list_clusters',
    'get_cluster_info',

    # Infrastructure Provisioning
    'InfraProvisioner',
    'create_infra_tool',
    'get_infra_tools_for_llm',
]
