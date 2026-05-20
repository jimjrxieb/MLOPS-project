# 1-local-pipeline — Training Engine

7-step MLOps pipeline for LoRA fine-tuning BERU, JADE, and Katie on local GPU. Data flows forward through numbered directories, files archive after each step. Includes a closed-loop evaluation and feedback system.

**Primary model:** BERU (GRC analyst, 3B). JADE (DevSecOps, 8B) and Katie (K8s ops, 3B) share the same pipeline with different configs and corpora.

## Architecture

```
01-raw-data-lake/        Raw training data drops here
       |
   etl_pipeline.py       STEP 1: Extract, Transform, Load
       |
02-ETL-data/             Cleaned, deduplicated, labeled JSONL
       |
   chunk_data.py         STEP 2: Split into training chunks
       |
03-chunked-untrained/    5k-10k example chunks + eval holdout
       |
   train_v10.py          STEP 3: LoRA fine-tuning per chunk
       |
04-trained-data/         Completed chunks (archived)
       |
   merge_model.py        STEP 4: Merge LoRA weights into base
       |
   convert_gguf.py       STEP 5: Convert to GGUF for Ollama
       |
   eval_bridge.py        STEP 6: Benchmark against GP-CLARIFY
       |
   feedback_loop.py      STEP 7: Identify gaps, generate new data
       |
01-raw-data-lake/        Loop closes — new training data for next cycle
```

## Quick Start

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE

# Step 1: ETL — clean and normalize raw data
python3 etl_pipeline.py

# Step 2: Chunk — split into training files
python3 chunk_data.py --shuffle

# Step 3: Train — fine-tune on each chunk (auto-resumes)
python3 train_v10.py

# Step 4: Merge LoRA weights
python3 merge_model.py

# Step 5: Convert to GGUF for Ollama
python3 convert_gguf.py

# Step 6: Benchmark evaluation
python3 eval_bridge.py --latest

