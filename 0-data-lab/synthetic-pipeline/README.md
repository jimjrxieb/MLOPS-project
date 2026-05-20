# Synthetic Data Pipeline — JADE/Katie Training Factory

Automated training data generation system that converts operational security workflows into high-quality training examples for JADE/Katie fine-tuning.

## Architecture

```
GP-PROJECTS/{instance}/{slot}/jsa/inbox/  ←── real JSA findings
              ↓
    pipeline.py (5 phases)
    ┌─────────────────────────────────────────┐
    │  1. Discover  →  _discover_sources()    │
    │  2. Generate  →  generator.py           │
    │  3. Merge     →  _merge_batches()       │
    │  4. Validate  →  quality_validator.py   │
    │  5. Save      →  JSONL + stats + report │
    └─────────────────────────────────────────┘
              ↓
    1-local-pipeline/01-raw-data-lake/   ←── training corpus
```

### Components

| File | Role |
|------|------|
| `models.py` | Data models: TrainingExample, TrainingBatch, GenerationConfig |
| `templates.py` | Scenario templates: trivy, gitleaks, kubescape, escalation, sast |
| `generator.py` | Converts JSA findings + scan/fix/escalation logs to training examples |
| `quality_validator.py` | Scores examples on instruction clarity, input completeness, output quality, metadata |
| `pipeline.py` | 5-phase orchestrator: discover → generate → merge → validate → save |
| `crew/` | CrewAI crew wrapping the pipeline (see below) |

## Quick Start

### Direct (no LLM overhead)

```bash
cd GP-MODEL-OPS/0-data-lab/synthetic-pipeline

# Generate from all instances
python3 -m pipeline

# Generate from one instance
python3 -m pipeline --instance 01-instance

# Custom quality threshold
python3 -m pipeline --min-quality 70.0 --max-examples 500
```

### Via CrewAI Crew (adds quality analysis + coverage report)

```bash
# CLI
python3 -m crew.main run --min-quality 60 --max-examples 500

# Single instance
python3 -m crew.main run --instance 01-instance

# API server (port 8001)
python3 -m crew.main serve

# curl
curl -X POST http://localhost:8001/run/synthetic-pipeline \
  -H 'Content-Type: application/json' \
  -d '{"min_quality_score": 60, "max_examples": 500}'
```

### Programmatic Usage

```python
from synthetic_pipeline.pipeline import TrainingPipeline

# Run full pipeline
pipeline = TrainingPipeline()
result = pipeline.run_full_pipeline()

print(f"Generated {result['total_examples']} training examples")
print(f"Quality pass rate: {result['quality_stats']['pass_rate']:.1f}%")
```

## Data Models

### TrainingExample

```python
from training_scenarios import TrainingExample

example = TrainingExample(
    instruction="Fix this SQL injection vulnerability detected by bandit.",
    input="""Scanner: bandit
CWE: CWE-89 (SQL Injection)
File: app.py
Line: 42

Vulnerable Code:
```python
query = "SELECT * FROM users WHERE id = " + user_id
```""",
    output="""**Fix:**
Use parameterized queries:

```python
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

