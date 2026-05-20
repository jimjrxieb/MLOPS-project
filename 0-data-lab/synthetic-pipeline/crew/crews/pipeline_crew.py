"""
Synthetic data pipeline crew.

Sequential crew: Orchestrator → Quality Auditor → Report Generator.
Each agent receives context from the previous task so it can build on results
without re-running expensive pipeline steps.
"""

from crewai import Crew, Task, Process

from ..agents import pipeline_orchestrator, quality_auditor, report_generator


def build_pipeline_crew(
    instance_filter: str = "",
    min_quality_score: float = 50.0,
    max_examples: int = 1000,
) -> Crew:
    """
    Build the synthetic data pipeline crew.

    Args:
        instance_filter: If set, only process this instance (e.g. '01-instance').
                         Empty string = process all instances.
        min_quality_score: Examples below this score are filtered out (0-100).
        max_examples: Cap on examples per batch.

    Returns:
        Configured Crew ready for kickoff().
    """
    orchestrator = pipeline_orchestrator()
    auditor = quality_auditor()
    reporter = report_generator()

    # ── Task 1: Discover and generate ──────────────────────────────────────
    instance_context = (
        f"Only process instance: {instance_filter}."
        if instance_filter
        else "Process all discovered instances."
    )

    generate_task = Task(
        description=(
            f"Run the training data generation pipeline.\n\n"
            f"Scope: {instance_context}\n"
            f"Quality threshold: min_quality_score={min_quality_score}\n"
            f"Batch cap: max_examples={max_examples}\n\n"
            "Steps:\n"
            "1. Use discover_sources to find all slots with operational data.\n"
            "2. Use run_full_pipeline (or run_pipeline_for_instance if a filter is set) "
            "to generate training examples.\n"
            "3. Report: sources found, examples generated, output file path, quality stats."
        ),
        expected_output=(
            "JSON or structured text containing: sources_found count, "
            "total_examples generated, output_file absolute path, "
            "pass_rate, avg_score from the pipeline run."
        ),
        agent=orchestrator,
    )

    # ── Task 2: Validate quality ────────────────────────────────────────────
    quality_task = Task(
        description=(
            "Validate the quality of the generated training data.\n\n"
            "Using the output file path from the previous task:\n"
            "1. Use validate_output_file on the output JSONL file.\n"
            "2. Use get_batch_stats to check domain and rank distribution.\n"
            "3. Assess: pass rate, avg score, tier breakdown, and top issues.\n\n"
            "Decision criteria:\n"
            "  APPROVE  — pass rate ≥60% AND avg score ≥65\n"
            "  REVIEW   — pass rate 40-59% OR avg score 50-64 (borderline, needs spot-check)\n"
            "  REJECT   — pass rate <40% OR avg score <50\n\n"
            "State your decision clearly as one of: APPROVE / REVIEW / REJECT."
        ),
        expected_output=(
            "Quality assessment: pass_rate, avg_score, by_quality tier counts, "
            "top issues list, domain distribution summary, "
            "and final decision: APPROVE / REVIEW / REJECT with brief justification."
        ),
        agent=auditor,
        context=[generate_task],
    )

    # ── Task 3: Coverage report ─────────────────────────────────────────────
    report_task = Task(
        description=(
            "Generate a training data quality and coverage report in markdown.\n\n"
            "Based on results from the generation and quality tasks, produce a report with:\n\n"
            "## Summary\n"
            "- Total examples, pass rate, avg score, quality decision\n\n"
            "## Domain Coverage\n"
            "- Which security domains are well-represented vs. underrepresented\n"
            "- Compare against target: secrets, kubernetes, sast, iac, cloud should each have ≥5%\n\n"
            "## Rank Level Distribution\n"
            "- Compare actual vs. target distribution:\n"
            "  Target: E=5%, D=30%, C=40%, B=20%, S=5%\n"
            "- Flag any tier that deviates by more than 10 percentage points\n\n"
            "## Issues\n"
            "- Top quality issues from failed examples\n"
            "- Root cause (template gaps, missing source data, etc.)\n\n"
            "## Recommendations\n"
            "- Concrete actions for the next pipeline run to address coverage gaps\n"
            "- Priority order (address rank imbalances before domain gaps)\n\n"
            "## Go/No-Go\n"
            "- Final corpus inclusion decision: GO / NO-GO / CONDITIONAL\n"
            "- If CONDITIONAL: state what must be verified before inclusion"
        ),
        expected_output=(
            "Markdown report (~400-600 words) with Summary, Domain Coverage, "
            "Rank Distribution, Issues, Recommendations, and Go/No-Go sections."
        ),
        agent=reporter,
        context=[generate_task, quality_task],
    )

    return Crew(
        agents=[orchestrator, auditor, reporter],
        tasks=[generate_task, quality_task, report_task],
        process=Process.sequential,
        verbose=True,
    )
