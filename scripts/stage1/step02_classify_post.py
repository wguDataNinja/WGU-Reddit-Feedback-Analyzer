# scripts/stage1/step02_classify_post.py

"""LLM classification of a single Reddit post into pain points."""

import time
from typing import Dict
from pydantic import BaseModel, ValidationError
from scripts.stage1.config_stage1 import MODEL_NAME, MAX_RETRIES, RETRY_SLEEP_SECONDS
from utils.logger import setup_logger
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)  #

logger = setup_logger("classify_post")


PROMPT = """Definitions:

A 'pain point' is a negative user experience that a student encounters in a course, 
traceable to how the course is designed, delivered, or supported.

A pain point must be directly tied to the course, with a potential 'root cause'.

A 'root cause' is the stated or implied fixable deficiency in the course 
that contributed to the student’s negative experience. It must be something the course designer could reasonably improve.

⸻

Your Task

You are a course designer reviewing Reddit posts about course {course_code}.
1. Decide if the post contains one or more distinct pain points.
2. For each pain point:
• Summarize the student’s struggle in one sentence.
• Identify the root cause.
• Include a short, relevant, quoted snippet from the post that captures the issue in their own words.

Merge multiple complaints into a single pain point if they share the same root cause.

⸻

If no course-related pain points are present:

{{
  "num_pain_points": 0
}}

⸻

Example Post

Confusing OA instructions  
"I kept putting off the OA because I didn’t know where or how to submit the lab. The course page never explained it clearly."

⸻

Example Output

{{
  "num_pain_points": 1,
  "pain_points": [
    {{
      "pain_point_summary": "The student delayed the OA due to unclear submission instructions.",
      "root_cause": "unclear OA instructions",
      "quoted_text": "I didn’t know where or how to submit the lab."
    }}
  ]
}}
"""

class PainPoint(BaseModel):
    pain_point_summary: str
    root_cause: str
    quoted_text: str

class PainPointOutput(BaseModel):
    num_pain_points: int
    pain_points: list[PainPoint]

class NoPainPointOutput(BaseModel):
    num_pain_points: int

def classify_post(post_id: str, course: str, text: str) -> Dict:
    system_msg = { "role": "system", "content": "You are a course designer extracting course-related pain points from Reddit student posts." }
    user_msg = {
        "role": "user",
        "content": PROMPT.format(course_code=course) + f"\n\nCourse: {course}\n\nPost:\n{text}"
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[system_msg, user_msg],
                temperature=0
            )
            raw = response.choices[0].message.content.strip()
            parsed = eval(raw)  # ! Replace with `json.loads()` once output is always valid JSON

            if parsed["num_pain_points"] == 0:
                return {
                    "post_id": post_id,
                    "course": course,
                    "num_pain_points": 0,
                    "pain_points": []
                }

            # Add pain_point_id
            enriched = []
            for i, p in enumerate(parsed["pain_points"]):
                p["pain_point_id"] = f"{post_id}_{i}"
                enriched.append(p)

            return {
                "post_id": post_id,
                "course": course,
                "num_pain_points": parsed["num_pain_points"],
                "pain_points": enriched
            }

        except Exception as e:
            logger.error(f"post_id={post_id} failed on attempt {attempt} - {e}")
            if attempt == MAX_RETRIES:
                return {
                    "post_id": post_id,
                    "course": course,
                    "num_pain_points": -1,
                    "error": str(e),
                    "pain_points": []
                }
            time.sleep(RETRY_SLEEP_SECONDS)
