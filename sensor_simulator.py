import csv
import random
import uuid
from datetime import datetime, timedelta

# Configuration
NUM_RECORDS = 1000          
OUTPUT_FILE = 'point_machine_telemetry_trend.csv'

HEADERS = [
    'message_id', 'timestamp', 'asset_id', 
    'motor_current_peak_amps', 'motor_current_avg_amps', 
    'throw_duration_ms', 'vibration_peak_g', 
    'ambient_temp_c', 'label_anomaly'
]

def main():
    print(f"Generating {NUM_RECORDS} progressive telemetry records...")
    
    start_time = datetime.utcnow() - timedelta(days=30)
    
    # State tracking for gradual degradation
    is_degrading = False
    degradation_severity = 0.0  # Will slowly increase
    
    with open(OUTPUT_FILE, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        
        anomaly_count = 0
        
        for i in range(NUM_RECORDS):
            # Time moves forward 5 to 60 minutes per record
            start_time += timedelta(minutes=random.randint(5, 60))
            
            # 1. Check if we should start a new degradation cycle (if currently healthy)
            if not is_degrading and random.random() < 0.02: # 2% chance to START failing
                is_degrading = True
                degradation_severity = 0.1 # Start slightly degraded
            
            # 2. Generate the physics based on current health state
            ambient_temp = round(random.uniform(15.0, 40.0), 1)
            
            if not is_degrading:
                # NORMAL STATE: Healthy baseline
                peak_amps = round(random.uniform(4.5, 5.5), 2)
                avg_amps = round(random.uniform(3.0, 3.8), 2)
                throw_duration = int(random.uniform(2800, 3200))
                vibration = round(random.uniform(0.05, 0.15), 3)
                label = 0
            else:
                # DEGRADING STATE: Apply the severity multiplier to baseline values
                peak_amps = round(random.uniform(4.5, 5.5) + (3.0 * degradation_severity), 2)
                avg_amps = round(random.uniform(3.0, 3.8) + (2.0 * degradation_severity), 2)
                throw_duration = int(random.uniform(2800, 3200) + (1500 * degradation_severity))
                vibration = round(random.uniform(0.05, 0.15) + (0.3 * degradation_severity), 3)
                label = 1
                anomaly_count += 1
                
                # Slowly increase severity for the next loop (wear and tear gets worse)
                degradation_severity += random.uniform(0.05, 0.15)
                
                # If it gets too severe, simulate a "repair" happening, returning it to normal
                if degradation_severity > 1.0:
                    is_degrading = False
                    degradation_severity = 0.0
            
            # 3. Save the record
            data = {
                'message_id': str(uuid.uuid4()),
                'timestamp': start_time.isoformat() + "Z",
                'asset_id': 'PM-42-EAST',
                'motor_current_peak_amps': peak_amps,
                'motor_current_avg_amps': avg_amps,
                'throw_duration_ms': throw_duration,
                'vibration_peak_g': vibration,
                'ambient_temp_c': ambient_temp,
                'label_anomaly': label
            }
            writer.writerow(data)
            
    print(f"Simulation complete! Data saved to '{OUTPUT_FILE}'.")
    print(f"Total Anomalous Records: {anomaly_count} ({(anomaly_count/NUM_RECORDS)*100:.1f}%)")

if __name__ == "__main__":
    main()