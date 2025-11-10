"""
Benchmark Cost Estimator

Purpose:
    Estimate LLM API cost and runtime for DEV, TEST, and full Stage 0 datasets
    under one or more prompt configurations.

Inputs:
    - artifacts/analysis/length_profile.json
    - artifacts/benchmark/DEV_candidates.jsonl
    - artifacts/benchmark/TEST_candidates.jsonl
    - benchmark/model_registry.py
    - utils/token_utils.count_tokens

Outputs:
    - artifacts/benchmark/cost_estimates.csv
        One row per (prompt_label, model, dataset).

Usage:
    Single configuration:
        python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost

    Multiple prompt configurations:
        python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost \\
          --scenario zero_shot:260:120:4:0.0 \\
          --scenario few_shot_simple:420:120:4:0.0 \\
          --scenario few_shot_opt:600:140:4:0.0

Notes:
    - Uses model_registry pricing and (optional) throughput hints.
    - Supports prompt cache fractions and batching assumptions.
    - Does not make real API calls; this is a projection tool.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Dict, Iterable, List

from wgu_reddit_analyzer.benchmark.model_registry import (
    MODEL_REGISTRY,
    get_model_info,
)
from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.utils.token_utils import count_tokens

LOGGER = get_logger("estimate_benchmark_cost")


def project_root() -> Path:
    """
    Resolve repository root from this file location.

    Returns:
        Repository root path.
    """
    return Path(__file__).resolve().parents[3]


def length_profile_path() -> Path:
    """
    Path to length_profile.json.

    Returns:
        Path to artifacts/analysis/length_profile.json.
    """
    return project_root() / "artifacts" / "analysis" / "length_profile.json"


def dev_path() -> Path:
    """
    Path to DEV candidates JSONL.

    Returns:
        Path to artifacts/benchmark/DEV_candidates.jsonl.
    """
    return project_root() / "artifacts" / "benchmark" / "DEV_candidates.jsonl"


def test_path() -> Path:
    """
    Path to TEST candidates JSONL.

    Returns:
        Path to artifacts/benchmark/TEST_candidates.jsonl.
    """
    return project_root() / "artifacts" / "benchmark" / "TEST_candidates.jsonl"


def stage0_path() -> Path:
    """
    Path to Stage 0 JSONL (sanity only).

    Returns:
        Path to artifacts/stage0_filtered_posts.jsonl.
    """
    return project_root() / "artifacts" / "stage0_filtered_posts.jsonl"


def output_dir() -> Path:
    """
    Directory for benchmark outputs.

    Returns:
        Path to artifacts/benchmark.
    """
    return project_root() / "artifacts" / "benchmark"


def output_csv_path() -> Path:
    """
    Default cost estimates CSV path.

    Returns:
        Path to artifacts/benchmark/cost_estimates.csv.
    """
    return output_dir() / "cost_estimates.csv"


@dataclass
class DatasetSpec:
    """
    Logical dataset configuration for cost estimation.
    """

    name: str
    num_posts: int
    avg_post_tokens: float


@dataclass
class CostConfig:
    """
    Prompt configuration for a scenario.
    """

    prompt_tokens: int
    output_tokens: int
    batch_size: int
    cache_fraction: float


@dataclass
class PromptScenario:
    """
    Named prompt configuration.
    """

    label: str
    cfg: CostConfig


@dataclass
class CostEstimate:
    """
    Cost and runtime estimate for one (prompt, model, dataset) triple.
    """

    prompt_label: str
    model: str
    dataset: str
    num_posts: int
    batch_size: int
    prompt_tokens: int
    avg_post_tokens: float
    avg_output_tokens: float
    total_input_tokens: float
    total_output_tokens: float
    cache_fraction: float
    cost_usd: float
    cost_per_1k_posts_usd: float
    throughput_posts_per_hour: float
    est_hours: float


def load_length_profile(path: Path) -> Dict:
    """
    Load the length_profile.json file.

    Args:
        path: Path to length_profile.json.

    Returns:
        Parsed JSON mapping.

    Raises:
        SystemExit: If file is missing.
    """
    if not path.exists():
        raise SystemExit(f"Missing length profile: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def count_jsonl_rows(path: Path) -> int:
    """
    Count non-empty lines in a JSONL file.

    Args:
        path: JSONL path.

    Returns:
        Number of non-empty lines.
    """
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def avg_post_tokens_from_jsonl(path: Path, model_name: str) -> float:
    """
    Compute average token length of posts in a JSONL dataset.

    Args:
        path: JSONL input path.
        model_name: Model name for tokenization rules.

    Returns:
        Average tokens per post, or 0.0 if not computable.
    """
    if not path.exists():
        return 0.0

    total = 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            title = (rec.get("title") or "").strip()
            selftext = (rec.get("selftext") or "").strip()
            text = (title + "\n\n" + selftext).strip()
            if not text:
                continue

            tokens = count_tokens(text, model=model_name)
            if tokens <= 0:
                continue

            total += tokens
            count += 1

    if count == 0:
        return 0.0
    return total / count


def build_dataset_specs(
    lp: Dict,
    dev_file: Path,
    test_file: Path,
    token_model: str,
) -> List[DatasetSpec]:
    """
    Build dataset specs for Stage 0, DEV, and TEST.

    Args:
        lp: Parsed length_profile.json.
        dev_file: DEV candidates JSONL path.
        test_file: TEST candidates JSONL path.
        token_model: Model name for token counting in DEV/TEST.

    Returns:
        List of DatasetSpec objects.
    """
    specs: List[DatasetSpec] = []

    total_records = int(
        lp.get("nonempty_text_records") or lp.get("total_records") or 0,
    )
    mean_tokens = float(lp.get("mean_tokens", 0.0))
    if total_records <= 0 or mean_tokens <= 0.0:
        raise SystemExit(
            "length_profile.json missing valid total_records/mean_tokens.",
        )

    specs.append(
        DatasetSpec(
            name="stage0_full",
            num_posts=total_records,
            avg_post_tokens=mean_tokens,
        )
    )

    dev_n = count_jsonl_rows(dev_file)
    if dev_n > 0:
        dev_avg = avg_post_tokens_from_jsonl(dev_file, token_model)
        if dev_avg <= 0.0:
            dev_avg = mean_tokens
        specs.append(
            DatasetSpec(
                name="DEV",
                num_posts=dev_n,
                avg_post_tokens=dev_avg,
            )
        )

    test_n = count_jsonl_rows(test_file)
    if test_n > 0:
        test_avg = avg_post_tokens_from_jsonl(test_file, token_model)
        if test_avg <= 0.0:
            test_avg = mean_tokens
        specs.append(
            DatasetSpec(
                name="TEST",
                num_posts=test_n,
                avg_post_tokens=test_avg,
            )
        )

    return specs


def estimate_for_model_dataset(
    model_name: str,
    ds: DatasetSpec,
    cfg: CostConfig,
    prompt_label: str,
) -> CostEstimate:
    """
    Estimate cost and runtime for one model and dataset under a prompt config.

    Args:
        model_name: Model key for model_registry.
        ds: DatasetSpec describing input corpus.
        cfg: Prompt and batching configuration.
        prompt_label: Scenario label.

    Returns:
        CostEstimate with tokens, cost, and runtime.
    """
    info = get_model_info(model_name)

    batch_size = max(1, cfg.batch_size)
    requests = int(ceil(ds.num_posts / batch_size))

    prompt_per_request = cfg.prompt_tokens
    post_tokens_per_post = ds.avg_post_tokens

    total_prompt_tokens = prompt_per_request * requests
    total_post_tokens = post_tokens_per_post * ds.num_posts
    total_input_tokens = total_prompt_tokens + total_post_tokens

    total_output_tokens = cfg.output_tokens * ds.num_posts

    throughput = float(
        getattr(info, "throughput_posts_per_hour", 0.0),
    )

    if (
        throughput <= 0.0
        and getattr(info, "is_local", False)
        and model_name.lower().startswith("llama3")
    ):
        throughput = 1000.0

    if throughput > 0.0 and ds.num_posts > 0:
        est_hours = ds.num_posts / throughput
    else:
        est_hours = 0.0

    if getattr(info, "is_local", False):
        return CostEstimate(
            prompt_label=prompt_label,
            model=model_name,
            dataset=ds.name,
            num_posts=ds.num_posts,
            batch_size=batch_size,
            prompt_tokens=cfg.prompt_tokens,
            avg_post_tokens=ds.avg_post_tokens,
            avg_output_tokens=cfg.output_tokens,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            cache_fraction=cfg.cache_fraction,
            cost_usd=0.0,
            cost_per_1k_posts_usd=0.0,
            throughput_posts_per_hour=throughput,
            est_hours=round(est_hours, 3),
        )

    cache_fraction = max(0.0, min(1.0, cfg.cache_fraction))
    cached_input = total_input_tokens * cache_fraction
    paid_input = max(0.0, total_input_tokens - cached_input)

    input_cost = (paid_input / 1000.0) * info.input_per_1k
    cached_cost = (cached_input / 1000.0) * (
        info.cached_input_per_1k
        if hasattr(info, "cached_input_per_1k")
        else info.input_per_1k
    )
    output_cost = (total_output_tokens / 1000.0) * info.output_per_1k

    total_cost = input_cost + cached_cost + output_cost
    if ds.num_posts > 0:
        cost_per_1k_posts = total_cost / (ds.num_posts / 1000.0)
    else:
        cost_per_1k_posts = 0.0

    return CostEstimate(
        prompt_label=prompt_label,
        model=model_name,
        dataset=ds.name,
        num_posts=ds.num_posts,
        batch_size=batch_size,
        prompt_tokens=cfg.prompt_tokens,
        avg_post_tokens=ds.avg_post_tokens,
        avg_output_tokens=cfg.output_tokens,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        cache_fraction=cache_fraction,
        cost_usd=round(total_cost, 6),
        cost_per_1k_posts_usd=round(cost_per_1k_posts, 6),
        throughput_posts_per_hour=throughput,
        est_hours=round(est_hours, 3),
    )


def write_csv(path: Path, rows: Iterable[CostEstimate]) -> None:
    """
    Write cost estimates to CSV.

    Args:
        path: Output CSV path.
        rows: Iterable of CostEstimate rows.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "prompt_label",
        "model",
        "dataset",
        "num_posts",
        "batch_size",
        "prompt_tokens",
        "avg_post_tokens",
        "avg_output_tokens",
        "total_input_tokens",
        "total_output_tokens",
        "cache_fraction",
        "cost_usd",
        "cost_per_1k_posts_usd",
        "throughput_posts_per_hour",
        "est_hours",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for est in rows:
            writer.writerow(
                {
                    "prompt_label": est.prompt_label,
                    "model": est.model,
                    "dataset": est.dataset,
                    "num_posts": est.num_posts,
                    "batch_size": est.batch_size,
                    "prompt_tokens": est.prompt_tokens,
                    "avg_post_tokens": f"{est.avg_post_tokens:.2f}",
                    "avg_output_tokens": f"{est.avg_output_tokens:.2f}",
                    "total_input_tokens": f"{est.total_input_tokens:.0f}",
                    "total_output_tokens": f"{est.total_output_tokens:.0f}",
                    "cache_fraction": f"{est.cache_fraction:.2f}",
                    "cost_usd": f"{est.cost_usd:.6f}",
                    "cost_per_1k_posts_usd": (
                        f"{est.cost_per_1k_posts_usd:.6f}"
                    ),
                    "throughput_posts_per_hour": (
                        f"{est.throughput_posts_per_hour:.2f}"
                    ),
                    "est_hours": f"{est.est_hours:.3f}",
                }
            )


