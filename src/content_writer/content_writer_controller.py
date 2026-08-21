from fastapi import APIRouter
try:
    from .content_writter import generate_content_ideas
except Exception:
    from content_writter import generate_content_ideas
from pydantic import BaseModel

router=APIRouter()

class content_request(BaseModel):
    transcription:str


@router.post('/c')
def llm_call(request: content_request):
    transcription= request.transcription
    try:
        response = generate_content_ideas(transcription)
        if hasattr(response, "json"):
            return response.json()
        return response
    except Exception as e:
        return {"status": False, "error": str(e)}