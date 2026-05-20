"""
Four agents for the RAG ingestion prep crew.

Design rule: each agent has one job and at most 2 tools.
Deterministic work (stages 1-4, routing rules) lives in collectors.py, not here.
"""
import os
from crewai import Agent
from .tools import (
    get_repair_items,
    override_quality_gate,
    get_unlabeled_items,
    apply_labels,
    get_routing_decisions,
    override_routing,
    get_pipeline_stats,
)

LLM_MODEL = os.getenv("CREWAI_LLM", "ollama/llama3.1")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def quality_reviewer() -> Agent:
    return Agent(
        role="RAG Quality Gatekeeper",
        goal=(
            "Review every item in the REPAIR batch and decide whether to promote it "
            "to PASS (worth ingesting despite partial issues) or demote it to FAIL "
            "(too corrupted or low-value to ingest). Call override_quality_gate for "
            "each item with a one-sentence rationale."
        ),
        backstory=(
            "You are a senior data quality engineer. The sanitize pipeline flagged "
            "these chunks as partially corrupted or borderline — they passed JSON repair "
            "but had issues. You know that a chunk with a minor encoding problem can still "
            "be a high-value NIST finding, while a chunk that's just a log dump with "
            "a fixed trailing comma is garbage. Context is everything. Review the content, "
            "not just the flag."
        ),
        tools=[get_repair_items, override_quality_gate],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )


def semantic_labeler() -> Agent:
    return Agent(
        role="Semantic Domain Classifier",
        goal=(
            "Classify every item in the unlabeled batch with the correct domain, "
            "content type, difficulty, and tags. Call apply_labels for each item. "
            "Domain must be one or more of: kubernetes, terraform, opa, docker, "
            "cloud, security, compliance, general. "
            "Type must be one or more of: documentation, troubleshooting, policy, "
            "example, fix, configuration, best-practice, vulnerability, tutorial."
        ),
        backstory=(
            "You are an expert in cloud-native security and infrastructure. The "
            "automated labeling pipeline (ontology lookup + regex patterns) couldn't "
            "classify these chunks — they don't match known keywords but they clearly "
            "belong somewhere. Read the content carefully and assign the most precise "
            "labels you can. Good labels make RAG retrieval accurate; vague labels "
            "send everything to jade-general and hurt JADE's answers."
        ),
        tools=[get_unlabeled_items, apply_labels],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )


def routing_validator() -> Agent:
    return Agent(
        role="Collection Routing Auditor",
        goal=(
            "Review all routing decisions and fix misroutes. Focus especially on: "
            "(1) items going to jade-general — the catch-all that should rarely be used; "
            "(2) items marked SKIP — are they genuinely low-value or was the rule wrong? "
            "Call override_routing for every item you reroute with a clear reason."
        ),
        backstory=(
            "You know every ChromaDB collection: jade-projects (scan results), "
            "jade-sessions (Claude sessions), jade-troubleshooting (debug guides), "
            "jade-consulting (playbooks/cheatsheets), jade-policy-as-code (rego), "
            "jade-operational (JSA operational training), jade-domain-sme (SME content), "
            "jade-nist-800-53 (controls + compliance), jade-general (everything else). "
            "A rego policy in jade-general is a routing bug. A NIST control narrative "
            "in jade-projects is a routing bug. Fix them."
        ),
        tools=[get_routing_decisions, override_routing],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )


def pipeline_reporter() -> Agent:
    return Agent(
        role="RAG Coverage Analyst",
        goal=(
            "Synthesize the full run statistics into a markdown coverage report. "
            "Include: files discovered/processed/failed, quality gate distribution, "
            "agent override counts and rationale summary, collection routing table "
            "(how many chunks go to each collection), and a go/no-go recommendation "
            "for ChromaDB ingestion."
        ),
        backstory=(
            "You produce the final artifact a data engineer uses to decide whether to "
            "run ingest_to_chromadb.py. Your report must answer: Was the data clean? "
            "Are the labels reasonable? Are the routing decisions defensible? "
            "Would a RAG query return useful results from this batch? "
            "If quality_overrides_count is high, flag it. If routing_overrides_count "
            "is high, note which collections had the most fixes. Be specific — "
            "vague go/no-go with no numbers is useless."
        ),
        tools=[get_pipeline_stats],
        llm=LLM_MODEL,
        verbose=False,
        allow_delegation=False,
    )
