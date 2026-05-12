# M4 — Agentic Systems

> **Goal:** Build a reasoning loop that takes a scanner file as input and produces a POA&M as output — without you in the middle.
> **Build:** `BERU-AI/agent.py` — LangGraph agentic loop, end-to-end.
> **Gate:** `python3 BERU-AI/agent.py --input sample-trivy.json` produces a POA&M and CISO summary.

---

## What "Agentic" Actually Means

A regular LLM call is: you send a prompt, you get a response. One step.

An agentic system is: the model decides what to do next, calls tools, processes results, then decides again — in a loop until the task is complete. Multiple steps, multiple tool calls, dynamic routing.

**The analogy:** A regular LLM call is asking a consultant one question and getting one answer. An agentic system is hiring that consultant for a day — they figure out what questions to ask, run the analysis, write the report, and hand it back. You set the goal; they manage the steps.

For BERU specifically:
- **Input**: raw Trivy JSON output
- **Steps**: parse scanner → identify affected controls → retrieve control text (RAG) → generate findings → route B/S-rank to human queue → produce POA&M + CISO summary
- **Output**: structured artifacts on disk

Without an agentic loop, you'd have to call each step manually. The agent orchestrates the pipeline.

---

## Concept 1 — LangGraph

LangGraph is the framework for building agentic loops. It models the workflow as a directed graph: nodes are functions (steps), edges are transitions (what happens after each step).

### StateGraph — the core concept

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# State = what gets passed between nodes
class BeruState(TypedDict):
    scanner_input: str          # raw scanner output
    findings: List[dict]        # parsed findings
    mapped_findings: List[dict] # findings + NIST controls
    rag_context: str            # retrieved control text
    poam: str                   # generated POA&M
    hitl_pending: List[str]     # queue IDs of B/S findings

# Nodes = functions that transform state
def parse_scanner(state: BeruState) -> BeruState:
    # Calls ToolOutputParser
    ...

def map_to_controls(state: BeruState) -> BeruState:
    # Calls NISTMapper
    ...

def retrieve_context(state: BeruState) -> BeruState:
    # Calls ChromaDB with the relevant control IDs
    ...

def generate_findings(state: BeruState) -> BeruState:
    # Calls LLM (Ollama/beru:v1.0) with control text in context
    ...

def route_by_rank(state: BeruState) -> BeruState:
    # Calls HITLRouter — B/S go to queue, E/D/C continue
    ...

def produce_outputs(state: BeruState) -> BeruState:
    # Writes POA&M, CISO summary, calls EvidencePackager
    ...

# Graph = wiring the nodes together
graph = StateGraph(BeruState)
graph.add_node("parse_scanner", parse_scanner)
graph.add_node("map_to_controls", map_to_controls)
graph.add_node("retrieve_context", retrieve_context)
graph.add_node("generate_findings", generate_findings)
graph.add_node("route_by_rank", route_by_rank)
graph.add_node("produce_outputs", produce_outputs)

graph.set_entry_point("parse_scanner")
graph.add_edge("parse_scanner", "map_to_controls")
graph.add_edge("map_to_controls", "retrieve_context")
graph.add_edge("retrieve_context", "generate_findings")
graph.add_edge("generate_findings", "route_by_rank")
graph.add_edge("route_by_rank", "produce_outputs")
graph.add_edge("produce_outputs", END)

beru_agent = graph.compile()
```

### Conditional routing
Not all edges are unconditional. Sometimes you need to branch: if a finding is B-rank, go to the HITL queue. If it's C-rank, go straight to output.

```python
def rank_router(state: BeruState) -> str:
    # Returns the name of the next node
    has_blocked = len(state["hitl_pending"]) > 0
    return "notify_human" if has_blocked else "produce_outputs"

