import csv
import time
import random
import uuid
from datetime import datetime, timedelta

# Configuration
NUM_RECORDS = 1000          # Total number of switch movements to simulate
ANOMALY_RATE = 0.05         # 5% chance of generating a degraded/anomalous reading
OUTPUT_FILE = 'point_machine_telemetry.csv'

# Define the CSV headers (flattened JSON)
HEADERS = [
    'message_id', 
    'timestamp', 
    'asset_id', 
    'motor_current_peak_amps', 
    'motor_current_avg_amps', 
    'throw_duration_ms', 
    'vibration_peak_g', 
    'ambient_temp_c', 
    'label_anomaly' # 0 = Normal, 1 = Anomaly (Useful for checking your ML accuracy later)
]

def generate_reading(start_time, current_step):
    """Generates a single sensor payload with a chance of being anomalous."""
    
    is_anomaly = random.random() < ANOMALY_RATE
    
    # Base timestamp incremented by a random interval (e.g., 5 to 60 minutes between trains)
    timestamp = start_time + timedelta(minutes=(current_step * random.randint(5, 60)))
    
    if not is_anomaly:
        # NORMAL BEHAVIOR: Smooth, quick switch movement
        peak_amps = round(random.uniform(4.5, 5.5), 2)
        avg_amps = round(random.uniform(3.0, 3.8), 2)
        throw_duration = int(random.uniform(2800, 3200)) # Under 3.2 seconds
        vibration = round(random.uniform(0.05, 0.15), 3)
    else:
        # DEGRADED BEHAVIOR: Struggling motor, high friction, longer time to switch
        peak_amps = round(random.uniform(6.5, 8.5), 2)   # Higher current draw
        avg_amps = round(random.uniform(4.5, 6.0), 2)
        throw_duration = int(random.uniform(3800, 5000)) # Takes longer to lock
        vibration = round(random.uniform(0.25, 0.50), 3) # Grinding/shaking
        
    # Ambient temperature fluctuates naturally (e.g., between 15C and 40C)
    ambient_temp = round(random.uniform(15.0, 40.0), 1)

    return {
        'message_id': str(uuid.uuid4()),
        'timestamp': timestamp.isoformat() + "Z",
        'asset_id': 'PM-42-EAST',
        'motor_current_peak_amps': peak_amps,
        'motor_current_avg_amps': avg_amps,
        'throw_duration_ms': throw_duration,
        'vibration_peak_g': vibration,
        'ambient_temp_c': ambient_temp,
        'label_anomaly': 1 if is_anomaly else 0
    }

def main():
    print(f"Generating {NUM_RECORDS} telemetry records...")
    
    start_time = datetime.utcnow() - timedelta(days=30) # Start generating from 30 days ago
    
    with open(OUTPUT_FILE, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        
        anomaly_count = 0
        
        for i in range(NUM_RECORDS):
            data = generate_reading(start_time, i)
            writer.writerow(data)
            
            if data['label_anomaly'] == 1:
                anomaly_count += 1
                
    print(f"Simulation complete! Data saved to '{OUTPUT_FILE}'.")
    print(f"Total Anomalies Generated: {anomaly_count} ({(anomaly_count/NUM_RECORDS)*100:.1f}%)")

if __name__ == "__main__":
    main()