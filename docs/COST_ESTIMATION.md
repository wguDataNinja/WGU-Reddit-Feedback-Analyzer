WGU Reddit Analyzer – Cost Estimation Guide

Last updated: 2025-11-19

============================================================
1 · Purpose

Defines how benchmark costs and runtimes are estimated before a run and measured afterward.
Includes:

• API pricing from model_registry.py
• Prompt token overhead
• Real observed API usage from Stage 1 benchmark runs
• Comparison between projected and observed cost behavior

============================================================
2 · Inputs

• artifacts/analysis/length_profile.json
• benchmark/model_registry.py
• benchmark/cost_latency.py
• benchmark/estimate_benchmark_cost.py
• prompts/ (all prompt templates)
• configs/*.yml

============================================================
3 · Estimation Phases

3.1 Pre-Run (Static)
Uses mean post length, prompt tokens, expected output length.

3.2 Post-Run (Observed)
Uses actual logged tokens from each model call:
input tokens, output tokens, and total cost.

============================================================
4 · Cost Formula

For model m, prompt p, dataset D:

cost(m,p,D) ≈ N_D · [ (T_prompt + T_post)/1000 · c_in(m)
+ T_out/1000 · c_out(m) ]

Where:
N_D = number of posts
c_in, c_out = input/output cost per 1k tokens

Local models have cost = 0 but non-zero runtime.

============================================================
5 · Benchmark Cost Artifacts

Pre-run:
artifacts/benchmark/cost_estimates.csv

Post-run:
artifacts/benchmark/final_cost_summary.json

Columns include:
model, dataset, prompt_label, num_posts, cost_usd, tokens_in, tokens_out, seconds_elapsed.

============================================================
6 · CLI Usage

Single scenario:

python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost 
–prompt-label zero_shot –prompt-tokens 260

Multiple scenarios:

python -m wgu_reddit_analyzer.benchmark.estimate_benchmark_cost 
–scenario zero_shot:260:120:4:0.0 
–scenario few_shot_simple:420:120:4:0.0 
–scenario few_shot_opt:600:140:4:0.0

============================================================
7 · Observed Costs (DEV runs to date)

The following are real API charges from all DEV runs performed so far
(most were 2–5 post smoke tests, plus the full 25-post zero-shot run).

gpt-5
• Input tokens total: 0.018 USD
• Output tokens total: 0.127 USD
• Notes: Most expensive model; output dominates cost.

gpt-5-mini
• Input tokens total: 0.003 USD
• Output tokens total: 0.029 USD
• Notes: 4–5× cheaper than gpt-5 per call.

gpt-5-nano
• Input tokens total: 0.003 USD
• Output tokens total: 0.081 USD
• Notes: Cheaper input, but surprisingly high output cost due to verbose responses.

llama3
• Input/output: 0.000 USD (local)
• Notes: Only time cost matters; runs ~1000 posts/hour CPU-only.

gpt-4o-mini
• Not included in this summary yet, but prior runs show very low cost per call.

============================================================
8 · Interpretation of Observed Costs

• Even with multiple DEV smoke tests, total spend stays extremely low.
• The 25-post zero-shot sweep across five models cost well below 0.50 USD.
• Output tokens dominate cost for OpenAI models, especially gpt-5 and gpt-5-nano.
• Few-shot prompts will increase input tokens but often reduce output verbosity,
potentially lowering total cost.
• llama3 continues to be effectively free, but slow.

============================================================
9 · Summary

• Pre-run formulas work well for rough planning.
• Real observed usage is now tracked, enabling reliable cost prediction for full DEV/TEST.
• All Stage 1 runs (zero-shot and upcoming few-shot) are economically trivial.
• Cost-efficiency evaluation is now part of the Stage 1 prompt-evolution workflow.

============================================================
END OF FILE