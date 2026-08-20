from fastapi import APIRouter
import requests
from pydantic import BaseModel

router = APIRouter()

class transcription_request(BaseModel):
    file_path:str

@router.post('/video')
def get_video(request:transcription_request):
    responce=requests.post('http://127.0.0.1:5050/api/transcribe',json={"file_path":request.file_path})
    return responce.json()