Here’s the full, detailed but condensed logic for a complete program scrape, using your config.py and anchors.py correctly, and skipping the Courses section as a hard stop.

⸻

📄 parse_steps_v10.md — Full Program Scrape Logic (Pre-Program JSON Phase)

⸻

✅ 1. Setup
	•	Load TEST_FILE from config.TEST_FILE
	•	Load COLLEGE_SNAPSHOTS using pick_snapshot(catalog_date, COLLEGE_SNAPSHOTS)
	•	Strip whitespace from all lines for clean comparison

⸻

✅ 2. Identify First Entry Point
	•	Find the first match for ANCHORS["CCN_HEADER"]
	•	Walk upward from this point to find the first line in valid_colleges
→ set as current_college

⸻

✅ 3. Walk Down to Discover Programs

While not at EOF:

a. Skip Until First Valid Program Title
	•	A valid program title is:
	•	Not matching FILTERS["PROGRAM_TITLE_EXCLUDE_PATTERNS"]
	•	Title-cased and not too short
	•	Not a known college name or generic label like “Program Outcomes”

b. Start Degree Fence
	•	degree_name = line
	•	Save fence_start = current_line_index

⸻

✅ 4. Locate CCN Table and Parse Course Block

a. Walk forward to first ANCHORS["CCN_HEADER"]

→ Marks start of course block

b. From here, collect lines until:
	•	First match for ANCHORS["FOOTER_TOTAL_CUS"]
	•	OR ANCHORS["FOOTER_COPYRIGHT"]
	•	OR next valid degree_name
	•	OR ANCHORS["SCHOOL_OF"] or a valid_college name
	•	OR ANCHORS["COURSES_SECTION_BREAK"]
→ Marks end of course block + degree fence

c. Save:
	•	fence = [fence_start, fence_end]
	•	degree_name, current_college, course lines

⸻

✅ 5. Update State
	•	If a new college is found (line in valid_colleges), update current_college
	•	If ANCHORS["COURSES_SECTION_BREAK"] matches, terminate parsing
	•	Advance to next unvisited line and repeat

⸻

✅ 6. Output
	•	Save discovered degree names grouped by college
→ Output to PROGRAM_NAMES_DIR / f"{catalog_date}_program_names_v10.json"
	•	Save fences per degree
→ Output to SECTION_INDEX_PATH as sections_index_v10.json

⸻

✅ 7. Notes
	•	Course rows are parsed later using COURSE_PATTERNS (CCN_FULL, CODE_ONLY, FALLBACK)
	•	This logic avoids needing prebuilt program JSON and builds toward it

⸻

Let me know if you want this turned into runnable scaffolding or split into build steps.