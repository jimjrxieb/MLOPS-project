import json
import re
import yaml
from pathlib import Path

TRAINING_DATA_PATH = Path("1-GP-GLUE/01-raw-data-lake/8b-jade/checkov_terraform_400.jsonl")

def validate_code_block(code_str, lang):
    if lang == "yaml":
        try:
            docs = list(yaml.safe_load_all(code_str))
            return True, None
        except yaml.YAMLError as e:
            return False, str(e)
    elif lang == "json":
        try:
            json.loads(code_str)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)
    elif lang == "hcl" or lang == "terraform":
        # Simple syntax check for HCL (brackets balance)
        if code_str.count('{') == code_str.count('}'):
            return True, None
        else:
            return False, "Unbalanced brackets in HCL"
    return True, None

def main():
    if not TRAINING_DATA_PATH.exists():
        print(f"Error: {TRAINING_DATA_PATH} not found.")
        return

    results = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "errors": []
    }

    print(f"Validating {TRAINING_DATA_PATH}...")
    
    with open(TRAINING_DATA_PATH, 'r') as f:
        for i, line in enumerate(f):
            results["total"] += 1
            try:
                example = json.loads(line)
                assistant_content = ""
                for msg in example.get("messages", []):
                    if msg["role"] == "assistant":
                        assistant_content = msg["content"]
                
                # Extract code blocks
                code_blocks = re.findall(r'```(\w+)\n(.*?)\n```', assistant_content, re.DOTALL)
                
                if not code_blocks:
                    results["invalid"] += 1
                    results["errors"].append({"index": i, "error": "No code blocks found"})
                    continue
                    
                for lang, block in code_blocks:
                    is_valid, error = validate_code_block(block, lang)
                    if is_valid:
                        results["valid"] += 1
                    else:
                        results["invalid"] += 1
                        results["errors"].append({
                            "index": i,
                            "error": f"{lang.upper()} Error: {error}"
                        })
            except Exception as e:
                results["invalid"] += 1
                results["errors"].append({"index": i, "error": f"JSON Parse Error: {str(e)}"})

    print("\nVALIDATION REPORT:")
    print(f"Total Examples Checked: {results['total']}")
    print(f"Valid Code Blocks:      {results['valid']}")
    print(f"Invalid/Missing Blocks: {results['invalid']}")
    
    if results["errors"]:
        print("\nTOP ERRORS:")
        for err in results["errors"][:10]:
            print(f"  Example {err['index']}: {err['error']}")
            
    if results["invalid"] == 0:
        print("\n✅ ALL CODE BLOCKS VALIDATED SUCCESSFULLY.")
    else:
        print(f"\n❌ FAILED: {results['invalid']} examples had issues.")

if __name__ == "__main__":
    main()
