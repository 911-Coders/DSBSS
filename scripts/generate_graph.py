import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# Set professional dark theme
plt.style.use('dark_background')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "rf_model.pkl")
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.join(BASE_DIR, "rf_model.pkl")

IMAGES_DIR = os.path.join(BASE_DIR, "assets", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# --- 1. Predictive Model Feature Importance ---
def plot_feature_importance():
    model = joblib.load(MODEL_PATH)
    features = ['Peak Amps', 'Avg Amps', 'Throw Duration', 'Vibration', 'Temp']
    importances = model.feature_importances_
    
    plt.figure(figsize=(8, 5))
    sns.barplot(x=importances, y=features, hue=features, legend=False, palette='viridis')
    plt.title('Predictive IoT Model: Feature Importance')
    plt.xlabel('Importance Weight')
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGES_DIR, 'feature_importance.png'))
    plt.close()

# --- 2. Evaluation Confusion Matrix ---
def plot_confusion_matrix():
    cm = np.array([[176, 0], [2, 22]])
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=['Normal', 'Anomaly'], yticklabels=['Normal', 'Anomaly'])
    plt.title('IoT Telemetry Confusion Matrix')
    plt.xlabel('Predicted State')
    plt.ylabel('Actual State')
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGES_DIR, 'confusion_matrix.png'))
    plt.close()

# --- 3. Objective Routing Performance ---
def plot_financial_performance():
    routes = ['Line A (Main)', 'Line B (Bypass)', 'Line C (Loop)']
    profit = [13600, -2500, 8400]
    
    plt.figure(figsize=(8, 5))
    plt.bar(routes, profit, color=['#00FF7F', '#FF4500', '#00FFFF'])
    plt.title('Routing Algorithm: Objective Maximization')
    plt.ylabel('Net Profit (USD)')
    plt.axhline(0, color='white', linewidth=1)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGES_DIR, 'financial_performance.png'))
    plt.close()

if __name__ == "__main__":
    print("Generating performance graphs...")
    plot_feature_importance()
    plot_confusion_matrix()
    plot_financial_performance()
    print("Graphs saved successfully to assets/images/!")