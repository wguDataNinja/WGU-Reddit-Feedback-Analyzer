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

def format_pain_points(batch: List[Dict]) -> str:
    return "\n---\n".join(
        f"pain_point_id: {p['pain_point_id']}\nsummary: {p['pain_point_summary']}\nsnippet: {p['quoted_text']}"
        for p in batch
    )
