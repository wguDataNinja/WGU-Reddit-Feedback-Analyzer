schema: wgu_reddit_analyzer_hugo_site
doc_version: 1
last_updated: 2025-12-17
site:
  generator: hugo
  theme: PaperMod
  stack: [hugo>=0.150, vanilla_js]
  no_live_calls: true
data:
  source_of_truth: artifacts/report_data
  contract:
    join_keys: [post_id, course_code, cluster_id, normalized_issue_label, global_cluster_id]
    global_issue_key: normalized_issue_label
ux:
  goal: evidence_backed_issue_explorer
  guardrails:
    no_time_series: true
    de_emphasize: [usernames, timestamps, sentiment_scores]
    avoid_quality_ranking_language: true
views:
  homepage:
    narrative_counts_from: artifacts/report_data/pipeline_counts_overview.md
    entry_points: [raw_posts, pain_points, courses, global_issues]
  raw_posts:
    filters: [course_code, college, keyword]
  pain_points:
    filters: [course_code, normalized_issue_label, keyword]
    click_goes_to: course_detail_focused
  courses_overview:
    sort_defaults: [total_pain_point_posts_desc, total_negative_posts_desc]
  course_detail:
    shows: [course_header, issue_groups, evidence_snippets]
    issue_group_is_embedded: true
  global_issues_overview:
    shows: [issue_name, description, total_posts, courses_affected, colleges_represented]
  global_issue_detail:
    shows: [impact_summary, colleges_list, course_breakdown]
    click_course_goes_to: course_detail
evidence:
  primary: snippets
  expandable: true