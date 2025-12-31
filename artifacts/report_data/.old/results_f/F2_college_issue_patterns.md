# F.2 College-level issue patterns

This section compares issue distributions across colleges using only catalog-defined single-college courses. Candidate issue–college pairs are selected deterministically by comparing each college’s issue share to the filtered global baseline (overrepresentation ratio) and are restricted to pairs supported by at least five posts. This minimum post requirement functions as a descriptive stability safeguard rather than a statistical significance test.

## How to read this section

For each college, the tables report which normalized issues appear unusually concentrated relative to the global distribution observed in the single-college dataset. Overrepresentation ratios are used only to highlight relative differences in distribution. They do not imply causality, severity, or institutional fault. The tables define where closer inspection is warranted; validation is performed by reading the original Stage 0 post text for the deterministic post_ids listed in `F2_sampling_manifest.jsonl`.

Course concentration is assessed descriptively using the `contributing_courses_top10` field. Most retained patterns draw from multiple distinct courses. Where a pattern is driven primarily by a single course, this is explicitly noted and caveated.

## School of Business

| normalized_issue_label | college_posts | college_pct | global_pct | overrep_ratio | contributing_courses_top10 |
|---|---|---|---|---|---|
| instructor_or_support_unresponsiveness | 5 | 0.045455 | 0.028249 | 1.609091 | C211(4); D464(1) |
| assessment_material_misalignment | 32 | 0.290909 | 0.220339 | 1.320280 | C214(5); D080(3); D196(3); D351(3); D101(2); D363(2); C207(1); C211(1); C213(1); C237(1) |
| evaluator_inconsistency_or_poor_feedback | 8 | 0.072727 | 0.062147 | 1.170248 | C207(3); C200(1); D072(1); D099(1); D546(1); D652(1) |
| missing_or_low_quality_materials | 14 | 0.127273 | 0.112994 | 1.126364 | D101(3); D102(3); D103(2); C200(1); C722(1); D076(1); D554(1); D774(1); D775(1) |
| missing_or_broken_resources | 8 | 0.072727 | 0.070621 | 1.029818 | QHT1(2); C204(1); C213(1); C214(1); C723(1); D432(1); D776(1) |
| platform_or_environment_failures | 11 | 0.100000 | 0.110169 | 0.907692 | D196(5); C214(2); C216(1); D078(1); D355(1); D464(1) |
| unclear_or_ambiguous_instructions | 16 | 0.145455 | 0.209040 | 0.695823 | C716(3); AFT2(1); C204(1); C212(1); D075(1); D078(1); D196(1); D255(1); D465(1); D547(1) |

Most School of Business patterns are supported by multiple courses, particularly assessment material misalignment and missing or low-quality materials. The weakest retained pattern is instructor or support unresponsiveness, which meets the minimum post threshold but is largely driven by a single course (C211). This pattern is retained for completeness but is not interpreted as a broad college-level condition.

Sampling manifest  
See `F2_sampling_manifest.jsonl` entries where section == F2 and catalog_college == School of Business.

## School of Education

| normalized_issue_label | college_posts | college_pct | global_pct | overrep_ratio | contributing_courses_top10 |
|---|---|---|---|---|---|
| unclear_or_ambiguous_instructions | 13 | 0.433333 | 0.209040 | 2.072973 | D660(3); D663(2); D675(2); D696(2); D635(1); D658(1); D662(1); D670(1) |
| assessment_material_misalignment | 5 | 0.166667 | 0.220339 | 0.756410 | D664(2); D184(1); D635(1); D677(1) |

In the School of Education, unclear or ambiguous instructions stands out as both relatively frequent within the college and broadly distributed across multiple courses. The second pattern, assessment material misalignment, meets the inclusion threshold but is supported by fewer posts and is correspondingly interpreted with caution.

Sampling manifest  
See `F2_sampling_manifest.jsonl` entries where section == F2 and catalog_college == School of Education.

## School of Technology

| normalized_issue_label | college_posts | college_pct | global_pct | overrep_ratio | contributing_courses_top10 |
|---|---|---|---|---|---|
| tooling_environment_misconfiguration_or_guidance | 14 | 0.070707 | 0.045198 | 1.564394 | D335(3); C969(2); D287(2); D387(2); D278(1); D282(1); D286(1); D412(1); D602(1) |
| external_tool_dependency_risks | 5 | 0.025253 | 0.019774 | 1.277056 | D280(3); D277(1); D335(1) |
| grading_or_answer_key_or_process_issues | 5 | 0.025253 | 0.019774 | 1.277056 | D385(3); D427(1); D599(1) |
| proctoring_or_exam_platform_issues | 8 | 0.040404 | 0.033898 | 1.191919 | C777(3); D281(2); D278(1); D336(1); D487(1) |
| workflow_or_policy_barriers | 8 | 0.040404 | 0.033898 | 1.191919 | C773(1); D278(1); D325(1); D329(1); D336(1); D479(1); D481(1); D601(1) |
| platform_or_environment_failures | 25 | 0.126263 | 0.110169 | 1.146076 | D288(7); D427(4); D197(3); D276(2); D277(1); D370(1); D412(1); D426(1); D485(1); D492(1) |
| missing_or_broken_resources | 15 | 0.075758 | 0.070621 | 1.072727 | D287(2); D483(2); C777(1); D276(1); D288(1); D324(1); D370(1); D427(1); D486(1); D488(1) |
| unclear_or_ambiguous_instructions | 42 | 0.212121 | 0.209040 | 1.014742 | D197(6); D287(5); D596(3); D602(3); D280(2); D284(2); D483(2); D597(2); C845(1); C867(1) |
| missing_or_low_quality_materials | 22 | 0.111111 | 0.112994 | 0.983333 | C777(2); D197(2); D278(2); C927(1); C949(1); C960(1); D276(1); D279(1); D280(1); D281(1) |
| assessment_material_misalignment | 38 | 0.191919 | 0.220339 | 0.871018 | D426(4); D427(4); D315(3); D330(3); C777(2); C949(2); C959(2); C960(2); D278(2); D322(2) |
| evaluator_inconsistency_or_poor_feedback | 10 | 0.050505 | 0.062147 | 0.812672 | C843(3); D277(2); C773(1); C783(1); C948(1); D490(1); D598(1) |

School of Technology exhibits a larger number of retained patterns, most of which are supported by contributions from many different courses. This distribution suggests that the observed issue concentrations reflect recurring themes across the college rather than isolated anomalies tied to a single course.

Sampling manifest  
See `F2_sampling_manifest.jsonl` entries where section == F2 and catalog_college == School of Technology.