def parse_scenario_arg(spec: str) -> PromptScenario:
    """
    Parse a --scenario definition.

    Format:
        LABEL:prompt_tokens:output_tokens:batch_size:cache_fraction

    Args:
        spec: Scenario specification string.

    Returns:
        PromptScenario instance.

    Raises:
        SystemExit: For invalid formats or values.
    """
    parts = spec.split(":")
    if len(parts) != 5:
        raise SystemExit(
            "Invalid --scenario '{spec}'. Expected "
            "LABEL:prompt_tokens:output_tokens:batch_size:cache_fraction",
        )

    label, pt, ot, bs, cf = parts
    try:
        cfg = CostConfig(
            prompt_tokens=int(pt),
            output_tokens=int(ot),
            batch_size=int(bs),
            cache_fraction=float(cf),
        )
    except ValueError as exc:
        raise SystemExit(
            f"Invalid --scenario values in '{spec}': {exc}",
        )

    return PromptScenario(label=label, cfg=cfg)


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments for the estimator.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Estimate LLM benchmark costs for DEV, TEST, and full Stage 0."
        ),
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=list(MODEL_REGISTRY.keys()),
        help="Model keys to estimate (default: all in model_registry).",
    )
    parser.add_argument(
        "--prompt-tokens",
        type=int,
        default=350,
        help=(
            "Prompt overhead tokens per request "
            "(system, instructions, schema)."
        ),
    )
    parser.add_argument(
        "--output-tokens",
        type=int,
        default=120,
        help="Assumed average completion tokens per post.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Posts per request for estimation.",
    )
    parser.add_argument(
        "--cache-fraction",
        type=float,
        default=0.0,
        help="Fraction of input tokens billed at cached rate (0–1).",
    )
    parser.add_argument(
        "--token-model",
        type=str,
        default="gpt-5-mini",
        help="Model name for counting tokens in DEV/TEST text.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=output_csv_path(),
        help="Output path for cost_estimates.csv.",
    )
    parser.add_argument(
        "--prompt-label",
        type=str,
        default="default",
        help=(
            "Label for this prompt configuration if --scenario is not used."
        ),
    )
    parser.add_argument(
        "--scenario",
        action="append",
        metavar="LABEL:prompt:output:batch:cache",
        help=(
            "Prompt scenario definition. May be repeated. When provided, "
            "overrides --prompt-tokens/--output-tokens/--batch-size/"
            "--cache-fraction."
        ),
    )
    return parser.parse_args()


