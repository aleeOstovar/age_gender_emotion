config/config.py
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
STATIC_DIR = ROOT_DIR / "static"

CONFIG = {
    "YOLO_MODEL": "yolov8n-face.pt",
    "MAX_FRAME_SIZE": (640, 480),
    "MIN_DETECTION_CONFIDENCE": 0.5,
    "PROCESS_INTERVAL": 1
}

models/face_analyzer.py

import os
import cv2
import numpy as np
from deepface import DeepFace
from ultralytics import YOLO
import logging
from utils.frame_processor import preprocess_frame
from config.config import CONFIG
import tensorflow as tf

# Suppress TensorFlow warnings
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
tf.get_logger().setLevel('ERROR')

class FaceAnalyzer:
    def __init__(self):
        self.face_detector = YOLO(CONFIG["YOLO_MODEL"])
        self.deepface_config = {
            "detector_backend": "mtcnn",
            "enforce_detection": False,
            "align": False,
            "silent": True
        }
        self._init_models()

    def _init_models(self):
        try:
            dummy_img = np.zeros((160, 160, 3), dtype=np.uint8)
            DeepFace.analyze(
                dummy_img,
                actions=['age', 'gender', 'emotion'],
                **self.deepface_config
            )
        except Exception as e:
            logging.warning(f"Model initialization warning: {str(e)}")

    def _map_gender(self, gender_result) -> str:
        """Map gender result to string"""
        if isinstance(gender_result, dict):
            return 'مرد' if gender_result.get('Man', 0) > gender_result.get('Woman', 0) else 'زن'
        return str(gender_result)

    def process_frame(self, frame: np.ndarray) -> dict:
        try:
            # Resize frame for faster processing
            scale_factor = 0.5
            small_frame = cv2.resize(frame, None, fx=scale_factor, fy=scale_factor)
            
            # Detect faces
            results = self.face_detector(small_frame, verbose=False, conf=CONFIG["MIN_DETECTION_CONFIDENCE"])[0]
            
            if not len(results.boxes):
                return {}

            # Get the face with highest confidence
            best_box = max(results.boxes, key=lambda x: x.conf[0].item())
            x1, y1, x2, y2 = map(lambda x: int(x/scale_factor), best_box.xyxy[0].tolist())
            
            # Ensure coordinates are within frame boundaries
            h, w = frame.shape[:2]
            x1, x2 = max(0, x1), min(w, x2)
            y1, y2 = max(0, y1), min(h, y2)
            
            face_region = frame[y1:y2, x1:x2]
            
            if face_region.size == 0:
                return {}

            # Analyze face with DeepFace
            face_region_small = cv2.resize(face_region, (160, 160))
            analysis = DeepFace.analyze(
                face_region_small,
                actions=['age', 'gender', 'emotion'],
                **self.deepface_config
            )[0]

            # Map emotion to Persian
            emotion_map = {
                "angry": "عصبانی",
                "disgust": "متنفر",
                "fear": "ترسیده",
                "happy": "خوشحال",
                "sad": "غمگین",
                "surprise": "متعجب",
                "neutral": "خنثی"
            }

            return {
                'bbox': [x1, y1, x2, y2],
                'confidence': float(best_box.conf[0].item()),
                'age': f"{analysis['age'] - 2} - {analysis['age'] + 3}",
                'gender': self._map_gender(analysis['gender']),
                'emotion': emotion_map.get(analysis['dominant_emotion'], analysis['dominant_emotion'])
            }

        except Exception as e:
            logging.error(f"Frame processing error: {str(e)}")
            return {}
        
controllers/websocket_controllers.py
import base64
import cv2
import numpy as np
from fastapi import WebSocket
from models.face_analyzer import FaceAnalyzer

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
            
            # Process frame
            return self.face_analyzer.process_frame(frame)
        except Exception as e:
            logging.error(f"Frame processing error: {str(e)}")
            return {}


utils/frame_preprocess.py

import cv2
import numpy as np
from typing import Tuple

def preprocess_frame(frame: np.ndarray, max_size: Tuple[int, int]) -> np.ndarray:
    h, w = frame.shape[:2]
    target_w, target_h = max_size
    
    scale = min(target_w/w, target_h/h)
    if scale < 1:
        new_size = (int(w*scale), int(h*scale))
        frame = cv2.resize(frame, new_size)
    
    return frame

routes/websocket_routes.py
from fastapi import APIRouter, WebSocket
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


routes/api_routes.py
from fastapi import APIRouter, WebSocket
from controllers.websocket_controller import WebSocketController
import cv2
import numpy as np
import base64
from fastapi.responses import JSONResponse

router = APIRouter()
ws_controller = WebSocketController()

