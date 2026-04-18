from __future__ import annotations

from dataclasses import dataclass

PIPELINE_STEPS = [
    "validate_input",
    "normalize_media",
    "extract_frames",
    "detect_damage",
    "classify_severity",
    "compute_dsq_v2",
    "fraud_signal_checks",
    "estimate_repair_cost",
    "recommend_next_steps",
    "assemble_part_graph",
    "generate_heatmap",
    "generate_report_payload",
    "persist_artifacts",
    "publish_webhooks",
]


@dataclass
class PipelineExecution:
    job_id: str
    current_step: str
    status: str


def start_pipeline(job_id: str) -> PipelineExecution:
    return PipelineExecution(
        job_id=job_id, current_step=PIPELINE_STEPS[0], status="queued"
    )
