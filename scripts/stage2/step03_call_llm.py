# filename: step03_call_llm.py

"""Call OpenAI to cluster new pain points into existing cluster structure."""

from typing import List, Dict
from time import sleep
import re
import json

from openai import OpenAI
from utils.logger import setup_logger, get_timestamp_str
from scripts.stage2.config_stage2 import (
    MODEL_NAME,
    MAX_RETRIES,
    RETRY_SLEEP_SECONDS,
)
from scripts.stage2.step02_prepare_prompt_data import format_clusters, format_pain_points

from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
logger = setup_logger("call_llm", filename="stage2.log")
from pydantic import BaseModel
from typing import Literal, Optional

class ClusterAction(BaseModel):
    pain_point_id: str
    action: Literal["assign", "new"]
    cluster_id: Optional[str] = None
    cluster_title: Optional[str] = None
    root_cause_summary: Optional[str] = None


PROMPT = """You are organizing student pain points from social media posts to present to the course design team for course {course}.

You will receive a small batch of pain points. Your task is to group them into distinct clusters based on root cause — the underlying issue that the course team could address.

If clusters already exist, they are listed below. Each includes:
  - cluster_id
  - title
  - root cause summary
  - number of posts

For each pain point:
- Assign it to an existing cluster if the root cause matches
- If it nearly fits, you may assign it and suggest a broader title and summary to better reflect the updated scope
- If it doesn’t fit any, propose a new cluster

Avoid fragmentation by reusing clusters when possible. Every pain point must be clustered.

Avoid creating unnecessary new clusters. Favor assignment and renaming existing clusters if the issue is broadly related.

Return ONE compact JSON object per pain point.  
Use the exact `pain_point_id` from the input. Do not rename, abbreviate, or simplify it.

Format:
{{
  "pain_point_id": "...",
  "action": "assign" | "new",
  "cluster_id": "COURSE_#" | null,
  "cluster_title": "..." | null,
  "root_cause_summary": "..." | null
}}

If action is "assign" and you propose a new cluster title or summary, include them. Otherwise, leave them null.

Existing clusters:
{existing_clusters}

Pain points:
{pain_points_block}
"""


# filename: step03_call_llm.py

# scripts/stage2/step03_call_llm.py

def call_llm(course: str, clusters: List[Dict], batch: List[Dict]) -> List[Dict]:
    import re

    print(f" call_llm() running for course={course} ")
    prompt = PROMPT.format(
        course=course,
        existing_clusters=format_clusters(clusters),
        pain_points_block=format_pain_points(batch)
    )
    messages = [
        {"role": "system", "content": "Respond with one JSON object per pain point. No preamble, no commentary. Just JSON blocks."},
        {"role": "user", "content": prompt}
    ]

    print(f"[call_llm] Starting call for course={course}, batch_size={len(batch)}", flush=True)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
            text = response.choices[0].message.content.strip()

            print("\nFULL LLM RAW RESPONSE (first 1000 chars):\n", flush=True)
            print(text[:1000], flush=True)

            # Remove markdown code block fences
            text_clean = text.replace("```json", "").replace("```", "").strip()

            # Use regex to extract JSON objects, even multiline
            raw_blocks = re.findall(r'\{(?:[^{}]|\n|\r)*?\}', text_clean, re.DOTALL)
            print(f"\n[call_llm] Found {len(raw_blocks)} JSON-ish blocks\n", flush=True)

            actions = []
            for i, block in enumerate(raw_blocks):
                print(f"\n[block {i}] Attempting parse:\n{block[:200]}", flush=True)
                try:
                    validated = ClusterAction.model_validate_json(block.strip())
                    actions.append(validated.model_dump())
                    print(f"[block {i}] ✅ Parsed successfully", flush=True)
                except Exception as e:
                    print(f"[block {i}] ❌ Parse failed: {e}", flush=True)

            if not actions:
                print(f"[call_llm] ❌ No valid blocks parsed for course={course}", flush=True)
                raise ValueError("No valid ClusterActions parsed from LLM response.")

            print(f"[call_llm] ✅ Success: {len(actions)} actions parsed for course={course}", flush=True)
            return actions

        except Exception as e:
            print(f"[call_llm] ❌ LLM call failed on attempt {attempt}: {e}", flush=True)
            if attempt < MAX_RETRIES:
                sleep(RETRY_SLEEP_SECONDS)
            else:
                raise