@router.get("/predict")  # This will become /api/predict due to the prefix
async def get_predictions():
    try:
        # Capture frame from default camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return JSONResponse(
                content={"error": "دوربین در دسترس نیست"},
                status_code=400
            )
            
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return JSONResponse(
                content={"error": "خطا در خواندن تصویر از دوربین"},
                status_code=400
            )
        
        # Convert frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        frame_data = f"data:image/jpeg;base64,{frame_base64}"
        
        # Process frame
        results = await ws_controller.process_frame(frame_data)
        
        if not results:
            return JSONResponse(
                content={"error": "چهره‌ای شناسایی نشد"},
                status_code=404
            )
        
        # Map emotion to Persian
        emotion_map = {
            "angry": "عصبانی",
            "disgust": "متنفر",
            "fear": "ترسیده",
            "happy": "خوشحال",
            "sad": "غمگین",
            "surprise": "متعجب",
            "neutral": "خنثی"
        }
        
        gender_map = {
            "Male": "مرد",
            "Female": "زن"
        }
        
        results["emotion"] = emotion_map.get(results["emotion"], results["emotion"])
        results["gender"] = gender_map.get(results["gender"], results["gender"])
        
        return JSONResponse(content=results)
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"خطای سیستم: {str(e)}"},
            status_code=500
        )

main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from routes.websocket_routes import router as ws_router
from routes.api_routes import router as api_router  # Add this import
from pathlib import Path
from config.config import STATIC_DIR
from pyngrok import ngrok

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include both WebSocket and API routes
app.include_router(ws_router)
app.include_router(api_router, prefix="/api")  # Add prefix to avoid conflicts

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Root route
@app.get("/")
async def read_root():
    return FileResponse(str(STATIC_DIR / "index.html"))

if __name__ == "__main__":
    # Set your ngrok auth token here
    AUTH_TOKEN = "2sWdTEp4SLH4zcdMRAvrxaoERyg_4NFX4YfoxJvtyB2sg5ku1"
    ngrok.set_auth_token(AUTH_TOKEN)

    # Specify the port your app will run on
    port = 8000

    # Open an ngrok tunnel on the specified port
    public_url = ngrok.connect(port, proto="http")
    print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}/\"")

    # Now start the Uvicorn server
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

static/index.html
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تحلیل چهره هوش مصنوعی</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        /* RTL specific styles */
        body[dir="rtl"] {
            font-family: 'Iranian Sans', 'Vazir', Arial, sans-serif;
        }
        
        body[dir="rtl"] .stats {
            text-align: right;
        }
        
        body[dir="rtl"] .analysis-overlay {
            direction: rtl;
        }
    </style>
</head>
<body dir="rtl">
    <div class="app-container">
        <div class="camera-module">
            <div class="ambient-glow"></div>
            <div class="reactive-glow"></div>
            <div class="video-container">
                <video id="videoElement" autoplay playsinline muted></video>
                <canvas id="overlay"></canvas>
                <div class="analysis-overlay">
                    <div class="stats" id="stats"></div>
                    <div class="status" id="status">
                        <span class="status-dot"></span>
                        <span class="status-text">در حال راه‌اندازی...</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="/static/js/main.js"></script>
</body>
</html>


static/css/style.css

:root {
    --glow-color-1: #00ff6e;
    --glow-color-2: #00b7ff;
    --glow-color-3: #2550ffaa;
    --glow-color-4: #ff9500;
    --glow-color-5: #ffd500;
    --bg-color: #0a0a0a;
    --border-radius: 20px;
}

body {
    margin: 0;
    padding: 0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg-color);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

.app-container {
    padding: 20px;
}

.camera-module {
    position: relative;
    width: 680px;
    height: 520px;
    display: flex;
    justify-content: center;
    align-items: center;
}

.ambient-glow {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border-radius: var(--border-radius);
    background: 
        radial-gradient(circle at 0% 0%, var(--glow-color-1), transparent 50%),
        radial-gradient(circle at 100% 0%, var(--glow-color-2), transparent 50%),
        radial-gradient(circle at 0% 100%, var(--glow-color-3), transparent 50%),
        radial-gradient(circle at 100% 100%, var(--glow-color-4), transparent 50%);
    filter: blur(20px);
    opacity: 0.5;
    animation: ambientMove 15s ease-in-out infinite;
    z-index: 1;
}

.reactive-glow {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border-radius: var(--border-radius);
    background: radial-gradient(circle at center, var(--glow-color-5), transparent 70%);
    filter: blur(20px);
    opacity: 0;
    transition: all 0.1s ease-out;
    z-index: 2;
}

.video-container {
    position: relative;
    width: 640px;
    height: 480px;
    background: #000;
    border-radius: calc(var(--border-radius) - 5px);
    overflow: hidden;
    z-index: 3;
    border: 2px solid rgba(255, 255, 255, 0.1);
}

#videoElement {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

#overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
}

.analysis-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 20px;
    background: linear-gradient(
        to bottom,
        rgba(0, 0, 0, 0.2) 0%,
        transparent 30%,
        transparent 70%,
        rgba(0, 0, 0, 0.2) 100%
    );
}

.stats {
    color: #fff;
    font-family: 'SF Mono', monospace;
    background: rgba(0, 0, 0, 0.6);
    padding: 15px 20px;
    border-radius: 15px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 14px;
    line-height: 1.5;
    max-width: 200px;
}

.status {
    align-self: center;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 20px;
    background: rgba(0, 0, 0, 0.7);
    color: #fff;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 14px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #ff3b3b;
    transition: background-color 0.3s ease;
}

