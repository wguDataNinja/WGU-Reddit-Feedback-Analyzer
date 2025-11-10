from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except Exception as e:
    raise RuntimeError("Install pyyaml: pip install pyyaml") from e

# Detect repo root; override with WGU_REDDIT_ROOT if desired
DETECTED_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(os.getenv("WGU_REDDIT_ROOT", DETECTED_ROOT))
CFG_PATH = PROJECT_ROOT / "configs" / "config.yaml"

def _load() -> Dict[str, Any]:
    with CFG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _abspath(p: str | None) -> str | None:
    if p is None:
        return None
    pth = Path(p)
    return str(pth if pth.is_absolute() else (PROJECT_ROOT / pth))

_cfg = _load()

# prefer stage1.output_dir; else fall back to io.output_root/tmp/stage1
_stage1_out = _cfg.get("stage1", {}).get("output_dir")
_output_root = _cfg.get("io", {}).get("output_root", "output/")
if not _stage1_out:
    _stage1_out = str(Path(_output_root) / "tmp" / "stage1")

CONFIG: Dict[str, Any] = {
    "provider": _cfg.get("stage1", {}).get("provider", "ollama"),
    "model": _cfg.get("stage1", {}).get("model", "llama3"),
    "ollama_base_url": _cfg.get("models", {}).get("ollama", {}).get("base_url", "http://localhost:11434/v1"),
    "openai_api_key_env": _cfg.get("models", {}).get("openai", {}).get("api_key_env", "OPENAI_API_KEY"),

    "input_dev": _abspath(_cfg.get("stage1", {}).get("input_dev")),
    "input_test": _abspath(_cfg.get("stage1", {}).get("input_test")),
    "output_dir": _abspath(_stage1_out),
    "extra_manifest_path": _abspath(_cfg.get("stage1", {}).get("manifest_path")),

    "default_prompt": str(PROJECT_ROOT / "llm" / "prompts" / "s1_v01_zero.txt"),
    "max_rows": _cfg.get("stage1", {}).get("max_rows", None),
    "debug": _cfg.get("stage1", {}).get("debug", False),
}