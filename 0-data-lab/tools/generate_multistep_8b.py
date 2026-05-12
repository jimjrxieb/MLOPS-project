import json
import random
from pathlib import Path

OUTPUT_DIR = Path("1-GP-GLUE/01-raw-data-lake/8b-jade")
OUTPUT_FILE = OUTPUT_DIR / "multistep_8b_800.jsonl"

def generate_complex_scenarios(count):
    scenarios = []
    
    types = [
        ("CrashLoopBackOff (Log Analysis)", 200),
        ("Multi-resource Networking", 200),
        ("Label/Selector Dependency", 150),
        ("Rollout Failure", 100),
        ("Cross-namespace Communication", 100),
        ("Init Container Ordering", 50)
    ]
    
    for type_name, type_count in types:
        for _ in range(type_count):
            app = f"app-{random.randint(100, 999)}"
            ns = random.choice(["prod", "staging", "secure"])
            
            if "Log Analysis" in type_name:
                finding = f"FINDING: Pod '{app}-0' in namespace '{ns}' is in CrashLoopBackOff."
                investigation = f"INVESTIGATION:\n$ kubectl logs {app}-0 -n {ns}\nError: connection refused to 'db-service.{ns}.svc.cluster.local:5432'\n$ kubectl get netpol -n {ns}\nNo resources found."
                diagnosis = f"DIAGNOSIS: The application is crashing because it cannot reach the database. Investigation reveals that while no NetworkPolicies exist to block traffic, the 'db-service' endpoints are empty, suggesting the database pod itself is not healthy or incorrectly labeled."
                remediation = f"REMEDIATION:\nCheck the database pod status and fix its labels to match the service selector.\n```yaml\napiVersion: v1\nkind: Pod\nmetadata:\n  name: {app}-db\n  labels:\n    app: {app}-db\nspec:\n  containers:\n  - name: db\n    image: postgres:15\n```"
                rationale = "Resolving the database connectivity issue is the first step. Once the database is reachable, the application container will be able to complete its initialization."

            elif "Networking" in type_name:
                finding = f"FINDING: External traffic is not reaching the '{app}' service in namespace '{ns}'."
                investigation = f"INVESTIGATION:\n$ kubectl get ingress {app}-ingress -n {ns}\nADDRESS: 1.2.3.4\n$ kubectl describe ingress {app}-ingress -n {ns}\nRules:\n  Host: {app}.corp.com\n  Path: / (backend: {app}-svc:80)\n$ kubectl get svc {app}-svc -n {ns}\nPORT: 80/TCP (targetPort: 8080)"
                diagnosis = f"DIAGNOSIS: The networking chain Ingress -> Service -> Pod is broken at the targetPort mapping. The Ingress correctly routes to the Service, but the Service is forwarding to port 8080, while the application is actually listening on port 9090."
                remediation = f"REMEDIATION:\nUpdate the Service targetPort to match the application's listening port.\n```yaml\napiVersion: v1\nkind: Service\nmetadata:\n  name: {app}-svc\n  namespace: {ns}\nspec:\n  ports:\n  - port: 80\n    targetPort: 9090\n```"
                rationale = "The mismatch between the Service's targetPort and the Container's containerPort prevented traffic from reaching the application process."

            elif "Dependency" in type_name:
                finding = f"FINDING: Deployment '{app}' has 0/3 available replicas. Pods are stuck in 'Pending'."
                investigation = f"INVESTIGATION:\n$ kubectl describe pod {app}-xxx -n {ns}\nEvents:\n  Warning  FailedScheduling  default-scheduler  0/10 nodes are available: 10 node(s) didn't match Pod's node affinity/selector.\n$ kubectl get nodes --show-labels\nLabels: role=compute, zone=us-east-1a"
                diagnosis = f"DIAGNOSIS: The Pods cannot be scheduled because the Deployment's nodeSelector requirement 'zone=us-west-1b' does not match any available nodes in the cluster."
                remediation = f"REMEDIATION:\nUpdate the Deployment to use an available zone or remove the restrictive nodeSelector.\n```yaml\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {app}\nspec:\n  template:\n    spec:\n      nodeSelector:\n        zone: us-east-1a\n```"
                rationale = "Aligning the nodeSelector with actual node labels allows the scheduler to find suitable nodes for the Pods."

            elif "Rollout" in type_name:
                finding = f"FINDING: Deployment '{app}' rollout is stuck. 'kubectl rollout status' shows 1 old replica remaining."
                investigation = f"INVESTIGATION:\n$ kubectl get pods -n {ns}\n{app}-new-xxx 0/1 Running\n$ kubectl describe pod {app}-new-xxx -n {ns}\nWarning Unhealthy: Readiness probe failed: HTTP probe failed with statuscode: 500"
                diagnosis = f"DIAGNOSIS: The new version of the application is failing its readiness probe, preventing the Deployment controller from progressing with the rollout and terminating the old replicas."
                remediation = f"REMEDIATION:\nRoll back the deployment or fix the application error causing the 500 status.\n```bash\nkubectl rollout undo deployment/{app} -n {ns}\n```"
                rationale = "Rolling back ensures service availability while the underlying application issue is investigated in a development environment."

            elif "Cross-namespace" in type_name:
                finding = f"FINDING: Pod '{app}' in namespace 'frontend' cannot communicate with 'auth-api' in namespace 'security'."
                investigation = f"INVESTIGATION:\n$ kubectl exec {app} -n frontend -- curl security.auth-api:8080\ncurl: (7) Failed to connect\n$ kubectl get netpol -n security\nNAME: deny-all-ingress"
                diagnosis = f"DIAGNOSIS: A default-deny NetworkPolicy in the 'security' namespace is blocking all ingress traffic, including the necessary communication from the 'frontend' namespace."
                remediation = f"REMEDIATION:\nAdd a NetworkPolicy in the 'security' namespace to allow ingress from the 'frontend' namespace.\n```yaml\napiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: allow-frontend-ingress\n  namespace: security\nspec:\n  podSelector:\n    matchLabels:\n      app: auth-api\n  ingress:\n  - from:\n    - namespaceSelector:\n        matchLabels:\n          name: frontend\n```"
                rationale = "Explicitly allowing ingress from trusted namespaces while maintaining a default-deny posture follows zero-trust security principles."

            else: # Init Container
                finding = f"FINDING: Pod '{app}' is stuck in 'Init:0/1'."
                investigation = f"INVESTIGATION:\n$ kubectl logs {app} -c init-db -n {ns}\nError: timed out waiting for database to be ready."
                diagnosis = f"DIAGNOSIS: The init container 'init-db' is failing because the database it depends on is not accessible or has not started, preventing the main application container from beginning its startup process."
                remediation = f"REMEDIATION:\nEnsure the database service is healthy or update the init container logic to retry with a longer timeout.\n```yaml\napiVersion: v1\nkind: Pod\nmetadata:\n  name: {app}\nspec:\n  initContainers:\n  - name: init-db\n    image: busybox:1.28\n    command: ['sh', '-c', 'until nc -vz db-service 5432; do echo waiting for db; sleep 2; done;']\n```"
                rationale = "The init container ensures that necessary dependencies are met before the application starts, but it requires a robust check mechanism to handle temporary unavailabilities."

            example = {
                "messages": [
                    {"role": "system", "content": "You are JADE, a senior security analysis engine. Perform deep diagnostic reasoning, analyze investigative output, and provide multi-step remediation."},
                    {"role": "user", "content": finding + "\n\nProvide full diagnostic analysis and remediation."},
                    {"role": "assistant", "content": f"{diagnosis}\n\n{investigation}\n\n{remediation}\n\nRATIONALE: {rationale}\n\nVERIFICATION: kubectl get pod {app} -n {ns}"}
                ]
            }
            scenarios.append(example)
            
    return scenarios

def main():
    examples = generate_complex_scenarios(800)
    random.shuffle(examples)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated 800 complex multi-step diagnostic examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
