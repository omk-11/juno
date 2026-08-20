from pathlib import Path
from pydantic import BaseModel

class transcript_result(BaseModel):
    text: list[str] = []
    status: bool

def check_file_exists(file):
    if not Path(file).exists():
        print("[transcription controller] video file does not exist")
        return False
    return True

def transcription_controller(whisper_model, file):
    if not check_file_exists(file):
        return transcript_result(status=False)
    try:
        segments, info = whisper_model.transcribe(
            file,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        transcript_segments = []
        for seg in segments:
            text = seg.text.strip()
            transcript_segments.append(text)
            print(text)

        print(f"[transcription_controller]: done transcripting the video")

        return transcript_result(text=transcript_segments, status=True)
    except Exception as e:
        print(f"[transcription controller] error occured while transcripting video {e}")
        return transcript_result(status=False)