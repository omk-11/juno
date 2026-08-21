from fastapi import FastAPI
from scraper.event_controller import router as event_router
from transcripter.transcript_controller import router as transcript_router
from content_writer.content_writer_controller import router as content_router

app= FastAPI()

app.include_router(event_router, prefix="/api/events", tags=["events"])
app.include_router(transcript_router, prefix='/api/transcript',tags=["transcription"])
app.include_router(content_router, prefix='/api/content',tags=["content", "llm"]) 