import json
from pathlib import Path
from typing import Dict

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CHUNKED_DIR = BASE_DIR / "03-chunked-untrained"
CLEANED_DIR = BASE_DIR / "03-chunked-cleaned" # Store cleaned files here

# Function to compute rank (same as curation script)
def compute_rank(user: str, assistant: str, metadata: Dict) -> str:
    score = 0
    meta_rank = metadata.get("rank", metadata.get("skill_level", "")).upper()
    if "S" in meta_rank: score += 90
    elif "B" in meta_rank: score += 75
    elif "C" in meta_rank: score += 50
    elif "D" in meta_rank: score += 30
    elif "E" in meta_rank: score += 10
    
    asst_len = len(assistant)
    if asst_len > 2000: score += 15
    elif asst_len > 1000: score += 10
    elif asst_len > 500: score += 5
    
    if "```" in assistant:
        score += 10
        if assistant.count("```") >= 4:
            score += 10
            
    multi_step_kws = ["step 1", "first", "second", "then", "finally", "remediation:", "analysis:"]
    if any(kw in assistant.lower() for kw in multi_step_kws):
        score += 5
        
    if "**" in assistant: score += 2
    if assistant.count("\n") > 10: score += 3
    
    if score >= 90: return "S"
    if score >= 75: return "B"
    if score >= 50: return "C"
    if score >= 20: return "D"
    return "E"

def strip_garbage():
    CLEANED_DIR.mkdir(exist_ok=True)
    chunk_files = sorted(CHUNKED_DIR.glob("chunk_*.jsonl"))
    
    overall_total = 0
    overall_cleaned = 0
    
    print(f"Cleaning {len(chunk_files)} chunks...")
    
    for chunk_file in chunk_files:
        infile = chunk_file
        outfile = CLEANED_DIR / chunk_file.name
        
        chunk_total = 0
        chunk_kept = 0
        
        with open(infile, 'r') as f_in, open(outfile, 'w') as f_out:
            for line in f_in:
                chunk_total += 1
                try:
                    data = json.loads(line)
                    messages = data.get("messages", [])
                    metadata = data.get("metadata", {})
                    
                    user_content = ""
                    assistant_content = ""
                    for msg in messages:
                        if msg["role"] == "user": user_content = msg["content"]
                        if msg["role"] == "assistant": assistant_content = msg["content"]
                    
                    rank = compute_rank(user_content, assistant_content, metadata)
                    
                    if rank != "E":
                        f_out.write(line)
                        chunk_kept += 1
                except Exception as e:
                    print(f"Error processing line in {chunk_file.name}: {e}")
        
        print(f"  {chunk_file.name}: {chunk_total:,} total, {chunk_total - chunk_kept:,} stripped, {chunk_kept:,} kept")
        overall_total += chunk_total
        overall_cleaned += chunk_kept

    print(f"\nOVERALL: {overall_total:,} total, {overall_total - overall_cleaned:,} stripped, {overall_cleaned:,} kept")

if __name__ == "__main__":
    strip_garbage()
