# routes/predict_routes.py
from fastapi import APIRouter, WebSocket
from controllers.websocket_controller import WebSocketController
from fastapi.responses import JSONResponse
import base64
import numpy as np
import cv2

router = APIRouter()
ws_controller = WebSocketController()

@router.post("/predict")
async def predict_face_attributes(frame_data: dict):
    """
    Endpoint for real-time face prediction based on input frame
    """
    try:
        # Decode base64 image from request
        frame_base64 = frame_data.get('frame', '')
        if not frame_base64:
            return JSONResponse(content={"error": "No frame provided"}, status_code=400)

        # Decode base64 image
        frame_bytes = base64.b64decode(frame_base64.split(',')[1])
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process frame and get results
        results = ws_controller.face_analyzer.process_frame(frame)
        
        if not results:
            return JSONResponse(content={"message": "No face detected"}, status_code=404)
        
        return JSONResponse(content=results)
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)