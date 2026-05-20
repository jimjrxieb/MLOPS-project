# Katie 3B Training — Bookmark (2026-03-11)

## Current Training State

```
Version:          v1.1-3b
Base model:       unsloth/Llama-3.2-3B-Instruct
Chunks completed: 22 / 36
Examples trained:  166,827
Last merged:      chunk_0022_10k -> 3-model-registry/v1.1-3b/chunk_0022_10k/merged
```

## Remaining Chunks (14 left)

| Chunk | Examples | Size |
|-------|----------|------|
| chunk_0023_10k.jsonl | 10,000 | 55 MB |
| chunk_0024_10k.jsonl | 10,000 | 33 MB |
| chunk_0025_10k.jsonl | 10,000 | 26 MB |
| chunk_0026_10k.jsonl | 10,000 | 11 MB |
| chunk_0027_10k.jsonl | 10,000 | 18 MB |
| chunk_0028_10k.jsonl | 10,000 | 20 MB |
| chunk_0029_10k.jsonl | 10,000 | 18 MB |
| chunk_0030_10k.jsonl | 10,000 | 18 MB |
| chunk_0031_10k.jsonl | 10,000 | 28 MB |
| chunk_0032_10k.jsonl | 10,000 | 48 MB |
| chunk_0033_10k.jsonl | 10,000 | 49 MB |
| chunk_0034_10k.jsonl | 10,000 | 34 MB |
| chunk_0035_10k.jsonl | 8,010 | 19 MB |
| chunk_0036_10k.jsonl | 161 | 0.2 MB |
| **TOTAL REMAINING** | **128,171** | **~377 MB** |

## Summary

- **Done**: 22 chunks, 166,827 examples
- **Left**: 14 chunks, 128,171 examples
- **Grand total**: 36 chunks, ~295,000 examples
- **Progress**: 61% complete

## Start Training

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-MODEL-OPS/1-data-pipeline

# Resume from where we left off (chunk_0023 next)
python3 train_llama3b.py --loop

# Or single chunk
python3 train_llama3b.py --chunk chunk_0023_10k.jsonl

# Check status
python3 train_llama3b.py --status
```

## History

### Session 3 (2026-03-11)
- Updated bookmark with current state: 22/36 chunks done, 14 remaining

### Session 2 (2026-03-05 to 2026-03-10)
- Trained chunks 0001-0022 (166,827 examples)

### Session 1 (2026-03-03)
- Fixed orphaned training data (hidden .enhance_checkpoint.jsonl)
- Fixed ETL pipeline stale path (1-GP-GLUE -> 1-data-pipeline)
- Reset training state (previous 2 chunks trained against lost checkpoint)
- Renumbered all 36 chunks to clean format
- Merged special files into chunk_0036 (161 examples)
- Fixed dry-run infinite loop bug in train_llama3b.py