.status.connected .status-dot {
    background: #00ff95;
}

@keyframes ambientMove {
    0%, 100% {
        transform: scale(1) rotate(0deg);
    }
    25% {
        transform: scale(1.1) rotate(3deg);
    }
    50% {
        transform: scale(1) rotate(-3deg);
    }
    75% {
        transform: scale(1.1) rotate(1deg);
    }
}

class FaceAnalysisApp {
    constructor() {
        // DOM Elements
        this.video = document.getElementById('videoElement');
        this.overlay = document.getElementById('overlay');
        this.ctx = this.overlay.getContext('2d');
        this.stats = document.getElementById('stats');
        this.status = document.getElementById('status');
        this.reactiveGlow = document.querySelector('.reactive-glow');

        // Audio Processing
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;

        // WebSocket
        this.ws = null;
        this.isProcessing = false;

        // Initialize
        this.initialize();
    }

    async initialize() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: true
            });

            // Set up video stream
            this.video.srcObject = stream;
            this.overlay.width = 640;
            this.overlay.height = 480;

            // Initialize components
            this.initializeWebSocket();
            this.initializeAudio(stream);

            this.video.addEventListener('play', () => {
                this.processFrame();
            });

        } catch (err) {
            console.error('Initialization error:', err);
            this.updateStatus('Error', false);
        }
    }

    async initializeAudio(stream) {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 64;

            const audioSource = this.audioContext.createMediaStreamSource(stream);
            audioSource.connect(this.analyser);

            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

            this.visualizeAudio();

        } catch (err) {
            console.error('Audio initialization error:', err);
        }
    }

    initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

        this.ws.onopen = () => {
            this.updateStatus('متصل', true);
            console.log('WebSocket connected');  // Debug log
        };

        this.ws.onclose = () => {
            this.updateStatus('قطع شده', false);
            console.log('WebSocket disconnected');  // Debug log
            setTimeout(() => this.initializeWebSocket(), 1000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);  // Debug log
        };

        this.ws.onmessage = (event) => {
            try {
                const results = JSON.parse(event.data);
                this.drawResults(results);
                this.isProcessing = false;
            } catch (error) {
                console.error('Error processing message:', error);  // Debug log
            }
        };
    }

    async processFrame() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN || this.isProcessing) {
            requestAnimationFrame(() => this.processFrame());
            return;
        }

        try {
            this.isProcessing = true;

            const canvas = document.createElement('canvas');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);

            const frame = canvas.toDataURL('image/jpeg', 0.7);
            this.ws.send(frame);

            console.log('Frame sent');  // Debug log
        } catch (error) {
            console.error('Error processing frame:', error);  // Debug log
            this.isProcessing = false;
        }

        requestAnimationFrame(() => this.processFrame());
    }

    updateStatus(message, isConnected) {
        this.status.className = isConnected ? 'status connected' : 'status';
        this.status.querySelector('.status-text').textContent = message;
    }

    visualizeAudio() {
        this.analyser.getByteFrequencyData(this.dataArray);

        // Calculate average volume
        const average = Array.from(this.dataArray).reduce((a, b) => a + b, 0) / this.dataArray.length;

        // Calculate reactive glow intensity
        const intensity = Math.min(1, average / 128);
        const scale = 1 + (intensity * 0.6); // Scale from 1 to 1.3
        const opacity = intensity * 0.8; // Max opacity 0.8

        // Update reactive glow
        this.reactiveGlow.style.opacity = opacity;
        this.reactiveGlow.style.transform = `scale(${scale})`;

        requestAnimationFrame(() => this.visualizeAudio());
    }


    drawResults(results) {
        this.ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);

        if (!results || !results.bbox) {
            return;
        }

        const [x1, y1, x2, y2] = results.bbox;

        // Draw face detection box with gradient stroke
        const gradient = this.ctx.createLinearGradient(x1, y1, x2, y2);
        gradient.addColorStop(0, '#ff9500');
        gradient.addColorStop(1, '#00b8ff');

        this.ctx.strokeStyle = gradient;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        // Draw mesh landmarks if available
        if (results.landmarks && results.landmarks.length > 0) {
            this.ctx.fillStyle = '#ff0000';  // red dots for landmarks
            results.landmarks.forEach(point => {
                const [px, py] = point;
                this.ctx.beginPath();
                this.ctx.arc(px, py, 1.5, 0, 2 * Math.PI);
                this.ctx.fill();
            });
        }

        // Process the gender value to ensure it's a string
        let genderValue = results.gender;
        if (typeof genderValue === 'object') {
            genderValue = genderValue.value || genderValue.label ||
                Object.values(genderValue)[0] || 'Unknown';
        }

        // Update stats with proper gender value
        this.stats.innerHTML = `
            <div style="opacity: 0.7; text-align: right; direction: ltr;">**AI Analysis** </div>
            <div style="margin: 8px 0; text-align: right; direction: rtl;">
                سن: <strong>${results.age}</strong><br>
                جنسیت: <strong>${results.gender}</strong><br>
                حالت چهره: <strong>${results.emotion}</strong>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FaceAnalysisApp();
});