# Changelog

All notable updates to the **WGU Reddit Analyzer** project are recorded here.  
This log documents the evolution from the original prototype through the structured benchmark pipeline.

---

## [v1.3.0] – 2025-11-10  
### Structured Benchmark Pipeline
#### Added
- Complete technical documentation in `docs/`
- Rewritten `README.md` describing full Stage 0–1 benchmark system
- Reorganized `src/` package architecture:
  - `fetchers/`, `utils/`, `pipeline/`, `benchmark/`, `daily/`
- Deterministic benchmark modules:
  - `build_length_profile.py` (Stage 1A)
  - `build_stratified_sample.py` (Stage 1B)
  - `label_posts.py` (Stage 1C)
- Cost and latency utilities:
  - `model_registry.py`, `cost_latency.py`, `estimate_benchmark_cost.py`
- Added prompt benchmarking support and `prompts/s1_v001.txt`

#### Changed
- Adopted installable `src/wgu_reddit_analyzer` namespace layout
- Standardized environment loading via `config_loader`
- Unified run manifests, logging, and reproducibility controls

#### Notes
- The interactive prototype (v1.1) remains available under  
  `/Users/buddy/Desktop/WGU-Reddit/prototype` for reference and future feature integration

---

## [v1.2.0] – 2025-07-30  
### Modular LLM Pipeline Transition
#### Added
- Split single-loop prototype into modular multi-stage system
- Introduced benchmark and pipeline directories for reproducible processing
- Added local SQLite database mirror (`db/WGU-Reddit.db`)
- Implemented consistent logging and manifest tracking

#### Changed
- Moved from dashboard-style app to reproducible command-line pipeline
- Introduced YAML configs and `.env`-based credentials
- Editable install via `pyproject.toml`

---

## [v1.1.0] – 2025-03-10  
### Initial Prototype Release
#### Added
- Reddit monitoring and clustering dashboard with GPT-4o-mini
- Automatic sentiment filtering and course-level feedback summaries
- Generated downloadable course reports and visuals
- Core directories: `data/`, `scripts/`, `outputs/`, `utils/`, `visuals/`

---
