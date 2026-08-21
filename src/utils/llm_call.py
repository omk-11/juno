from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()
OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")

LLM_PROVIDERS={
    'mini': [],
    'moderate': ["nvidia/nemotron-3-super-120b-a12b:free"],
    'large': ["nvidia/nemotron-3-ultra-550b-a55b:free"]
}

def llm_health():
    pass

def call_llm(prompt,provider):

    llm_health()

    client = Anthropic(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api",
    )

    response = client.messages.create(
        model=LLM_PROVIDERS[provider],
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
    )

    return response.json()
