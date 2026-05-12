"""KFP training pipeline for chunk_0005 — runs on Docker Desktop WSL2 with GPU.

Downloads data from SeaweedFS, validates, trains via Unsloth, reports metrics.
Every step visible in KFP UI at http://localhost:8888.
"""
from kfp import dsl, Client
from kfp.dsl import Output, Input, Dataset, Artifact, Metrics


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["boto3"],
)
def download_training_data(
    s3_endpoint: str,
    s3_bucket: str,
    s3_key: str,
    access_key: str,
    secret_key: str,
    raw_data: Output[Dataset],
):
    """Step 1: Download training data from SeaweedFS."""
    import boto3
    import os

    s3 = boto3.client("s3", endpoint_url=s3_endpoint,
                       aws_access_key_id=access_key,
                       aws_secret_access_key=secret_key,
                       region_name="us-east-1")
    s3.download_file(s3_bucket, s3_key, raw_data.path)
    size = os.path.getsize(raw_data.path)
    print(f"Downloaded {s3_key} ({size:,} bytes)")


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["jsonlines"],
)
def validate_data(
    raw_data: Input[Dataset],
    validation_metrics: Output[Metrics],
    validation_report: Output[Artifact],
) -> bool:
    """Step 2: Data quality gates — format, content, dedup."""
    import json
    import jsonlines
    from collections import Counter

    total = 0
    passed = 0
    garbage = 0
    domain_hits = Counter()
    errors = []

    domain_keywords = {
        "CKS": ["pod security", "rbac", "networkpolicy", "falco", "admission", "seccomp", "apparmor", "cis benchmark"],
        "CKA": ["cluster", "etcd", "kubeadm", "deployment", "statefulset", "service", "ingress", "troubleshoot", "kubectl"],
        "CKAD": ["rolling update", "canary", "configmap", "liveness", "readiness", "helm", "resource limit"],
        "CNPA": ["vpc", "cni", "calico", "cilium", "service mesh", "terraform", "platform engineering"],
        "OPS": ["argocd", "rank routing", "incident response", "gitops"],
    }

    with jsonlines.open(raw_data.path) as reader:
        for ex in reader:
            total += 1
            messages = ex.get("messages", [])
            if not messages or not isinstance(messages, list):
                errors.append(f"Line {total}: not ChatML")
                continue
            if "assistant" not in [m.get("role") for m in messages]:
                errors.append(f"Line {total}: no assistant")
                continue
            assistant_msg = [m for m in messages if m["role"] == "assistant"][0]
            if len(assistant_msg.get("content", "")) < 50:
                garbage += 1
                continue

            text = " ".join(m.get("content", "") for m in messages).lower()
            for domain, kws in domain_keywords.items():
                if any(kw in text for kw in kws):
                    domain_hits[domain] += 1

            passed += 1

    pass_rate = round(passed / max(total, 1) * 100, 1)

    validation_metrics.log_metric("total_examples", total)
    validation_metrics.log_metric("passed", passed)
    validation_metrics.log_metric("garbage", garbage)
    validation_metrics.log_metric("pass_rate", pass_rate)
    for domain in ["CKS", "CKA", "CKAD", "CNPA", "OPS"]:
        validation_metrics.log_metric(f"domain_{domain}", domain_hits.get(domain, 0))

    report = {
        "total": total, "passed": passed, "garbage": garbage,
        "pass_rate": pass_rate, "domains": dict(domain_hits),
        "errors": errors[:20],
    }
    with open(validation_report.path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Validation: {passed}/{total} passed ({pass_rate}%)")
    print(f"Domains: {dict(domain_hits)}")
    return pass_rate >= 90.0


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["jsonlines"],
)
def etl_and_chunk(
    raw_data: Input[Dataset],
    chunk_size: int,
    eval_holdout_pct: float,
    chunked_data: Output[Dataset],
    eval_holdout: Output[Dataset],
    etl_metrics: Output[Metrics],
):
    """Step 3: ETL — dedup, shuffle, chunk, split holdout."""
    import json
    import jsonlines
    import hashlib
    import random

    examples = []
    seen = set()
    dupes = 0

    with jsonlines.open(raw_data.path) as reader:
        for ex in reader:
            h = hashlib.sha256(json.dumps(ex, sort_keys=True).encode()).hexdigest()
            if h in seen:
                dupes += 1
                continue
            seen.add(h)
            examples.append(ex)

    random.seed(42)
    random.shuffle(examples)

    holdout_n = int(len(examples) * eval_holdout_pct)
    eval_examples = examples[:holdout_n]
    train_examples = examples[holdout_n:holdout_n + chunk_size]

    with jsonlines.open(chunked_data.path, mode="w") as w:
        for ex in train_examples:
            w.write(ex)
    with jsonlines.open(eval_holdout.path, mode="w") as w:
        for ex in eval_examples:
            w.write(ex)

    etl_metrics.log_metric("total_loaded", len(examples) + dupes)
    etl_metrics.log_metric("duplicates_removed", dupes)
    etl_metrics.log_metric("unique_examples", len(examples))
    etl_metrics.log_metric("train_chunk_size", len(train_examples))
    etl_metrics.log_metric("eval_holdout_size", len(eval_examples))

    print(f"ETL: {len(examples)} unique, {len(train_examples)} train, "
          f"{len(eval_examples)} holdout, {dupes} dupes removed")


