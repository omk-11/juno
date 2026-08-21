from fastapi import APIRouter
import requests
from pydantic import BaseModel

router = APIRouter()

class transcription_request(BaseModel):
    file_path:str

@router.post('/video')
def get_video(request:transcription_request):
    try:
        responce = requests.post(
            "http://127.0.0.1:5050/api/transcribe",
            json={"file_path": request.file_path},
            timeout=30,
        )
        # propagate the transcription service response if JSON, else return raw text
        try:
            return responce.json()
        except Exception:
            return {"status": False, "error": "invalid response from transcription service", "raw": responce.text}
    except requests.RequestException as e:
        return {"status": False, "error": f"transcription service request failed: {e}"}