# routes/api_routes.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from shared_state import last_detected, detection_lock

router = APIRouter()

@router.get("/predict")  # This will become /api/predict due to the prefix
async def get_predictions():
    """
    Returns the most recent detected age, gender, and emotion.
    """
    with detection_lock:
        if not last_detected:
            return JSONResponse(content={"error": "هیچ چهره‌ای تشخیص داده نشده است"}, status_code=404)
        
        # Copy the latest results to avoid race conditions
        results = last_detected.copy()
    
    # Map emotion and gender to Persian
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
    
    results["emotion"] = emotion_map.get(results.get("emotion", ""), results.get("emotion", ""))
    results["gender"] = gender_map.get(results.get("gender", ""), results.get("gender", ""))
    
    return JSONResponse(content=results)
