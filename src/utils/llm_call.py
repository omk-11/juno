from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

LLM_PROVIDERS={
    'mini': [],
    'moderate': ["nvidia/nemotron-3-super-120b-a12b:free"],
    'large': ["nvidia/nemotron-3-ultra-550b-a55b:free"]
}

def llm_health():
    """Basic health check for LLM configuration.

    Raises RuntimeError if a required configuration (API key) is missing.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in the environment")

def call_llm(prompt, provider: str = "moderate"):
    """Call the configured LLM provider.

    - `provider` selects an entry from `LLM_PROVIDERS`.
    - Returns a Python object (dict) with the LLM response when possible.
    """
    llm_health()

    if provider not in LLM_PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")

    models = LLM_PROVIDERS[provider]
    if not models:
        raise ValueError(f"no models configured for provider '{provider}'")

    model = models[0] if isinstance(models, (list, tuple)) else models

    client = Anthropic(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api",
    )

    response = client.messages.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    # Try to return a JSON-like response; be tolerant if the client
    # returns an object with a .json() method or already a dict-like.
    try:
        if hasattr(response, "json"):
            return response.json()
    except Exception:
        pass

    return response
