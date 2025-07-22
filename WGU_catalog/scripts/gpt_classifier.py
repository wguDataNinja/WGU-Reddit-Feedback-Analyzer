# filename: gpt_classifier.py

import json
import logging

def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def save_jsonl(records, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def log_batch(posts, results, mode):
    ids = [p["post_id"] for p in posts]
    texts = [p["text"][:10] + "..." for p in posts]
    total_chars = sum(len(p["text"]) for p in posts)
    logging.info(
        f"[{mode.upper()}] post_ids={ids} | char_count={total_chars} | inputs={texts} | outputs={results}"
    )

def log_gpt_config():
    system_msg = "You are a classifier for Reddit posts about university courses."
    prompt_template = """\
Classify it using one or more of the following categories (by number):
0: Assessment & Exam Content — PA, OA, proctoring, retaking, etc  
1: Course Content Issues — outdated, incorrect, missing, or misleading course material  
2: Study Support & Resources — study materials, guides, notes, etc  
3: Course Planning & Timing — degree plan, course order, pacing guide, timeline  
4: Celebration & Motivation — passing, graduating, confetti, encouragement  
5: uncategorized — not fitting into other categories

INTENT TAGS (optional):
0: help_request — explicit asks for help, support, etc  
1: advice_offered — offering advice, tips, etc

Return the following JSON structure:

{
  "post_id": "<id>",
  "categories": [...],
  "intent_tags": [...]
}
"""
    logging.info("[GPT CONFIG] model=gpt-4o-mini")
    logging.info("[GPT CONFIG] system_message=%s", system_msg)
    logging.info("[GPT CONFIG] prompt_template=%s", prompt_template)

def classify_file(input_path):

    posts = load_jsonl(input_path)
    output_records = []
    batch = []
    char_count = 0

    for post in posts:
        text = post["text"]
        length = len(text)

        if length > 10000:
            log_batch([post], [], mode="flagged-too-long")
            continue

        if length > 5000:
            result = classify_reddit_post(post_id=post["post_id"], text=text)
            if hasattr(result, "model_dump"):
                result = result.model_dump()  # ✅ fix deprecated .dict()
            log_batch([post], [result], mode="solo")
            output_records.append(result)
            continue

        if len(batch) < MAX_POSTS_PER_BATCH and (char_count + length) <= BATCH_CHAR_LIMIT:
            batch.append(post)
            char_count += length
        else:
            results = []
            for p in batch:
                r = classify_reddit_post(p["post_id"], p["text"])
                if hasattr(r, "model_dump"):
                    r = r.model_dump()  # ✅ fix deprecated .dict()
                results.append(r)
            log_batch(batch, results, mode="batched")
            output_records.extend(results)
            batch = [post]
            char_count = length

    if batch:
        results = []
        for p in batch:
            r = classify_reddit_post(p["post_id"], p["text"])
            if hasattr(r, "model_dump"):
                r = r.model_dump()
            results.append(r)
        log_batch(batch, results, mode="batched")
        output_records.extend(results)

    out_name = input_path.stem.replace("_posts", "_classified") + ".jsonl"
    save_jsonl(output_records, OUTPUT_DIR / out_name)