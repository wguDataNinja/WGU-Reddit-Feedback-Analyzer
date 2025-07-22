🛠️ DEV LOG — WGU Catalog Scraper (Section 1 Test)

Objective:
- Test initial logic that locates and fences the first academic program section in a catalog file.

What We Did:
- Ran fence-building script on the first catalog (`catalog_2017_01.txt`)
- Loaded program names for the catalog date
- Identified the **first college** from snapshot: `College of Health Professions`
- Located the **first degree** listed under that college: `Bachelor of Science, Nursing (RN to BSN)`
- Scanned forward to find the associated `CCN_HEADER`
- Calculated a **fence range**: `start_idx` to `stop_idx` for that degree's course block

Cutoff:
✅ **Script halted immediately after successfully fencing the first degree**
🛑 This is the precise point where the script normally continues looping through all degrees — 
we stopped here to validate section parsing logic before scaling up.

Scraper_V10_config.py


# 📓 catalog_dev_log.md  
**Date:** 2025-07-13  
**Topic:** VSCode + ChatGPT Integration, Shortcuts, and Live File Editing

---

## ✅ Goal  
Connect ChatGPT to VSCode and enable a fluid workflow between code editing and AI assistance — without constant app switching or manual copy/paste.

---

## 🧠 Key Learnings & Outcomes

### 🔹 VSCode Features & Shortcuts
- Discovered **`Cmd + Shift + P`** → **Command Palette**
  - Power feature: run anything (interpreter switch, extension command, kernel select, etc.)
- Learned **`Cmd + \``** opens the VSCode terminal
- Understood the role of the **left sidebar (Activity Bar)** and how to toggle panels

### 🔹 ChatGPT Desktop Integration (Reality Check)
- Installed and tested the **official ChatGPT VSCode extension (by OpenAI)**
- Learned it **does not open a sidebar in VSCode**
- Instead, it **opens the ChatGPT desktop app**, passing code selections into a new or paired conversation
- Confirmed that even with pairing, **ChatGPT can only edit files — not execute code or show output**
- Used the "Option + Space" shortcut to open ChatGPT pairing popup inside VSCode

### 🔹 Verified Integration Path
- Opened `scrape_catalog.py` in VSCode
- Used ChatGPT to inject a debug line:
  ```python
  import os
  print("[DEBUG] Current working directory:", os.getcwd())


  Sure — here’s a concise dev log summarizing your progress so far, structured like a proper internal note.

⸻

📓 Dev Log – WGU Catalog Scraper (Notebook Refactor)

Date: 2025-07-13
Author: Buddy
Goal: Refactor the catalog scraper logic into a notebook environment using existing tools from lib/config.py and lib/anchors.py

⸻

✅ What’s Working

📦 Config + Imports
	•	config.py provides all shared paths, input files, and constants
	•	anchors.py includes all structural regex patterns (CCN_HEADER, COURSE_CODE, etc.)
	•	sys.path.insert(...) used to access lib/ from inside /notebooks
	•	Config constants like TEXT_DIR, COLLEGE_SNAPSHOTS, and COURSE_PATTERNS are usable

🛠 Helper Functions

Defined directly in the notebook (clean workaround to import/exec errors from config.py):
	•	extract_catalog_date(file_name)
	•	pick_snapshot(catalog_date, snapshot_dict)

These enable date-based lookups of trusted college sections.

📄 Catalog Parsing
	•	Read .txt catalog file from TEXT_DIR
	•	Extracted catalog_date from file name
	•	Pulled list of valid colleges using college_snapshots.json via pick_snapshot()
	•	Located the first college block using valid_colleges[0]
	•	Found first CCN_HEADER after that block
	•	Collected candidate course rows below it
	•	Matched course rows using COURSE_PATTERNS

⸻

🧩 Code Structure

Notebook has clear, modular sections:
	1.	Import project + define helpers
	2.	Load + preprocess catalog file
	3.	Locate first real program block (by college)
	4.	Detect first CCN block and extract sample rows
	5.	Match rows using regex patterns

⸻

⚠️ Issues Encountered
	•	extract_catalog_date was not visible via from lib import config due to runtime crash in config.py (file I/O before function defs)
	•	VS Code flagged false ModuleNotFoundError: 'lib' due to static analysis (harmless, ignored)
	•	Jupyter notebook’s dynamic pathing caused temporary import confusion (resolved via sys.path.insert)

⸻

📌 Next Steps
	•	Generalize fence detection across all colleges in a file
	•	Export matched rows into CSV
	•	Optionally write sections_index_v10.json (if doing verified output)
	•	Add anomaly logging for non-matching rows
	•	Wrap parsing into a reusable parse_catalog(file_path) function

⸻

Let me know if you’d like this saved as markdown, or embedded directly into your repo as devlog.md.






