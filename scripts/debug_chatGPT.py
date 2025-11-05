# filename: debug_chatGPT.py

import os
from openai import OpenAI, RateLimitError
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
        temperature=0
    )
    print(response.choices[0].message.content)

except RateLimitError as e:
    print("RateLimitError:", e)
    if e.response:
        request_id = e.response.headers.get("x-request-id")
        print("Request ID:", request_id)