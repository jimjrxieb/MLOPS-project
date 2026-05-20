"""
RAG ingestion prep crew — sequential, 4 tasks.

Task chain:
  quality_task  → labeling_task → routing_task → report_task

Inputs come from the state file written by collectors.py.
main.py calls collectors.run_prep_collectors() then this crew's kickoff().
"""
from crewai import Crew, Task, Process
from ..agents import quality_reviewer, semantic_labeler, routing_validator, pipeline_reporter


def build_prep_crew() -> Crew:
    """Build the RAG ingestion prep crew. Call after collectors.py writes the state file."""
    reviewer = quality_reviewer()
    labeler = semantic_labeler()
    validator = routing_validator()
    reporter = pipeline_reporter()

    quality_task = Task(
        description=(
            "Call get_repair_items to retrieve all REPAIR-flagged items from this run. "
            "For each item, read its content and chunks. Decide: is this worth ingesting "
            "despite the quality issue, or should it be discarded? "
            "Call override_quality_gate(content_hash, decision, rationale) for each item "
            "where decision is 'PASS' (promote) or 'FAIL' (discard). "
            "If the repair_batch is empty, report '0 REPAIR items — no overrides needed'."
        ),
        expected_output=(
            "A summary table: content_hash | file | decision | rationale. "
            "Total PASS overrides: N. Total FAIL overrides: N."
        ),
        agent=reviewer,
    )

    labeling_task = Task(
        description=(
            "Call get_unlabeled_items to retrieve items that Tier 1 + Tier 2 labeling "
            "could not classify. For each item, read its content and infer: "
            "domain (e.g. ['kubernetes', 'security']), type (e.g. ['documentation']), "
            "difficulty ('beginner'/'intermediate'/'advanced'), tags (specific keywords). "
            "Call apply_labels(content_hash, domain, type_, difficulty, tags) for each. "
            "If unlabeled_batch is empty, report '0 unlabeled items — no labels applied'."
        ),
        expected_output=(
            "A summary table: content_hash | file | domain | type | difficulty | tags. "
            "Total items labeled: N."
        ),
        agent=labeler,
        context=[quality_task],
    )

    routing_task = Task(
        description=(
            "Call get_routing_decisions. Review the 'needs_review' list — items going to "
            "jade-general or marked SKIP. For each, determine the correct collection: "
            "jade-projects (scan results/project docs), jade-sessions (Claude sessions), "
            "jade-troubleshooting (debug/fix guides), jade-consulting (playbooks/cheatsheets), "
            "jade-policy-as-code (rego/OPA), jade-operational (JSA operational training), "
            "jade-domain-sme (SME content), jade-nist-800-53 (NIST/compliance controls), "
            "jade-general (truly general content with no better home). "
            "Call override_routing(content_hash, destination, rag_collection, reason) for "
            "each rerouted item. Leave correctly-routed items alone."
        ),
        expected_output=(
            "A summary: total routing decisions reviewed, items rerouted (N), items confirmed correct (N). "
            "For rerouted items: content_hash | old collection | new collection | reason."
        ),
        agent=validator,
        context=[labeling_task],
    )

    report_task = Task(
        description=(
            "Call get_pipeline_stats to retrieve the full run statistics and override counts. "
            "Write a markdown coverage report with these sections:\n"
            "1. Run Summary — discovered, preprocessed, pass/repair/fail counts, total chunks\n"
            "2. Quality Gate Results — PASS/REPAIR/FAIL distribution, override breakdown\n"
            "3. Labeling Coverage — labeled vs unlabeled, domains detected\n"
            "4. Collection Routing — table of rag_collection → chunk count, override count\n"
            "5. Agent Overrides — quality N, label N, routing N, notable decisions\n"
            "6. Go/No-Go — APPROVED or NEEDS_REVIEW with one-paragraph justification\n\n"
            "APPROVED means: fail rate < 20%, labeled rate > 70%, routing overrides < 15% of total. "
            "NEEDS_REVIEW means any of those thresholds failed."
        ),
        expected_output=(
            "A complete markdown report with all 6 sections and a clear APPROVED or NEEDS_REVIEW "
            "verdict in section 6."
        ),
        agent=reporter,
        context=[quality_task, labeling_task, routing_task],
    )

    return Crew(
        agents=[reviewer, labeler, validator, reporter],
        tasks=[quality_task, labeling_task, routing_task, report_task],
        process=Process.sequential,
        verbose=False,
    )
