#!/usr/bin/env python3
"""
deploy-sagemaker-training.py — Launch a SageMaker Training Job for LoRA fine-tuning.

Usage:
    python3 tools/deploy-sagemaker-training.py \
        --model-name katie-3b \
        --training-data s3://bucket/training-data/katie_v2_clean.jsonl \
        --output-path s3://bucket/model-output/ \
        --instance-type ml.g5.xlarge \
        --use-spot
"""

import argparse
import json
import os

try:
    import sagemaker
    from sagemaker.huggingface import HuggingFace
    SAGEMAKER_AVAILABLE = True
except ImportError:
    SAGEMAKER_AVAILABLE = False
    print("pip install sagemaker to use this tool")


def launch_training(args):
    if not SAGEMAKER_AVAILABLE:
        print("Error: sagemaker SDK not installed. Run: pip install sagemaker")
        return

    role = args.role or os.environ.get("SAGEMAKER_ROLE")
    if not role:
        print("Error: --role or SAGEMAKER_ROLE env var required")
        return

    print(f"=== Launching SageMaker Training Job ===")
    print(f"  Model: {args.model_name}")
    print(f"  Instance: {args.instance_type}")
    print(f"  Spot: {args.use_spot}")
    print(f"  Training data: {args.training_data}")
    print(f"  Output: {args.output_path}")

    estimator = HuggingFace(
        entry_point="train_sagemaker.py",
        source_dir=args.source_dir,
        instance_type=args.instance_type,
        instance_count=1,
        role=role,
        transformers_version="4.37",
        pytorch_version="2.1",
        py_version="py310",
        hyperparameters={
            "model_name": "unsloth/Llama-3.2-3B-Instruct",
            "lora_r": 64,
            "lora_alpha": 128,
            "epochs": 2,
            "batch_size": 4,
            "learning_rate": "2e-5",
            "max_seq_length": 2048,
        },
        output_path=args.output_path,
        max_run=7200,
        use_spot_instances=args.use_spot,
        max_wait=10800 if args.use_spot else None,
        checkpoint_s3_uri=f"{args.output_path}checkpoints/" if args.use_spot else None,
    )

    print("\nStarting training job...")
    estimator.fit({"training": args.training_data})

    print(f"\nTraining job complete.")
    print(f"Model artifacts: {args.output_path}")


def main():
    parser = argparse.ArgumentParser(description="Launch SageMaker Training Job")
    parser.add_argument("--model-name", default="katie-3b")
    parser.add_argument("--training-data", required=True, help="S3 URI to training JSONL")
    parser.add_argument("--output-path", required=True, help="S3 URI for model output")
    parser.add_argument("--instance-type", default="ml.g5.xlarge")
    parser.add_argument("--use-spot", action="store_true", help="Use spot instances (60-70% cheaper)")
    parser.add_argument("--role", help="SageMaker execution role ARN")
    parser.add_argument("--source-dir", default="./src", help="Directory with training script")
    args = parser.parse_args()

    launch_training(args)


if __name__ == "__main__":
    main()
