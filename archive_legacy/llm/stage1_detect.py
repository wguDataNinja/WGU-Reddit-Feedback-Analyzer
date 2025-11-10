# llm/stage1_detect.py
from __future__ import annotations
import os, json, pathlib, yaml, time
from typing import Any, Dict, Iterable, List
from utils.config_loader import ROOT
from utils.llm_runner import LLMRunner

SYSTEM = (
    "Return ONLY JSON with fields num_pain_points:int and "
    "pain_points:list (each item has pain_point_summary, root_cause, quoted_text)."
)

SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "num_pain_points": {"type": "integer"},
        "pain_points": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["num_pain_points", "pain_points"],
    "additionalProperties": True
}

def _resolve(p: str) -> str:
    return str((ROOT / p).resolve()) if not os.path.isabs(p) else p

def _read_yaml(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.is_absolute(): p = (ROOT / path).resolve()
    with open(p, "r") as f: return yaml.safe_load(f)

def _read_jsonl(path: str) -> Iterable[dict]:
    with open(path, "r") as f:
        for ln in f:
            s = ln.strip()
            if s: yield json.loads(s)

def _write_jsonl(path: str, rows: Iterable[dict]) -> None:
    p = pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")

def _format_prompt(tmpl: str, row: dict) -> str:
    title = (row.get("title") or "").strip()
    body  = (row.get("selftext") or row.get("text") or "").strip()
    text  = (title + ("\n\n" if title and body else "") + body).strip()
    # support {text} or {post_text}
    return tmpl.format(course_code=row.get("course_code",""), text=text, post_text=text)

class Stage1Detect:
    def __init__(self, cfg_path: str = "configs/config.yaml"):
        raw = _read_yaml(cfg_path)
        s1 = raw.get("stage1", {})
        self.provider = s1.get("provider", "openai")
        # prefer explicit model; else models.{provider}.{strength}
        if s1.get("model"):
            model_name = s1["model"]
        else:
            strength = s1.get("strength", "weak")
            model_name = raw["models"][self.provider][strength]
        self.model_id = f"{self.provider}:{model_name}"

        self.prompt_path = _resolve(s1.get("prompt_file", "llm/prompts/s1_v01_zero.txt"))
        self.input_dev   = _resolve(s1["input_dev"])
        self.input_test  = _resolve(s1["input_test"])
        self.output_dir  = _resolve(s1.get("output_dir", "output/tmp/stage1"))
        self.max_rows    = s1.get("max_rows")  # None = full

        self.prompt_tmpl = pathlib.Path(self.prompt_path).read_text(encoding="utf-8").strip()
        self.runner = LLMRunner()

    def _out_path(self, split: str) -> str:
        pslug = pathlib.Path(self.prompt_path).stem
        model_name = self.model_id.split(":",1)[1]
        out_dir = pathlib.Path(self.output_dir) / split / self.provider / model_name / pslug
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / "pain_points.jsonl")

    def run_split(self, split: str) -> str:
        inp = self.input_dev if split.lower()=="dev" else self.input_test
        rows = list(_read_jsonl(inp))
        if isinstance(self.max_rows, int): rows = rows[: self.max_rows]

        preds: List[dict] = []
        for r in rows:
            up = _format_prompt(self.prompt_tmpl, r)
            out = self.runner.run_json(
                user_prompt=up,
                system_prompt=SYSTEM,
                schema=SCHEMA,
                model_id=self.model_id,
                seed=1,
            )
            n = out.get("num_pain_points")
            pts = out.get("pain_points") or []
            if not isinstance(n, int): n = len(pts) if isinstance(pts, list) else 0
            preds.append({
                "post_id": r.get("post_id"),
                "course_code": r.get("course_code"),
                "num_pain_points": max(0, int(n)),
                "pain_points": pts if isinstance(pts, list) else [],
            })

        out_path = self._out_path(split)
        _write_jsonl(out_path, preds)
        man = {
            "split": split,
            "model_id": self.model_id,
            "provider": self.provider,
            "prompt_file": self.prompt_path,
            "input_file": inp,
            "output_file": out_path,
            "count": len(preds),
            "timestamp": int(time.time()),
        }
        pathlib.Path(out_path).with_name("run_manifest.json").write_text(json.dumps(man, indent=2))
        return out_path

# ---- run on import? no. run when executed directly ----
if __name__ == "__main__":
    s = Stage1Detect("configs/config.yaml")
    # Run DEV then TEST; skip if file missing
    for split, path in [("dev", s.input_dev), ("test", s.input_test)]:
        if pathlib.Path(path).exists():
            outp = s.run_split(split)
            print(f"{split.upper()} predictions -> {outp}")
        else:
            print(f"{split.upper()} skipped (missing input): {path}")