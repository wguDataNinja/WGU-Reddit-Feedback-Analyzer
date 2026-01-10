# filename: view_clusters_with_pain_points.py

import json
from pathlib import Path
from collections import defaultdict
from utils.paths import project_path  # this already exists in your codebase

course = "D335"
pain_points_path = project_path / f"outputs/stage2/pain_points_by_course/{course}.jsonl"
clusters_path = project_path / f"outputs/stage2/clusters_by_course/{course}_clusters.json"

# === Load pain points ===
pain_point_index = {}
with pain_points_path.open("r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        pain_point_index[obj["pain_point_id"]] = obj

# === Load clusters ===
with clusters_path.open("r", encoding="utf-8") as f:
    cluster_data = json.load(f)

clusters = cluster_data.get("clusters", [])

# === Print each cluster with assigned pain points ===
for cluster in clusters:
    print("\n" + "=" * 60)
    print(f"🔹 Cluster ID: {cluster['cluster_id']}")
    print(f"Title: {cluster['title']}")
    print(f"Summary: {cluster['root_cause_summary']}")
    print(f"Potential: {cluster['is_potential']}")
    print(f"Pain Points ({len(cluster['pain_point_ids'])}):")
    print("-" * 60)

    for pp_id in cluster["pain_point_ids"]:
        pp = pain_point_index.get(pp_id)
        if not pp:
            print(f"  ⚠️ MISSING: {pp_id}")
            continue
        print(f"• {pp['pain_point_summary']}")
        print(f"  → \"{pp['quoted_text']}\"\n")
