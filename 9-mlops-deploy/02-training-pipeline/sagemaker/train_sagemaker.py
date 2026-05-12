#!/usr/bin/env python3
"""
train_sagemaker.py — SageMaker-compatible training script.

This wraps the existing LoRA training logic to work with SageMaker's
environment variables and directory conventions.

SageMaker provides:
  SM_CHANNEL_TRAINING  → path to training data
  SM_MODEL_DIR         → path to save model (uploaded to S3 after training)
  SM_HPS               → hyperparameters as JSON string
  SM_OUTPUT_DATA_DIR   → path for additional output files
"""

import json
import os
import sys
from pathlib import Path


def main():
    # SageMaker environment
    training_dir = Path(os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training"))
    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    output_dir = Path(os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output/data"))
    hps = json.loads(os.environ.get("SM_HPS", "{}"))

    print(f"Training data: {training_dir}")
    print(f"Model output: {model_dir}")
    print(f"Hyperparameters: {json.dumps(hps, indent=2)}")

    # Extract hyperparameters
    model_name = hps.get("model_name", "unsloth/Llama-3.2-3B-Instruct")
    lora_r = int(hps.get("lora_r", 64))
    lora_alpha = int(hps.get("lora_alpha", 128))
    epochs = int(hps.get("epochs", 2))
    batch_size = int(hps.get("batch_size", 4))
    learning_rate = float(hps.get("learning_rate", 2e-5))
    max_seq_length = int(hps.get("max_seq_length", 2048))

    # Import training dependencies
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import load_dataset

    # Load model with LoRA
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0,
    )

    # Load training data
    training_files = list(training_dir.glob("*.jsonl"))
    if not training_files:
        print(f"ERROR: No .jsonl files found in {training_dir}")
        sys.exit(1)

    dataset = load_dataset("json", data_files=[str(f) for f in training_files], split="train")
    print(f"Loaded {len(dataset)} training examples from {len(training_files)} files")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(model_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=8,
        learning_rate=learning_rate,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="epoch",
        fp16=True,
    )

    # Format function for ChatML
    def format_chatml(example):
        messages = example.get("messages", [])
        text = tokenizer.apply_chat_template(messages, tokenize=False)
        return {"text": text}

    dataset = dataset.map(format_chatml)

    # Train
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        tokenizer=tokenizer,
    )

    trainer.train()

    # Save model (SageMaker uploads this to S3)
    model.save_pretrained(str(model_dir))
    tokenizer.save_pretrained(str(model_dir))

    # Save training metadata
    metadata = {
        "model_name": model_name,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "epochs": epochs,
        "examples_trained": len(dataset),
        "training_files": [f.name for f in training_files],
    }
    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nTraining complete. Model saved to {model_dir}")


if __name__ == "__main__":
    main()
