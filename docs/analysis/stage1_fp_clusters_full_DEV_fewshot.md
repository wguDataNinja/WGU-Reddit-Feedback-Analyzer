Stage-1 FP Cluster Analysis — Full DEV, Few-Shot Prompt

Date: 2025-11-21
Prompt: s1_few.txt
Scope: All models (llama3, gpt-5-nano, gpt-5-mini, gpt-5)
Dataset: Full DEV (135 posts × 4 models = 540 predictions)

⸻

1. Purpose

This document summarizes the false positive patterns observed across all models on the full DEV dataset using the few-shot v1 prompt.

The goal is to identify the dominant FP categories that must be addressed in s1_optimal.txt.
This analysis is cross-model and prompt-focused — not tied to any single run.

⸻

2. High-Level Summary

Across all four models, FPs fall into a small, stable set of themes.
There are no model-specific FP types.
Differences between models are primarily frequency, not type.

The shared FP clusters:
	1.	emotional struggle / discouragement / OA fear
	2.	requests for tips, resources, or study advice
	3.	policy, process, and program-level questions
	4.	assignment confusion, rubric interpretation, or debugging help
	5.	celebration / success / “I passed” posts
	6.	out-of-scope external exam or proctoring issues
	7.	borderline “this class is disorganized” posts without a concrete course defect

The few-shot prompt reduces FP counts vs zero-shot, but all models still over-trigger on these same categories.

⸻

3. FP Cluster Breakdown

3.1 Struggle / discouragement / OA anxiety

Most common FP category across all models.

Typical structure:
	•	“This class is kicking my ass.”
	•	“I failed the OA twice and I’m devastated.”
	•	“I’m overwhelmed by D066/D076/D315/D335.”
	•	“Proctored tests make me anxious.”

Characteristics:
	•	Strong emotion: fear, stress, embarrassment.
	•	No explicit claim that the course design or materials are defective.
	•	Often includes “any advice” at the end.

Reason these are FPs:
	•	Difficulty ≠ pain point.
	•	Stage-1 requires a concrete, fixable course or system issue.

⸻

3.2 Study tips / resources / strategy requests

Second most common FP category.

Examples:
	•	“Any tips for C190 / C721 / C723 / D076?”
	•	“How do I pass D335?”
	•	“What study resources work for this class?”

Characteristics:
	•	Purely about study tactics.
	•	Often framed as: “I’m struggling, what should I do?”

Reason these are FPs:
	•	Asking for help is not a course defect.
	•	The few-shot prompt does not yet explicitly prohibit treating these as pain points.

⸻

3.3 Policy, process, and program-level questions

Examples:
	•	“What happens if I don’t finish tasks before the class end date?”
	•	“When should I take the pre-assessment?”
	•	“BSBAA program changes — do I still need D075?”
	•	“Will WGU think my paper is AI-generated?”

Characteristics:
	•	All about mentors, deadlines, term structure, academic integrity rules, etc.

Reason these are FPs:
	•	Stage-1 only tracks course pain points.
	•	These posts are about WGU policy, not course design.

⸻

3.4 Assignment confusion, evaluator feedback, and debugging help

Examples:
	•	Confusion about C216 Capstone projections.
	•	C773 evaluator feedback misread.
	•	D197 screenshot instructions.
	•	D277 JS validation bugs.
	•	D288 Angular / mapping issues.
	•	D602 mlflow vs subprocess confusion.

Characteristics:
	•	Students are stuck or debugging; rarely claim the course is wrong.
	•	“What am I missing?” or “My code isn’t working.”

Reason these are FPs:
	•	Being stuck is not a structural course defect.
	•	Few-shot prompt does not differentiate “I’m confused” from “the rubric/materials are broken.”

⸻

3.5 Celebration and “I passed” posts

Examples:
	•	“I passed C722 first try.”
	•	“Passed C724.”
	•	“Finally passed C960!!”
	•	“SSCP certification done.”
	•	D337 brag post.

Reason these are FPs:
	•	Short negative phrasing (“hard,” “stressful”) often appears, but the post is fundamentally positive.
	•	Not actionable as pain point data.

⸻

3.6 External exam and proctoring issues (out of scope)

Examples:
	•	Long ITIL v4 / SSCP / CySa+ / Pentest exam stories.
	•	Third-party proctoring demands.
	•	Issues with external cert workflows.

Reason these are FPs:
	•	These exams are not WGU courses.
	•	Pain points are valid, but outside Stage-1’s defined domain.

⸻

3.7 Borderline “course is disorganized / instructor unhelpful” posts

Examples:
	•	“D366 is wrecking me, so disorganized, instructor doesn’t care.”
	•	“Study guide is huge, cohorts missing.”

Characteristics:
	•	Express dissatisfaction with course organization or support.
	•	Still mostly framed around “how do I pass?” or “what resources should I use?”

Reason these are still FPs under gold labels:
	•	Gold labels appear to require explicit course defects:
	•	contradictory rubric
	•	broken materials
	•	outdated or missing required content
	•	evaluator inconsistency
	•	platform bugs

If the post does not state such a defect, annotators marked it “n”.

⸻

4. Model-Level Behavior Summary

All four models:
	•	show the same FP clusters
	•	differ only in how aggressively they over-trigger
	•	gained precision from few-shot but still misfire on the same themes

There is no need for model-specific prompt adjustments.
A single tightened prompt should improve all four.

⸻

5. Implications for s1_optimal.txt

To fix these FPs, the next prompt must:
	1.	Require a specific, course-related defect or barrier for “y”.
	2.	Explicitly tell the model to answer “n” when the post is primarily:
	•	struggle / discouragement
	•	fear of OA or anxiety
	•	study tips / resource requests
	•	debugging help or assignment confusion without clear course defects
	•	celebration / brag / reflection posts
	•	policy / mentor / program / term-date questions
	•	external exam or proctoring issues
	3.	Clarify borderline cases:
	•	Only label “y” when the student directly links their difficulty to a concrete flaw in course design, assessment design, evaluator behavior, or platform functionality.
	4.	Possibly include 1–2 negative examples for:
	•	policy posts
	•	debugging posts
	•	celebration posts

This will be the foundation for the next prompt-iteration (s1_optimal).

⸻

6. Next Steps
	•	Draft and test s1_optimal.txt on the fixed DEV-25 subset.
	•	Verify FP reduction on the full DEV panel.
	•	Freeze the prompt, then run full TEST evaluation.