def summarize_to_log(estimates: List[CostEstimate]) -> None:
    """
    Log aggregate cost and runtime summaries.

    Args:
        estimates: List of CostEstimate rows.
    """
    if not estimates:
        return

    total_cost = sum(e.cost_usd for e in estimates)
    LOGGER.info(
        "Total estimated API cost across all configs: %.4f USD",
        total_cost,
    )

    cost_by_model: Dict[str, float] = {}
    hours_by_model: Dict[str, float] = {}
    for est in estimates:
        cost_by_model[est.model] = (
            cost_by_model.get(est.model, 0.0) + est.cost_usd
        )
        if est.est_hours > 0.0:
            hours_by_model[est.model] = (
                hours_by_model.get(est.model, 0.0) + est.est_hours
            )

    for model, cost in sorted(cost_by_model.items()):
        LOGGER.info("  %s total: %.4f USD", model, cost)

    for model, hours in sorted(hours_by_model.items()):
        LOGGER.info(
            "  %s local runtime (sum over scenarios/datasets): %.3f hours",
            model,
            hours,
        )


def main() -> int:
    """
    CLI entrypoint for benchmark cost estimation.

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    args = parse_args()

    length_profile = load_length_profile(length_profile_path())
    specs = build_dataset_specs(
        lp=length_profile,
        dev_file=dev_path(),
        test_file=test_path(),
        token_model=args.token_model,
    )

    scenarios: List[PromptScenario] = []
    if args.scenario:
        for spec in args.scenario:
            scenarios.append(parse_scenario_arg(spec))
    else:
        scenarios.append(
            PromptScenario(
                label=args.prompt_label,
                cfg=CostConfig(
                    prompt_tokens=args.prompt_tokens,
                    output_tokens=args.output_tokens,
                    batch_size=args.batch_size,
                    cache_fraction=args.cache_fraction,
                ),
            )
        )

    estimates: List[CostEstimate] = []

    for model_name in args.models:
        try:
            get_model_info(model_name)
        except KeyError:
            LOGGER.warning(
                "Unknown model in --models: %s (skipping)",
                model_name,
            )
            continue

        for ds in specs:
            for scenario in scenarios:
                estimates.append(
                    estimate_for_model_dataset(
                        model_name=model_name,
                        ds=ds,
                        cfg=scenario.cfg,
                        prompt_label=scenario.label,
                    )
                )

    if not estimates:
        LOGGER.warning("No cost estimates produced.")
        return 1

    write_csv(args.output_csv, estimates)
    summarize_to_log(estimates)
    LOGGER.info("Wrote cost estimates to %s.", args.output_csv)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())