from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

client = Anthropic(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api",
)

response = client.messages.create(
    model="poolside/laguna-s-2.1:free",
    max_tokens=500,
    messages=[
        {
            "role": "user",
            "content": "Explain what an API is in simple terms."
        }
    ],
)

print(response.content[0].text)