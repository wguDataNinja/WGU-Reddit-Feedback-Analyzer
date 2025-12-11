PYTHONPATH=src python - << 'EOF'
import json, glob
from pathlib import Path
import pandas as pd

print("=== Stage 0 – Locked Reddit corpus ===")
stage0_path = Path("artifacts/stage0_filtered_posts.jsonl")
stage0 = pd.read_json(stage0_path, lines=True)
print("Stage0 rows:", len(stage0), "unique post_id:", stage0["post_id"].nunique())
print()

print("=== Stage 1 – Full-corpus pain-point predictions ===")
# Use the latest gpt-5-mini full-corpus run
fc_dirs = sorted(Path("artifacts/stage1/full_corpus").glob("gpt-5-mini_s1_optimal_fullcorpus_*"))
if not fc_dirs:
    raise SystemExit("No gpt-5-mini_s1_optimal_fullcorpus_* run found.")
fc_dir = fc_dirs[-1]
pred = pd.read_csv(fc_dir / "predictions_FULL.csv")
print("Run dir:", fc_dir)
print("Stage1 rows:", len(pred), "unique post_id:", pred["post_id"].nunique())
print("pred_contains_painpoint value_counts:")
print(pred["pred_contains_painpoint"].value_counts())
print("llm_failure count:", int(pred["llm_failure"].sum()))
print()

print("ID alignment Stage0 vs Stage1:")
s0_ids = set(stage0["post_id"])
s1_ids = set(pred["post_id"])
print("missing_from_pred:", len(s0_ids - s1_ids))
print("extra_in_pred:", len(s1_ids - s0_ids))
print()

print("=== Stage 2 – Painpoints + course-level clusters ===")
pp = pd.read_csv("artifacts/stage2/painpoints_llm_friendly.csv")
print("Stage2 painpoints rows:", len(pp), "unique post_id:", pp["post_id"].nunique())
print("Painpoints by course (top 10):")
print(pp["course_code"].value_counts().head(10))
print()

# Compare Stage1 painpoints used by Stage2
mask_s1_pp = (pred["pred_contains_painpoint"] == "y") & (~pred["llm_failure"])
s1_pp_ids = set(pred[mask_s1_pp]["post_id"])
s2_pp_ids = set(pp["post_id"])
missing = sorted(s1_pp_ids - s2_pp_ids)
extra = sorted(s2_pp_ids - s1_pp_ids)
print("Stage1 painpoints (y, no failure):", len(s1_pp_ids))
print("Stage2 painpoints rows:", len(s2_pp_ids))
print("Missing painpoints (in Stage1 but not Stage2):", len(missing), missing)
print("Extra painpoints (in Stage2 but not Stage1):", len(extra), extra)
print()

# Stage2 cluster count via preprocessed CSV
pre_dirs = sorted(Path("artifacts/stage3/preprocessed").glob("gpt-5-mini_s2_cluster_full*"))
if not pre_dirs:
    raise SystemExit("No gpt-5-mini_s2_cluster_full* preprocessed dir found.")
pre_dir = pre_dirs[-1]
pre = pd.read_csv(pre_dir / "clusters_llm.csv")
print("Stage2 preprocessed dir:", pre_dir)
print("Course-level clusters (from clusters_llm.csv):", pre["cluster_id"].nunique())
print()

print("=== Stage 3 – Global normalization (latest fixed run) ===")
s3_runs = sorted(Path("artifacts/stage3/runs").glob("gpt-5-mini_s3_global_gpt-5-mini_s2_cluster_full_*"))
if not s3_runs:
    raise SystemExit("No Stage3 global run matching gpt-5-mini_s3_global_gpt-5-mini_s2_cluster_full_* found.")
s3_dir = s3_runs[-1]
print("Stage3 run dir:", s3_dir)

# Manifest metadata (checks run_id and source_stage2_run)
manifest = json.loads((s3_dir / "manifest.json").read_text(encoding="utf-8"))
print("Stage3 run_id:", manifest.get("run_id"))
print("Stage3 stage2_run_slug:", manifest.get("stage2_run_slug"))
print("Stage3 source_stage2_run:", manifest.get("source_stage2_run"))
print()

cg = pd.read_csv(s3_dir / "cluster_global_index.csv")
print("Course-level clusters in cluster_global_index:", cg["cluster_id"].nunique())
print("Global issue types (non-empty normalized labels):",
      cg["normalized_issue_label"].replace("", pd.NA).dropna().nunique())
print()

with (s3_dir / "global_clusters.json").open(encoding="utf-8") as f:
    gc_obj = json.load(f)
gc_list = gc_obj.get("global_clusters", [])
unassigned = gc_obj.get("unassigned_clusters", [])
print("global_clusters.json: num global clusters:", len(gc_list),
      "unassigned cluster_ids:", len(unassigned))
print()

print("=== Stage 4 – Report data layer ===")
pm = pd.read_csv("artifacts/report_data/post_master.csv")
cs = pd.read_csv("artifacts/report_data/course_summary.csv")
gi = pd.read_csv("artifacts/report_data/global_issues.csv")
icm = pd.read_csv("artifacts/report_data/issue_course_matrix.csv")

print("post_master rows:", len(pm), "unique post_id:", pm["post_id"].nunique())
print("course_summary rows:", len(cs), "unique courses:", cs["course_code"].nunique())
print("global_issues rows:", len(gi), "unique global_cluster_id:", gi["global_cluster_id"].nunique())
print("issue_course_matrix rows:", len(icm))
print()

print("post_master painpoint flag (is_pain_point) value_counts:")
print(pm["is_pain_point"].value_counts(dropna=False))
print("Missing normalized_issue_label in post_master:",
      pm["normalized_issue_label"].isna().sum())
print()

print("Sanity check: global_issues vs Stage3 normalized labels:")
print("global_issues normalized_issue_label unique:",
      gi["normalized_issue_label"].nunique())
print("cluster_global_index normalized_issue_label unique:",
      cg["normalized_issue_label"].replace("", pd.NA).dropna().nunique())
print("Done.")
EOF