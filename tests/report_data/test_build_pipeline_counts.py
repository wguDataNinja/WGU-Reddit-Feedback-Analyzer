from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from wgu_reddit_analyzer.report_data.build_pipeline_counts import (
    compute_pipeline_counts,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def test_compute_pipeline_counts_basic(tmp_path: Path) -> None:
    report_data_dir = tmp_path / "artifacts" / "report_data"
    report_data_dir.mkdir(parents=True, exist_ok=True)

    # Minimal post_master with two courses
    pm = pd.DataFrame(
        [
            {
                "post_id": "p1",
                "course_code": "C101",
                "is_pain_point": 1,
                "course_title_final": "Test Course 101",
                "college_list": "School A",
            },
            {
                "post_id": "p2",
                "course_code": "C101",
                "is_pain_point": 0,
                "course_title_final": "Test Course 101",
                "college_list": "School A",
            },
            {
                "post_id": "p3",
                "course_code": "C102",
                "is_pain_point": 1,
                "course_title_final": "Test Course 102",
                "college_list": "School B; School A",
            },
        ]
    )
    pm.to_csv(report_data_dir / "post_master.csv", index=False)

    # course_cluster_detail: one cluster per course
    _write_jsonl(
        report_data_dir / "course_cluster_detail.jsonl",
        [
            {
                "course_code": "C101",
                "course_title": "Test Course 101",
                "cluster_id": "C101_1",
                "example_post_ids": ["p1"],
            },
            {
                "course_code": "C102",
                "course_title": "Test Course 102",
                "cluster_id": "C102_1",
                "example_post_ids": ["p3"],
            },
        ],
    )

    # issue_course_matrix: one issue per course
    icm = pd.DataFrame(
        [
            {
                "normalized_issue_label": "assessment_material_misalignment",
                "course_code": "C101",
                "num_posts": 1,
                "num_clusters": 1,
            },
            {
                "normalized_issue_label": "unclear_or_ambiguous_instructions",
                "course_code": "C102",
                "num_posts": 1,
                "num_clusters": 1,
            },
        ]
    )
    icm.to_csv(report_data_dir / "issue_course_matrix.csv", index=False)

    # global_issues stub
    gi = pd.DataFrame(
        [
            {"global_cluster_id": "G001"},
            {"global_cluster_id": "G002"},
        ]
    )
    gi.to_csv(report_data_dir / "global_issues.csv", index=False)

    course_counts, college_counts = compute_pipeline_counts(report_data_dir)

    # Course-level assertions
    c101 = course_counts.set_index("course_code").loc["C101"]
    assert c101["stage0_posts"] == 2
    assert c101["stage1_painpoints"] == 1
    assert c101["stage1_non_painpoints"] == 1
    assert c101["stage2_clusters"] == 1
    assert c101["stage2_clustered_posts"] == 1
    assert c101["stage2_unclustered_painpoints"] == 0
    assert c101["stage3_global_issues_in_course"] == 1
    assert c101["stage3_posts_with_global_issue"] == 1

    c102 = course_counts.set_index("course_code").loc["C102"]
    assert c102["stage0_posts"] == 1
    assert c102["stage1_painpoints"] == 1
    assert c102["stage1_non_painpoints"] == 0
    assert c102["stage2_clusters"] == 1
    assert c102["stage2_clustered_posts"] == 1
    assert c102["stage2_unclustered_painpoints"] == 0
    assert c102["stage3_global_issues_in_course"] == 1
    assert c102["stage3_posts_with_global_issue"] == 1

    # College-level aggregation: School A gets contributions from both courses
    college_indexed = college_counts.set_index("college")
    school_a = college_indexed.loc["School A"]
    assert school_a["stage0_posts"] == 3
    assert school_a["stage1_painpoints"] == 2

    school_b = college_indexed.loc["School B"]
    assert school_b["stage0_posts"] == 1
    assert school_b["stage1_painpoints"] == 1