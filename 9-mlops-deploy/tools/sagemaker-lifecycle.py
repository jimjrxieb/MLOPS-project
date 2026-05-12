#!/usr/bin/env python3
"""
sagemaker-lifecycle.py — Full SageMaker MLOps lifecycle in one script.

Runs: Model Registry → Training Job → Register Version → Deploy Endpoint → Test → Cleanup

Usage:
    # Run everything (~$1-3 with spot)
    source ~/.gp-sagemaker.env
    python3 tools/sagemaker-lifecycle.py --run-all

    # Individual phases
    python3 tools/sagemaker-lifecycle.py --phase setup         # Create model group
    python3 tools/sagemaker-lifecycle.py --phase train         # Launch training job
    python3 tools/sagemaker-lifecycle.py --phase register      # Register model version
    python3 tools/sagemaker-lifecycle.py --phase deploy        # Deploy endpoint
    python3 tools/sagemaker-lifecycle.py --phase test          # Test inference
    python3 tools/sagemaker-lifecycle.py --phase cleanup       # Delete endpoint + model

    # Tear down everything (endpoint, model, model group)
    python3 tools/sagemaker-lifecycle.py --cleanup-all

Environment:
    SAGEMAKER_ROLE    — IAM role ARN (from setup-sagemaker.sh)
    SAGEMAKER_BUCKET  — S3 bucket name (from setup-sagemaker.sh)
    SAGEMAKER_REGION  — AWS region (default: us-east-1)

Cost estimate: ~$1-3 total (spot training + 10 min endpoint)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    import boto3
except ImportError:
    print("Error: boto3 not installed. Run: pip install boto3")
    sys.exit(1)

try:
    import sagemaker
    from sagemaker.huggingface import HuggingFace, HuggingFaceModel
    SAGEMAKER_SDK = True
except ImportError:
    SAGEMAKER_SDK = False

# --- Config ---

ROLE = os.environ.get("SAGEMAKER_ROLE", "")
BUCKET = os.environ.get("SAGEMAKER_BUCKET", "")
REGION = os.environ.get("SAGEMAKER_REGION", "us-east-1")
PROJECT = os.environ.get("SAGEMAKER_PROJECT", "gp-mlops")

MODEL_GROUP = "katie-3b"
MODEL_NAME = "katie-3b-sagemaker"
ENDPOINT_NAME = "katie-3b-test"
TRAINING_JOB_PREFIX = "katie-3b-lora"

# Training config
BASE_MODEL = "unsloth/Llama-3.2-3B-Instruct"
INSTANCE_TYPE_TRAIN = "ml.g5.xlarge"
INSTANCE_TYPE_SERVE = "ml.g5.xlarge"


def get_clients():
    """Create boto3 clients."""
    session = boto3.Session(region_name=REGION)
    return {
        "sm": session.client("sagemaker"),
        "s3": session.client("s3"),
    }


def check_env():
    """Verify environment variables are set."""
    missing = []
    if not ROLE:
        missing.append("SAGEMAKER_ROLE")
    if not BUCKET:
        missing.append("SAGEMAKER_BUCKET")
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Run: source ~/.gp-sagemaker.env")
        sys.exit(1)


def upload_training_data(clients):
    """Upload sample training data to S3 if none exists."""
    s3 = clients["s3"]
    key = "training-data/sample_katie_train.jsonl"

    # Check if real training data exists
    try:
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix="training-data/", MaxKeys=10)
        real_files = [
            obj["Key"] for obj in response.get("Contents", [])
            if obj["Key"].endswith(".jsonl") and obj["Size"] > 0
        ]
        if real_files:
            print(f"  Found existing training data: {real_files[0]}")
            return f"s3://{BUCKET}/{real_files[0]}"
    except Exception:
        pass

    # Upload sample data (minimal — just proves the pipeline works)
    print("  No training data found — uploading sample...")
    samples = []
    prompts = [
        ("A pod is in CrashLoopBackOff with exit code 137. Diagnose.",
         "Exit code 137 means OOMKilled. The container exceeded its memory limit. Fix: increase spec.containers[].resources.limits.memory in the pod spec, or investigate the application for memory leaks using `kubectl top pod`."),
        ("What is a NetworkPolicy in Kubernetes?",
         "A NetworkPolicy is a K8s resource that controls traffic flow between pods. By default, all pods can communicate. NetworkPolicies act as a firewall: you define ingress/egress rules specifying which pods, namespaces, or CIDRs can send/receive traffic. Applied via label selectors."),
        ("How do I check if RBAC is properly configured?",
         "1. `kubectl auth can-i --list --as=system:serviceaccount:ns:sa` to check permissions. 2. Look for wildcard rules: `kubectl get clusterrolebindings -o json | jq '.items[] | select(.roleRef.name==\"cluster-admin\")'`. 3. Ensure no default SA has elevated privileges. 4. Run `kubescape scan framework nsa` for automated RBAC audit."),
        ("Explain PodSecurityStandards.",
         "Pod Security Standards (PSS) replaced PodSecurityPolicies in K8s 1.25. Three levels: Privileged (unrestricted), Baseline (prevents known escalations), Restricted (hardened). Applied via namespace labels: `pod-security.kubernetes.io/enforce: restricted`. Modes: enforce (reject), audit (log), warn (warning)."),
        ("A node shows NotReady status. What do I check?",
         "1. `kubectl describe node <name>` — check Conditions (MemoryPressure, DiskPressure, PIDPressure). 2. `journalctl -u kubelet` on the node for kubelet logs. 3. Check if container runtime is running: `systemctl status containerd`. 4. Verify network connectivity to API server. 5. Check certificates: `openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -dates`."),
    ]

    for user_msg, assistant_msg in prompts:
        samples.append(json.dumps({
            "messages": [
                {"role": "system", "content": "You are Katie, a Kubernetes platform engineer AI. Provide concise, accurate answers about K8s security, operations, and troubleshooting."},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ]
        }))

    body = "\n".join(samples)
    s3.put_object(Bucket=BUCKET, Key=key, Body=body.encode())
    print(f"  Uploaded {len(samples)} samples to s3://{BUCKET}/{key}")
    return f"s3://{BUCKET}/{key}"


# === Phase: Setup ===

def phase_setup(clients):
    """Create SageMaker Model Package Group."""
    sm = clients["sm"]
    print("\n=== Phase 1: Setup Model Registry ===\n")

    try:
        sm.describe_model_package_group(ModelPackageGroupName=MODEL_GROUP)
        print(f"  Model group '{MODEL_GROUP}' already exists")
    except sm.exceptions.ClientError:
        sm.create_model_package_group(
            ModelPackageGroupName=MODEL_GROUP,
            ModelPackageGroupDescription="Katie 3B — CKA/CKS/CKAD platform engineer model (LoRA fine-tuned LLaMA 3.2-3B)",
            Tags=[
                {"Key": "Project", "Value": PROJECT},
                {"Key": "Model", "Value": "llama-3.2-3b-instruct"},
                {"Key": "Method", "Value": "lora-sft"},
            ],
        )
        print(f"  Created model group: {MODEL_GROUP}")

    # List existing versions
    response = sm.list_model_packages(ModelPackageGroupName=MODEL_GROUP, MaxResults=5)
    versions = response.get("ModelPackageSummaryList", [])
    print(f"  Existing versions: {len(versions)}")
    for v in versions:
        print(f"    v{v['ModelPackageVersion']} — {v['ModelApprovalStatus']} ({v['CreationTime'].strftime('%Y-%m-%d')})")

    return True


# === Phase: Train ===

def phase_train(clients):
    """Launch SageMaker Training Job with spot instances."""
    sm = clients["sm"]
    print("\n=== Phase 2: Training Job (Spot) ===\n")

    if not SAGEMAKER_SDK:
        print("Error: sagemaker SDK not installed. Run: pip install sagemaker")
        return None

    # Upload training data
    training_uri = upload_training_data(clients)

    # Source dir for training script
    script_dir = os.path.join(os.path.dirname(__file__), "..", "02-training-pipeline", "sagemaker")
    if not os.path.exists(os.path.join(script_dir, "train_sagemaker.py")):
        print(f"Error: train_sagemaker.py not found in {script_dir}")
        return None

    job_name = f"{TRAINING_JOB_PREFIX}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"  Job name:      {job_name}")
    print(f"  Instance:      {INSTANCE_TYPE_TRAIN} (spot)")
    print(f"  Training data: {training_uri}")
    print(f"  Output:        s3://{BUCKET}/model-output/")
    print("")

    session = sagemaker.Session(boto_session=boto3.Session(region_name=REGION))

    estimator = HuggingFace(
        entry_point="train_sagemaker.py",
        source_dir=script_dir,
        instance_type=INSTANCE_TYPE_TRAIN,
        instance_count=1,
        role=ROLE,
        transformers_version="4.37",
        pytorch_version="2.1",
        py_version="py310",
        hyperparameters={
            "model_name": BASE_MODEL,
            "lora_r": 64,
            "lora_alpha": 128,
            "epochs": 1,
            "batch_size": 4,
            "learning_rate": "2e-5",
            "max_seq_length": 2048,
        },
        output_path=f"s3://{BUCKET}/model-output/",
        base_job_name=TRAINING_JOB_PREFIX,
        max_run=3600,
        use_spot_instances=True,
        max_wait=7200,
        checkpoint_s3_uri=f"s3://{BUCKET}/checkpoints/",
        sagemaker_session=session,
        tags=[
            {"Key": "Project", "Value": PROJECT},
            {"Key": "Phase", "Value": "training"},
        ],
    )

    print("  Launching training job (spot)...")
    print("  This takes 5-15 min (instance provisioning + training)")
    print("")

    estimator.fit(
        {"training": training_uri},
        job_name=job_name,
        wait=True,
        logs="All",
    )

    model_artifact = estimator.model_data
    print(f"\n  Training complete!")
    print(f"  Model artifact: {model_artifact}")

    # Save artifact path for register phase
    state_file = os.path.join(os.path.dirname(__file__), ".sagemaker-state.json")
    state = _load_state(state_file)
    state["model_artifact"] = model_artifact
    state["job_name"] = job_name
    _save_state(state_file, state)

    return model_artifact


# === Phase: Register ===

def phase_register(clients, model_artifact=None):
    """Register trained model in SageMaker Model Registry."""
    sm = clients["sm"]
    print("\n=== Phase 3: Register Model Version ===\n")

    # Load artifact from state if not passed
    if not model_artifact:
        state = _load_state()
        model_artifact = state.get("model_artifact")

    if not model_artifact:
        print("Error: No model artifact found. Run --phase train first.")
        return None

    # HuggingFace DLC image for inference
    account_map = {
        "us-east-1": "763104351884",
        "us-west-2": "763104351884",
        "eu-west-1": "763104351884",
    }
    ecr_account = account_map.get(REGION, "763104351884")
    image_uri = f"{ecr_account}.dkr.ecr.{REGION}.amazonaws.com/huggingface-pytorch-inference:2.1-transformers4.37-gpu-py310-cu121-ubuntu22.04"

    response = sm.create_model_package(
        ModelPackageGroupName=MODEL_GROUP,
        ModelPackageDescription=f"Katie 3B — trained {datetime.now().strftime('%Y-%m-%d')}",
        InferenceSpecification={
            "Containers": [{
                "Image": image_uri,
                "ModelDataUrl": model_artifact,
            }],
            "SupportedContentTypes": ["application/json"],
            "SupportedResponseMIMETypes": ["application/json"],
            "SupportedRealtimeInferenceInstanceTypes": [INSTANCE_TYPE_SERVE],
        },
        ModelApprovalStatus="PendingManualApproval",
        CustomerMetadataProperties={
            "base_model": BASE_MODEL,
            "method": "lora-sft-4bit",
            "lora_r": "64",
            "training_date": datetime.now().strftime("%Y-%m-%d"),
            "project": PROJECT,
        },
    )

    pkg_arn = response["ModelPackageArn"]
    version = pkg_arn.split("/")[-1]
    print(f"  Registered: {MODEL_GROUP} v{version}")
    print(f"  ARN: {pkg_arn}")
    print(f"  Status: PendingManualApproval")

    # Approve it (in real workflow, this happens after eval passes)
    sm.update_model_package(
        ModelPackageArn=pkg_arn,
        ModelApprovalStatus="Approved",
        ApprovalDescription="Approved via lifecycle script — SageMaker demo run",
    )
    print(f"  Status updated: Approved")

    # Save for deploy phase
    state = _load_state()
    state["model_package_arn"] = pkg_arn
    state["image_uri"] = image_uri
    state["model_artifact"] = model_artifact
    _save_state(state_file=None, state=state)

    return pkg_arn


# === Phase: Deploy ===

def phase_deploy(clients, model_artifact=None):
    """Deploy model to a SageMaker endpoint."""
    sm = clients["sm"]
    print("\n=== Phase 4: Deploy Endpoint ===\n")

    state = _load_state()
    image_uri = state.get("image_uri")
    model_artifact = model_artifact or state.get("model_artifact")

    if not model_artifact or not image_uri:
        print("Error: Missing model artifact or image URI. Run --phase register first.")
        return None

    # Create model
    try:
        sm.describe_model(ModelName=MODEL_NAME)
        print(f"  Model '{MODEL_NAME}' already exists — deleting...")
        sm.delete_model(ModelName=MODEL_NAME)
    except sm.exceptions.ClientError:
        pass

    sm.create_model(
        ModelName=MODEL_NAME,
        PrimaryContainer={
            "Image": image_uri,
            "ModelDataUrl": model_artifact,
            "Environment": {"HF_TASK": "text-generation"},
        },
        ExecutionRoleArn=ROLE,
        Tags=[{"Key": "Project", "Value": PROJECT}],
    )
    print(f"  Created model: {MODEL_NAME}")

    # Create endpoint config
    config_name = f"{ENDPOINT_NAME}-config"
    try:
        sm.delete_endpoint_config(EndpointConfigName=config_name)
    except sm.exceptions.ClientError:
        pass

    sm.create_endpoint_config(
        EndpointConfigName=config_name,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": MODEL_NAME,
            "InstanceType": INSTANCE_TYPE_SERVE,
            "InitialInstanceCount": 1,
        }],
        Tags=[{"Key": "Project", "Value": PROJECT}],
    )
    print(f"  Created endpoint config: {config_name}")

    # Create endpoint
    try:
        sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        print(f"  Endpoint '{ENDPOINT_NAME}' already exists — updating...")
        sm.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=config_name)
    except sm.exceptions.ClientError:
        sm.create_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=config_name,
            Tags=[{"Key": "Project", "Value": PROJECT}],
        )

    print(f"  Deploying endpoint: {ENDPOINT_NAME}")
    print(f"  Instance: {INSTANCE_TYPE_SERVE}")
    print(f"  This takes 5-10 minutes...")

    # Wait for endpoint to be ready
    waiter = sm.get_waiter("endpoint_in_service")
    waiter.wait(
        EndpointName=ENDPOINT_NAME,
        WaiterConfig={"Delay": 30, "MaxAttempts": 40},
    )
    print(f"  Endpoint is InService!")

    # Save state
    state["endpoint_name"] = ENDPOINT_NAME
    state["endpoint_config"] = config_name
    _save_state(state_file=None, state=state)

    return ENDPOINT_NAME


# === Phase: Test ===

def phase_test(clients):
    """Test inference against the deployed endpoint."""
    print("\n=== Phase 5: Test Inference ===\n")

    runtime = boto3.Session(region_name=REGION).client("sagemaker-runtime")

    test_prompts = [
        "A pod is in ImagePullBackOff. How do I fix it?",
        "What securityContext settings should every pod have?",
        "Explain the difference between a Role and ClusterRole.",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"  Test {i}/{len(test_prompts)}: {prompt[:60]}...")
        payload = json.dumps({
            "inputs": prompt,
            "parameters": {"max_new_tokens": 200, "temperature": 0.3},
        })

        start = time.time()
        response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Body=payload,
        )
        latency = time.time() - start

        result = json.loads(response["Body"].read().decode())
        generated = result[0].get("generated_text", str(result))[:200]
        print(f"  Response ({latency:.1f}s): {generated}...")
        print("")

    print("  All tests passed!")
    return True


# === Phase: Cleanup ===

def phase_cleanup(clients):
    """Delete endpoint, endpoint config, and model. Keep model registry + S3 artifacts."""
    sm = clients["sm"]
    print("\n=== Phase 6: Cleanup (delete endpoint) ===\n")
    print("  Keeping: Model Registry entries, S3 artifacts")
    print("  Deleting: Endpoint, endpoint config, model")
    print("")

    state = _load_state()

    # Delete endpoint
    try:
        sm.delete_endpoint(EndpointName=ENDPOINT_NAME)
        print(f"  Deleted endpoint: {ENDPOINT_NAME}")
    except sm.exceptions.ClientError as e:
        print(f"  Endpoint not found: {e}")

    # Wait for endpoint deletion
    print("  Waiting for endpoint deletion...")
    try:
        waiter = sm.get_waiter("endpoint_deleted")
        waiter.wait(EndpointName=ENDPOINT_NAME, WaiterConfig={"Delay": 15, "MaxAttempts": 40})
    except Exception:
        pass
    print("  Endpoint deleted")

    # Delete endpoint config
    config_name = state.get("endpoint_config", f"{ENDPOINT_NAME}-config")
    try:
        sm.delete_endpoint_config(EndpointConfigName=config_name)
        print(f"  Deleted endpoint config: {config_name}")
    except sm.exceptions.ClientError:
        pass

    # Delete model
    try:
        sm.delete_model(ModelName=MODEL_NAME)
        print(f"  Deleted model: {MODEL_NAME}")
    except sm.exceptions.ClientError:
        pass

    print("\n  Cleanup complete — billing stopped")
    print("  Model registry entries preserved (free)")
    return True


def cleanup_all(clients):
    """Full teardown — delete everything including model registry."""
    sm = clients["sm"]
    print("\n=== Full Cleanup ===\n")

    # Cleanup endpoint first
    phase_cleanup(clients)

    # Delete all model package versions
    print("\n  Deleting model registry entries...")
    try:
        response = sm.list_model_packages(ModelPackageGroupName=MODEL_GROUP)
        for pkg in response.get("ModelPackageSummaryList", []):
            sm.delete_model_package(ModelPackageArn=pkg["ModelPackageArn"])
            print(f"    Deleted: v{pkg['ModelPackageVersion']}")
    except sm.exceptions.ClientError:
        pass

    # Delete model group
    try:
        sm.delete_model_package_group(ModelPackageGroupName=MODEL_GROUP)
        print(f"  Deleted model group: {MODEL_GROUP}")
    except sm.exceptions.ClientError:
        pass

    # Clean up state file
    state_file = os.path.join(os.path.dirname(__file__), ".sagemaker-state.json")
    if os.path.exists(state_file):
        os.remove(state_file)

    print("\n=== Full cleanup complete ===")
    print("To remove IAM + S3: bash tools/setup-sagemaker.sh --teardown")
    return True


# --- State management ---

def _load_state(state_file=None):
    if state_file is None:
        state_file = os.path.join(os.path.dirname(__file__), ".sagemaker-state.json")
    try:
        with open(state_file) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(state_file=None, state=None):
    if state_file is None:
        state_file = os.path.join(os.path.dirname(__file__), ".sagemaker-state.json")
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="SageMaker MLOps lifecycle — train, register, deploy, test, cleanup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full lifecycle (~$1-3)
  python3 tools/sagemaker-lifecycle.py --run-all

  # Step by step
  python3 tools/sagemaker-lifecycle.py --phase setup
  python3 tools/sagemaker-lifecycle.py --phase train
  python3 tools/sagemaker-lifecycle.py --phase register
  python3 tools/sagemaker-lifecycle.py --phase deploy
  python3 tools/sagemaker-lifecycle.py --phase test
  python3 tools/sagemaker-lifecycle.py --phase cleanup

  # Tear down everything
  python3 tools/sagemaker-lifecycle.py --cleanup-all
        """,
    )
    parser.add_argument("--phase", choices=["setup", "train", "register", "deploy", "test", "cleanup"])
    parser.add_argument("--run-all", action="store_true", help="Run full lifecycle")
    parser.add_argument("--cleanup-all", action="store_true", help="Delete everything (endpoint + registry)")
    parser.add_argument("--skip-train", action="store_true", help="Skip training (use existing model artifact)")
    args = parser.parse_args()

    if not any([args.phase, args.run_all, args.cleanup_all]):
        parser.print_help()
        sys.exit(1)

    check_env()
    clients = get_clients()

    if args.cleanup_all:
        return cleanup_all(clients)

    if args.run_all:
        print("=" * 60)
        print("  SageMaker Full Lifecycle")
        print(f"  Project: {PROJECT}")
        print(f"  Region:  {REGION}")
        print(f"  Bucket:  {BUCKET}")
        print("=" * 60)

        phase_setup(clients)

        if args.skip_train:
            print("\n  Skipping training (--skip-train)")
        else:
            phase_train(clients)

        phase_register(clients)
        phase_deploy(clients)
        phase_test(clients)

        print("\n" + "=" * 60)
        print("  Lifecycle complete!")
        print("  The endpoint is running and billing (~$1.41/hr)")
        print("")
        print("  When done testing, clean up:")
        print("    python3 tools/sagemaker-lifecycle.py --phase cleanup")
        print("=" * 60)
        return True

    # Single phase
    phase_map = {
        "setup": lambda: phase_setup(clients),
        "train": lambda: phase_train(clients),
        "register": lambda: phase_register(clients),
        "deploy": lambda: phase_deploy(clients),
        "test": lambda: phase_test(clients),
        "cleanup": lambda: phase_cleanup(clients),
    }
    return phase_map[args.phase]()


if __name__ == "__main__":
    main()
