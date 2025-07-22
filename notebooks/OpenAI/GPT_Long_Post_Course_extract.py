# open_ai_loop.py

# TO-DO: /Users/buddy/Desktop/WGU-Reddit/Ivy/outputs/decomposed output and confirm name



import yaml
import os
import csv
from openai import OpenAI

CONFIG_PATH = "api_config.yaml"
INPUT_PATH = "/Users/buddy/Desktop/WGU-Reddit/Ivy/outputs/long_posts12k.csv"
OUTPUT_DIR = "/Users/buddy/Desktop/WGU-Reddit/Ivy/outputs/long_post_extracts"

with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)

os.environ["OPENAI_API_KEY"] = config.get("OPENAI_API_KEY")

client = OpenAI()

# Parse CSV to get posts
posts = []
with open(INPUT_PATH, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f, quoting=csv.QUOTE_ALL)
    for row in reader:
        posts.append({
            "post_id": row["post_id"],
            "post_text": row["Post_Text"]
        })

PROMPT_TEMPLATE = """
TASK: Extract course-specific information from this WGU student post.

POST_ID: {post_id}

POST:
{post_text}

For each course mentioned, return JSON with:
- post_id: "{post_id}"
- course_code: (e.g., "C207", "D335")
- course_name: (full course title if mentioned)
- pain_points: [list of challenges/difficulties mentioned]
- advice: [study tips, recommendations, what worked]
- general_feedback: [overall experience, difficulty rating, time investment]
- sentiment: [positive/negative/neutral for this specific course]
- key_quotes: [direct quotes about this course]

Also return:
- summary: a single-sentence summary of the entire post.

Return JSON with:
{{
  "courses": [ ... ],
  "summary": "..."
}}
"""

os.makedirs(OUTPUT_DIR, exist_ok=True)

for post in posts[:3]:
    prompt = PROMPT_TEMPLATE.format(
        post_id=post["post_id"],
        post_text=post["post_text"]
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    output_text = response.choices[0].message.content

    output_path = os.path.join(
        OUTPUT_DIR, f"{post['post_id']}_GPT_output.txt"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"Saved: {output_path}")