"""
KFP v2 Training Pipeline — ETL → Chunk → Train → Merge → Convert → Eval → Promote/Fail

Each step runs in its own container. Artifacts flow between steps automatically.
KFP tracks lineage, caches identical steps, and provides a UI for monitoring.

Usage:
    # Compile to YAML (for upload to KFP UI)
    python3 training_pipeline.py --compile

    # Submit directly to KFP server
    python3 training_pipeline.py --submit --endpoint http://kfp.mlops.svc:8888

    # Submit with custom parameters
    python3 training_pipeline.py --submit --model katie-3b --data s3://bucket/corpus.jsonl
"""
import argparse
from kfp import dsl, compiler, Client
from kfp.dsl import Input, Output, Dataset, Model, Metrics, Artifact


# --- Pipeline Components (each runs in its own container) ---

@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["jsonlines", "pandas"],
)
def validate_data(
    data_path: str,
    validation_report: Output[Artifact],
) -> bool:
    """Step 0: Data quality gates. Rejects garbage before training."""
    import json
    import jsonlines
    import os

    errors = []
    total = 0
    passed = 0

    with jsonlines.open(data_path) as reader:
        for example in reader:
            total += 1
            messages = example.get("messages", [])

            # ChatML format check
            if not messages or not isinstance(messages, list):
                errors.append(f"Line {total}: not ChatML format")
                continue

            roles = [m.get("role") for m in messages]
            if "assistant" not in roles:
                errors.append(f"Line {total}: missing assistant response")
                continue

            # Content quality check
            assistant_msg = [m for m in messages if m["role"] == "assistant"][0]
            content = assistant_msg.get("content", "")
            if len(content) < 50:
                errors.append(f"Line {total}: response too short ({len(content)} chars)")
                continue

            passed += 1

    report = {
        "total_examples": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / max(total, 1) * 100, 1),
        "errors": errors[:50],  # Cap error list
    }

    with open(validation_report.path, "w") as f:
        json.dump(report, f, indent=2)

    # Fail if pass rate < 90%
    return report["pass_rate"] >= 90.0


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["jsonlines", "pandas"],
)
def etl_and_chunk(
    data_path: str,
    chunk_size: int,
    eval_holdout_pct: float,
    chunked_data: Output[Dataset],
    eval_holdout: Output[Dataset],
):
    """Steps 1-2: ETL (normalize to ChatML, dedup) then chunk."""
    import json
    import jsonlines
    import hashlib
    import os
    import random

    examples = []
    seen_hashes = set()

    with jsonlines.open(data_path) as reader:
        for example in reader:
            # Dedup by content hash
            content = json.dumps(example, sort_keys=True)
            h = hashlib.sha256(content.encode()).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            examples.append(example)

    random.seed(42)
    random.shuffle(examples)

    # Split eval holdout
    holdout_count = int(len(examples) * eval_holdout_pct)
    eval_examples = examples[:holdout_count]
    train_examples = examples[holdout_count:]

    # Write chunks (KFP handles artifact storage)
    with jsonlines.open(chunked_data.path, mode="w") as writer:
        for ex in train_examples[:chunk_size]:
            writer.write(ex)

    with jsonlines.open(eval_holdout.path, mode="w") as writer:
        for ex in eval_examples:
            writer.write(ex)


@dsl.component(
    base_image="nvcr.io/nvidia/pytorch:24.01-py3",
    packages_to_install=["unsloth", "trl", "peft"],
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
    trained_model: Output[Model],
    training_metrics: Output[Metrics],
):
    """Step 3: LoRA fine-tuning via Unsloth."""
    import json
    import time
    import jsonlines

    from unsloth import FastLanguageModel

    start_time = time.time()

    # Load base model with 4-bit quantization
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
    )

    # Apply LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
    )

    # Load training data
    examples = []
    with jsonlines.open(training_data.path) as reader:
        for ex in reader:
            examples.append(ex)

    # Format for SFT
    from trl import SFTTrainer
    from transformers import TrainingArguments

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=examples,
        args=TrainingArguments(
            output_dir=trained_model.path,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            logging_steps=10,
            save_strategy="epoch",
            fp16=True,
        ),
        max_seq_length=max_seq_length,
    )

    trainer.train()
    trainer.save_model(trained_model.path)

    elapsed = time.time() - start_time
    training_metrics.log_metric("train_loss", trainer.state.log_history[-1].get("loss", 0))
    training_metrics.log_metric("examples_trained", len(examples))
    training_metrics.log_metric("training_time_seconds", round(elapsed, 1))
    training_metrics.log_metric("epochs", epochs)
    training_metrics.log_metric("lora_r", lora_r)


