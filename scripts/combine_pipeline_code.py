# /Users/buddy/Desktop/WGU-Reddit/scripts/combine_scripts_to_doc.py

from pathlib import Path

ROOT_DIR = Path("/Users/buddy/Desktop/WGU-Reddit")

STAGE1_FILES = [
    "scripts/stage1/config_stage1.py",
    "scripts/stage1/step04_run_stage1.py",
    "scripts/stage1/step03_classify_file.py",
    "scripts/stage1/step02_classify_post.py",
    "scripts/stage1/step01_fetch_filtered_posts.py",
]

STAGE2_FILES = [
     "scripts/stage2/config_stage2.py",
     "scripts/stage2/step01_group_by_course.py",
     "scripts/stage2/step02_prepare_prompt_data.py",
     "scripts/stage2/step03_call_llm.py",
    "scripts/stage2/step04_apply_actions.py",
     "scripts/stage2/step05_run_stage2.py",
]

OTHER_FILES = [
    "scripts/batch_generate_pdfs.py",
    "scripts/merge_course_feedback.py",
    "scripts/run_daily_pipeline.py",
    #"utils/logger.py"
]

OUTPUT_FILE = ROOT_DIR / "outputs/combined_pipeline_code.txt"

def write_section(header, file_list, out_f):
    out_f.write(f"# --- {header} ---\n\n")
    for relative_path in file_list:
        full_path = ROOT_DIR / relative_path
        out_f.write(f"# {relative_path}\n\n")
        with open(full_path, "r", encoding="utf-8") as in_f:
            out_f.write(in_f.read())
        out_f.write("\n\n")

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        write_section("STAGE 1", STAGE1_FILES, out_f)
        write_section("STAGE 2", STAGE2_FILES, out_f)
        write_section("OTHER SCRIPTS", OTHER_FILES, out_f)

if __name__ == "__main__":
    main()