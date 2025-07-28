# Filename: scripts/stage2/step03_call_llm.py

import os
import json
from typing import List, Dict, Any
from time import sleep

from pydantic import BaseModel
from openai import OpenAI

from utils.logger import setup_logger
from scripts.stage2.config_stage2 import MODEL_NAME, MAX_RETRIES, RETRY_SLEEP_SECONDS
from scripts.stage2.step02_prepare_prompt_data import format_pain_points
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
logger = setup_logger("call_llm", filename="stage2.log")


class Cluster(BaseModel):
    cluster_id: str
    title: str
    root_cause_summary: str
    pain_point_ids: List[str]


class FinalOutput(BaseModel):
    course: str
    clusters: List[Cluster]


def get_openai_json_schema() -> Dict[str, Any]:
    schema = FinalOutput.model_json_schema()
    def fix(s: Any):
        if isinstance(s, dict) and s.get("type") == "object":
            s["additionalProperties"] = False
            if "properties" in s:
                s["required"] = list(s["properties"].keys())
        if isinstance(s, dict):
            for v in s.values():
                fix(v)
        elif isinstance(s, list):
            for item in s:
                fix(item)
    fix(schema)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "stage2_output",
            "description": "Final clustered output schema",
            "schema": schema,
            "strict": True
        }
    }

FULL_BATCH_PROMPT = """You will produce exactly one JSON object matching the FinalOutput schema. No extra text.

These are student pain points for course {course}:

{pain_points_block}

Your job is to group them by root cause for curriculum designers:

1. Determine each pain point that has a real, fixable root cause (not just venting).
2. Create clusters and assign each pain point to its cluster.

Return exactly this JSON structure:
{{
  "course": "{course}",
  "clusters": [
    {{
      "cluster_id": "{course}_1",
      "title": "cluster title",
      "root_cause_summary": "summary of the root cause",
      "pain_point_ids": ["id1", "id2"]
    }}
  ]
}}

Use strict JSON only, matching the schema. No additional fields or comments."""


def call_llm_full(course: str, clusters: List[Dict], pain_points: List[Dict], verbose: bool = False) -> Dict:
    prompt = FULL_BATCH_PROMPT.format(
        course=course,
        pain_points_block=format_pain_points(pain_points)
    )
    messages = [
        {"role": "system", "content": "Respond only with valid JSON matching the schema."},
        {"role": "user", "content": prompt}
    ]
    if verbose:
        logger.debug(f"[call_llm_full] Prompt length: {len(prompt)} characters")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                response_format=get_openai_json_schema(),
                temperature=0
            )
            content = response.choices[0].message.content.strip()
            parsed = json.loads(content)
            return FinalOutput.model_validate(parsed).model_dump()
        except Exception as e:
            if attempt < MAX_RETRIES:
                sleep(RETRY_SLEEP_SECONDS)
            else:
                raise