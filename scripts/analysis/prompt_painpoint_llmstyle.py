PROMPT_CLASSIFY_PAINPOINT_LLMSTYLE = """Definitions:

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

{
  "num_pain_points": 0
}

⸻

Example Post

Confusing OA instructions  
"I kept putting off the OA because I didn't know where or how to submit the lab. The course page never explained it clearly."

⸻

Example Output

{
  "num_pain_points": 1,
  "pain_points": [
    {
      "pain_point_summary": "The student delayed the OA due to unclear submission instructions.",
      "root_cause": "unclear OA instructions",
      "quoted_text": "I didn't know where or how to submit the lab."
    }
  ]
}

You must respond with valid JSON that matches this exact structure.
"""