from openai import OpenAI

import os

BASE_URL =os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")

client = OpenAI(
    
    base_url= BASE_URL,
    api_key=API_KEY,
)
chat_completion = client.chat.completions.create(
    model="meta-llama-3-8b-instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": """Give me the tops skills of Data Scientist"""},
    ],
    stream=True,
    max_tokens=500
)

# iterate and print stream
for message in chat_completion:
    print(message.choices[0].delta.content, end="")