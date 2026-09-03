from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib

# 1. Initialize the API
app = FastAPI(title="Railway Predictive Maintenance API")

# 2. Load the trained AI model
print("Loading AI Model...")
model = joblib.load('rf_model.pkl')

# 3. Define the expected JSON payload format
class SensorTelemetry(BaseModel):
    motor_current_peak_amps: float
    motor_current_avg_amps: float
    throw_duration_ms: int
    vibration_peak_g: float
    ambient_temp_c: float

# 4. Create the prediction endpoint
@app.post("/predict")
def predict_failure(telemetry: SensorTelemetry):
    try:
        # Convert incoming JSON to a pandas DataFrame
        data = pd.DataFrame([telemetry.model_dump()])
        
        # Run it through the AI
        prediction = model.predict(data)[0]
        confidence = model.predict_proba(data)[0].max()
        
        # Format the response
        if prediction == 1:
            return {
                "status": "DANGER",
                "message": "Degradation Detected! Maintenance Block Recommended.",
                "confidence": round(confidence * 100, 2)
            }
        else:
            return {
                "status": "HEALTHY",
                "message": "Asset operating normally.",
                "confidence": round(confidence * 100, 2)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))