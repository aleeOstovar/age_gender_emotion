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