july 13 2025 — captured insights from capstone discussion on NLP and data science. saved detailed reflection as `docs/capstone-discussion-NLP-Data-Science.txt`. key relevance to project:
- Highlights importance of starting analysis with a well-defined question.
- Differentiates between data analytics and scientific inquiry — useful for framing future logic decisions.
- Provides justification for NLP techniques (e.g., sentiment + phrase matching) used in Reddit post classification.
- Supports development of alert system tied to program/course feedback, aligning with GUI reporting goals.

july 13 2025 — initial scraper logic cleaned and modularized. refactored to use snapshot-based college matching and flexible program title detection (footer → CCN). dropped brittle “Bachelor of”/“Master of” prefix check. verified that exclusion-filter style from legacy parser is more robust. logging added (later replaced with debug_mode + print()). imports in notebooks locked to hardcoded PROJECT_ROOT with sys.path.insert — works reliably in vscode + jupyter. kept as-is.

compared to the old version (V10), this refactor introduces config-based control, centralized anchors, and clean toggled output. consulted the legacy logic from Scraper_V10(16), saved as `/data/Scraper_V10-16.html`. that legacy code worked but was fragile, lacked modularity, and required exact formatting. V11 generalizes the parser and introduces helper functions, filters, and snapshot logic.


---

july 13 2025 — continued development after initial program extraction success. plan set to achieve full-depth parsing by extracting course rows within a single program. will confirm detection completeness by comparing against raw text line counts for both programs and courses.

once confirmed, shift to a summary count view per catalog: show college names, program counts per college, total courses detected. begin looping through all 99 catalogs with CSV-style summary output to detect structural changes over time. old dev log logic will be used to handle anomalies.

final output (ASAP): master Course List CSV with CCN, Course Code, Name, College(s). secondary output: institutional diff over time + GUI. lowest priority: scrape additional catalog sections such as course descriptions, policies, etc.











july 13 2025 — added visual representation work for college structure changes. created initial graphic mockups showing WGU and its four colleges (Technology, Health, Education, Business) over a timeline from 2017–2025. added overlays to highlight name changes (e.g., College of Health Professions → Leavitt School of Health in 2023-01). these snapshots will guide future generation of consistent visual diffs.

created `media/` directory under WGU_catalog to store reference graphics, including deliberately crude “snapshot + arrow” visual that accurately maps college transitions by date. this serves as a visual checklist for remaining image tasks.

next steps: produce similar graphics for remaining dates in structured list (2023-03, 2024-02, 2024-04, 2024-09). final goal is a timeline-aligned visual diff showing college name history and expansion over time, integrated into the GUI or summary report.

---

july 13 2025 — outlined alerting system design from capstone NLP reflection. implementation-relevant notes for Reddit help-seeking detection pipeline:
- Alert conditions include course mentions, help-seeking phrase flags, negative sentiment, and reply analysis (e.g., no helpful answers).
- Prioritization logic: High (negative + help-seeking + no replies), Low (just complaints or already answered).
- Configurable per faculty/department via JSON or CLI (e.g., course filters, alert thresholds).
- Alert output payload: post excerpt, sentiment score, matched phrases, link, reply summary (e.g., upvotes, sentiment of replies).
- Useful for surfacing unanswered or critical student issues to staff via daily report or UI flag.

Also captured methodology notes relevant to implementation:
- Help-seeking detection uses a combination of keyword/phrase matching and VADER sentiment scoring.
- NLP classifier flags posts when help-related language + negative tone appear together.
- Additional clustering step groups similar complaint posts for summary views.
- Basis for GUI hooks and future alert integration into institutional dashboard or workflow.

potential notes for project:

You’re right — your earlier discussion included much more than just alerting. Here’s a focused rewrite for the dev log entry, capturing only exploratory ideas and emergent insights from our full conversation — not just alarms, but also NLP limitations, GPT integration potential, catalog strategy, and signal fidelity.

⸻

