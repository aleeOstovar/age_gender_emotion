# controllers/websocket_controllers.py
import base64
import cv2
import numpy as np
import logging
from fastapi import WebSocket
from models.face_analyzer import FaceAnalyzer
from shared_state import last_detected, detection_lock 
class WebSocketController:
    def __init__(self):
        self.face_analyzer = FaceAnalyzer()
        self.active_connections = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def process_frame(self, frame_data: str) -> dict:
        try:
            # Decode base64 image
            frame_bytes = base64.b64decode(frame_data.split(',')[1])
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Process frame using FaceAnalyzer
            results = self.face_analyzer.process_frame(frame)
            
            # If detection succeeded, update the shared state with a lock
            if results:
                with detection_lock:
                    last_detected.clear()
                    last_detected.update(results)
            
            return results
        except Exception as e:
            logging.error(f"Frame processing error: {str(e)}")
            return {}
