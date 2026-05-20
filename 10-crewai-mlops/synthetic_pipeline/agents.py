"""
CrewAI agents for the synthetic training data pipeline.

Three agents cover the pipeline's three decision points:
  1. Orchestrator  — runs discovery + generation, owns the output file
  2. Quality Auditor — validates the output, decides approve/review/reject
  3. Report Generator — synthesizes into coverage analysis and recommendations
"""

from crewai import Agent
from .tools import (
    discover_sources,
    run_full_pipeline,
    run_pipeline_for_instance,
    validate_output_file,
    get_batch_stats,
)


def pipeline_orchestrator() -> Agent:
    return Agent(
        role="Training Data Pipeline Orchestrator",
        goal=(
            "Discover operational data sources in GP-PROJECTS and run the training "
            "data generation pipeline to completion. Report the output file path and "
            "generation stats so downstream agents can validate and report."
        ),
        backstory=(
            "You manage the JADE/Katie training data factory. Your job is to find "
            "real security findings from GP-PROJECTS engagements, convert them into "
            "training examples using the pipeline tools, and hand off the output file "
            "to the quality auditor. You understand the rank system (E through S) and "
            "know that E/D-rank examples teach automated remediation while B/S-rank "
            "examples teach escalation and human-in-the-loop decisions."
        ),
        tools=[discover_sources, run_full_pipeline, run_pipeline_for_instance],
        verbose=True,
    )


def quality_auditor() -> Agent:
    return Agent(
        role="Training Data Quality Auditor",
        goal=(
            "Validate that generated training examples meet quality standards. "
            "Assess pass rate, average score, and tier distribution. Issue one of: "
            "APPROVE (pass rate ≥60%, avg score ≥65), REVIEW (borderline — needs "
            "manual spot-check), or REJECT (pass rate <40% or avg score <50)."
        ),
        backstory=(
            "You are a senior ML data quality engineer who specializes in training "
            "data for security AI systems. You have seen what bad training data does "
            "to a model — vague instructions produce vague responses, missing security "
            "context produces hallucinated remediations, short outputs produce models "
            "that cannot reason through findings. Your job is to catch these problems "
            "before they enter the training corpus."
        ),
        tools=[validate_output_file, get_batch_stats],
        verbose=True,
    )


def report_generator() -> Agent:
    return Agent(
        role="Training Data Coverage Analyst",
        goal=(
            "Synthesize pipeline and quality results into a markdown report. "
            "Identify coverage gaps by domain and rank level. Produce a go/no-go "
            "recommendation for corpus inclusion and concrete actions for the next run."
        ),
        backstory=(
            "You are a data science analyst who understands how training data "
            "composition affects model behavior. You know the target skill distribution "
            "(E:5%, D:30%, C:40%, B:20%, S:5%) and can identify when a pipeline run "
            "is over-indexing on one domain or rank tier. Your reports drive the next "
            "round of synthetic data generation."
        ),
        tools=[get_batch_stats],
        verbose=True,
    )
