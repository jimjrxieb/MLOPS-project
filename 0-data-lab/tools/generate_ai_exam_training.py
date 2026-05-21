#!/usr/bin/env python3
"""
AI exam Q&A → BERU training data converter.

Parses mock exam question files from 0-data-lab/seclab-findings/ and converts
to ChatML BERU training examples. Two formats handled:
  1. Simple Q:/A: pairs (top section of file)
  2. Structured exam blocks: Question N / Correct answer / Explanation /
     Overall explanation / Domain

BERU needs AI engineering literacy to audit AI systems under AI RMF and 800-53.
These Q&As are framed as technical background a GRC analyst must understand —
not to build systems, but to ask the right audit questions.

Usage:
    python3 tools/generate_ai_exam_training.py --file seclab-findings/genl-examtips.txt
    python3 tools/generate_ai_exam_training.py --file seclab-findings/genl-examtips.txt --dry-run
"""

import json
import re
import argparse
from pathlib import Path

_DATA_LAB = Path(__file__).resolve().parent.parent
_REPO_ROOT = _DATA_LAB.parents[1]
OUTPUT_DIR = _DATA_LAB.parent / "1-FineTuning-Pipeline" / "01-raw-data-lake"

BERU_SYSTEM = (
    "You are BERU, a GRC analyst specializing in NIST 800-53 Rev 5 and NIST AI RMF / "
    "AI 600-1 audits. You assess AI systems, document findings with dual citations, and "
    "produce POA&M items, SSP narratives, and CISO briefings. You do not build or fix "
    "systems — you audit and document them. When asked about AI engineering concepts, "
    "explain them clearly and connect them to the governance implications: what risk does "
    "this introduce, what control applies, what an auditor should verify."
)

# Concepts that map to specific AI RMF / 800-53 controls — used to enrich answers
GOVERNANCE_HOOKS = {
    "epoch": "Training stability and convergence behavior are relevant to AI RMF MANAGE-2.2 (model testing) and SI-10 (input validation) if training is automated.",
    "model evaluation": "Evaluation methodology is directly audited under AI RMF MEASURE-2.5 and NIST 800-53 SA-11 (developer testing). Holdout sets, metrics, and eval frequency must be documented.",
    "foundation model": "Foundation model use is a supply chain risk. AI RMF GOVERN-6.1 and NIST 800-53 SR-3 require documenting third-party model provenance, licensing, and known limitations.",
    "fine-tun": "Fine-tuning changes model behavior. AI RMF MANAGE-1.3 requires re-evaluation after any fine-tuning. NIST 800-53 SA-9 applies if a vendor fine-tunes on your data.",
    "tokeniz": "Tokenization choices affect how the model handles sensitive input. PII in prompts may persist through tokenization artifacts — relevant to SC-28 and AI RMF MAP-1.5.",
    "attention": "Attention mechanisms determine what context the model weighs. Interpretability of attention weights is relevant to AI RMF MEASURE-2.9 (explainability).",
    "positional encoding": "Positional encoding affects sequence handling. Long-context inputs that exceed the encoding range can cause silent degradation — a model reliability risk under AI RMF MANAGE-2.2.",
    "zero-shot": "Zero-shot use means the model was not validated on your specific task. AI RMF MEASURE-2.6 requires task-specific evaluation before deployment.",
    "few-shot": "Few-shot prompting is an in-context learning technique. Prompt content is not trained away — sensitive few-shot examples persist in the context window. Relevant to SC-28.",
    "chain-of-thought": "CoT prompting exposes intermediate reasoning, which can be audited for bias or factual errors. Relevant to AI RMF MEASURE-2.9.",
    "rag": "RAG introduces a retrieval dependency. The knowledge base is an attack surface — prompt injection and retrieval poisoning are relevant to AI RMF MAP-5.2 and SI-10.",
    "transfer learning": "Transferred weights carry the biases and capabilities of the source task. AI RMF GOVERN-6.1 requires documenting what the base model was trained on and its known failure modes.",
    "knowledge distillation": "Distillation compresses a model but may compress in biases. The student model's behavior must be independently evaluated — not assumed equivalent to the teacher.",
    "generative ai": "Generative AI output is inherently non-deterministic. AI RMF GOVERN-1.7 requires documenting this and informing stakeholders of hallucination risk.",
    "a/b testing": "A/B testing is a deployment validation method. AI RMF MANAGE-3.2 requires production monitoring and comparison. Biased randomization invalidates the test.",
    "system message": "System messages define model behavior constraints. They are a governance control — document them as a configuration artifact under CM-6 and AI RMF MANAGE-1.1.",
}


def governance_note(question: str, answer: str) -> str:
    """Return a relevant governance hook if the concept matches a known mapping."""
    combined = (question + " " + answer).lower()
    for keyword, note in GOVERNANCE_HOOKS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', combined):
            return note
    return ""


def clean_explanation(text: str) -> str:
    """Strip exam-platform artifacts from explanation text."""
    text = re.sub(r'\s*For support or reporting issues.*?(?:\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*include Question ID:.*?(?:\n|$)', '', text, flags=re.IGNORECASE)
    return text.strip()


