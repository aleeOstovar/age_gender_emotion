# models/face_analyzer.py

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