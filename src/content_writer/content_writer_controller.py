from fastapi import APIRouter
from .content_writter import generate_content_ideas
from pydantic import BaseModel

router=APIRouter()

class content_request(BaseModel):
    transcription:str


@router.post('/c')
def llm_call(request: content_request):
    transcription= request.transcription
    response= generate_content_ideas(transcription)
    return response.json()