def qa_to_chatml(question: str, answer: str, domain: str = "Data Science") -> dict:
    """Wrap a Q&A pair in BERU ChatML format with governance framing."""
    user_msg = (
        f"As part of an AI system audit, I need to understand the following concept "
        f"from a governance and risk perspective.\n\n"
        f"Domain: {domain}\n\n"
        f"Question: {question.strip()}"
    )

    note = governance_note(question, answer)
    assistant_content = answer.strip()
    if note:
        assistant_content += f"\n\n**Governance note:** {note}"

    return {
        "messages": [
            {"role": "system", "content": BERU_SYSTEM},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_content},
        ]
    }


def parse_secai_exam(text: str) -> list[dict]:
    """
    Parse format used in secai-exam1.txt:
      Question N
      Skipped (or Correct / Incorrect)
      [question text]
      [wrong option]
      Correct answer
      [correct option text]
      [wrong options...]
      Overall explanation
      [explanation]
      Domain
      [N.N domain name]
    """
    examples = []
    blocks = re.split(r"(?:^|\n)Question \d+\n", text)

    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if len(lines) < 4:
            continue

        # Line 0: status (Skipped / Correct / Incorrect) — skip
        # Line 1+: question text until we hit short option lines or "Correct answer"
        status_line = lines[0].strip()

        # Find "Overall explanation" and "Domain" anchors
        overall_match = re.search(r"Overall explanation\n(.+?)(?:\nDomain|\Z)", block, re.DOTALL)
        domain_match = re.search(r"\nDomain\n(.+?)(?:\n|$)", block)

        if not overall_match:
            continue

        overall_explanation = clean_explanation(overall_match.group(1))
        domain = domain_match.group(1).strip() if domain_match else "AI Security"

        # Strip numeric prefix from domain (e.g. "4.0 AI Governance..." → kept as-is for context)
        domain = re.sub(r"^\d+\.\d+\s+", "", domain)

        # Extract correct answer: text on the line immediately after "Correct answer"
        correct_match = re.search(r"^Correct answer\n(.+?)$", block, re.MULTILINE)
        if not correct_match:
            continue
        correct_answer = correct_match.group(1).strip()

        # Extract question: lines after status, before options/Correct answer marker
        question_lines = []
        for i, line in enumerate(lines[1:], 1):
            stripped = line.strip()
            if not stripped or stripped in ("Skipped", "Correct", "Incorrect"):
                continue
            if stripped == "Correct answer":
                break
            # Primary stop signal: next line is "Explanation" or "Correct answer"
            # (cgrc format puts Explanation after each option)
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if next_line in ("Explanation", "Correct answer"):
                break
            # Fallback: short line after we already have question content (secai format)
            if question_lines and len(stripped) < 80:
                break
            question_lines.append(stripped)

        question = " ".join(question_lines).strip()

        if not question or len(question) < 30 or not correct_answer or len(overall_explanation) < 30:
            continue

        answer = f"{correct_answer}\n\n{overall_explanation}"
        examples.append(qa_to_chatml(question, answer, domain))

    return examples


def parse_cysa_exam(text: str) -> list[dict]:
    """
    Parse CySA+/CompTIA style format:
      Question N
      Correct | Incorrect
      [question text]
      Correct answer          ← only present when Incorrect
      [correct option]
      Your answer is correct | Your answer is incorrect
      [user's answer / other options]
      [more options...]
      Overall explanation
      OBJ. X.Y: [explanation]
      Domain
      N.N - Domain Name
    """
    examples = []
    blocks = re.split(r"(?:^|\n)Question \d+\n", text)

    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if len(lines) < 4:
            continue

        overall_match = re.search(r"Overall explanation\n(.+?)(?:\nDomain|\Z)", block, re.DOTALL)
        domain_match = re.search(r"\nDomain\n(.+?)(?:\n|$)", block)

        if not overall_match:
            continue

        overall_explanation = clean_explanation(overall_match.group(1))
        domain = domain_match.group(1).strip() if domain_match else "Cybersecurity"
        domain = re.sub(r"^\d+\.\d+\s+-?\s*", "", domain)

        # Correct answer: after "Correct answer" label (Incorrect questions)
        # or after "Your answer is correct" (Correct questions)
        correct_match = re.search(r"^Correct answer\n(.+?)$", block, re.MULTILINE)
        if not correct_match:
            correct_match = re.search(r"^Your answer is correct\n(.+?)$", block, re.MULTILINE)
        if not correct_match:
            continue
        correct_answer = correct_match.group(1).strip()

        # Question: line immediately after the status line
        status_line = lines[0].strip()
        question = lines[1].strip() if len(lines) > 1 else ""

        if not question or len(question) < 20 or not correct_answer or len(overall_explanation) < 30:
            continue

        answer = f"{correct_answer}\n\n{overall_explanation}"
        examples.append(qa_to_chatml(question, answer, domain))

    return examples