@dsl.component(
    base_image="kfp-cuda-python:v1",
    packages_to_install=["torch", "unsloth", "trl", "peft", "transformers",
                         "datasets", "jsonlines", "accelerate", "bitsandbytes"],
    pip_index_urls=["https://pypi.org/simple"],
)
def train_lora(
    training_data: Input[Dataset],
    base_model: str,
    lora_r: int,
    lora_alpha: int,
    learning_rate: float,
    epochs: int,
    batch_size: int,
    max_seq_length: int,
    checkpoint_path: str,
    training_metrics: Output[Metrics],
    training_report: Output[Artifact],
):
    """Step 4: LoRA fine-tune via Unsloth on GPU."""
    import json
    import time
    import jsonlines

    start_time = time.time()

    # Load training data
    examples = []
    with jsonlines.open(training_data.path) as reader:
        for ex in reader:
            examples.append(ex)
    print(f"Loaded {len(examples)} training examples")

    from unsloth import FastLanguageModel, is_bfloat16_supported

    # Load from last checkpoint or base model
    import os
    model_source = checkpoint_path if os.path.exists(checkpoint_path) else base_model
    print(f"Loading model from: {model_source}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_source,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
        device_map="auto",
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # Format for training
    system_prompt = ("You are JADE (Junior Automated DevSecOps Engineer), a security-focused "
                     "AI assistant specializing in Kubernetes, cloud security, policy-as-code "
                     "(OPA/Rego, Kyverno, Gatekeeper), and DevSecOps practices.")

    formatted = []
    for ex in examples:
        messages = ex.get("messages", [])
        if not messages:
            continue
        if messages[0].get("role") == "system":
            messages[0]["content"] = system_prompt
        try:
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            formatted.append({"text": text})
        except Exception:
            continue

    from datasets import Dataset as HFDataset
    dataset = HFDataset.from_dict({"text": [ex["text"] for ex in formatted]})

    from trl import SFTTrainer
    from transformers import TrainingArguments

    output_dir = "/tmp/training-output"
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=8,
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=1,
        save_strategy="no",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        args=training_args,
    )

    print(f"Training {len(formatted)} examples for {epochs} epochs...")
    trainer.train()

    # Save merged model
    merge_path = "/tmp/merged-model"
    print(f"Merging LoRA weights...")
    model.save_pretrained_merged(merge_path, tokenizer, save_method="merged_16bit")

    elapsed = time.time() - start_time
    final_loss = trainer.state.log_history[-1].get("loss", 0) if trainer.state.log_history else 0

    training_metrics.log_metric("examples_trained", len(formatted))
    training_metrics.log_metric("epochs", epochs)
    training_metrics.log_metric("final_loss", round(final_loss, 4))
    training_metrics.log_metric("training_time_minutes", round(elapsed / 60, 1))
    training_metrics.log_metric("lora_r", lora_r)
    training_metrics.log_metric("lora_alpha", lora_alpha)
    training_metrics.log_metric("learning_rate", learning_rate)
    training_metrics.log_metric("batch_size", batch_size)
    training_metrics.log_metric("merged_to", merge_path)

    report = {
        "examples_trained": len(formatted),
        "epochs": epochs,
        "final_loss": round(final_loss, 4),
        "training_time_minutes": round(elapsed / 60, 1),
        "model_source": model_source,
        "merged_to": merge_path,
        "config": {
            "lora_r": lora_r, "lora_alpha": lora_alpha,
            "learning_rate": learning_rate, "batch_size": batch_size,
            "max_seq_length": max_seq_length,
        },
    }
    with open(training_report.path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Training complete: {len(formatted)} examples, {epochs} epochs, "
          f"loss={final_loss:.4f}, {elapsed/60:.1f}m")


@dsl.pipeline(
    name="katie-v2-chunk5-training",
    description="Full training pipeline: download → validate → ETL → train (GPU) — chunk_0005",
)
def training_pipeline(
    s3_endpoint: str = "http://seaweedfs.kubeflow.svc:8333",
    s3_bucket: str = "ml-artifacts",
    s3_key: str = "training-data/chunk_0005_10k.jsonl",
    access_key: str = "minio",
    secret_key: str = "minio123",
    base_model: str = "unsloth/Llama-3.2-3B-Instruct",
    checkpoint_path: str = "/home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/3-model-registry/v2.0-3b/chunk_0002_10k/merged",
    lora_r: int = 64,
    lora_alpha: int = 128,
    learning_rate: float = 2e-5,
    epochs: int = 2,
    batch_size: int = 4,
    max_seq_length: int = 2048,
    chunk_size: int = 3000,
    eval_holdout_pct: float = 0.05,
):
    # Step 1: Download from S3
    download_task = download_training_data(
        s3_endpoint=s3_endpoint, s3_bucket=s3_bucket, s3_key=s3_key,
        access_key=access_key, secret_key=secret_key,
    )

    # Step 2: Validate
    validate_task = validate_data(
        raw_data=download_task.outputs["raw_data"],
    )

    # Step 3: ETL + Chunk (only if validation passes)
    with dsl.If(validate_task.outputs["Output"] == True):  # noqa: E712
        etl_task = etl_and_chunk(
            raw_data=download_task.outputs["raw_data"],
            chunk_size=chunk_size,
            eval_holdout_pct=eval_holdout_pct,
        )

        # Step 4: Train (GPU via default-runtime: nvidia)
        train_task = train_lora(
            training_data=etl_task.outputs["chunked_data"],
            base_model=base_model,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            learning_rate=learning_rate,
            epochs=epochs,
            batch_size=batch_size,
            max_seq_length=max_seq_length,
            checkpoint_path=checkpoint_path,
        )


if __name__ == "__main__":
    client = Client(host="http://localhost:8887")
    run = client.create_run_from_pipeline_func(
        training_pipeline,
        experiment_name="katie-3b-training",
    )
    print(f"Run submitted: {run.run_id}")
    print(f"View at: http://localhost:8888/#/runs/details/{run.run_id}")
