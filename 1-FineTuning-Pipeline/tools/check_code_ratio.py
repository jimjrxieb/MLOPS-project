import json
from pathlib import Path

_PIPELINE_DIR = Path(__file__).resolve().parent.parent
path = _PIPELINE_DIR / "01-raw-data-lake" / "cks_training_batch_v1.jsonl"

with_yaml = 0
without_yaml = 0

with open(path, 'r') as f:
    for line in f:
        entry = json.loads(line)
        assistant_content = ""
        for msg in entry.get("messages", []):
            if msg["role"] == "assistant":
                assistant_content += msg["content"]
        if "```yaml" in assistant_content or "```rego" in assistant_content:
            with_yaml += 1
        else:
            without_yaml += 1

print(f"With YAML/Rego: {with_yaml}")
print(f"Without code:   {without_yaml}")
print(f"Code ratio:     {with_yaml}/{with_yaml + without_yaml} ({with_yaml/(with_yaml+without_yaml)*100:.1f}%)")
