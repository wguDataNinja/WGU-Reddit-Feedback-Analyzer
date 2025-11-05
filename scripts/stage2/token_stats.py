# filename: scripts/stage2/token_totals.py

import json
from pathlib import Path
import tiktoken
from statistics import mean

MODEL_NAME = "gpt-4o-mini"

def count_tokens(text: str, model: str = MODEL_NAME) -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def summarize_token_totals(dir_path: str):
    dir_path = Path(dir_path)
    files = sorted(dir_path.glob("*.jsonl"))

    if not files:
        print("No JSONL files found.")
        return

    token_counts = []

    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            content_blocks = []
            for line in lines:
                if not line.strip():
                    continue
                data = json.loads(line)
                summary = data.get("pain_point_summary", "")
                quoted = data.get("quoted_text", "")
                content_blocks.append(f"{summary}\n{quoted}")
            full_text = "\n---\n".join(content_blocks)
            token_counts.append(count_tokens(full_text))
        except Exception:
            continue  # silently skip errors

    if not token_counts:
        print("No valid data to summarize.")
        return

    print("Each input file in 'pain_points_by_course' was counted by tokens and summary stats are:")
    print(f"- Total files:   {len(token_counts)}")
    print(f"- Total tokens:  {sum(token_counts)}")
    print(f"- Max tokens:    {max(token_counts)}")
    print(f"- Min tokens:    {min(token_counts)}")
    print(f"- Avg tokens:    {mean(token_counts):.2f}")

if __name__ == "__main__":
    summarize_token_totals("/outputs/.old/stage2/pain_points_by_course")