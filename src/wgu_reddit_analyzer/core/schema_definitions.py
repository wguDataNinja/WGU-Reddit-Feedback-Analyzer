"""Shared schema definitions and invariants for all stages.

This module defines:
- The canonical schema_version.
- Enumerations for categorical values (e.g., pain-point flags, global issues).
- Cross-stage Pydantic models and invariants, especially Stage 1 outputs.

All Stage 1–4 code should import from here rather than defining ad-hoc enums.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Sequence

from pydantic import BaseModel, Field, root_validator


SCHEMA_VERSION: str = "1.0.0"

ContainsPainPoint = Literal["y", "n", "u"]


GlobalIssueLabel = Literal[
    "assessment_material_misalignment",
    "unclear_or_ambiguous_instructions",
    "course_pacing_or_workload",
    "technology_or_platform_issues",
    "staffing_or_instructor_availability",
    "course_structure_or_navigation",
    "prerequisite_or_readiness_mismatch",
    "other_or_uncategorized",
]


class GlobalIssueDefinition(BaseModel):
    """Definition and examples for a single global issue label.

    This mirrors the catalog in docs/schema_and_hierarchy.md and provides
    a programmatic representation for validation and reporting.
    """

    label: GlobalIssueLabel
    description: str
    examples: Sequence[str]


def default_global_issue_catalog() -> List[GlobalIssueDefinition]:
    """Return the default catalog for schema_version 1.0.0."""
    return [
        GlobalIssueDefinition(
            label="assessment_material_misalignment",
            description=(
                "Assessments test content that is missing, under-emphasized, "
                "or inconsistent with course materials."
            ),
            examples=[
                "The OA covered topics that were never mentioned in the modules.",
                "Practice questions are nothing like the actual exam.",
            ],
        ),
        GlobalIssueDefinition(
            label="unclear_or_ambiguous_instructions",
            description=(
                "Students cannot understand what is required due to vague, "
                "contradictory, or missing instructions."
            ),
            examples=[
                "The project instructions and rubric contradict each other.",
                "I don't know what artifacts I'm supposed to upload.",
            ],
        ),
        GlobalIssueDefinition(
            label="course_pacing_or_workload",
            description=(
                "The expected time or effort is unreasonable relative to "
                "credits or other courses."
            ),
            examples=[
                "This 3-credit course is more work than my entire term.",
                "Deadlines pile up in the last week with no warning.",
            ],
        ),
        GlobalIssueDefinition(
            label="technology_or_platform_issues",
            description=(
                "Persistent problems with labs, third-party platforms, "
                "or course-integrated tools."
            ),
            examples=[
                "The lab environment crashes every time I start task 3.",
                "The proctoring tool disconnects and I have to start over.",
            ],
        ),
        GlobalIssueDefinition(
            label="staffing_or_instructor_availability",
            description=(
                "Difficulty getting timely help from course instructors, "
                "evaluators, or mentors for course-specific questions."
            ),
            examples=[
                "My course instructor hasn't responded in two weeks.",
                "No one is available to clarify the project rubric.",
            ],
        ),
        GlobalIssueDefinition(
            label="course_structure_or_navigation",
            description=(
                "The layout or ordering of content makes it hard "
                "to progress logically."
            ),
            examples=[
                "Modules reference content that appears later in the course.",
                "Important resources are buried and hard to find.",
            ],
        ),
        GlobalIssueDefinition(
            label="prerequisite_or_readiness_mismatch",
            description=(
                "Course assumes knowledge or skills students commonly lack, "
                "or repeats material excessively."
            ),
            examples=[
                "This course expects advanced statistics we never learned.",
                "Half the course repeats content from the previous class.",
            ],
        ),
        GlobalIssueDefinition(
            label="other_or_uncategorized",
            description=(
                "Real, course-side pain points that do not fit any other "
                "label or represent new/emerging themes."
            ),
            examples=[
                "Mentor incentives create pressure to accelerate through "
                "this course.",
                "Mandatory live sessions are at impossible times.",
            ],
        ),
    ]


GLOBAL_ISSUE_DEFINITIONS: Dict[GlobalIssueLabel, GlobalIssueDefinition] = {
    issue.label: issue for issue in default_global_issue_catalog()
}


class Stage1PredictionOutput(BaseModel):
    """Canonical Stage 1 prediction schema and invariants.

    This model should match the predictions.csv and any JSONL representation
    used between Stage 1 and downstream stages.

    Invariants:
    - On parse/schema error -> contains_painpoint = "u".
    - confidence_pred is always in [0.0, 1.0]; invalid values become 0.0.
    """

    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Schema version used for this prediction record.",
    )
    run_id: str = Field(..., description="Identifier for the Stage 1 run.")
    post_id: str = Field(..., description="Unique identifier for the source post.")
    contains_painpoint: ContainsPainPoint = Field(
        ...,
        description='Pain-point flag: "y", "n", or "u" (unknown/unusable).',
    )
    confidence_pred: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Model-reported confidence in the predicted pain-point label, "
            "normalized to [0.0, 1.0]."
        ),
    )
    root_cause_summary: str | None = Field(
        None,
        description="Short natural-language summary of the main pain point, if any.",
    )
    grounded_snippet: str | None = Field(
        None,
        description="Quotation or snippet from the post supporting the summary.",
    )
    parse_error_flag: bool = Field(
        False,
        description="True if the LLM output could not be parsed as expected.",
    )
    schema_error_flag: bool = Field(
        False,
        description="True if required fields were missing or invalid.",
    )
    model: str = Field(
        ...,
        description="Model name used for this prediction (e.g., gpt-4.x).",
    )
    prompt_version: str = Field(
        ...,
        description="Identifier for the Stage 1 prompt / template used.",
    )
    raw_response_text: str | None = Field(
        None,
        description=(
            "Raw text returned by the LLM, preserved for debugging. "
            "Should not be used directly by downstream stages."
        ),
    )

    @root_validator
    def enforce_invariants(cls, values: Dict[str, object]) -> Dict[str, object]:
        """Apply Stage 1 invariants for pain-point flag and confidence."""
        parse_error = bool(values.get("parse_error_flag"))
        schema_error = bool(values.get("schema_error_flag"))

        # Enforce contains_painpoint = "u" when parsing/schema fails.
        if parse_error or schema_error:
            values["contains_painpoint"] = "u"

        # Coerce confidence_pred into [0.0, 1.0], defaulting to 0.0 on error.
        raw_conf = values.get("confidence_pred")
        try:
            conf = float(raw_conf) if raw_conf is not None else 0.0
        except (TypeError, ValueError):
            conf = 0.0

        if conf < 0.0 or conf > 1.0:
            conf = 0.0

        values["confidence_pred"] = conf

        # Ensure schema_version is populated.
        if not values.get("schema_version"):
            values["schema_version"] = SCHEMA_VERSION

        return values