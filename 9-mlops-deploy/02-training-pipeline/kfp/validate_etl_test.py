"""CPU-only pipeline test — runs validate + ETL stages on Docker Desktop (no GPU).

Proves the KFP DAG works end-to-end through the data prep stages.
Data flows: SeaweedFS (S3) → download → validate → ETL + chunk → artifacts.
"""
from kfp import dsl, Client
from kfp.dsl import Output, Input, Dataset, Artifact


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["boto3"],
)
def download_data(
    s3_endpoint: str,
    s3_bucket: str,
    s3_key: str,
    access_key: str,
    secret_key: str,
    raw_data: Output[Dataset],
):
    """Download training data from SeaweedFS (S3-compatible)."""
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=s3_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )
    s3.download_file(s3_bucket, s3_key, raw_data.path)

    import os
    size = os.path.getsize(raw_data.path)
    print(f"Downloaded {s3_key} ({size:,} bytes)")


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["jsonlines"],
)
def validate_data(
    raw_data: Input[Dataset],
    validation_report: Output[Artifact],
) -> bool:
    """Validate training data quality gates."""
    import json
    import jsonlines

    errors = []
    total = 0
    passed = 0

    with jsonlines.open(raw_data.path) as reader:
        for example in reader:
            total += 1
            messages = example.get("messages", [])
            if not messages or not isinstance(messages, list):
                errors.append(f"Line {total}: not ChatML")
                continue
            if "assistant" not in [m.get("role") for m in messages]:
                errors.append(f"Line {total}: no assistant")
                continue
            assistant_msg = [m for m in messages if m["role"] == "assistant"][0]
            if len(assistant_msg.get("content", "")) < 50:
                errors.append(f"Line {total}: too short")
                continue
            passed += 1

    report = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / max(total, 1) * 100, 1),
        "errors": errors[:20],
    }

    with open(validation_report.path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Validation: {passed}/{total} passed ({report['pass_rate']}%)")
    return report["pass_rate"] >= 90.0


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["jsonlines"],
)
def etl_and_chunk(
    raw_data: Input[Dataset],
    chunk_size: int,
    eval_holdout_pct: float,
    chunked_data: Output[Dataset],
    eval_holdout: Output[Dataset],
    etl_report: Output[Artifact],
):
    """ETL: dedup, shuffle, chunk, split holdout."""
    import json
    import jsonlines
    import hashlib
    import random

    examples = []
    seen = set()
    dupes = 0

    with jsonlines.open(raw_data.path) as reader:
        for ex in reader:
            h = hashlib.sha256(json.dumps(ex, sort_keys=True).encode()).hexdigest()
            if h in seen:
                dupes += 1
                continue
            seen.add(h)
            examples.append(ex)

    random.seed(42)
    random.shuffle(examples)

    holdout_n = int(len(examples) * eval_holdout_pct)
    eval_examples = examples[:holdout_n]
    train_examples = examples[holdout_n:holdout_n + chunk_size]

    with jsonlines.open(chunked_data.path, mode="w") as w:
        for ex in train_examples:
            w.write(ex)

    with jsonlines.open(eval_holdout.path, mode="w") as w:
        for ex in eval_examples:
            w.write(ex)

    report = {
        "total_loaded": len(examples) + dupes,
        "duplicates_removed": dupes,
        "unique": len(examples),
        "chunk_size": len(train_examples),
        "eval_holdout": len(eval_examples),
    }

    with open(etl_report.path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"ETL complete: {report['unique']} unique, {report['chunk_size']} chunked, "
          f"{report['eval_holdout']} holdout, {report['duplicates_removed']} dupes removed")


@dsl.pipeline(
    name="validate-etl-test",
    description="CPU-only test: download from S3 → validate → ETL + chunk (no GPU required)",
)
def validate_etl_pipeline(
    s3_endpoint: str = "http://seaweedfs.kubeflow.svc:8333",
    s3_bucket: str = "ml-artifacts",
    s3_key: str = "training-data/katie_v2_chunk002.jsonl",
    access_key: str = "minio",
    secret_key: str = "minio123",
    chunk_size: int = 9500,
    eval_holdout_pct: float = 0.05,
):
    # Step 0: Download from S3
    download_task = download_data(
        s3_endpoint=s3_endpoint,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        access_key=access_key,
        secret_key=secret_key,
    )

    # Step 1: Validate
    validate_task = validate_data(
        raw_data=download_task.outputs["raw_data"],
    )

    # Step 2: ETL + Chunk (only if validation passes)
    with dsl.If(validate_task.outputs["Output"] == True):  # noqa: E712
        etl_and_chunk(
            raw_data=download_task.outputs["raw_data"],
            chunk_size=chunk_size,
            eval_holdout_pct=eval_holdout_pct,
        )


if __name__ == "__main__":
    client = Client(host="http://localhost:8887")
    run = client.create_run_from_pipeline_func(
        validate_etl_pipeline,
        experiment_name="katie-3b-training",
    )
    print(f"Run submitted: {run.run_id}")
    print(f"View at: http://localhost:8888/#/runs/details/{run.run_id}")
