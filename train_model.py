import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
# 1. Load the generated dataset
DATA_FILE = 'point_machine_telemetry_trend.csv'
print(f"Loading data from {DATA_FILE}...")
df = pd.read_csv(DATA_FILE)

# 2. Prepare the Features (X) and Target (y)
# We drop strings and IDs because the ML model only understands numbers
X = df.drop(columns=['message_id', 'timestamp', 'asset_id', 'label_anomaly'])
y = df['label_anomaly']

# 3. Split into Training (80%) and Testing (20%) sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Training set size: {len(X_train)} | Testing set size: {len(X_test)}")

# 4. Initialize and Train the Random Forest Model
print("Training the Random Forest model...")
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
model.fit(X_train, y_train)
joblib.dump(model, 'rf_model.pkl')
print("Model successfully saved!")

# 5. Evaluate the Model on the Test Set
print("\n--- Model Evaluation ---")
predictions = model.predict(X_test)
print("Confusion Matrix:\n", confusion_matrix(y_test, predictions))
print("\nClassification Report:\n", classification_report(y_test, predictions))

# 6. Analyze Feature Importance
# This tells us which sensor readings are most critical for predicting a failure
print("--- Feature Importance ---")
feature_importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
for feature, importance in feature_importances.items():
    print(f"{feature}: {importance:.4f}")

# 7. Test a "Live" Reading
print("\n--- Simulating a Real-Time Prediction ---")
# Simulating a new incoming payload (e.g., high current, long throw time)
live_reading = pd.DataFrame([{
    'motor_current_peak_amps': 7.2,
    'motor_current_avg_amps': 5.1,
    'throw_duration_ms': 4200,
    'vibration_peak_g': 0.31,
    'ambient_temp_c': 28.5
}])

prediction = model.predict(live_reading)
confidence = model.predict_proba(live_reading)[0][1] # Probability of being class 1 (Anomaly)

if prediction[0] == 1:
    print(f"🚨 ALERT: Degradation Detected! (Confidence: {confidence*100:.1f}%)")
    print("Recommendation: Schedule Combined Maintenance Block.")
else:
    print(f"✅ Asset operating normally. (Anomaly Probability: {confidence*100:.1f}%)")