@dsl.component(
    base_image="nvcr.io/nvidia/pytorch:24.01-py3",
    packages_to_install=["peft", "transformers"],
)
def merge_lora(
    lora_model: Input[Model],
    base_model: str,
    merged_model: Output[Model],
):
    """Step 4: Merge LoRA adapters back into base model."""
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base = AutoModelForCausalLM.from_pretrained(base_model)
    model = PeftModel.from_pretrained(base, lora_model.path)
    merged = model.merge_and_unload()

    merged.save_pretrained(merged_model.path)
    AutoTokenizer.from_pretrained(base_model).save_pretrained(merged_model.path)


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["llama-cpp-python"],
)
def convert_gguf(
    merged_model: Input[Model],
    quantization: str,
    gguf_model: Output[Model],
):
    """Step 5: Convert merged model to GGUF for vLLM/Ollama serving."""
    import subprocess

    subprocess.run([
        "python3", "-m", "llama_cpp.convert",
        "--outfile", f"{gguf_model.path}/model.gguf",
        "--outtype", quantization,
        merged_model.path,
    ], check=True)


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["jsonlines", "requests"],
)
def evaluate_model(
    model_path: Input[Model],
    eval_data: Input[Dataset],
    promotion_threshold: float,
    eval_results: Output[Metrics],
) -> bool:
    """Step 6: Run benchmark evaluation. Returns True if model passes promotion gate."""
    import json
    import jsonlines

    # Eval logic — run model against benchmark questions
    # In production this calls the eval_bridge.py or runs inference directly
    results = {"weighted_score": 0.0, "categories": {}}

    # Placeholder — real eval loads model and runs inference
    # The actual eval_bridge.py handles this
    eval_results.log_metric("weighted_score", results["weighted_score"])
    eval_results.log_metric("promotion_threshold", promotion_threshold)

    promoted = results["weighted_score"] >= promotion_threshold
    eval_results.log_metric("promoted", 1.0 if promoted else 0.0)
    return promoted


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["boto3"],
)
def register_model(
    model: Input[Model],
    model_name: str,
    model_version: str,
    s3_destination: str,
):
    """Step 7: Upload promoted model to S3 for KServe to serve."""
    import boto3
    import os

    s3 = boto3.client("s3")
    bucket = s3_destination.split("/")[2]
    prefix = "/".join(s3_destination.split("/")[3:])

    for root, _, files in os.walk(model.path):
        for f in files:
            local_path = os.path.join(root, f)
            rel_path = os.path.relpath(local_path, model.path)
            s3_key = f"{prefix}/{model_name}/{model_version}/{rel_path}"
            s3.upload_file(local_path, bucket, s3_key)


# --- Pipeline Definition ---

@dsl.pipeline(
    name="model-training-pipeline",
    description="Full training lifecycle: validate → ETL → train → merge → convert → eval → promote",
)
def training_pipeline(
    data_path: str = "s3://ml-artifacts/training-data/corpus.jsonl",
    base_model: str = "unsloth/Llama-3.2-3B-Instruct",
    model_name: str = "katie-3b",
    model_version: str = "v2.0",
    lora_r: int = 64,
    lora_alpha: int = 128,
    learning_rate: float = 2e-4,
    epochs: int = 2,
    batch_size: int = 4,
    max_seq_length: int = 4096,
    chunk_size: int = 10000,
    eval_holdout_pct: float = 0.05,
    quantization: str = "q4_k_m",
    promotion_threshold: float = 60.0,
    s3_model_store: str = "s3://ml-artifacts/models",
):
    # Step 0: Validate
    validate_task = validate_data(data_path=data_path)

    # Steps 1-2: ETL + Chunk (only if validation passes)
    with dsl.If(validate_task.outputs["Output"] == True):  # noqa: E712
        chunk_task = etl_and_chunk(
            data_path=data_path,
            chunk_size=chunk_size,
            eval_holdout_pct=eval_holdout_pct,
        )

        # Step 3: Train
        train_task = train_lora(
            training_data=chunk_task.outputs["chunked_data"],
            base_model=base_model,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            learning_rate=learning_rate,
            epochs=epochs,
            batch_size=batch_size,
            max_seq_length=max_seq_length,
        )
        # GPU access: On EKS with Karpenter, uncomment these:
        # train_task.set_accelerator_type("nvidia.com/gpu")
        # train_task.set_accelerator_limit(1)
        # On Docker Desktop WSL2, GPU is available to all pods via
        # default-runtime: nvidia in daemon.json (no resource request needed).

        # Step 4: Merge
        merge_task = merge_lora(
            lora_model=train_task.outputs["trained_model"],
            base_model=base_model,
        )

        # Step 5: Convert to GGUF
        convert_task = convert_gguf(
            merged_model=merge_task.outputs["merged_model"],
            quantization=quantization,
        )

        # Step 6: Evaluate
        eval_task = evaluate_model(
            model_path=convert_task.outputs["gguf_model"],
            eval_data=chunk_task.outputs["eval_holdout"],
            promotion_threshold=promotion_threshold,
        )

        # Step 7: Register (only if eval passes)
        with dsl.If(eval_task.outputs["Output"] == True):  # noqa: E712
            register_model(
                model=convert_task.outputs["gguf_model"],
                model_name=model_name,
                model_version=model_version,
                s3_destination=s3_model_store,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", action="store_true", help="Compile pipeline to YAML")
    parser.add_argument("--submit", action="store_true", help="Submit to KFP server")
    parser.add_argument("--endpoint", default="http://kfp.mlops.svc:8888")
    parser.add_argument("--model", default="katie-3b")
    parser.add_argument("--data", default="s3://ml-artifacts/training-data/corpus.jsonl")
    args = parser.parse_args()

    if args.compile:
        compiler.Compiler().compile(
            pipeline_func=training_pipeline,
            package_path="training_pipeline.yaml",
        )
        print("Compiled to training_pipeline.yaml")

    elif args.submit:
        client = Client(host=args.endpoint)
        run = client.create_run_from_pipeline_func(
            training_pipeline,
            arguments={
                "data_path": args.data,
                "model_name": args.model,
            },
            experiment_name=f"{args.model}-training",
        )
        print(f"Pipeline submitted: {run.run_id}")
        print(f"View at: {args.endpoint}/#/runs/details/{run.run_id}")
