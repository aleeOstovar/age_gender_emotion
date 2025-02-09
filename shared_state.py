import threading

# Global variable to store the most recent estimation
last_detected = {}

# A lock to ensure thread-safe access to last_detected
detection_lock = threading.Lock()
