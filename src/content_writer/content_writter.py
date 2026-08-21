from ..utils.llm_call import call_llm

def prompt_designer(transcription: str):
    pass

def generate_content_ideas(transcription):

    prompt=prompt_designer(transcription)
    response=call_llm(prompt)

    return response.json()