graph.add_conditional_edges(
    "route_by_rank",
    rank_router,
    {
        "notify_human": "notify_human",
        "produce_outputs": "produce_outputs",
    }
)
```

**The analogy:** LangGraph is an airport's routing system. Each security checkpoint is a node. Your ticket (state) passes through. Conditional edges are the "business class goes left, economy goes right" signs. The state carries everything you learned at each checkpoint forward.

---

## Concept 2 — Playbook-as-Brain

From `architecture-laws.md`:
> Agents don't think — playbooks think. Agents execute.

BERU's "thinking" is not in `agent.py`. It's in the playbooks:
- `GP-CONSULTING/NIST-800-53/controls/` — what evidence to gather per control
- `CAPSTONE-PROJECT/frameworks/` — how to classify AI RMF findings
- `BERU-AI/config/scanner_mappings.yaml` — which scanner maps to which controls

The agent reads these at runtime. When a new control is added or a scanner mapping changes, you update the playbook — not the Python code. The agent automatically picks it up.

This is why `BERU` "does not improvise" — it follows the playbook routing, not its own reasoning about what to do next.

---

## Concept 3 — Tool Use

In LangGraph, "tools" are Python functions the agent can call. Unlike regular function calls, tools are called by the LLM during its reasoning — the model decides when to call them based on the task.

```python
from langchain_core.tools import tool

@tool
def retrieve_nist_control(control_id: str) -> str:
    """Retrieve the full text of a NIST 800-53 control from ChromaDB."""
    collection = get_beru_collection()
    results = collection.query(
        query_texts=[control_id],
        n_results=1,
    )
    return results["documents"][0][0] if results["documents"] else "Control not found"

@tool
def check_hitl_required(rank: str) -> bool:
    """Returns True if this rank requires human review before output."""
    return rank in ("B", "S")
```

The model sees the tool's docstring, decides when to call it, and uses the return value in its next step.

**For BERU's level of task:** we don't need the LLM to decide which tools to call — the graph structure defines the sequence. Tool use in BERU is for the LLM inside each node (e.g., "retrieve this specific control"), not for dynamic tool selection.

---

## Concept 4 — Human-in-the-Loop (HITL)

BERU has a hardcoded rule: B/S-rank findings don't leave the pipeline without human approval. This is MANAGE-2.2 from the AI RMF.

The `HITLRouter` we built in M0 (`BERU-AI/tools/hitl_router.py`) handles this. In the agent:

```python
def route_by_rank(state: BeruState) -> BeruState:
    router = HITLRouter()
    pending = []

    for finding in state["mapped_findings"]:
        result = router.route(finding)
        if result["status"] == "pending_human":
            pending.append(result["queue_id"])
            # Finding is queued — NOT in the output yet
        # E/D/C findings continue to produce_outputs

    state["hitl_pending"] = pending
    return state
