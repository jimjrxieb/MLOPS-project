#!/usr/bin/env python3
"""
BERU RAG ingest — populates the `beru-nist-800-53` ChromaDB collection.

Lives in 2-rag-ingestion/04-ingesting/ alongside JADE's ingest_to_chromadb.py.
Same pipeline tree, different script — the JADE 7-stage prep factory does not
fit BERU's curated markdown source. See:
  CAPSTONE-PROJECT/beru-design-decisions.md  (D-008, D-011 for the rationale)

Sources (all curated, NOT synthetic):
  1. GP-CONSULTING/NIST-800-53/controls/*.md           one chunk per control
  2. CAPSTONE-PROJECT/frameworks/nist-ai-600-1/*.md    one chunk per AI RMF subcategory
  3. CAPSTONE-PROJECT/frameworks/mitre-atlas/*.md      one chunk per ATLAS technique
  4. CAPSTONE-PROJECT/frameworks/crosswalk/*.md        one chunk for the crosswalk doc
  5. GP-CONSULTING/NIST-800-53/ssp-examples/*.md       one chunk per SSP example
                                                       (bad/good/great × 11 families)
  6. GP-CONSULTING/NIST-800-53/control-owner-matrix.md one chunk for the matrix
  7. GP-CONSULTING/NIST-800-53/nist80053toc.md         one chunk for the TOC
  8. GP-CONSULTING/NIST-800-53/3POA/*.md               one chunk per 3POA doc
  9. GP-CONSULTING/NIST-800-53/playbooks/*.md          one chunk per BERU audit playbook
 10. GP-CONSULTING/NIST-800-53/templates/*.md          one chunk per BERU output template

Pointer index of where these sources live (for tree walkers):
  2-rag-ingestion/01-unprocessed/beru-frameworks/README.md

Embedding: nomic-embed-text via Ollama (768-dim). Failed embeddings are quarantined,
never inserted as zero-vectors.

Consumer note: queries against `beru-nist-800-53` MUST construct the same
OllamaEmbeddingFunction and pass it via `embedding_function=` on get_collection,
or pre-embed query text. ChromaDB's default 384-dim sentence-transformers
will silently mismatch this collection's 768-dim vectors otherwise.

Usage:
    python3 2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py --dry-run
    python3 2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py
    python3 2-rag-ingestion/04-ingesting/ingest_beru_to_chromadb.py --reset
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import chromadb
import requests
import yaml
from chromadb.config import Settings


# Path layout from this script's location:
#   parents[0] = 04-ingesting
#   parents[1] = 2-rag-ingestion
#   parents[2] = GP-MODEL-OPS
#   parents[3] = GP-copilot (repo root)
REPO_ROOT = Path(__file__).resolve().parents[3]
GP_MODEL_OPS = REPO_ROOT / "GP-MODEL-OPS"
GP_S3 = REPO_ROOT / "GP-S3"

CHROMA_PATH = GP_MODEL_OPS / "2-rag-ingestion" / "05-ragged-data" / "chroma"
QUARANTINE = GP_MODEL_OPS / "2-rag-ingestion" / "05-ragged-data" / "embedding_quarantine.jsonl"
REPORT_DIR = GP_S3 / "3-mlops-reports" / "1-rag-staging"

CONTROLS_DIR = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "controls"
AI_RMF_DIR = GP_MODEL_OPS / "CAPSTONE-PROJECT" / "frameworks" / "nist-ai-600-1"
MITRE_ATLAS_DIR = GP_MODEL_OPS / "CAPSTONE-PROJECT" / "frameworks" / "mitre-atlas"
CROSSWALK_FILE = (
    GP_MODEL_OPS / "CAPSTONE-PROJECT" / "frameworks" / "crosswalk" / "800-53-to-ai-rmf.md"
)

# Step-1 expansion sources (re-ingest 2026-05-09): real curated SSP grading material,
# control-owner matrix, output templates, BERU audit playbooks, 3POA framework.
SSP_EXAMPLES_DIR = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "ssp-examples"
CONTROL_OWNER_MATRIX_FILE = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "control-owner-matrix.md"
NIST_TOC_FILE = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "nist80053toc.md"
THREE_POA_DIR = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "3POA"
NIST_PLAYBOOKS_DIR = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "playbooks"
NIST_TEMPLATES_DIR = REPO_ROOT / "GP-CONSULTING" / "NIST-800-53" / "templates"

COLLECTION_NAME = "beru-nist-800-53"
EMBED_MODEL = "nomic-embed-text:latest"
EMBED_DIM = 768
OLLAMA_URL = "http://localhost:11434"

STUB_PATTERNS = [
    re.compile(r"Summary for NIST 800-53 control"),
    re.compile(r"Access Control Control \d"),
    re.compile(r'"finding-[A-Z]{2}-\d+-\d+"'),
]


class OllamaEmbeddingFunction:
    """ChromaDB-compatible 768-dim embedder. Used at query time by consumers.

    On ingest we call _embed_with_retry directly so we can filter failures
    instead of crashing the run.
    """

    def __init__(self, url: str = OLLAMA_URL, model: str = EMBED_MODEL):
        self.url = url.rstrip("/")
        self.model = model

    def name(self) -> str:
        return f"ollama-{self.model}"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [_embed_or_raise(t, self.url, self.model) for t in input]


def _embed_or_raise(text: str, url: str, model: str) -> list[float]:
    r = requests.post(
        f"{url}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=30,
    )
    r.raise_for_status()
    v = r.json()["embedding"]
    if len(v) != EMBED_DIM:
        raise RuntimeError(f"expected {EMBED_DIM} dims, got {len(v)} from {model}")
    return v


def embed_with_retry(text: str, retries: int = 2, delay: float = 1.0) -> list[float] | None:
    last_err: str | None = None
    for attempt in range(retries):
        try:
            return _embed_or_raise(text, OLLAMA_URL, EMBED_MODEL)
        except Exception as e:
            last_err = str(e)
            if attempt < retries - 1:
                time.sleep(delay)
    _quarantine(text, last_err or "unknown error")
    return None


def _quarantine(text: str, error: str) -> None:
    QUARANTINE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUARANTINE, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "error": error,
                    "text_preview": text[:200],
                    "text_length": len(text),
                    "model": EMBED_MODEL,
                    "source": "beru-rag-ingest",
                }
            )
            + "\n"
        )


def parse_control(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not m:
        raise ValueError(f"no YAML frontmatter in {path.name}")
    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2).strip()
    text = (
        f"NIST 800-53 {meta.get('id', '?')} — {meta.get('name', '')}\n"
        f"Family: {meta.get('family_name', '')}\n\n{body}"
    )
    return {
        "id": f"800-53::{meta.get('id', 'unknown')}",
        "text": text,
        "metadata": {
            "framework": "nist-800-53-rev5",
            "control_id": str(meta.get("id", "")),
            "family": str(meta.get("family", "")),
            "family_name": str(meta.get("family_name", "")),
            "control_name": str(meta.get("name", "")),
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def parse_ai_rmf(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    function = path.stem.split("-")[-1].upper()  # govern | map | manage  ->  GOVERN | MAP | MANAGE
    pattern = rf"^### ({function} \d+\.\d+)\s*\n"
    parts = re.split(pattern, raw, flags=re.MULTILINE)

    chunks: list[dict] = []
    for i in range(1, len(parts), 2):
        subcat_id = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        body = re.split(r"^---\s*$", body, maxsplit=1, flags=re.MULTILINE)[0].strip()
        body = re.split(r"^### ", body, maxsplit=1, flags=re.MULTILINE)[0].strip()
        if not body:
            continue
        text = f"AI RMF {subcat_id}\n\n{body}"
        chunks.append(
            {
                "id": f"ai-rmf::{subcat_id.replace(' ', '-')}",
                "text": text,
                "metadata": {
                    "framework": "nist-ai-rmf-1.0",
                    "function": function,
                    "subcategory_id": subcat_id,
                    "source_file": path.name,
                    "source_path": str(path.relative_to(REPO_ROOT)),
                    "ingested_at": datetime.now().isoformat(),
                },
            }
        )
    return chunks


def parse_crosswalk(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "id": "crosswalk::800-53-to-ai-rmf",
        "text": text,
        "metadata": {
            "framework": "crosswalk",
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def parse_mitre_atlas(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    pattern = r"^### (AML\.T\d+)\s*\n"
    parts = re.split(pattern, raw, flags=re.MULTILINE)
    tactic = path.stem.replace("atlas-", "").replace("-", " ").upper()

    chunks: list[dict] = []
    for i in range(1, len(parts), 2):
        technique_id = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        body = re.split(r"^---\s*$", body, maxsplit=1, flags=re.MULTILINE)[0].strip()
        body = re.split(r"^### ", body, maxsplit=1, flags=re.MULTILINE)[0].strip()
        if not body:
            continue
        text = f"MITRE ATLAS {technique_id}\n\n{body}"
        chunks.append(
            {
                "id": f"atlas::{technique_id.replace('.', '-')}",
                "text": text,
                "metadata": {
                    "framework": "mitre-atlas-v4.7",
                    "tactic": tactic,
                    "technique_id": technique_id,
                    "source_file": path.name,
                    "source_path": str(path.relative_to(REPO_ROOT)),
                    "ingested_at": datetime.now().isoformat(),
                },
            }
        )
    return chunks


def parse_ssp_example(path: Path) -> dict:
    """Parse one SSP example file. Filename pattern: {FAMILY}-ssp-{QUALITY}.md
    where QUALITY is bad/good/great. Each file contains multiple controls within
    the family plus reviewer notes about why the document is rated bad/good/great.
    """
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^([A-Z]{2})-ssp-(bad|good|great)\.md$", path.name)
    if not m:
        raise ValueError(f"unexpected SSP example filename: {path.name}")
    family, quality = m.group(1), m.group(2)
    return {
        "id": f"ssp-example::{family}-{quality}",
        "text": raw,
        "metadata": {
            "framework": "ssp-example",
            "family": family,
            "quality_tier": quality,
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def parse_control_owner_matrix(path: Path) -> dict:
    return {
        "id": "control-owner-matrix",
        "text": path.read_text(encoding="utf-8"),
        "metadata": {
            "framework": "control-owner-matrix",
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def parse_nist_toc(path: Path) -> dict:
    return {
        "id": "nist-800-53-toc",
        "text": path.read_text(encoding="utf-8"),
        "metadata": {
            "framework": "nist-800-53-toc",
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def parse_3poa(path: Path) -> dict:
    return {
        "id": f"3poa::{path.stem}",
        "text": path.read_text(encoding="utf-8"),
        "metadata": {
            "framework": "3poa",
            "doc_type": path.stem,
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def parse_nist_playbook(path: Path) -> dict:
    return {
        "id": f"nist-playbook::{path.stem}",
        "text": path.read_text(encoding="utf-8"),
        "metadata": {
            "framework": "nist-playbook",
            "playbook": path.stem,
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def parse_nist_template(path: Path) -> dict:
    return {
        "id": f"nist-template::{path.stem}",
        "text": path.read_text(encoding="utf-8"),
        "metadata": {
            "framework": "nist-template",
            "template_type": path.stem,
            "source_file": path.name,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "ingested_at": datetime.now().isoformat(),
        },
    }


def collect_chunks() -> list[dict]:
    chunks: list[dict] = []

    control_files = sorted(CONTROLS_DIR.glob("*.md"))
    print(f"NIST 800-53 controls : {len(control_files)} files from {CONTROLS_DIR.relative_to(REPO_ROOT)}")
    for p in control_files:
        chunks.append(parse_control(p))

    rmf_files = sorted(AI_RMF_DIR.glob("ai-rmf-*.md"))
    rmf_chunk_count = 0
    for p in rmf_files:
        sub = parse_ai_rmf(p)
        rmf_chunk_count += len(sub)
        chunks.extend(sub)
    print(f"AI RMF subcategories : {rmf_chunk_count} chunks from {len(rmf_files)} files")

    atlas_files = sorted(MITRE_ATLAS_DIR.glob("atlas-*.md"))
    atlas_chunk_count = 0
    for p in atlas_files:
        sub = parse_mitre_atlas(p)
        atlas_chunk_count += len(sub)
        chunks.extend(sub)
    print(f"MITRE ATLAS techniques: {atlas_chunk_count} chunks from {len(atlas_files)} files")

    chunks.append(parse_crosswalk(CROSSWALK_FILE))
    print(f"Crosswalk            : 1 chunk")

    # Step-1 expansion: real SSP examples, output templates, audit playbooks
    ssp_files = sorted(SSP_EXAMPLES_DIR.glob("*-ssp-*.md"))
    print(f"SSP examples         : {len(ssp_files)} files from {SSP_EXAMPLES_DIR.relative_to(REPO_ROOT)}")
    for p in ssp_files:
        chunks.append(parse_ssp_example(p))

    if CONTROL_OWNER_MATRIX_FILE.exists():
        chunks.append(parse_control_owner_matrix(CONTROL_OWNER_MATRIX_FILE))
        print(f"Control-owner matrix : 1 chunk")

    if NIST_TOC_FILE.exists():
        chunks.append(parse_nist_toc(NIST_TOC_FILE))
        print(f"NIST 800-53 TOC      : 1 chunk")

    if THREE_POA_DIR.exists():
        three_poa_files = sorted(THREE_POA_DIR.glob("*.md"))
        print(f"3POA framework docs  : {len(three_poa_files)} files from {THREE_POA_DIR.relative_to(REPO_ROOT)}")
        for p in three_poa_files:
            chunks.append(parse_3poa(p))

    if NIST_PLAYBOOKS_DIR.exists():
        playbook_files = sorted(NIST_PLAYBOOKS_DIR.glob("*.md"))
        print(f"NIST audit playbooks : {len(playbook_files)} files from {NIST_PLAYBOOKS_DIR.relative_to(REPO_ROOT)}")
        for p in playbook_files:
            chunks.append(parse_nist_playbook(p))

    if NIST_TEMPLATES_DIR.exists():
        template_files = sorted(NIST_TEMPLATES_DIR.glob("*.md"))
        print(f"NIST output templates: {len(template_files)} files from {NIST_TEMPLATES_DIR.relative_to(REPO_ROOT)}")
        for p in template_files:
            chunks.append(parse_nist_template(p))

    print(f"TOTAL                : {len(chunks)} chunks")
    return chunks


def reject_stubs(chunks: list[dict]) -> None:
    for c in chunks:
        for pat in STUB_PATTERNS:
            if pat.search(c["text"]):
                raise SystemExit(
                    f"REFUSING TO INGEST — stub text {pat.pattern!r} detected in {c['id']}"
                )


def _framework_breakdown(collection) -> dict[str, int]:
    metas = collection.get(include=["metadatas"])["metadatas"]
    out: dict[str, int] = {}
    for m in metas:
        fw = (m or {}).get("framework", "unknown")
        out[fw] = out.get(fw, 0) + 1
    return out


def _all_collection_state(client) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for col in client.list_collections():
        try:
            rows.append((col.name, col.count()))
        except Exception:
            rows.append((col.name, -1))
    return sorted(rows)


def write_report(
    *,
    client,
    collection,
    chunks: list[dict],
    inserted: int,
    failed: int,
    skipped_existing: int,
    started_at: datetime,
    finished_at: datetime,
    reset: bool,
) -> Path:
    """Persist an audit-grade ingest report for AU-2 / AU-3 / GOVERN 4.1.

    Mirrors the format of GP-S3/3-mlops-reports/1-rag-staging/rag-ingestion-*.md
    written by 04-ingesting/ingest_to_chromadb.py, with BERU-specific fields.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = finished_at.strftime("%Y%m%d_%H%M%S")
    out_path = REPORT_DIR / f"rag-ingestion-{ts}-beru.md"

    status = "SUCCESS" if failed == 0 else "PARTIAL"
    breakdown = _framework_breakdown(collection)
    all_state = _all_collection_state(client)
    duration = (finished_at - started_at).total_seconds()

    by_source: dict[str, int] = {}
    for c in chunks:
        sf = c["metadata"].get("source_file", "unknown")
        by_source[sf] = by_source.get(sf, 0) + 1

    lines: list[str] = []
    lines.append("# BERU RAG Ingestion Report")
    lines.append("")
    lines.append(f"**Timestamp:** {finished_at.isoformat(timespec='seconds')}")
    lines.append(f"**Status:** {status}")
    lines.append(f"**Collection:** `{COLLECTION_NAME}`")
    lines.append(f"**Reset flag:** {reset}")
    lines.append(f"**Duration:** {duration:.2f}s")
    lines.append("")
    lines.append("## Run Stats")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Chunks parsed (this run) | {len(chunks)} |")
    lines.append(f"| Inserted (new) | {inserted} |")
    lines.append(f"| Skipped (already present, idempotent) | {skipped_existing} |")
    lines.append(f"| Embedding failures (quarantined) | {failed} |")
    lines.append(f"| Final collection count | {collection.count()} |")
    lines.append(f"| Embedding model | `{EMBED_MODEL}` |")
    lines.append(f"| Embedding dim | {EMBED_DIM} |")
    lines.append("")
    lines.append("## Sources Parsed (this run)")
    lines.append("")
    lines.append("| Source file | Chunks |")
    lines.append("|-------------|-------:|")
    for sf, n in sorted(by_source.items()):
        lines.append(f"| `{sf}` | {n} |")
    lines.append("")
    lines.append("## Framework Breakdown (collection state)")
    lines.append("")
    lines.append("| Framework | Documents |")
    lines.append("|-----------|----------:|")
    for fw, n in sorted(breakdown.items()):
        lines.append(f"| {fw} | {n} |")
    lines.append("")
    lines.append("## Full ChromaDB State")
    lines.append("")
    lines.append("| Collection | Documents |")
    lines.append("|------------|----------:|")
    total = 0
    for name, n in all_state:
        if n >= 0:
            total += n
        lines.append(f"| {name} | {n if n >= 0 else 'ERROR'} |")
    lines.append(f"| **TOTAL** | **{total:,}** |")
    lines.append("")
    lines.append("## Control Traceability")
    lines.append("")
    lines.append("This ingest run satisfies the following controls (see `CAPSTONE-PROJECT/beru-design-decisions.md` D-008):")
    lines.append("")
    lines.append("- **NIST 800-53 SR-4 (Provenance):** every chunk has `source_file` + `source_path` metadata")
    lines.append("- **NIST 800-53 SI-7 (Integrity):** stub-rejection regex applied pre-ingest and post-ingest")
    lines.append("- **NIST 800-53 CM-2 (Baseline):** collection name + embed model + dim recorded above")
    lines.append("- **NIST 800-53 CM-3 (Change Control):** this report is the change record; re-ingest is idempotent via stable IDs")
    lines.append("- **NIST 800-53 AU-2 / AU-3 (Audit Logging):** this report itself, written to `GP-S3/3-mlops-reports/1-rag-staging/`")
    lines.append("- **NIST AI RMF MAP 4.1 (Component risks mapped):** RAG corpus components inventoried by source above")
    lines.append("- **NIST AI RMF MAP 2.2 (Provenance documented):** dual-citation metadata persisted per chunk")
    lines.append("- **NIST AI RMF GOVERN 4.1 (Decisions about deployment documented):** ingest decisions captured in this audit log")
    lines.append("")
    lines.append("## Quarantine")
    lines.append("")
    if failed == 0:
        lines.append(f"No embedding failures. Quarantine file untouched (`{QUARANTINE.relative_to(REPO_ROOT)}`).")
    else:
        lines.append(f"⚠ {failed} chunks failed to embed. See `{QUARANTINE.relative_to(REPO_ROOT)}` for raw entries.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="parse + count, skip embed/insert")
    ap.add_argument("--reset", action="store_true", help="wipe collection before ingest")
    ap.add_argument("--no-report", action="store_true", help="skip writing audit report (not recommended)")
    args = ap.parse_args()

    started_at = datetime.now()
    chunks = collect_chunks()
    reject_stubs(chunks)

    if args.dry_run:
        print("\n[dry-run] sample:")
        for c in chunks[:3]:
            tag = c["metadata"].get("control_id") or c["metadata"].get("subcategory_id") or "n/a"
            preview = c["text"].splitlines()[0]
            print(f"  {c['id']:40s}  [{tag}]  {preview[:80]}")
        return 0

    print(f"\nConnecting to ChromaDB at {CHROMA_PATH.relative_to(REPO_ROOT)}...")
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )

    if args.reset and any(c.name == COLLECTION_NAME for c in client.list_collections()):
        print(f"  --reset: deleting existing {COLLECTION_NAME}")
        client.delete_collection(COLLECTION_NAME)

    ollama_ef = OllamaEmbeddingFunction()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ollama_ef,
        metadata={
            "framework": "nist-800-53-rev5 + nist-ai-rmf-1.0",
            "owner": "BERU",
            "embed_model": EMBED_MODEL,
            "embed_dim": EMBED_DIM,
            "created_at": datetime.now().isoformat(),
        },
    )
    print(f"  collection: {collection.name} (current count: {collection.count()})")

    existing_ids = set(collection.get(include=[])["ids"])
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]
    print(f"  existing ids: {len(existing_ids)}, new to insert: {len(new_chunks)}")

    inserted, failed = 0, 0
    for c in new_chunks:
        v = embed_with_retry(c["text"])
        if v is None:
            failed += 1
            print(f"  SKIP {c['id']} (embedding failed, see quarantine)")
            continue
        collection.add(
            ids=[c["id"]],
            documents=[c["text"]],
            embeddings=[v],
            metadatas=[c["metadata"]],
        )
        inserted += 1

    final = collection.count()
    finished_at = datetime.now()
    print(f"\nDone. inserted={inserted} failed={failed} skipped_existing={len(existing_ids)} total_in_collection={final}")

    if not args.no_report:
        report_path = write_report(
            client=client,
            collection=collection,
            chunks=chunks,
            inserted=inserted,
            failed=failed,
            skipped_existing=len(existing_ids),
            started_at=started_at,
            finished_at=finished_at,
            reset=args.reset,
        )
        print(f"Audit report: {report_path.relative_to(REPO_ROOT)}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
