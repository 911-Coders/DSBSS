import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# Set professional dark theme
plt.style.use('dark_background')

# --- 1. Predictive Model Feature Importance ---
def plot_feature_importance():
    model = joblib.load('rf_model.pkl')
    features = ['Peak Amps', 'Avg Amps', 'Throw Duration', 'Vibration', 'Temp']
    importances = model.feature_importances_
    
    plt.figure(figsize=(8, 5))
    sns.barplot(x=importances, y=features, palette='viridis')
    plt.title('Predictive IoT Model: Feature Importance')
    plt.xlabel('Importance Weight')
    plt.tight_layout()
    plt.savefig('feature_importance.png')
    plt.close()

# --- 2. Evaluation Confusion Matrix ---
def plot_confusion_matrix():
    # Simulated test set results (from your 99% accuracy training output)
    cm = np.array([[176, 0], [2, 22]])
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=['Normal', 'Anomaly'], yticklabels=['Normal', 'Anomaly'])
    plt.title('IoT Telemetry Confusion Matrix')
    plt.xlabel('Predicted State')
    plt.ylabel('Actual State')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png')
    plt.close()

# --- 3. Objective Routing Performance ---
def plot_financial_performance():
    routes = ['Line A (Main)', 'Line B (Bypass)', 'Line C (Loop)']
    profit = [13600, -2500, 8400] # Simulated route evaluation values
    
    plt.figure(figsize=(8, 5))
    plt.bar(routes, profit, color=['#00FF7F', '#FF4500', '#00FFFF'])
    plt.title('Routing Algorithm: Objective Maximization')
    plt.ylabel('Net Profit (USD)')
    plt.axhline(0, color='white', linewidth=1)
    plt.tight_layout()
    plt.savefig('financial_performance.png')
    plt.close()

if __name__ == "__main__":
    print("Generating performance graphs...")
    plot_feature_importance()
    plot_confusion_matrix()
    plot_financial_performance()
    print("✅ Graphs saved successfully!")