from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from App.services.prediction import PredictionService
from App.routes.auth import get_current_user
from typing import Dict, Any

router = APIRouter(tags=["Disease Prediction"])
from fastapi import Request

def get_prediction_service(request: Request):
    return request.app.state.prediction_service
    
@router.post("/predict/disease")
async def predict_disease(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    service: PredictionService = Depends(get_prediction_service)
):
    """
    Endpoint to upload an image of a wheat leaf and get a disease prediction.
    Predicted classes: Brown Rust, Yellow Rust, Healthy.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        contents = await file.read()
        result = await service.predict_wheat_disease(contents, file.filename)
        print(f"Prediction Result -> {result}")
        
        return {
            "status": "success",
            "filename": file.filename,
            "prediction": result
        }
    except Exception as e:
        print(f"DEBUG: Prediction Error -> {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
