# M0 — Python for AI Engineering

> **Goal:** Write Python that a senior engineer would merge without comments.
> **Build:** Harden `tools/gap-to-poam.py` — type hints, validation, CLI, 80% coverage.
> **Gate:** `mypy` reports zero errors. `pytest` hits ≥80% coverage.

---

## The Problem This Module Solves

You can write Python that works. The question is: would it work six months from now when someone else touches it? Would it tell you clearly what went wrong when it fails? Can someone use it from the command line without reading the source?

AI engineering is not data science. Data science lives in notebooks. AI engineering ships code that runs in production, handles bad inputs gracefully, and gets reviewed by other engineers before it merges. This module is the gap between "it runs on my machine" and "I'd put this on a resume."

---

## Concept 1 — Type Hints

### What they are
Type hints tell Python (and tools like `mypy`) what kind of value a variable holds or a function expects. They don't change runtime behavior — they're documentation that can be automatically checked.

```python
# Without type hints — works, but fragile
def map_finding(finding):
    return finding["controls"]

# With type hints — clear contract
from typing import Dict, List, Any

def map_finding(finding: Dict[str, Any]) -> List[str]:
    return finding["controls"]
```

### The analogy
Electrical schematics use standardized symbols so any electrician can read them. Type hints are the same thing for code. A function signature without types is a handwritten note. A function signature with types is a schematic — unambiguous, verifiable, machine-readable.

### What to look for in this repo
Open `BERU-AI/core/nist_mapper.py`. Every function has typed arguments and return types. The `map_finding` method returns `Dict[str, Any]` — that contract is what lets the triage engine use its output without guessing.

### How to check it
```bash
pip install mypy
mypy BERU-AI/core/nist_mapper.py
# Good: "Success: no issues found in 1 source file"
# Bad: error: Argument 1 to "map_finding" has incompatible type "str"
```

### Common errors
- `error: Name "Optional" is not defined` → add `from typing import Optional`
- `error: Need type annotation for "x"` → add `: List[str] = []` not just `= []`
- `error: Item "None" of "Optional[str]" has no attribute "upper"` → check for None before calling methods

---

## Concept 2 — pathlib

### What it is
`pathlib.Path` is the modern way to work with file paths. It's an object, not a string, so you get methods instead of string manipulation.

```python
# Old way — fragile, platform-specific
import os
path = os.path.join("GP-MODEL-OPS", "BERU-AI", "config", "scanner_mappings.yaml")
if os.path.exists(path):
    with open(path) as f:
        ...

# pathlib way — clean, cross-platform, composable
from pathlib import Path
path = Path("GP-MODEL-OPS") / "BERU-AI" / "config" / "scanner_mappings.yaml"
if path.exists():
    content = path.read_text()
```

### What to look for in this repo
Every tool in `BERU-AI/core/` uses `Path(__file__).parent.parent / "config"` to find the config directory relative to the source file. That means the code works regardless of where you run it from — no hardcoded absolute paths, no `os.getcwd()` hacks.

### Common errors
- `TypeError: unsupported operand type(s) for /: 'str' and 'str'` → you're using `/` on two strings, not Path objects. Wrap the first one: `Path("dir") / "subdir"`
- `FileNotFoundError` when path looks right → check `path.resolve()` to see the absolute path being used

---

## Concept 3 — Pydantic for Structured Data

### What it is
Pydantic is a library that validates data against a schema and gives you typed Python objects back. Instead of `dict["field"]` and hoping the field exists, you get `obj.field` and a clear error if it's missing.

```python
from pydantic import BaseModel
from typing import Optional, List

class BeruFinding(BaseModel):
    finding_id: str
    control: str
    status: str  # "PASS" | "PARTIAL" | "FAIL"
    rank: str    # "E" | "D" | "C" | "B" | "S"
    ai_context: bool = False
    ai_rmf_subcategories: List[str] = []

# This validates at creation — bad data raises immediately
finding = BeruFinding(
    finding_id="F-001",
    control="AC-6",
    status="FAIL",
    rank="C",
)
```

### The analogy
Pydantic is a bouncer at the door. Regular dicts let anything in — wrong types, missing fields, typos. Pydantic checks ID before you get in. The error happens at the door (input validation), not when you try to use the data five functions later.

### What to look for
The `7-data-schemas/` directory has JSON Schema files for the data contracts. Pydantic is the Python equivalent — same idea, Python-native.

---

## Concept 4 — pytest

### What it is
pytest is the test runner. You write functions that start with `test_` and call `assert`. pytest finds them and runs them.

```python
# 8-tests/test_beru_tools.py — real example from this repo
def test_b_rank_is_blocked(self):
    result = self.router.route(self._finding("B"))
    assert result["status"] == "pending_human"
    assert result["auto_ok"] is False
    assert result["queue_id"] is not None
```