```

When the agent finishes, if `hitl_pending` is non-empty, the agent exits cleanly but prints:

```
BERU: 2 findings queued for human review (B-rank)
Review and approve with: python3 agent.py --approve <queue_id>
```

The pipeline does not hang waiting for approval. It completes the E/D/C findings and stops. The human reviews the queue at their own schedule. This is the correct pattern — don't block production on human latency.

---

## Concept 5 — State Management

Every node receives the full state dict and returns the full state dict with modifications. Nothing is global. This is what makes LangGraph pipelines testable — you can inject a test state and inspect what each node produces.

```python
# Testing a node in isolation
test_state = BeruState(
    scanner_input='{"vulnerabilities": [{"id": "CVE-2024-1234"}]}',
    findings=[],
    mapped_findings=[],
    rag_context="",
    poam="",
    hitl_pending=[],
)
result = parse_scanner(test_state)
assert len(result["findings"]) == 1
assert result["findings"][0]["scanner"] == "trivy"
```

---

## Troubleshooting M4

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent runs infinitely | No `END` node reached | Check conditional edges — one branch must always reach `END` |
| State lost between nodes | Node returns new dict instead of updating state | Return `{**state, "findings": new_findings}` — always include all state keys |
| LLM calls not using RAG context | Context not in the prompt | Check `generate_findings` node — `rag_context` from state must be in the user message |
| B-rank findings appearing in output | HITL not wired in | Check `route_by_rank` calls `HITLRouter.route()` before findings go to `produce_outputs` |
| `ImportError: No module named 'langgraph'` | Not installed | `pip install langgraph langchain-core langchain-ollama` |
| Agent produces same output regardless of input | Scanner parsing not working | Debug `parse_scanner` node first — print the finding list before mapping |
| Slow (30+ seconds per finding) | Ollama responding slowly | BERU 3B is CPU-viable but adding GPU helps. Check `nvidia-smi` if available. On CPU expect 5-15s per response (faster than the 8B JADE path). |

---

## What You Build

`BERU-AI/agent.py` — a LangGraph StateGraph with 6 nodes wired together:

```
parse_scanner → map_to_controls → retrieve_context → generate_findings → route_by_rank → produce_outputs
```

Each node uses the tools already built:
- `ToolOutputParser` (core/) → node 1
- `NISTMapper` (core/) → node 2
- ChromaDB query (M2) → node 3
- Ollama `beru:v1.0` call → node 4
- `HITLRouter` (tools/) → node 5
- `EvidencePackager` (tools/) → node 6

**The demo test:**
```bash
python3 BERU-AI/agent.py \
  --input GP-S3/6-seclab-reports/cybersec-evidence/sample-trivy.json \
  --output /tmp/beru-output/
```

Expected output:
```
/tmp/beru-output/
├── findings.jsonl       ← structured findings
├── poam.md             ← POA&M draft
├── ciso-briefing.md    ← CISO summary
└── evidence.zip        ← packaged artifacts
```

**3PAO question this answers:** "How does BERU decide what to do at each step?"
Your answer: "BERU follows a defined LangGraph StateGraph — 6 nodes, fixed sequence, no improvisation. The nodes call tools that read playbooks. The routing logic for B/S-rank is architecturally enforced by HITLRouter before any output is written."

---

## Control Traceability

> When an auditor asks "what stops BERU from approving a risk acceptance it shouldn't?" — point here.

**NIST 800-53:**

| Control | What it maps to in M4 | Audit answer |
|---------|----------------------|--------------|
| **PM-9** — Risk Management Strategy | E/D/C/B/S rank system is risk management policy encoded in software — each rank has a defined automation level | "The rank system is documented in `architecture-laws.md`. E/D are automated. C requires BERU confidence score. B/S are human-only. This is not a convention — it's enforced by the router." |
| **CP-2** — Contingency Planning | LangGraph `StateGraph` defines explicit failure states and error transitions — BERU does not silently continue on error | "The LangGraph workflow has explicit error nodes. A failed tool call routes to a defined error state, not to a retry loop that could produce garbage output." |
| **IR-10** — Integrated Information Security Analysis Team | B/S-rank routing to HITLRouter creates a human review queue — the analyst is the team, not optional | "B/S-rank findings are never auto-approved. `HITLRouter.route()` writes them to `pending.jsonl` and returns `pending_human`. The pipeline blocks until a human approves." |

**NIST AI RMF:**

| Subcategory | What it maps to | Audit answer |
|-------------|----------------|--------------|
| **MANAGE-2.2** — Human oversight mechanisms are in place | `HITLRouter` is the architectural enforcement of HITL — no bypass path exists for B/S-rank | "MANAGE-2.2 is implemented by `HITLRouter`. The code has no path that auto-approves a B or S-rank finding. Tests verify this: `test_b_rank_is_blocked` and `test_s_rank_is_blocked`." |
| **GOVERN-5.1** — Organizational policies for AI risk | The rank system (E/D/C/B/S) encodes the organization's risk tolerance as code — policy is not a document, it's the router | "The rank boundaries are in `architecture-laws.md` and enforced in `HITLRouter._RANK_ROUTING`. Changing the policy means changing the code, which triggers code review." |
