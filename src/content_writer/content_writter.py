try:
    from ..utils.llm_call import call_llm
except Exception:
    from utils.llm_call import call_llm

from pathlib import Path


def prompt_designer(transcription: str) -> str:
    """Compose a prompt for the LLM using the master prompt as a template.

    If `master_prompt.md` is missing, fall back to a short built-in instruction.
    """
    master_path = Path(__file__).resolve().parents[1] / "utils" / "master_prompt.md"
    if master_path.exists():
        try:
            master_text = master_path.read_text(encoding="utf-8")
        except Exception:
            master_text = "You are an assistant that extracts short, high-signal clips from a transcript."
    else:
        master_text = "You are an assistant that extracts short, high-signal clips from a transcript."

    prompt = f"{master_text}\n\nTRANSCRIPTION:\n{transcription}\n\nReturn JSON with recommended clip timestamps and short descriptions."
    return prompt


def generate_content_ideas(transcription, provider: str = "moderate"):
    prompt = prompt_designer(transcription)
    response = call_llm(prompt, provider=provider)

    # call_llm returns a dict-like object when possible; be tolerant.
    return response
