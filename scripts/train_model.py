import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# 1. Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "point_machine_telemetry_trend.csv")
if not os.path.exists(DATA_FILE):
    DATA_FILE = os.path.join(BASE_DIR, "point_machine_telemetry_trend.csv")

MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)
MODEL_OUT = os.path.join(MODELS_DIR, "rf_model.pkl")

print(f"Loading data from {DATA_FILE}...")
df = pd.read_csv(DATA_FILE)

# 2. Prepare the Features (X) and Target (y)
X = df.drop(columns=['message_id', 'timestamp', 'asset_id', 'label_anomaly'])
y = df['label_anomaly']

# 3. Split into Training (80%) and Testing (20%) sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Training set size: {len(X_train)} | Testing set size: {len(X_test)}")

# 4. Initialize and Train the Random Forest Model
print("Training the Random Forest model...")
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
model.fit(X_train, y_train)
joblib.dump(model, MODEL_OUT)
print(f"Model successfully saved to {MODEL_OUT}!")

# 5. Evaluate the Model on the Test Set
print("\n--- Model Evaluation ---")
predictions = model.predict(X_test)
print("Confusion Matrix:\n", confusion_matrix(y_test, predictions))
print("\nClassification Report:\n", classification_report(y_test, predictions))

# 6. Analyze Feature Importance
print("--- Feature Importance ---")
feature_importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
for feature, importance in feature_importances.items():
    print(f"{feature}: {importance:.4f}")

# 7. Test a "Live" Reading
print("\n--- Simulating a Real-Time Prediction ---")
live_reading = pd.DataFrame([{
    'motor_current_peak_amps': 7.2,
    'motor_current_avg_amps': 5.1,
    'throw_duration_ms': 4200,
    'vibration_peak_g': 0.31,
    'ambient_temp_c': 28.5
}])

prediction = model.predict(live_reading)
confidence = model.predict_proba(live_reading)[0][1]

if prediction[0] == 1:
    print(f"[ALERT] Degradation Detected! (Confidence: {confidence*100:.1f}%)")
    print("Recommendation: Schedule Combined Maintenance Block.")
else:
    print(f"[OK] Asset operating normally. (Anomaly Probability: {confidence*100:.1f}%)")