# Step 7: Generate training data for weak areas
python3 feedback_loop.py --latest --export
```

## Directory Structure

```
1-GP-GLUE/
├── 00-processed/                 # Archive (files move here after processing)
│   └── etl-data/                     # Archived ETL sources with checkpoints
│
├── 01-raw-data-lake/             # INPUT: Drop raw data here
│   ├── claudecode-sessions/          # Claude Code session transcripts
│   ├── eval-gaps/                    # Auto-generated from feedback_loop.py
│   └── (other raw sources)
│
├── 02-ETL-data/                  # Cleaned, deduplicated, labeled JSONL
│   └── jade_v10_etl_*.jsonl
│
├── 03-chunked-untrained/         # Ready for training
│   ├── chunk_0001_5k.jsonl           # 5k examples per chunk
│   ├── ...
│   ├── chunk_0047_5k.jsonl
│   ├── manifest.json                 # Chunk metadata (232,266 total examples)
│   └── sources/                      # Archived from 02-ETL-data
│
├── 04-trained-data/              # Completed chunks (moved after training)
│   ├── chunk_0001_10k.jsonl
│   ├── ...
│   └── v1.1/                         # Version subdirectory
│
├── rank-training-data/           # Rank classifier outputs
│   ├── rank_classifier.joblib        # Trained scikit-learn model
│   └── rank_classifier.metrics.json  # Performance metrics
│
├── npcs/                         # NPC integration scripts
│   └── merge_and_convert_v09.py      # V0.9 merge helper
│
├── etl_pipeline.py               # Step 1: Extract, Transform, Load
├── chunk_data.py                 # Step 2: Split into training chunks
├── train_v10.py                  # Step 3: LoRA fine-tuning
├── merge_model.py                # Step 4: Merge LoRA into base model
├── convert_gguf.py               # Step 5: Convert to GGUF
├── eval_bridge.py                # Step 6: Benchmark evaluation
├── feedback_loop.py              # Step 7: Gap analysis + data generation
└── README.md                     # This file
```

Related directories in `GP-SAGEMAKER/`:
```
GP-SAGEMAKER/
├── 1-GP-GLUE/                    # This pipeline (data + scripts)
├── 3-jade-model-versions/        # Model checkpoints and merged outputs
│   └── v1.0/
│       ├── chunk_*/final/            # LoRA checkpoints per chunk
│       ├── jade-v1.0-merged/         # Full merged HuggingFace model
│       ├── jade-v1.0-q4_k_m.gguf    # Quantized GGUF for Ollama
│       └── training_state.json       # Training progress tracker
├── 4-GP-CLARIFY/                 # Evaluation benchmark framework
│   ├── 2-test-data/                  # 65 benchmark questions (7 categories)
│   └── 3-results/                    # Evaluation run results
├── 5-GP-TRAINING-SCENARIOS/      # Training scenario definitions
└── llama.cpp/                    # GGUF conversion tooling
```

---

## Step 1: ETL Pipeline (`etl_pipeline.py`)

Extracts, transforms, and loads raw data into clean ChatML training format.

**What it does:**
- Reads `.jsonl`, `.json`, `.md`, `.txt`, `.pdf` from `01-raw-data-lake/` and `00-processed/`
- Deduplicates via MD5 hash of messages
- Auto-labels by category: policy, benchmark, compliance, iac, devsecops, consultant, session, documentation
- Auto-detects domain from keywords: kubernetes, opa, aws, azure, gcp, cicd, docker, network, rbac, secrets
- Normalizes multiple input formats to standard ChatML
- Archives source files to `00-processed/`

**Input formats:**

| Format | Structure |
|--------|-----------|
| ChatML | `{"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}` |
| Alpaca | `{"instruction": "...", "input": "...", "output": "..."}` |
| Q&A | `{"question": "...", "answer": "..."}` |
| Benchmark | `{"question": "...", "jade_response": "...", "correct": true}` |

**Commands:**
```bash
python3 etl_pipeline.py             # Process all
python3 etl_pipeline.py --dry-run   # Preview only
python3 etl_pipeline.py --keep      # Don't archive source files
python3 etl_pipeline.py --delete    # Delete instead of archive
```

**Output:** `02-ETL-data/jade_v10_etl_YYYYMMDD_HHMMSS.jsonl`

---

## Step 2: Chunking (`chunk_data.py`)

Splits ETL output into training chunks with eval holdout.

**What it does:**
- Validates examples (user + assistant messages, content > 20 chars, no `[NEEDS CORRECTION]` markers)
- Creates 5% holdout eval set (seed=42 for reproducibility)
- Shuffles data for better training distribution
- Chunks into 5k or 10k example files
- Auto-detects next chunk number (continues from existing)
- Archives source files to `03-chunked-untrained/sources/`
- Creates manifest with chunk count, total examples, source files

**Commands:**
```bash
python3 chunk_data.py --shuffle               # Recommended: shuffle before chunking
python3 chunk_data.py --chunk-size 10000      # 10k examples per chunk
python3 chunk_data.py --holdout-pct 10        # 10% eval holdout
python3 chunk_data.py --dry-run               # Preview only
python3 chunk_data.py --keep                  # Don't archive source files
```

**Output:**
```
03-chunked-untrained/
├── chunk_0001_5k.jsonl    (5,000 examples)
├── chunk_0002_5k.jsonl    (5,000 examples)
├── ...
└── manifest.json          (metadata: 232,266 total examples, 47 chunks)
```

---

## Step 3: Training (`train_v10.py`)

Fine-tunes JADE on each chunk using LoRA with Unsloth.

**What it does:**
- Auto-resumes from last trained checkpoint
- Uses Unsloth + LoRA for memory-efficient training
- Base model: `v0.9/jade-v0.9-merged` or fallback to `unsloth/Llama-3.1-8B-Instruct`
- Tracks training state with session history
- Moves trained chunks to `04-trained-data/`

**Training configuration:**

| Parameter | Value |
|-----------|-------|
| Max Sequence Length | 4096 |
| LoRA r | 64 |
| LoRA alpha | 128 |
| Batch Size | 4 |
| Gradient Accumulation | 8 (effective: 32) |
| Learning Rate | 2e-5 |
| Epochs per Chunk | 2 |

**Commands:**
```bash
python3 train_v10.py                # Train next chunk (auto-detects)
python3 train_v10.py --loop         # Train all remaining chunks
python3 train_v10.py --status       # Show training progress
python3 train_v10.py --chunk 5      # Train specific chunk number
python3 train_v10.py --epochs 3     # Override epochs per chunk
python3 train_v10.py --dry-run      # Preview without training
python3 train_v10.py --reset        # Reset all progress (destructive)
```

**Prerequisites:**
```bash
pip install unsloth trl transformers datasets
```

**Output:**
```
GP-SAGEMAKER/3-jade-model-versions/v1.0/
├── chunk_0001/final/         # LoRA checkpoint after chunk 1
├── chunk_0002/final/         # LoRA checkpoint after chunk 2
├── ...
└── training_state.json       # Progress tracking (JSON)
```

---

## Step 4: Merge LoRA Weights (`merge_model.py`)

Merges the final LoRA checkpoint into a full model.

**Merge strategies:**

| Method | VRAM | Speed | Notes |
|--------|------|-------|-------|
| `unsloth` | 24GB+ | Fast | GPU-accelerated (recommended if VRAM available) |
| `16bit` | 16GB | Medium | Balanced with GPU offload (default) |
| `peft-cpu` | 8GB | Slow | CPU-only, works on any machine |

**Commands:**
```bash
python3 merge_model.py                    # Auto-detect, use 16-bit
python3 merge_model.py --method unsloth   # GPU-accelerated
python3 merge_model.py --method peft-cpu  # CPU-only
python3 merge_model.py --dry-run          # Preview
```

**Output:** `3-jade-model-versions/v1.0/jade-v1.0-merged/`

---

## Step 5: Convert to GGUF (`convert_gguf.py`)

Converts merged model to GGUF format for Ollama deployment.

**Requires:** `llama.cpp` at `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/llama.cpp`

**Quantization options:**

| Format | Size | Quality | Use Case |
|--------|------|---------|----------|
| Q4_K_M | ~4GB | Good | Production (default) |
| Q5_K_M | ~5GB | Better | Higher quality, more VRAM |
| Q8_0 | ~8GB | Best | When VRAM is available |
| F16 | ~14GB | Lossless | Evaluation/reference |

**Commands:**
```bash
python3 convert_gguf.py                # Q4_K_M quantization (default)
python3 convert_gguf.py --quant Q5_K_M # Higher quality quantization
python3 convert_gguf.py --no-quant     # F16 only (no quantization)
```

**Output:**
```
3-jade-model-versions/v1.0/
├── jade-v1.0-f16.gguf       # Float16 (intermediate)
└── jade-v1.0-q4_k_m.gguf    # Quantized (for Ollama)
```

**Deploy to Ollama:**
```bash
ollama create jade:v1.0 -f Modelfile
```

---

## Step 6: Evaluation (`eval_bridge.py`)

Benchmarks the trained model against GP-CLARIFY test data.

**What it does:**
- Loads merged model directly with Unsloth (4-bit, no Ollama needed)
- Runs 65 benchmark questions across 7 security categories
- Detects hallucinations: fake CVEs (`CVE-9999-`), fake CIS references (`CIS 99.`)
- Compares responses against expected keyword lists
- Generates detailed accuracy report by category

**Categories (7):**
cloud, cks, devsecops, compliance, hardening, incident-response, threat-modeling

**Commands:**
```bash
python3 eval_bridge.py --latest                              # Full benchmark (65 questions)
python3 eval_bridge.py --latest --quick                      # Quick run (21 questions, 3/category)
python3 eval_bridge.py --model-path /path/to/merged          # Specific model
python3 eval_bridge.py --latest --category cloud --category cks  # Specific categories
```

**Output:** `GP-SAGEMAKER/4-GP-CLARIFY/3-results/bridge_YYYYMMDD_HHMMSS/full_results.json`

---

## Step 7: Feedback Loop (`feedback_loop.py`)

Closes the training loop: identifies weak categories and generates new training data.

**What it does:**
- Loads eval results from the latest bridge run
- Identifies categories scoring below threshold (default: 80%)
- Extracts failed test cases (questions, responses, expected keywords)
- Generates new Alpaca-format training examples for weak areas
- Writes to `01-raw-data-lake/eval-gaps/` — ready for next ETL cycle

**Commands:**
```bash
python3 feedback_loop.py --latest                   # Analyze newest eval results
python3 feedback_loop.py --latest --threshold 75    # Custom threshold
python3 feedback_loop.py --latest --export          # Write gap data to raw-data-lake
python3 feedback_loop.py --latest --dry-run         # Preview without writing
```

**Output:** `01-raw-data-lake/eval-gaps/gaps_YYYYMMDD.jsonl`

**Closed loop:**
```
Train → Eval → Find Gaps → Generate Data → ETL → Chunk → Train (repeat)
```

---

## Complete Workflow

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE

# 1. Add raw training data
cp new_training_data.jsonl 01-raw-data-lake/

# 2. Run the full pipeline
python3 etl_pipeline.py              # 01 → 02 (archives to 00)
python3 chunk_data.py --shuffle      # 02 → 03 (archives to 00/etl-done)
python3 train_v10.py --loop          # 03 → 04 (creates checkpoints)

# 3. Post-training
python3 merge_model.py               # Merge LoRA → full model
python3 convert_gguf.py              # Convert → GGUF
ollama create jade:v1.0 -f Modelfile # Deploy to Ollama

# 4. Evaluate + feedback
python3 eval_bridge.py --latest      # Benchmark
python3 feedback_loop.py --latest --export  # Generate gap data

# 5. Next cycle (re-enter pipeline with gap data)
python3 etl_pipeline.py              # Picks up eval-gaps/ automatically
```

---

## Current State

| Metric | Value |
|--------|-------|
| Total Examples Prepared | 232,266 |
| Chunks Created | 47 (5k each) |
| Chunks Trained | 26+ |
| Chunked Data Size | 2.0 GB |
| Trained Data Size | 741 MB |
| Base Model | Llama-3.1-8B-Instruct |
| Model Version | v1.0 (building on v0.9) |

---

## Troubleshooting

**"No files found in 01-raw-data-lake/"**
Add `.jsonl` files to `01-raw-data-lake/` before running ETL.

**"No chunks found in 03-chunked-untrained/"**
Run `chunk_data.py` before training.

**"Training dependencies not installed"**
```bash
pip install unsloth trl transformers datasets
```

**CUDA out of memory**
Edit `train_v10.py` and reduce `BATCH_SIZE` from 4 to 2, or reduce `MAX_SEQ_LENGTH` from 4096 to 2048.

**Want to re-process archived files?**
Move files from `00-processed/` back to `01-raw-data-lake/`.

**llama.cpp not found for GGUF conversion**
```bash
git clone https://github.com/ggerganov/llama.cpp /home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/llama.cpp
cd /home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/llama.cpp && make
```

---

## Key Principles

1. **Data flows forward**: raw → ETL → chunks → trained → merged → GGUF
2. **Files archive after processing**: No duplicates, clear pipeline state
3. **Idempotent**: Re-running any step is safe
4. **Resumable**: Training auto-resumes from last chunk checkpoint
5. **Auditable**: All processed files preserved in `00-processed/`
6. **Closed-loop**: Evaluation feeds back into training via gap analysis

---

## LLM Execution Guide

This section is for an LLM agent (Claude Code, JADE, or similar) to execute the training pipeline. All steps require explicit human approval before execution.

### Prerequisites Check

Before starting any training work, verify the environment:

```bash
# 1. Check GPU availability
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

# 2. Check dependencies
python3 -c "import unsloth, trl, transformers, datasets; print('All training deps OK')"

# 3. Check llama.cpp for GGUF conversion
ls /home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/llama.cpp/llama-quantize

# 4. Check Ollama is running (for deployment)
ollama list
```

### Pipeline Execution Reference

All commands are executed from:
```
/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE
```

#### Step 1: ETL (safe, read-only preview first)
```bash
# ALWAYS preview first
python3 etl_pipeline.py --dry-run

# Execute ETL (moves files — ask human first)
# Input:  01-raw-data-lake/*.jsonl, *.json, *.md, *.txt
# Output: 02-ETL-data/jade_v10_etl_YYYYMMDD_HHMMSS.jsonl
# Effect: Source files archived to 00-processed/
python3 etl_pipeline.py
```

#### Step 2: Chunk (safe, read-only preview first)
```bash
# ALWAYS preview first
python3 chunk_data.py --dry-run

# Execute chunking (moves files — ask human first)
# Input:  02-ETL-data/jade_v10_etl_*.jsonl
# Output: 03-chunked-untrained/chunk_NNNN_Nk.jsonl + manifest.json
# Effect: Source files archived to 03-chunked-untrained/sources/
python3 chunk_data.py --shuffle
```

#### Step 3: Train (GPU-intensive, long-running)
```bash
# Check current status first (read-only, always safe)
python3 train_v10.py --status

# Preview what will train (read-only)
python3 train_v10.py --dry-run

# Train next chunk (GPU-intensive — ask human first)
# Input:  03-chunked-untrained/chunk_NNNN_Nk.jsonl
# Output: 3-jade-model-versions/v1.0/chunk_NNNN/final/ (LoRA checkpoint)
# Effect: Trained chunk moved to 04-trained-data/
# Time:   ~30-60 min per chunk depending on GPU
python3 train_v10.py

# Train ALL remaining chunks (very long — ask human first)
python3 train_v10.py --loop
```

#### Step 4: Merge (GPU-intensive, one-time)
```bash
# Preview (read-only)
python3 merge_model.py --dry-run

# Merge LoRA into full model (ask human first)
# Input:  3-jade-model-versions/v1.0/chunk_NNNN/final/ (latest checkpoint)
# Output: 3-jade-model-versions/v1.0/jade-v1.0-merged/
# Time:   ~10-20 min
python3 merge_model.py
```

#### Step 5: Convert to GGUF (CPU-intensive, one-time)
```bash
# Convert + quantize (ask human first)
# Input:  3-jade-model-versions/v1.0/jade-v1.0-merged/
# Output: 3-jade-model-versions/v1.0/jade-v1.0-q4_k_m.gguf
# Time:   ~15-30 min
python3 convert_gguf.py

# Deploy to Ollama
ollama create jade:v1.0 -f Modelfile
```

#### Step 6: Evaluate (GPU, read-only analysis)
```bash
# Quick benchmark (21 questions, ~10 min)
python3 eval_bridge.py --latest --quick

# Full benchmark (65 questions, ~30 min)
# Output: 4-GP-CLARIFY/3-results/bridge_YYYYMMDD_HHMMSS/full_results.json
python3 eval_bridge.py --latest
```

#### Step 7: Feedback (safe, generates new training data)
```bash
# Preview gaps (read-only)
python3 feedback_loop.py --latest --dry-run

# Export gap training data (ask human first)
# Output: 01-raw-data-lake/eval-gaps/gaps_YYYYMMDD.jsonl
python3 feedback_loop.py --latest --export
```

### Decision Matrix for LLM Agents

| Action | Safe to Run? | Needs Approval? | Notes |
|--------|-------------|-----------------|-------|
| `--dry-run` on any step | Yes | No | Read-only preview |
| `--status` on training | Yes | No | Read-only status check |
| `etl_pipeline.py` | Moves files | Yes | Archives raw data |
| `chunk_data.py` | Moves files | Yes | Archives ETL data |
| `train_v10.py` | GPU, long | Yes | ~30-60 min per chunk |
| `train_v10.py --loop` | GPU, very long | Yes | Hours for all chunks |
| `merge_model.py` | GPU, writes model | Yes | ~10-20 min |
| `convert_gguf.py` | CPU, writes model | Yes | ~15-30 min |
| `ollama create` | Deploys model | Yes | Replaces active model |
| `eval_bridge.py` | GPU, read-only | Yes (GPU use) | ~10-30 min |
| `feedback_loop.py --export` | Writes data | Yes | Writes to raw-data-lake |
| `train_v10.py --reset` | Destructive | **Always ask** | Deletes all progress |

### Common LLM Agent Workflows

**"Check training progress"** (safe, no approval needed):
```bash
python3 train_v10.py --status
```

**"Run the full pipeline on new data"** (needs approval at each step):
```bash
python3 etl_pipeline.py --dry-run       # Preview
# → Ask human to approve
python3 etl_pipeline.py                  # Execute ETL
python3 chunk_data.py --dry-run          # Preview
# → Ask human to approve
python3 chunk_data.py --shuffle          # Execute chunking
python3 train_v10.py --dry-run           # Preview
# → Ask human to approve
python3 train_v10.py --loop              # Train all chunks
```

**"Evaluate current model and fix weak areas"** (needs approval):
```bash
python3 eval_bridge.py --latest --quick  # Quick benchmark
python3 feedback_loop.py --latest --dry-run  # Preview gaps
# → Ask human to approve export
python3 feedback_loop.py --latest --export   # Generate gap data
# → Re-enter pipeline with ETL
```

---

## File Locations

| Purpose | Absolute Path |
|---------|---------------|
| Raw input | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE/01-raw-data-lake/` |
| Cleaned data | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE/02-ETL-data/` |
| Training chunks | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE/03-chunked-untrained/` |
| Trained chunks | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE/04-trained-data/` |
| Archive | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE/00-processed/` |
| Model checkpoints | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/3-jade-model-versions/v1.0/` |
| Merged model | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/3-jade-model-versions/v1.0/jade-v1.0-merged/` |
| GGUF output | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/3-jade-model-versions/v1.0/jade-v1.0-q4_k_m.gguf` |
| Eval results | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/4-GP-CLARIFY/3-results/` |
| Rank classifier | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/1-GP-GLUE/rank-training-data/` |
| llama.cpp | `/home/jimmie/linkops-industries/GP-copilot/GP-SAGEMAKER/llama.cpp/` |
