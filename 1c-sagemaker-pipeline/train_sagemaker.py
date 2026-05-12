#!/usr/bin/env python3
"""
train_sagemaker.py — SageMaker training script for Katie v2 LoRA fine-tuning.

Runs inside SageMaker's managed container. SageMaker provides:
  SM_CHANNEL_TRAINING  → /opt/ml/input/data/training (training data from S3)
  SM_MODEL_DIR         → /opt/ml/model (saved here → uploaded to S3)
  SM_OUTPUT_DATA_DIR   → /opt/ml/output/data (additional outputs)
  SM_HPS               → hyperparameters as JSON string
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def install_deps():
    """Install Unsloth and deps not in the HuggingFace DLC."""
    print("Installing Unsloth + dependencies...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir",
        "unsloth", "jsonlines", "bitsandbytes",
    ])
    print("Dependencies installed.")


def main():
    install_deps()

    # SageMaker environment
    training_dir = Path(os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training"))
    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    output_dir = Path(os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output/data"))
    output_dir.mkdir(parents=True, exist_ok=True)

    hps = json.loads(os.environ.get("SM_HPS", "{}"))

    # Hyperparameters
    model_name = hps.get("model_name", "unsloth/Llama-3.2-3B-Instruct")
    lora_r = int(hps.get("lora_r", 64))
    lora_alpha = int(hps.get("lora_alpha", 128))
    epochs = int(hps.get("epochs", 2))
    batch_size = int(hps.get("batch_size", 4))
    learning_rate = float(hps.get("learning_rate", 2e-5))
    max_seq_length = int(hps.get("max_seq_length", 2048))
    grad_accum = int(hps.get("gradient_accumulation_steps", 8))

    print(f"Model: {model_name}")
    print(f"LoRA r={lora_r}, alpha={lora_alpha}")
    print(f"Epochs: {epochs}, Batch: {batch_size}, LR: {learning_rate}")

    # Import after install
    import jsonlines
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset as HFDataset

    # Load training data
    training_files = sorted(training_dir.glob("*.jsonl"))
    if not training_files:
        print(f"ERROR: No .jsonl files in {training_dir}")
        sys.exit(1)

    examples = []
    for tf in training_files:
        with jsonlines.open(tf) as reader:
            for ex in reader:
                examples.append(ex)
    print(f"Loaded {len(examples)} examples from {len(training_files)} files")

    # Load model
    start_time = time.time()
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
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

    # Format for ChatML
    system_prompt = (
        "You are Katie, a CKA/CKS/CKAD/CNPA-certified autonomous Kubernetes engineer "
        "for GP-Copilot. You diagnose and fix production issues at 2 AM without human "
        "intervention. You provide complete, working fixes with exact commands and YAML "
        "manifests. You check ArgoCD ownership before any fix. You route by rank "
        "(E/D/C/B/S). You reference real tools: kubectl, Falco, Trivy, Kubescape, "
        "Kyverno, OPA/Rego, Helm, ArgoCD. You never hallucinate commands."
    )

    formatted = []
    for ex in examples:
        messages = ex.get("messages", [])
        if not messages:
            continue
        if messages[0].get("role") == "system":
            messages[0]["content"] = system_prompt
        try:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            formatted.append({"text": text})
        except Exception:
            continue

    dataset = HFDataset.from_dict({"text": [ex["text"] for ex in formatted]})
    print(f"Formatted {len(formatted)} examples for training")

    # Training
    training_args = TrainingArguments(
        output_dir="/tmp/training-output",
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
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

    # Save merged model (SageMaker uploads model_dir to S3)
    print("Merging LoRA weights...")
    model.save_pretrained_merged(str(model_dir), tokenizer, save_method="merged_16bit")

    elapsed = time.time() - start_time
    final_loss = trainer.state.log_history[-1].get("loss", 0) if trainer.state.log_history else 0

    # Save training metadata
    metadata = {
        "model_name": model_name,
        "examples_trained": len(formatted),
        "epochs": epochs,
        "final_loss": round(final_loss, 4),
        "training_time_minutes": round(elapsed / 60, 1),
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "max_seq_length": max_seq_length,
    }
    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nTraining complete: {len(formatted)} examples, {epochs} epochs, "
          f"loss={final_loss:.4f}, {elapsed/60:.1f}m")
    print(f"Model saved to {model_dir}")


if __name__ == "__main__":
    main()
