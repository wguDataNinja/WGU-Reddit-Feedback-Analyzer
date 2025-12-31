# F.4 What not to act on

This section identifies issue categories that appear in the dataset but are unlikely to justify institutional escalation within the scope of this analysis. The intent is to demonstrate analytical restraint by distinguishing between issues that are present and issues that are sufficiently stable, repeated, and specific to warrant action.

Candidates are selected deterministically as issues with fewer than five unique posts in the single-college filtered dataset. One higher-volume boundary case is intentionally included to test whether volume alone is sufficient for actionability.

## Candidate table

| normalized_issue_label | issue_total_posts | num_courses | num_colleges | top_courses_top10 |
|---|---|---|---|---|
| ai_detection_confusion_and_false_flags | 2 | 2 | 1 | C200(1); D101(1) |
| prerequisite_gaps_or_unpreparedness | 2 | 2 | 2 | C200(1); D287(1) |
| scheduling_or_simulation_availability_issues | 4 | 4 | 3 | D080(1); D577(1); D659(1); D676(1) |
| workload_or_scope_issues | 4 | 4 | 2 | C213(1); C716(1); C723(1); C958(1) |
| instructor_or_support_unresponsiveness | 10 | 6 | 3 | C211(4); D277(2); C777(1); D398(1); D464(1); D522(1) |

Low-volume issues in this table are characterized by dispersion across courses and colleges, with no repeated, specific failure mode observable within a single course. Posts associated with these issues are often episodic, time-bound, or framed around individual circumstances rather than a consistently malfunctioning instructional or platform component.

The boundary case, instructor or support unresponsiveness, has a higher total post count but remains highly heterogeneous in context. Sampled posts reference delayed responses, holiday timing, evaluator turnaround, retake approvals, and scheduling constraints. The absence of a single repeated operational mechanism prevents this issue from being interpreted as a coherent, actionable institutional pattern within this snapshot.

## Sampling manifest

All candidate issues are fully sampled using deterministic post selection. Every post_id listed in `F4_sampling_manifest.jsonl` is reviewed against the original Stage 0 text to confirm the absence of repeated failure modes and to document contextual variability.

Non-action classification does not imply that student experiences are invalid or unimportant. It reflects only that, within this frozen Reddit snapshot, the observed signal is too sparse, dispersed, or context-dependent to support escalation. Reclassification would be appropriate under expanded, longitudinal, or corroborating data.

See `F4_sampling_manifest.jsonl`.