**Rank:** D - Automated fix (70-90% confidence)""",
    metadata={
        "domain": "sast",
        "task_type": "fix-execution",
        "skill_level": "D-rank"
    }
)
```

### Skill Levels

Training examples are classified by automation level:

| Rank | Automation | Examples |
|------|------------|----------|
| **E** | 95-100% | Hardcoded secrets, missing resource limits |
| **D** | 70-90% | SQL injection, XSS, dependency CVEs |
| **C** | 40-70% | Network policies, multi-file IaC changes |
| **B** | 20-40% | Architecture changes, compliance gaps |
| **A** | 5-20% | Org-wide policy design |
| **S** | 0-5% | Zero-trust architecture, incident response |

## Scenario Templates

Templates define how to convert operational data into training examples.

### Available Templates

```python
from training_scenarios import list_templates

print(list_templates())
# ['trivy-scan', 'gitleaks-secret', 'kubescape-policy',
#  'escalation-b-rank', 'sql-injection', 'xss-fix',
#  'cis-benchmark', 'executive-report']
```

### Using Templates

```python
from training_scenarios import get_template

# Get Trivy scan template
template = get_template("trivy-scan")

# Generate example from operational data
data = {
    "scanner": "trivy",
    "severity": "HIGH",
    "package": "lodash",
    "vulnerability_id": "CVE-2024-1234",
    "current_version": "4.17.0",
    "fixed_version": "4.17.21",
    "description": "Prototype pollution vulnerability",
    "action": "UPGRADE",
    "fix_command": "npm update lodash@4.17.21",
    "rank": "D",
    "rank_justification": "Automated dependency upgrade"
}

example = template.generate_example(data)
```

### Custom Templates

```python
from training_scenarios import ScenarioTemplate, Domain, TaskType, SkillLevel

template = ScenarioTemplate(
    name="custom-scan",
    description="Custom scanner template",
    domain=Domain.KUBERNETES,
    task_type=TaskType.SCAN_ANALYSIS,
    skill_level=SkillLevel.C_RANK,
    instruction_template="Analyze this {scanner} finding.",
    input_template="Scanner: {scanner}\nSeverity: {severity}",
    output_template="Analysis: {analysis}\nAction: {action}",
    required_fields=["scanner", "severity", "analysis", "action"]
)
```

## Training Data Generator

Converts operational logs into training examples.

### Generate from Slot

```python
from training_scenarios import TrainingGenerator

generator = TrainingGenerator()

# Generate from specific slot
batch = generator.generate_from_slot("02-instance", "slot-2")

print(f"Generated {len(batch.examples)} examples")
print(batch.get_stats())

# Save to file
generator.save_batch(batch, Path("training.jsonl"))
```

### Data Sources

The generator reads from:
- **Scan logs**: `GP-BEDROCK-AGENTS/jadeSecureAgent/target-slot-logs/{instance}/scans/`
- **Fix logs**: `GP-BEDROCK-AGENTS/jadeSecureAgent/target-slot-logs/{instance}/fixes/`
- **Escalations**: `GP-PROJECTS/{instance}/{slot}/escalations/`
- **Workflow states**: `GP-PROJECTS/{instance}/{slot}/workflow/`

### Generation Process

```python
# 1. Read scan results
scans = read_scans(instance, slot)

# 2. Apply templates
examples = []
for scan in scans:
    template = get_template_for_scanner(scan["scanner"])
    example = template.generate_example(scan)
    examples.append(example)

# 3. Validate quality
passing = [e for e in examples if validate(e).score >= 70]

# 4. Deduplicate
unique = deduplicate(passing)

# 5. Output
save_to_jsonl(unique, "training.jsonl")
```

## Quality Validation

Ensures training examples meet quality standards.

### Validate Examples

```python
from training_scenarios import QualityValidator

validator = QualityValidator()

metrics = validator.validate(example)

print(f"Overall score: {metrics.overall_score}/100")
print(f"Quality level: {metrics.quality_level.value}")

if metrics.issues:
    print("Issues:", metrics.issues)

if metrics.suggestions:
    print("Suggestions:", metrics.suggestions)
```

### Quality Metrics

Each example is scored on:
- **Instruction Clarity** (25%): Clear, actionable, security-focused
- **Input Completeness** (25%): Structured data with context
- **Output Quality** (35%): Well-formatted, with reasoning and examples
- **Metadata Completeness** (15%): Domain, task type, skill level

### Batch Validation

```python
result = validator.batch_validate(examples, min_quality_score=70.0)

print(f"Pass rate: {result['stats']['pass_rate']:.1f}%")
print(f"Avg score: {result['stats']['avg_score']:.1f}/100")
print(f"Excellent: {len(result['by_quality']['excellent'])}")
print(f"Good: {len(result['by_quality']['good'])}")
```

### Validate Training File

```python
from training_scenarios import validate_training_file

result = validate_training_file("training.jsonl", min_quality_score=70.0)

print(f"Total: {result['total']}")
print(f"Passed: {len(result['passed'])}")
print(f"Failed: {len(result['failed'])}")

# Review failed examples
for item in result['failed']:
    print(f"\nFailed example:")
    print(f"Issues: {item['metrics'].issues}")
    print(f"Score: {item['metrics'].overall_score}")
```

## Pipeline Orchestration

End-to-end automation of training data generation.

### Run Full Pipeline

```bash
# Generate from all instances
python3 -m pipeline

# Output:
# ============================================================
# JADE Training Data Generation Pipeline
# ============================================================
# Phase 1: Discovering operational data sources...
# Found 6 slots with operational data
#
# Phase 2: Generating training examples...
#   Processing 01-instance/slot-1... ✓ 45 examples
#   Processing 02-instance/slot-2... ✓ 127 examples
#   ...
#
# Phase 3: Merging batches...
# Total examples: 512
#
# Phase 4: Validating quality...
#   Pass rate: 87.3%
#   Avg score: 78.4/100
#   Excellent: 156
#   Good: 291
#
# Phase 5: Saving training data...
#   Saved to: training_20260101_120000.jsonl
# ============================================================
```

### Custom Pipeline

```python
from training_scenarios import TrainingPipeline, GenerationConfig

config = GenerationConfig(
    min_quality_score=70.0,
    max_examples_per_batch=1000,
    include_metadata=True,
    deduplicate=True,
    shuffle=True
)

pipeline = TrainingPipeline(config=config)
result = pipeline.run_full_pipeline()
```

### Instance-Specific Generation

```python
# Generate only for specific instance
result = pipeline.run_for_instance("02-instance")

print(f"Generated {result['total_examples']} examples for 02-instance")
```

## Output Formats

### JSONL Format

```jsonl
{"instruction": "...", "input": "...", "output": "...", "metadata": {...}}
{"instruction": "...", "input": "...", "output": "...", "metadata": {...}}
```

### Alpaca Format

```python
example.to_alpaca()
# {
#   "instruction": "Fix this SQL injection vulnerability",
#   "input": "Scanner: bandit\nFile: app.py\n...",
#   "output": "**Fix:** Use parameterized queries..."
# }
```

### ChatML Format

```python
example.to_chatml()
# [
#   {"role": "system", "content": "You are JADE..."},
#   {"role": "user", "content": "Fix this SQL injection..."},
#   {"role": "assistant", "content": "**Fix:** Use parameterized..."}
# ]
```

## CrewAI Crew

The `crew/` directory wraps the pipeline with a 3-agent CrewAI crew. The existing pipeline code is unchanged — the crew adds LLM-driven quality analysis and coverage reporting on top.

```
crew/
├── tools.py              # 5 @tool functions wrapping pipeline phases
├── agents.py             # 3 agents: Orchestrator, Quality Auditor, Report Generator
├── main.py               # FastAPI (POST /run/synthetic-pipeline) + CLI
├── requirements.txt      # crewai[tools]==0.80.0 + fastapi stack
└── crews/
    └── pipeline_crew.py  # Sequential crew: generate → validate → report
```

### What the crew adds over bare pipeline

| Pipeline alone | + Crew |
|---------------|--------|
| pass/fail counts | Quality Auditor reasons about failure patterns |
| raw stats JSON | Coverage report: actual vs. target rank distribution |
| no recommendation | Go/No-Go for corpus inclusion |
| no gap analysis | Concrete actions for next run to fix coverage gaps |

### Agent roles

| Agent | Tools | Decision |
|-------|-------|----------|
| Pipeline Orchestrator | `discover_sources`, `run_full_pipeline` | Runs discovery + generation |
| Quality Auditor | `validate_output_file`, `get_batch_stats` | APPROVE / REVIEW / REJECT |
| Report Generator | `get_batch_stats` | Go / No-Go / Conditional |

### Import note

The package dir is named `synthetic-pipeline` (hyphen), so `tools.py` registers it under the alias `synthetic_pipeline` via `importlib.util` before importing. This is transparent to callers — import via the crew, not directly from the hyphen-named dir.

---

## Integration with Training Pipeline

### Directory Structure

```
GP-MODEL-OPS/
├── 0-data-lab/
│   └── synthetic-pipeline/     # This module
│       ├── models.py
│       ├── templates.py
│       ├── generator.py
│       ├── quality_validator.py
│       ├── pipeline.py
│       └── crew/               # CrewAI crew
└── 1-local-pipeline/
    └── 01-raw-data-lake/       # Output from this pipeline drops here
        ├── training_YYYYMMDD_HHMMSS.jsonl
        ├── training_YYYYMMDD_HHMMSS.stats.json
        └── training_YYYYMMDD_HHMMSS.report.md
```

### Next Steps After Generation

1. **Review Quality**:
   ```bash
   python3 -m crew.main run --min-quality 70
   # crew Quality Auditor issues APPROVE/REVIEW/REJECT with gap analysis
   ```

2. **Merge with Corpus**:
   ```bash
   cat 1-local-pipeline/01-raw-data-lake/training_*.jsonl >> master_corpus.jsonl
   ```

3. **Create Training Chunks**:
   ```bash
   python3 1-local-pipeline/chunk_data.py
   ```

4. **Fine-tune**:
   ```bash
   python3 1-local-pipeline/train_v11.py
   ```

## CLI Commands

### Direct pipeline

```bash
# From GP-MODEL-OPS/0-data-lab/synthetic-pipeline/
python3 pipeline.py                          # all instances
python3 pipeline.py --instance 01-instance   # one instance
python3 pipeline.py --min-quality 70.0 --max-examples 1000
python3 pipeline.py --output-dir /path/to/output
```

### Crew CLI (adds quality report + go/no-go)

```bash
python3 -m crew.main run                     # all instances
python3 -m crew.main run --instance 01-instance
python3 -m crew.main run --min-quality 70 --max-examples 500
python3 -m crew.main serve                   # FastAPI on port 8001
```

### Validate Quality

```bash
# Validate training file
python3 -c "from training_scenarios import validate_training_file; \
    result = validate_training_file('training.jsonl', 70.0); \
    print(f\"Pass rate: {result['stats']['pass_rate']:.1f}%\")"
```

### List Templates

```bash
python3 -c "from training_scenarios import list_templates; \
    print('Available templates:'); \
    for t in list_templates(): print(f'  - {t}')"
```

## Configuration

### GenerationConfig

```python
from training_scenarios import GenerationConfig

config = GenerationConfig(
    min_quality_score=50.0,           # Minimum quality threshold
    max_examples_per_batch=1000,      # Max examples per batch
    include_metadata=True,             # Include metadata in output
    deduplicate=True,                  # Remove duplicates
    shuffle=True,                      # Shuffle examples

    # Length constraints
    min_instruction_length=10,
    max_instruction_length=500,
    min_output_length=50,
    max_output_length=5000,

    # Skill level distribution (percentages)
    skill_distribution={
        "E-rank": 0.05,   # 5%
        "D-rank": 0.30,   # 30%
        "C-rank": 0.40,   # 40%
        "B-rank": 0.20,   # 20%
        "A-rank": 0.04,   # 4%
        "S-rank": 0.01    # 1%
    }
)
```

## Statistics and Reporting

### Batch Statistics

```python
batch = generator.generate_from_slot("02-instance", "slot-2")
stats = batch.get_stats()

print(stats)
# {
#   "batch_id": "training_02-instance_slot-2_20260101_120000",
#   "total_examples": 127,
#   "by_domain": {
#     "dependencies": 45,
#     "secrets": 32,
#     "kubernetes": 28,
#     "sast": 22
#   },
#   "by_task_type": {
#     "fix-execution": 89,
#     "scan-analysis": 28,
#     "escalation-decision": 10
#   },
#   "by_skill_level": {
#     "D-rank": 89,
#     "C-rank": 28,
#     "B-rank": 10
#   }
# }
```

### Pipeline Reports

After running the pipeline, a markdown report is generated:

```markdown
# Training Data Generation Report

**Batch ID:** training_pipeline_20260101_120000
**Generated:** 2026-01-01 12:00:00 UTC
**Total Examples:** 512

## Distribution

### By Domain
| Category | Count |
|----------|-------|
| dependencies | 187 |
| secrets | 124 |
| kubernetes | 98 |
| sast | 103 |

### By Task Type
| Category | Count |
|----------|-------|
| fix-execution | 389 |
| scan-analysis | 98 |
| escalation-decision | 25 |

### By Skill Level
| Category | Count |
|----------|-------|
| D-rank | 356 |
| C-rank | 121 |
| B-rank | 35 |
```

## Best Practices

### 1. Quality Over Quantity

Focus on high-quality examples (70+ score) rather than large quantities of poor examples.

### 2. Balanced Distribution

Maintain skill level distribution matching real-world automation levels:
- 60% C-rank (requires approval)
- 30% D-rank (automated with logging)
- 10% B-rank (human review)

### 3. Regular Generation

Run pipeline after each major JSA cycle to capture fresh operational data.

### 4. Review Failed Examples

Regularly review failed validation examples to improve templates:

```python
result = validator.batch_validate(examples, 70.0)
for item in result['failed']:
    print(f"Issues: {item['metrics'].issues}")
    print(f"Suggestions: {item['metrics'].suggestions}")
```

### 5. Deduplicate Across Runs

Maintain a master corpus and deduplicate before fine-tuning:

```bash
# Merge all training files
cat training_*.jsonl > master_corpus.jsonl

# Deduplicate
python3 -c "
import json
from pathlib import Path

seen = set()
with open('master_corpus.jsonl') as f_in, open('deduped.jsonl', 'w') as f_out:
    for line in f_in:
        if line.strip():
            data = json.loads(line)
            key = data['instruction'] + data['input']
            if key not in seen:
                seen.add(key)
                f_out.write(line)
"
```

## Troubleshooting

### No Examples Generated

**Problem**: Pipeline generates 0 examples

**Solutions**:
1. Check if operational data exists:
   ```bash
   ls -la GP-BEDROCK-AGENTS/jadeSecureAgent/target-slot-logs/*/scans/
   ```

2. Verify slot workflow directories exist:
   ```bash
   ls -la GP-PROJECTS/*/slot-*/workflow/
   ```

3. Lower quality threshold:
   ```python
   config = GenerationConfig(min_quality_score=30.0)
   ```

### Low Quality Scores

**Problem**: Most examples fail validation

**Solutions**:
1. Review template structure
2. Ensure operational logs have complete data
3. Add more context to templates
4. Review validator threshold settings

### Template Not Found

**Problem**: `KeyError: Template 'xyz' not found`

**Solutions**:
1. List available templates:
   ```python
   from training_scenarios import list_templates
   print(list_templates())
   ```

2. Create custom template or use existing one

## Examples

### Complete Workflow

```python
from training_scenarios import (
    TrainingPipeline,
    GenerationConfig,
    validate_training_file
)
from pathlib import Path

# 1. Configure pipeline
config = GenerationConfig(
    min_quality_score=70.0,
    max_examples_per_batch=1000,
    deduplicate=True,
    shuffle=True
)

# 2. Run pipeline
pipeline = TrainingPipeline(config=config)
result = pipeline.run_full_pipeline()

# 3. Validate output
output_file = result['output_file']
validation = validate_training_file(output_file, min_quality_score=70.0)

print(f"Generated: {result['total_examples']} examples")
print(f"Pass rate: {validation['stats']['pass_rate']:.1f}%")
print(f"Avg score: {validation['stats']['avg_score']:.1f}/100")

# 4. Review quality distribution
for quality_level, items in validation['by_quality'].items():
    print(f"{quality_level}: {len(items)}")
```

## Feeds Into

`1-local-pipeline/` → `chunk_data.py` → `train_v11.py` → `3-model-registry/`

Output JSONL drops to `1-local-pipeline/01-raw-data-lake/`. ETL picks it up on the next run.
