import os
import signal
import threading
import time
from contextlib import asynccontextmanager
 
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
 
from faster_whisper import WhisperModel
from src.controllers.transcripter_controller import transcription_controller
 
MODEL_PATH = "/home/om-konde/Desktop/vive/models/medium.en"
IDLE_TIMEOUT_SECONDS = 20 * 60  # shut down after 20 minutes of no requests
WATCHDOG_CHECK_INTERVAL = 30    # how often the watchdog checks, in seconds
 
# Shared state between the watchdog thread and the request handlers
state = {
    "model": None,
    "last_request_time": time.time(),
}
 
 
def idle_watchdog():
    while True:
        time.sleep(WATCHDOG_CHECK_INTERVAL)
        idle_for = time.time() - state["last_request_time"]
        if idle_for > IDLE_TIMEOUT_SECONDS:
            print(f"[watchdog] Idle for {idle_for:.0f}s, shutting down to free GPU...")
            os.kill(os.getpid(), signal.SIGTERM)
            return
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[server] Loading model from {MODEL_PATH}...")
    try:
        state["model"] = WhisperModel(MODEL_PATH, device="cuda", compute_type="int8_float16")
    except Exception as e:
        print(f"[server] GPU load failed ({e}), falling back to CPU int8...")
        state["model"] = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")
 
    state["last_request_time"] = time.time()
 
    watchdog_thread = threading.Thread(target=idle_watchdog, daemon=True)
    watchdog_thread.start()
 
    yield
 
    print("[server] Shutting down, releasing model...")
    state["model"] = None
 
 
app = FastAPI(lifespan=lifespan)
 
 
class TranscriptionRequest(BaseModel):
    file_path: str
 
 
@app.middleware("http")
async def track_activity(request: Request, call_next):
    state["last_request_time"] = time.time()
    response = await call_next(request)
    return response
 
 
@app.post("/api/transcribe")
def transcribe_video(request: TranscriptionRequest):
    result = transcription_controller(state["model"], request.file_path)
    return result
 
 
def start_server(args):
    uvicorn.run(app, host="127.0.0.1", port=5050)
 
 
if __name__ == "__main__":
    start_server()
 