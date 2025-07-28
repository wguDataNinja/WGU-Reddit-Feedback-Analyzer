# scripts/stage1/step02_classify_post.py

"""LLM classification of a single Reddit post into pain points."""

import time
import json
from typing import Dict
from pydantic import BaseModel, ValidationError
from scripts.stage1.config_stage1 import MODEL_NAME, MAX_RETRIES, RETRY_SLEEP_SECONDS
from utils.logger import setup_logger
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
import logging
logger = setup_logger("classify_post", filename="stage1.log", to_console=True, verbose=True)  # Toggle verbose here
PROMPT = """Definitions:

A 'pain point' is a negative user experience that a student encounters in a course, 
traceable to how the course is designed, delivered, or supported. It is not just venting or expressing frustration.

A pain point must be directly tied to the course, with a potential 'root cause'.

A 'root cause' is the stated or implied fixable deficiency in the course 
that contributed to the student's negative experience. It must be something the course designer could reasonably improve.

⸻

Your Task

You are a course designer reviewing Reddit posts about course {course_code}.
1. Decide if the post contains one or more distinct pain points.
2. For each pain point:
• Summarize the student's struggle in one sentence.
• Identify the root cause.
• Include a short, relevant, quoted snippet from the post that captures the issue in their own words.

Merge multiple complaints into a single pain point if they share the same root cause.

⸻
"I was scared to take this course, I heard it's really hard" - this is NOT a pain point, as there's no root cause. 


If no course-related pain points are present:

{{
  "num_pain_points": 0
}}

⸻

Example Post

Confusing OA instructions  
"I kept putting off the OA because I didn't know where or how to submit the lab. The course page never explained it clearly."


⸻

Example Output

{{
  "num_pain_points": 1,
  "pain_points": [
    {{
      "pain_point_summary": "The student delayed the OA due to unclear submission instructions.",
      "root_cause": "unclear OA instructions",
      "quoted_text": "I didn't know where or how to submit the lab."
    }}
  ]
}}

You must respond with valid JSON that matches this exact structure.
"""

class PainPoint(BaseModel):
    pain_point_summary: str
    root_cause: str
    quoted_text: str

class PainPointOutput(BaseModel):
    num_pain_points: int
    pain_points: list[PainPoint]

def get_json_schema():
    schema = PainPointOutput.model_json_schema()

    def enforce_openai_rules(obj):
        if isinstance(obj, dict):
            if obj.get("type") == "object":
                obj["additionalProperties"] = False
                if "properties" in obj:
                    obj["required"] = list(obj["properties"].keys())
            for v in obj.values():
                enforce_openai_rules(v)
        elif isinstance(obj, list):
            for item in obj:
                enforce_openai_rules(item)

    enforce_openai_rules(schema)

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "pain_point_extraction",
            "description": "Extract pain points from student Reddit posts",
            "schema": schema,
            "strict": True
        }
    }
# scripts/stage1/step02_classify_post.py

def classify_post(post_id: str, course: str, text: str) -> Dict:
    system_msg = {
        "role": "system",
        "content": "You are a course designer extracting course-related pain points from Reddit student posts. You must respond with valid JSON matching the specified schema."
    }
    user_msg = {
        "role": "user",
        "content": PROMPT.format(course_code=course) + f"\n\nCourse: {course}\n\nPost:\n{text}"
    }

    for attempt in range(1, 3):  # max 2 tries
        try:
            logger.debug(f"Sending classification request (attempt {attempt}) for post_id={post_id}")
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[system_msg, user_msg],
                    response_format=get_json_schema(),
                    temperature=0,
                    timeout=10
                )
            except Exception as schema_error:
                logger.warning(f"Schema mode failed for post_id={post_id}, using JSON mode: {schema_error}")
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[system_msg, user_msg],
                    response_format={"type": "json_object"},
                    temperature=0,
                    timeout=10
                )

            raw_content = response.choices[0].message.content

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Raw LLM response for post_id={post_id}:\n{raw_content}")

            try:
                json_data = json.loads(raw_content)
            except json.JSONDecodeError as decode_error:
                logger.error(f"JSON decode failed for post_id={post_id}: {decode_error}")
                logger.debug(f"Raw response that failed decoding:\n{raw_content}")
                raise

            if json_data.get("num_pain_points", 0) == 0:
                json_data["pain_points"] = []

            parsed = PainPointOutput(**json_data)

            enriched = [
                {
                    "pain_point_id": f"{post_id}_{i}",
                    "pain_point_summary": p.pain_point_summary,
                    "root_cause": p.root_cause,
                    "quoted_text": p.quoted_text,
                }
                for i, p in enumerate(parsed.pain_points)
            ]

            logger.info(f"Extracted {parsed.num_pain_points} pain points from post_id={post_id}")
            return {
                "post_id": post_id,
                "course": course,
                "num_pain_points": parsed.num_pain_points,
                "pain_points": enriched,
            }

        except (json.JSONDecodeError, ValidationError, Exception) as e:
            logger.error(f"post_id={post_id} failed on attempt {attempt}: {type(e).__name__}: {e}")
            if attempt < 2:
                logger.debug(f"Retrying post_id={post_id} (attempt {attempt + 1}) after sleeping 2s")
                time.sleep(2)

    logger.error(f"All attempts failed for post_id={post_id}")
    return {
        "post_id": post_id,
        "course": course,
        "num_pain_points": -1,
        "error": "All attempts failed",
        "pain_points": [],
    }