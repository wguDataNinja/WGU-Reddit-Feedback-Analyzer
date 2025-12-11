from __future__ import annotations

"""
Stage 3 data models.

Defines:
    - LlmGlobalCluster: one global issue group from the Stage 3 LLM.
    - LlmGlobalOutput: raw per-batch LLM output schema.
    - Stage3RunManifest: run-level manifest for Stage 3 global clustering.
"""

from typing import List

from pydantic import BaseModel, Field


class LlmGlobalCluster(BaseModel):
    """
    One global issue cluster from the Stage-3 LLM.
    """

    provisional_label: str = Field(
        ...,
        description=(
            "Short handle for this global issue "
            "(e.g., 'unclear_or_ambiguous_instructions')."
        ),
    )
    normalized_issue_label: str = Field(
        ...,
        description="Human readable label for reporting.",
    )
    short_description: str = Field(
        ...,
        description="One or two sentence description of the root cause.",
    )
    member_cluster_ids: List[str] = Field(
        ...,
        description=(
            "List of Stage-2 course-level cluster_ids assigned to this global issue."
        ),
    )


class LlmGlobalOutput(BaseModel):
    """
    Exact JSON schema expected from the Stage-3 LLM.
    """

    global_clusters: List[LlmGlobalCluster]
    unassigned_clusters: List[str]


class Stage3RunManifest(BaseModel):
    """
    Run-level manifest for Stage 3 global clustering.
    """

    # Run identity
    run_id: str
    stage3_run_dir: str
    stage3_run_slug: str

    # Upstream Stage-2 run
    source_stage2_run: dict
    stage2_run_dir: str
    stage2_run_slug: str
    stage2_manifest_path: str

    # Inputs
    clusters_csv_path: str

    # Model / prompt
    global_model_name: str
    global_prompt_path: str

    # Counts
    num_input_clusters: int
    num_input_courses: int
    total_input_posts: int

    num_batches: int
    num_global_clusters: int
    num_unassigned_clusters: int

    total_assigned_posts: int
    total_unassigned_posts: int

    cluster_coverage_fraction: float
    post_coverage_fraction: float

    # Timing and cost
    started_at_epoch: float
    finished_at_epoch: float
    wallclock_sec: float
    total_cost_usd: float
    total_elapsed_sec_model_calls: float