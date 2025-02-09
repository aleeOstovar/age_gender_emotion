# routes/websocket_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from controllers.websocket_controller import WebSocketController

router = APIRouter()
ws_controller = WebSocketController()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_controller.connect(websocket)
    try:
        while True:
            frame_data = await websocket.receive_text()
            results = await ws_controller.process_frame(frame_data)
            await websocket.send_json(results)
    except WebSocketDisconnect:
        ws_controller.disconnect(websocket)