def detect_format(text: str) -> str:
    if re.search(r"^Q:", text, re.MULTILINE):   # simple Q:/A: pairs — unique to genl
        return "genl"
    if re.search(r"\nSkipped\n", text):
        return "secai"
    if re.search(r"\nYour answer is correct\n|\nYour answer is incorrect\n", text):
        return "cysa"
    return "genl"


def parse_simple_qa(text: str) -> list[dict]:
    """Parse Q:/A: format from the top of the file."""
    examples = []
    pattern = re.compile(r"Q:\s*(.+?)\nA:\s*(.+?)(?=\nQ:|\Z)", re.DOTALL)
    for m in pattern.finditer(text):
        q = m.group(1).strip()
        a = m.group(2).strip()
        if len(q) > 20 and len(a) > 20:
            examples.append(qa_to_chatml(q, a))
    return examples


def parse_structured_exam(text: str) -> list[dict]:
    """Parse the structured Question N / Correct answer / Overall explanation / Domain blocks."""
    examples = []

    # Split on "Question N" boundaries
    blocks = re.split(r"\nQuestion \d+\n", text)

    for block in blocks[1:]:  # Skip preamble before first Question N
        lines = block.strip().splitlines()
        if not lines:
            continue

        # Status line (Correct / Incorrect) is first
        # Question text follows

        # Extract question text: everything from line 2 up to the first answer option line
        # The question ends when we hit answer choices (short lines before Explanation)
        question_lines = []
        domain = "Data Science"
        overall_explanation = ""
        correct_answer = ""

        # Find "Correct answer" or "Correct selection" block
        correct_match = re.search(r"Correct answer\n(.+?)\nExplanation", block, re.DOTALL)
        if not correct_match:
            correct_match = re.search(r"Correct selection\n(.+?)\nExplanation", block, re.DOTALL)
        if correct_match:
            correct_answer = correct_match.group(1).strip()

        # Find Overall explanation
        overall_match = re.search(r"Overall explanation\n(.+?)(?:\nDomain|\Z)", block, re.DOTALL)
        if overall_match:
            overall_explanation = clean_explanation(overall_match.group(1))

        # Find domain
        domain_match = re.search(r"Domain\n(.+)", block)
        if domain_match:
            domain = domain_match.group(1).strip()

        # Extract question: skip the status line, collect until we hit an answer option pattern
        # Answer options are short lines (< 80 chars) followed by "Explanation"
        in_question = False
        for i, line in enumerate(lines):
            if i == 0:
                continue  # status line (Correct/Incorrect)
            if line in ("Correct", "Incorrect", "Your answer is correct",
                        "Your answer is incorrect", "Your selection is incorrect",
                        "Correct selection"):
                continue
            # Stop at answer choices — they're short and followed by Explanation
            if i > 1 and len(line.strip()) < 80 and i + 1 < len(lines) and lines[i + 1].startswith("Explanation"):
                break
            question_lines.append(line)

        question = " ".join(l.strip() for l in question_lines if l.strip())

        if not question or not correct_answer or not overall_explanation:
            continue
        if len(question) < 20 or len(overall_explanation) < 30:
            continue

        answer = f"{correct_answer}\n\n{overall_explanation}"
        examples.append(qa_to_chatml(question, answer, domain))

    return examples


def main():
    parser = argparse.ArgumentParser(description="Convert AI exam Q&A to BERU ChatML training data")
    parser.add_argument("--file", required=True, help="Input .txt exam file (relative to 0-data-lab/)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    src = _DATA_LAB / args.file
    if not src.exists():
        print(f"ERROR: {src} not found")
        return

    text = src.read_text(encoding="utf-8", errors="replace")

    fmt = detect_format(text)
    print(f"Format:  {fmt}")

    if fmt == "secai":
        candidates = parse_secai_exam(text)
    elif fmt == "cysa":
        candidates = parse_cysa_exam(text)
    else:
        simple = parse_simple_qa(text)
        structured = parse_structured_exam(text)
        candidates = simple + structured
        print(f"Parsed:  {len(simple)} simple Q/A + {len(structured)} structured blocks")

    # Deduplicate by question text
    seen = set()
    all_examples = []
    for ex in candidates:
        user_content = ex["messages"][1]["content"]
        # Key on the actual question text, not the boilerplate prefix
        q_start = user_content.find("Question: ")
        key = user_content[q_start:q_start + 100] if q_start != -1 else user_content[:100]
        if key not in seen:
            seen.add(key)
            all_examples.append(ex)

    stem = src.stem.replace(" ", "_").lower()
    output_file = OUTPUT_DIR / f"ai_exam_{stem}.jsonl"

    print(f"Source: {src}")
    print(f"Unique:  {len(all_examples)} examples after dedup")
    print(f"Output:  {output_file}")

    if args.dry_run:
        print("\n--- DRY RUN — first 2 examples ---")
        for ex in all_examples[:2]:
            print(json.dumps(ex, indent=2))
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nWrote {len(all_examples)} examples → {output_file}")
    print("Next: python3 -m pytest 8-tests/test_beru_data_quality.py -v")


if __name__ == "__main__":
    main()
