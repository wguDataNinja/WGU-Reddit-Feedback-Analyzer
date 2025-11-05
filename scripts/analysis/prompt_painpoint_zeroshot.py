PROMPT_CLASSIFY_PAINPOINT_ZERO = """
Task: Determine if the following Reddit post contains a *course-related pain point*.

Definition: A pain point is a negative user experience caused by how the course is designed, delivered, or supported. It must have a fixable root cause — not just general frustration.

Respond with one of:
- "Yes" if the post contains a course-related pain point.
- "No" if it does not.

Post:
{POST_TEXT}
"""