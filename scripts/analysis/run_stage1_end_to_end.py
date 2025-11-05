# run_stage1_end_to_end.py:.py

import argparse
import json
import os
import pandas as pd
from stage1_eval_utils import (
    load_jsonl_to_df,
    assign_length_bins,
    parse_is_pain_point,
    get_metrics,
    bin_metrics,
)

from collections import defaultdict
from pathlib import Path

def wrap_predictions(pain_points_path, all_posts_path=None):
    records = []
    with open(pain_points_path, "r") as f:
        pain_recs = [json.loads(l) for l in f if l.strip()]

    post_to_count = defaultdict(int)

    for rec in pain_recs:
        pid = rec.get("post_id")
        if not pid:
            continue

        # Handle different output formats
        if "pain_points" in rec and isinstance(rec["pain_points"], list):
            count = len(rec["pain_points"])
        elif "extracted_pain_points" in rec and isinstance(rec["extracted_pain_points"], list):
            count = len(rec["extracted_pain_points"])
        else:
            count = 0

        post_to_count[pid] = count

    # Allow for complete list of post IDs (e.g., from sample set)
    all_post_ids = set(post_to_count.keys())
    if all_posts_path:
        with open(all_posts_path, "r") as f:
            all_posts = [json.loads(l) for l in f if l.strip()]
        ids = {r.get("post_id") for r in all_posts if r.get("post_id")}
        all_post_ids = ids.union(all_post_ids)

    wrapped = []
    for pid in sorted(all_post_ids):
        num = post_to_count.get(pid, 0)
        wrapped.append({
            "post_id": pid,
            "is_pain_point": bool(num),
            "num_extracted": num,
        })

    return pd.DataFrame(wrapped)

def normalize_gold(df):
    if "is_pain_point" in df.columns:
        df["is_pain_point_true"] = df["is_pain_point"].apply(parse_is_pain_point)
    elif "label" in df.columns:
        df["is_pain_point_true"] = df["label"].apply(parse_is_pain_point)
    else:
        raise ValueError("Gold file must contain 'is_pain_point' or 'label'.")
    return df

def normalize_pred(df):
    if "is_pain_point" in df.columns:
        df["is_pain_point_pred"] = df["is_pain_point"].apply(parse_is_pain_point)
    elif "is_pain_point_pred" in df.columns:
        df["is_pain_point_pred"] = df["is_pain_point_pred"].apply(parse_is_pain_point)
    else:
        raise ValueError("Prediction df must contain 'is_pain_point' or 'is_pain_point_pred'.")
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True, help="Gold JSONL file with true labels.")
    parser.add_argument("--sample", required=True, help="Sample JSONL (for bin assignment).")
    parser.add_argument("--pain-points", required=True, help="Raw pain_points_stage1.jsonl")
    parser.add_argument("--output-dir", required=True, help="Directory to write wrapped + eval outputs.")
    args = parser.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # wrap predictions
    wrapped_df = wrap_predictions(args.pain_points, all_posts_path=args.sample)
    wrapped_path = outdir / "classified_painpoint_zeroshot.jsonl"
    with open(wrapped_path, "w") as f:
        for rec in wrapped_df.to_dict(orient="records"):
            f.write(json.dumps(rec) + "\n")

    # load gold and sample
    gold_df = load_jsonl_to_df(args.gold)
    sample_df = load_jsonl_to_df(args.sample)

    gold_df = normalize_gold(gold_df)
    pred_df = normalize_pred(wrapped_df)

    merged = pd.merge(
        gold_df[["post_id", "is_pain_point_true"]],
        pred_df[["post_id", "is_pain_point_pred"]],
        on="post_id",
        how="inner",
    )
    if merged.empty:
        raise RuntimeError("No overlap between gold and predictions.")

    # attach bins
    if "bin" not in sample_df.columns:
        sample_df = assign_length_bins(sample_df, col="text_clean")
    bins = sample_df[["post_id", "bin"]]
    merged = merged.merge(bins, on="post_id", how="left")

    # overall
    overall = get_metrics(merged["is_pain_point_true"].tolist(), merged["is_pain_point_pred"].tolist())
    print("===== Overall metrics =====")
    for k in ["precision", "recall", "f1", "accuracy", "support_pos", "support_neg"]:
        print(f"{k}: {overall[k]}")

    # per-bin
    per_bin = bin_metrics(merged, true_col="is_pain_point_true", pred_col="is_pain_point_pred", bin_col="bin")
    print("\n===== By-bin =====")
    for b, m in per_bin.items():
        print(f"{b}: precision={m['precision']:.3f} recall={m['recall']:.3f} f1={m['f1']:.3f} support+={m['support_pos']}")

    # save per-post CSV
    cmp_df = merged.copy()
    cmp_df["true"] = cmp_df["is_pain_point_true"].astype(int)
    cmp_df["pred"] = cmp_df["is_pain_point_pred"].astype(int)
    csv_path = outdir / "stage1_eval_comparison.csv"
    cmp_df.to_csv(csv_path, index=False)
    print(f"\nSaved per-post comparison to {csv_path}")
    print(f"Wrapped predictions written to {wrapped_path}")

if __name__ == "__main__":
    main()