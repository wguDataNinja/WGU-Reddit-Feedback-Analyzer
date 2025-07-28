# step02_prepare_prompt_data.py

"""
Formats clusters and pain point batches into LLM-ready prompt strings
"""

from typing import List, Dict

def format_clusters(clusters: List[Dict]) -> str:
    return "(none)" if not clusters else "\n".join(
        f"{i+1}. {c['title']} – {c['root_cause_summary']} ({len(c['pain_point_ids'])} items) (id={c['cluster_id']})"
        for i, c in enumerate(clusters)
    )

def format_pain_points(pain_points: List[Dict]) -> str:
    return "\n---\n".join(
        f"pain_point_id: {p.get('pain_point_id')}\n"
        f"summary: {p.get('pain_point_summary')}\n"
        f"snippet: {p.get('quoted_text')}"
        for p in pain_points
    )
