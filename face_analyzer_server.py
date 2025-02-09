from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import ssl
import cv2
import numpy as np
import json
import base64
from models.face_analyzer import FaceAnalyzer
import logging
from pyngrok import ngrok

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class FaceAnalyzerServer:
    def __init__(self):
        self.face_analyzer = FaceAnalyzer()
        self.active_connections = set()

    async def process_frame(self, frame_data: str) -> dict:
        try:
            # Decode base64 image
            frame_bytes = base64.b64decode(frame_data.split(',')[1])
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Process frame and get results
            results = self.face_analyzer.process_frame(frame)
            return results if results else {}
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {}

# Initialize the server
face_analyzer_server = FaceAnalyzerServer()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")
    
    try:
        while True:
            # Receive the frame data
            frame_data = await websocket.receive_text()
            
            # Process the frame
            results = await face_analyzer_server.process_frame(frame_data)
            
            # Send back the results
            await websocket.send_json(results)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("Client disconnected")

def start_server():
    # Set your ngrok auth token
    AUTH_TOKEN = "2sWdTEp4SLH4zcdMRAvrxaoERyg_4NFX4YfoxJvtyB2sg5ku1"
    ngrok.set_auth_token(AUTH_TOKEN)  # Replace with your token
    
    # Start the server
    port = 8000
    
    # Create ngrok tunnel
    public_url = ngrok.connect(port, bind_tls=True)  # Force HTTPS/WSS
    logger.info(f"Public URL: {public_url}")
    # logger.info(f"WebSocket URL: {public_url.replace('https://', 'wss://')}/ws")
    
    # Start the FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    start_server()