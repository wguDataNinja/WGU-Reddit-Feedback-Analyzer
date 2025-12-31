from __future__ import annotations

"""
Stage 2 data models.

Defines:
    - PainpointRecord: input to Stage 2 clustering (per post).
    - Cluster: one cluster for a course.
    - CourseClusters: all clusters for a single course.
    - Stage2ClusterFile: top-level JSON schema written per course.
    - Stage2CourseClusterSummary: per-course summary for the manifest.
    - Stage2RunManifest: Stage 2 run-level manifest, similar in spirit to
      the Stage 1 full-corpus manifest.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION


class PainpointRecord(BaseModel):
    """
    One extracted painpoint from Stage 1, per post and course.
    This matches artifacts/stage2/painpoints_llm_friendly.csv.
    """

    post_id: str
    course_code: str
    root_cause_summary: str
    pain_point_snippet: str


class Cluster(BaseModel):
    """
    One cluster for a course, as produced by the Stage 2 LLM.
    """

    cluster_id: str = Field(
        ...,
        description="Cluster identifier in the form COURSECODE_INT (e.g., C211_1).",
    )
    issue_summary: str = Field(
        ...,
        description="Short root-cause description for this cluster.",
    )
    num_posts: int = Field(
        ...,
        ge=0,
        description="Number of posts in this cluster.",
    )
    post_ids: List[str] = Field(
        ...,
        description="List of post_ids assigned to this cluster.",
    )


class CourseClusters(BaseModel):
    """
    All clusters for a single course.
    """

    course_code: str
    course_title: str
    total_posts: int = Field(
        ...,
        ge=0,
        description="Total number of posts with painpoints for this course.",
    )
    clusters: List[Cluster]


class Stage2ClusterFile(BaseModel):
    """
    Top-level JSON schema written per course.

    This mirrors the REQUIRED JSON STRUCTURE from the Stage 2 spec:

    {
      "courses": [
        {
          "course_code": "...",
          "course_title": "...",
          "total_posts": 0,
          "clusters": [...]
        }
      ]
    }
    """

    courses: List[CourseClusters]


class Stage2CourseClusterSummary(BaseModel):
    """
    Per-course cluster summary for the Stage 2 run manifest.
    """

    course_code: str
    num_clusters: int
    num_painpoints: int
    cluster_file: str

    llm_model_name: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_total_cost_usd: Optional[float] = None
    llm_elapsed_sec: Optional[float] = None


class Stage2RunManifest(BaseModel):
    """
    Run-level manifest for Stage 2 clustering.

    Parallels the Stage 1 full-corpus manifest, but focused on clustering.
    """

    # Schema
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Canonical schema version for Stage 0–4 artifacts.",
    )

    # Run identity and structure
    stage2_run_dir: str
    stage2_run_slug: str

    # Inputs
    painpoints_csv_path: str
    course_meta_csv_path: str

    # Model / prompt used for clustering
    cluster_model_name: str
    cluster_prompt_path: str

    # Counts
    num_courses: int
    total_painpoints: int
    num_cluster_calls: int

    # Timing and cost
    started_at_epoch: float
    finished_at_epoch: float
    wallclock_sec: float
    total_cost_usd: float
    total_elapsed_sec_model_calls: float

    # Per-course summaries
    per_course: Dict[str, Stage2CourseClusterSummary]
