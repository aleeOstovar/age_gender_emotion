from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
STATIC_DIR = ROOT_DIR / "static"

CONFIG = {
    "YOLO_MODEL": "yolov8n-face.pt",
    "MAX_FRAME_SIZE": (640, 480),
    "MIN_DETECTION_CONFIDENCE": 0.6,
    "PROCESS_INTERVAL": 4
}