### Key patterns you need

**Fixtures** — setup code that runs before each test:
```python
def setup_method(self):
    self.router = HITLRouter(queue_dir=tempfile.mkdtemp())
```

**Parametrize** — run the same test with different inputs:
```python
@pytest.mark.parametrize("rank,expected", [
    ("E", "auto"), ("D", "auto"), ("C", "auto"),
    ("B", "pending_human"), ("S", "pending_human"),
])
def test_rank_routing(self, rank, expected):
    result = self.router.route({"rank": rank, "finding_id": "x"})
    assert result["status"] == expected
```

### Running the tests in this repo
```bash
cd GP-MODEL-OPS
python3 -m pytest 8-tests/test_beru_tools.py -v       # one file
python3 -m pytest 8-tests/ -v                          # all tests
python3 -m pytest 8-tests/ -v --tb=short               # short traceback on failure
python3 -m pytest 8-tests/ --cov=BERU-AI/core          # coverage report
```

### Common errors
- `ModuleNotFoundError: No module named 'core'` → look at the top of the test file. It does `sys.path.insert(0, str(BERU_PATH))` to add BERU-AI to the import path. Do the same.
- `FAILED test_x — assert False` → read the output. pytest shows you the actual vs expected value.
- `fixture 'tmpdir' not found` → use `tempfile.mkdtemp()` directly or `tmp_path` (built-in pytest fixture)

---

## Concept 5 — argparse (CLI Tools)

### What it is
`argparse` turns a Python script into a proper command-line tool with `--flag` arguments, help text, and input validation.

```python
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Convert BERU gap analysis to POA&M"
    )
    parser.add_argument("--input", required=True, help="Path to gap analysis JSON")
    parser.add_argument("--output", default="poam.md", help="Output file path")
    parser.add_argument("--system", default="unknown", help="System name")
    args = parser.parse_args()

    # args.input, args.output, args.system are now validated strings
    run(args.input, args.output, args.system)

if __name__ == "__main__":
    main()
```

Usage after this: `python3 gap-to-poam.py --input findings.json --output poam.md`

Without `main()` and `if __name__ == "__main__"`: the script runs top to bottom when imported, which breaks tests.

---

## Troubleshooting Checklist for M0

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `mypy` reports 40 errors | No types anywhere | Start with return types on every function, then arguments |
| Tests fail with import errors | Wrong sys.path | Check how `test_beru_core.py` adds BERU-AI to path — copy that pattern |
| Coverage under 50% | Only happy path tested | Add tests for missing input, wrong type, empty list |
| `TypeError: 'NoneType'` deep in call stack | No input validation | Validate at the boundary — check for None/empty before processing |
| argparse errors on `--help` | Missing `help=` strings | Add `help="..."` to every `add_argument` call |

---

## What You Build

Look at `tools/gap-to-poam.py`. Run `mypy` on it. It will complain. Fix every complaint. Then:

1. Add a `main()` function with `argparse` — `--input`, `--output`, `--system`
2. Add input validation — what happens if the file doesn't exist? If the JSON is malformed?
3. Write tests that cover: happy path, missing file, malformed input, empty findings list
4. Run `pytest --cov` and get to 80%

**3PAO question this answers:** "Show me a production-quality Python tool from your portfolio."
Your answer: `gap-to-poam.py` — typed, validated, tested, CLI-ready.

---

## Control Traceability

> When an auditor asks "why did you use mypy?" or "how was the CLI validated?" — point here.

**NIST 800-53:**

| Control | What it maps to in M0 | Audit answer |
|---------|----------------------|--------------|
| **SA-15** — Development Process, Standards, and Tools | `mypy --strict` enforces type safety as a mandatory development standard | "We run mypy strict on every commit. Zero type errors is the gate before any code ships." |
| **SA-11** — Developer Testing and Evaluation | `pytest` + 80% coverage gate on `gap-to-poam.py` | "Developer testing is enforced by a coverage gate. Below 80% the build fails." |
| **SI-10** — Information Input Validation | `argparse` with `is_dir()` check, `try/except OSError` on file reads, `sys.exit(1)` on bad input | "All inputs are validated at the system boundary. Bad path → explicit error and non-zero exit. No silent failures." |
| **CM-3** — Configuration Change Control | Type annotations make function contracts explicit and machine-verifiable — interface changes are detectable | "Type hints enforce interface contracts. A caller passing the wrong type is caught before runtime." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **GOVERN-1.7** — Processes for AI risk management are in place | The test suite and mypy checks are the automated enforcement layer for code quality across the BERU codebase | "Our development process enforces type safety and test coverage on every AI system component. This is documented in M0 and enforced in CI." |
