import logging
import os
from typing import Optional
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    DeepgramClientOptions
)

# Load environment variables
load_dotenv()

# Configuration
class Settings(BaseSettings):
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    class Config:
        env_file = ".env"

settings = Settings()

# WebSocket connections
active_connections: set[WebSocket] = set()


# Set up logging
logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Set up static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Set up Deepgram client
deepgram_config = DeepgramClientOptions(
    verbose=logging.INFO if settings.debug else logging.WARNING,
    options={"keepalive": "true"}
)
deepgram = DeepgramClient(settings.deepgram_api_key, deepgram_config)

# Deepgram connection
dg_connection: Optional[LiveTranscriptionEvents] = None
    
async def initialize_deepgram_connection():
    global dg_connection
    #dg_connection = deepgram.listen.websocket.v("1")
    dg_connection = deepgram.listen.asynclive.v("1")

    if not asyncio.get_event_loop().is_running():  
        raise RuntimeError("No running event loop")
    
    def on_open(self, open, **kwargs):
        logger.info(f"Deepgram connection opened: {open}")

    async def on_message(self, result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        if transcript:
            logger.info(f"Transcription: {transcript}")
            print('transcript', transcript)
            await broadcast_transcription(transcript)


    async def on_close(self, close, **kwargs):
        logger.info(f"Deepgram connection closed: {close}")

    async def on_error(self, error, **kwargs):
        logger.error(f"Deepgram error: {error}")

    dg_connection.on(LiveTranscriptionEvents.Open, on_open)
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Close, on_close)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(model="nova-2", language="en-US")
    try:
        await dg_connection.start(options)
        logger.info("Deepgram connection started successfully")
    except Exception as e:
        logger.error(f"Failed to start Deepgram connection: {e}")
        dg_connection = None
        raise

async def broadcast_transcription(transcript: str):
    for connection in list(active_connections):
        try:
            await connection.send_json({"transcription": transcript})
        except Exception as e:
            logger.error(f"Error broadcasting to WebSocket: {e}")
            active_connections.remove(connection)
            
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            if dg_connection:
                try:
                    await dg_connection.send(data)
                except Exception as e:
                    logger.error(f"Error sending data to Deepgram: {e}")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)


@app.websocket("/control")
async def control_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "start":
                logger.info("Starting Deepgram connection")
                try:
                    await initialize_deepgram_connection()
                    await websocket.send_json({"status": "started"})
                except Exception as e:
                    logger.error(f"Failed to start Deepgram connection: {e}")
                    await websocket.send_json({"status": "error", "message": str(e)})
            elif action == "stop":
                logger.info("Stopping Deepgram connection")
                if dg_connection:
                    try:
                        await dg_connection.finish()
                        dg_connection = None
                        await websocket.send_json({"status": "stopped"})
                    except Exception as e:
                        logger.error(f"Error stopping Deepgram connection: {e}")
                        await websocket.send_json({"status": "error", "message": str(e)})
                else:
                    await websocket.send_json({"status": "not_connected"})
    except WebSocketDisconnect:
        logger.info("Control WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in control WebSocket: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

