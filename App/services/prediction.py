import io
import asyncio
import os
from pathlib import Path
from typing import Dict, Any
import numpy as np
from PIL import Image
import cv2

# Lazy imports for heavy libraries
tf = None
load_model = None
img_to_array = None

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "wheat_disease_classifier.keras"

def get_segmented_image(image_np: np.ndarray, label_hint: str = "Healthy") -> np.ndarray:
    """
    Perform color-based segmentation in-memory using OpenCV.
    Replaces the previous slow disk-based watershed function.
    """
    color_ranges = {
        'Brown_Rust': (np.array([10, 45, 45]), np.array([30, 255, 255])),
        'Healthy': (np.array([35, 40, 40]), np.array([85, 255, 255])),
        'Yellow_Rust': (np.array([20, 100, 100]), np.array([35, 255, 255])),
    }

    # Normalize label hint
    label = 'Healthy'
    if "brown" in label_hint.lower(): label = 'Brown_Rust'
    elif "yellow" in label_hint.lower(): label = 'Yellow_Rust'

    lower, upper = color_ranges[label]

    # Convert RGB (from PIL/NumPy) to HSV for OpenCV
    hsv_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv_image, lower, upper)
    
    # Apply mask
    segmented = cv2.bitwise_and(image_np, image_np, mask=mask)
    return segmented

class PredictionService:
    def __init__(self):
        self.model = None
        self.class_names = ['Brown Rust', 'Healthy', 'Yellow Rust']
        self.class_info = {
            'Brown Rust': {
                "status": "Infected",
                "severity": "Moderate",
                "recommendation": "Apply Propiconazole 25% EC at 500ml/acre."
            },
            'Healthy': {
                "status": "Healthy",
                "severity": "None",
                "recommendation": "Maintain current irrigation and fertilization."
            },
            'Yellow Rust': {
                "status": "Infected",
                "severity": "High",
                "recommendation": "Spray Tebuconazole 25% @ 200ml/acre."
            }
        }
        print(f"PredictionService initialized (Ready for lazy loading from {MODEL_PATH})")

    def _ensure_model_loaded(self):
        """Lazy loads the heavy TensorFlow model only when needed."""
        global tf, load_model, img_to_array
        if self.model is None:
            print("🚀 Loading Wheat Disease Classification Model (First time use)...")
            import tensorflow as as_tf
            from keras.models import load_model as keras_load_model
            from tensorflow.keras.preprocessing.image import img_to_array as k_img_to_array
            
            tf = as_tf
            load_model = keras_load_model
            img_to_array = k_img_to_array
            
            if not MODEL_PATH.exists():
                raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
                
            self.model = load_model(str(MODEL_PATH), safe_mode=False)
            print("✅ Model loaded successfully.")

    def _sync_predict(self, image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        # 1. Ensure model is ready
        self._ensure_model_loaded()

        # 2. Process image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)
        
        # 3. Apply Segmentation (In-memory)
        segmented_np = get_segmented_image(image_np, filename)
        
        # 4. Final resize and prep for model
        input_image = Image.fromarray(segmented_np).resize((224, 224))
        arr = img_to_array(input_image)
        arr = np.expand_dims(arr, axis=0)

        # 5. Inference
        preds = self.model.predict(arr, verbose=0)
        idx = int(np.argmax(preds))
        confidence = float(np.max(preds)) * 100

        disease = self.class_names[idx]
        info = self.class_info[disease]

        return {
            "disease": disease,
            "status": info["status"],
            "severity": info["severity"],
            "recommendation": info["recommendation"],
            "confidence": round(confidence, 2),
            "class_index": idx
        }

    async def predict_wheat_disease(self, image_bytes: bytes, filename: str = ""):
        """
        Predicts disease from image bytes. 
        Uses a thread pool to avoid blocking the main async loop.
        """
        return await asyncio.to_thread(self._sync_predict, image_bytes, filename)

if __name__ == "__main__":
    # Test block
    service = PredictionService()
    # Mock some bytes for testing
    mock_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...' 
    # This will trigger the actual load
    # print(asyncio.run(service.predict_wheat_disease(mock_bytes, "healthy_leaf.jpg")))
