#step_04_apply_actions.py

"""
Applies LLM actions to update cluster state and checks alert conditions
"""

from typing import List, Dict
from datetime import datetime

def next_cluster_id(course: str, clusters: List[Dict]) -> str:
    nums = [int(c["cluster_id"].split("_")[-1]) for c in clusters] if clusters else [0]
    return f"{course}_{max(nums) + 1}"

def apply_actions(course: str, state: Dict, actions: List[Dict]) -> None:
    for act in actions:
        pid = act["pain_point_id"]
        if act["action"] == "assign":
            for c in state["clusters"]:
                if c["cluster_id"] == act["cluster_id"]:
                    c["pain_point_ids"].append(pid)
                    if act.get("cluster_title"):
                        c["title"] = act["cluster_title"]
                    if act.get("root_cause_summary"):
                        c["root_cause_summary"] = act["root_cause_summary"]
                    break
        else:
            new_id = next_cluster_id(course, state["clusters"])
            state["clusters"].append({
                "cluster_id": new_id,
                "title": act["cluster_title"],
                "root_cause_summary": act["root_cause_summary"],
                "pain_point_ids": [pid],
                "is_potential": act["action"] == "new"
            })

def deduplicate_and_reindex(course: str, clusters: List[Dict]) -> None:
    for c in clusters:
        c["pain_point_ids"] = list(set(c["pain_point_ids"]))
    clusters.sort(key=lambda c: (not c["is_potential"], len(c["pain_point_ids"])), reverse=True)
    for i, c in enumerate(clusters, 1):
        c["cluster_id"] = f"{course}_{i}"

def check_alerts(state: Dict, threshold: int) -> None:
    alerts = state.get("alerts", [])
    for c in state["clusters"]:
        count = len(c["pain_point_ids"])
        if count >= threshold and c.get("is_potential"):
            c["is_potential"] = False
            new_alert = {
                "cluster_id": c["cluster_id"],
                "summary": c["root_cause_summary"],
                "post_count": count,
                "detected_on": datetime.utcnow().isoformat() + "Z"
            }
            if not any(a["cluster_id"] == new_alert["cluster_id"] and a["summary"] == new_alert["summary"] for a in alerts):
                alerts.append(new_alert)
        elif count < threshold:
            c["is_potential"] = True
    state["alerts"] = alerts
