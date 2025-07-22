# /Users/buddy/Desktop/coomer-tampermonkey/OpenAI/GPT_Summarize_Chunk.py

import os
import re
import yaml
import openai
import pandas as pd

# Load API key
CONFIG_PATH = "api_config.yaml"
with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)

OPENAI_API_KEY = config.get("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Paths
chunk_dir = "/Users/buddy/Desktop/coomer-tampermonkey/text/TikTok/chunks"
output_dir = "/Users/buddy/Desktop/coomer-tampermonkey/text/TikTok"

# Prompt template
system_message = {
    "role": "system",
    "content": "You are a helpful AI and you output in JSON only."
}

prompt_prefix = """You will be given a list of transcriptions from TikTok videos created by a 30-year-old Canadian adult content creator. She discusses sex work, body image, industry transparency, personal stories, and audience interaction.

For each item:
- If the transcription conveys a clear and meaningful message related to her typical themes or shares personal information, write one short sentence summarizing it.
- If the transcription is vague, noisy, too short, or lacks a meaningful message, respond with: "no meaning".

Respond only with a JSON array of objects, each containing: "id" and "summary".

Example output:
[
  { "id": 1, "summary": "no meaning" },
  { "id": 2, "summary": "Encourages body positivity and confidence for plus-size women." },
  { "id": 3, "summary": "Describes buying a bold outfit for work and feeling excited about it." }
]

Here is the transcription list:
"""

# Natural sort helper
def extract_chunk_number(filename):
    match = re.search(r"chunk_(\d+)\.csv", filename)
    return int(match.group(1)) if match else float('inf')

# Get remaining chunks starting from chunk_11
chunk_files = sorted(
    (f for f in os.listdir(chunk_dir) if f.startswith("chunk_") and f.endswith(".csv")),
    key=extract_chunk_number
)[10:]

# Process each chunk
for filename in chunk_files:
    input_path = os.path.join(chunk_dir, filename)
    base_name = filename.replace(".csv", "")
    output_txt_path = os.path.join(output_dir, f"GPT_Output_{base_name}.txt")

    print(f"Processing {filename}...")

    # Load chunk
    df = pd.read_csv(input_path)
    entries = [
        {"id": int(row["id"]), "transcription": str(row["transcription"])}
        for _, row in df.iterrows()
    ]

    user_prompt = prompt_prefix + "\n" + str(entries)

    # Send to OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            system_message,
            {"role": "user", "content": user_prompt}
        ]
    )

    # Save raw response
    raw_response = response.choices[0].message.content
    with open(output_txt_path, "w") as f:
        f.write(raw_response)

    print(f"Saved output to {output_txt_path}")