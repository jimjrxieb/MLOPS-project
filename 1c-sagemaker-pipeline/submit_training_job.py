#!/usr/bin/env python3
"""
submit_training_job.py — Submit a SageMaker training job for Katie v2 LoRA fine-tuning.

Usage:
    python3 submit_training_job.py --chunk chunk_0005_10k.jsonl
    python3 submit_training_job.py --chunk chunk_0005_10k.jsonl --spot  # Use spot instances (60-90% cheaper)
    python3 submit_training_job.py --chunk chunk_0005_10k.jsonl --instance ml.g4dn.xlarge  # Cheapest GPU

Uploads training data to S3, submits SageMaker training job, monitors progress.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import boto3
import sagemaker
from sagemaker.estimator import Estimator

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
CHUNK_DIR = REPO_ROOT / "1-FineTuning-Pipeline" / "03-chunked-untrained"
REGISTRY_DIR = REPO_ROOT / "3-model-registry"
SM_BUCKET = None  # Auto-detect from SageMaker session
SM_ROLE = "arn:aws:iam::026090554981:role/service-role/AmazonSageMakerAdminIAMExecutionRole"
ECR_IMAGE = None  # Set after build, or use HuggingFace DLC + pip install

# Default hyperparameters (match 1-FineTuning-Pipeline/config.yaml)
DEFAULT_HPS = {
    "model_name": "unsloth/Llama-3.2-3B-Instruct",
    "lora_r": "64",
    "lora_alpha": "128",
    "epochs": "2",
    "batch_size": "4",
    "learning_rate": "2e-5",
    "max_seq_length": "2048",
    "gradient_accumulation_steps": "8",
}


def upload_chunk_to_s3(session, chunk_path: Path, bucket: str) -> str:
    """Upload training chunk to S3. Returns S3 URI."""
    s3_key = f"katie-training/data/{chunk_path.name}"
    s3_uri = f"s3://{bucket}/{s3_key}"

    print(f"Uploading {chunk_path.name} ({chunk_path.stat().st_size / 1024 / 1024:.1f} MB) to {s3_uri}")
    s3 = session.boto_session.client("s3")
    s3.upload_file(str(chunk_path), bucket, s3_key)
    print(f"Upload complete: {s3_uri}")
    return s3_uri


def get_training_image(region: str) -> str:
    """Get the HuggingFace Deep Learning Container URI for the region."""
    # HuggingFace DLC with PyTorch 2.x + CUDA — Unsloth gets pip installed at runtime
    account_map = {
        "us-east-1": "763104351884",
        "us-east-2": "763104351884",
        "us-west-2": "763104351884",
    }
    account = account_map.get(region, "763104351884")
    # PyTorch 2.3 + Python 3.11 + CUDA 12.1
    return f"{account}.dkr.ecr.{region}.amazonaws.com/huggingface-pytorch-training:2.3.0-transformers4.43.4-gpu-py311-cu121-ubuntu22.04"


def submit_job(args):
    """Submit SageMaker training job."""
    session = sagemaker.Session()
    region = session.boto_region_name
    bucket = session.default_bucket()

    chunk_path = CHUNK_DIR / args.chunk
    if not chunk_path.exists():
        print(f"ERROR: {chunk_path} not found")
        sys.exit(1)

    # Count examples
    with open(chunk_path) as f:
        example_count = sum(1 for _ in f)
    print(f"Chunk: {args.chunk} ({example_count} examples)")

    # Upload data
    s3_data_uri = upload_chunk_to_s3(session, chunk_path, bucket)

    # Job name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    chunk_name = chunk_path.stem.replace("_10k", "").replace("chunk_", "c")
    job_name = f"katie-v2-{chunk_name}-{timestamp}"

    # Training image
    image_uri = get_training_image(region)

    # Hyperparameters
    hyperparameters = {**DEFAULT_HPS}
    if args.checkpoint:
        hyperparameters["checkpoint_s3"] = args.checkpoint

    # Estimator
    estimator_kwargs = {
        "image_uri": image_uri,
        "role": SM_ROLE,
        "instance_count": 1,
        "instance_type": args.instance,
        "hyperparameters": hyperparameters,
        "output_path": f"s3://{bucket}/katie-training/output",
        "base_job_name": "katie-v2-lora",
        "sagemaker_session": session,
        "environment": {
            # Install Unsloth at runtime (adds ~2-3 min to startup)
            "SAGEMAKER_REQUIREMENTS": "unsloth,jsonlines,trl,peft,bitsandbytes,accelerate",
        },
        "max_run": 7200,  # 2 hour max
        "keep_alive_period_in_seconds": 0,  # No warm pool
    }

    # Spot training
    if args.spot:
        estimator_kwargs["use_spot_instances"] = True
        estimator_kwargs["max_wait"] = 14400  # Wait up to 4 hours for spot
        estimator_kwargs["checkpoint_s3_uri"] = f"s3://{bucket}/katie-training/checkpoints/{job_name}"
        print(f"Spot training ENABLED (60-90% discount, up to 4hr wait)")

    estimator = Estimator(**estimator_kwargs)

    print(f"\n{'='*60}")
    print(f"Job name:    {job_name}")
    print(f"Instance:    {args.instance}")
    print(f"Spot:        {'YES' if args.spot else 'NO'}")
    print(f"Image:       {image_uri.split('/')[-1]}")
    print(f"Data:        {s3_data_uri}")
    print(f"Examples:    {example_count}")
    print(f"Epochs:      {hyperparameters['epochs']}")
    print(f"Batch size:  {hyperparameters['batch_size']}")
    print(f"LoRA r/α:    {hyperparameters['lora_r']}/{hyperparameters['lora_alpha']}")
    print(f"{'='*60}\n")

    if not args.yes:
        confirm = input("Submit training job? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return

    # Submit
    print("Submitting training job...")
    estimator.fit(
        inputs={"training": s3_data_uri},
        job_name=job_name,
        wait=not args.background,
        logs="All" if not args.background else None,
    )

    if args.background:
        print(f"\nJob submitted in background: {job_name}")
        print(f"Monitor: aws sagemaker describe-training-job --training-job-name {job_name}")
        print(f"Logs: aws logs tail /aws/sagemaker/TrainingJobs --filter-pattern {job_name} --follow")
    else:
        print(f"\nTraining complete!")
        print(f"Model artifacts: {estimator.model_data}")

    # Save job metadata locally
    meta = {
        "job_name": job_name,
        "chunk": args.chunk,
        "examples": example_count,
        "instance": args.instance,
        "spot": args.spot,
        "hyperparameters": hyperparameters,
        "s3_data": s3_data_uri,
        "s3_output": f"s3://{bucket}/katie-training/output/{job_name}",
        "submitted_at": datetime.now().isoformat(),
    }
    meta_path = Path(__file__).parent / f"jobs/{job_name}.json"
    meta_path.parent.mkdir(exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Job metadata saved: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="Submit SageMaker training job for Katie v2")
    parser.add_argument("--chunk", required=True, help="Chunk filename (e.g., chunk_0005_10k.jsonl)")
    parser.add_argument("--instance", default="ml.g5.xlarge", help="Instance type (default: ml.g5.xlarge)")
    parser.add_argument("--spot", action="store_true", help="Use spot instances (cheaper, may be interrupted)")
    parser.add_argument("--checkpoint", help="S3 URI of previous checkpoint to resume from")
    parser.add_argument("--background", action="store_true", help="Submit and return immediately (don't wait)")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    submit_job(args)


if __name__ == "__main__":
    main()
