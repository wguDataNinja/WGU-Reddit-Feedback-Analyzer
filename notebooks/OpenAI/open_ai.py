# open_ai.py

import yaml
import os
from openai import OpenAI  # ✅ correct import for new version

# Load API keys from config file
CONFIG_PATH = "api_config.yaml"

with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)

# Set the env var
os.environ["OPENAI_API_KEY"] = config.get("OPENAI_API_KEY")

# ✅ Do NOT pass api_key here!
client = OpenAI()

question = 'How do you like the name "Ivy" for a custom AI?'

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": question}
    ]
)

print(response.choices[0].message.content)