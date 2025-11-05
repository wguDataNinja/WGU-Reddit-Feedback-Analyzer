PROMPT_CLASSIFY_PAINPOINT_FEWSHOT = """
Task: Classify whether the Reddit post contains a course-related pain point.

Definition: A pain point is a negative experience caused by the course’s design, delivery, or support. It must include an identifiable or implied root cause — something fixable by the course team.

Examples:

Post: "The OA instructions were really unclear. I didn’t know where to upload the lab."
→ Pain Point: Yes

Post: "I was nervous to take the course because people said it was hard."
→ Pain Point: No

Post: "The pacing of the course was fine. I just wish I’d started earlier."
→ Pain Point: No

Now classify this post:

Post:
{POST_TEXT}

→ Pain Point:
"""