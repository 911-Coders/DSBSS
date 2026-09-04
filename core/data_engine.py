import pandas as pd
import os

def get_corridor_schedule(station_code='MAO'):
    """
    Loads the railway dataset and extracts the schedule for a specific corridor.
    Applies financial penalty weights based on train commercial categories.
    """
    # 1. Locate the CSV dynamically (looks in the parent directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "FINAL_ML_READY_DATA.csv")
    
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: Could not find {csv_path}")
        return pd.DataFrame()

    # 2. Extract the specific station/corridor (e.g., MAO for Madgaon)
    corridor_df = df[df['station code'].str.contains(station_code, na=False, case=False)].copy()
    
    # Take a manageable chunk for the live simulation (e.g., 20 trains)
    corridor_df = corridor_df.head(20).copy()

    # 3. Apply Financial Weights (For the OR-Tools Solver)
    def assign_weight(train_name):
        name = str(train_name).lower()
        if 'rajdhani' in name or 'vande' in name or 'shatabdi' in name: 
            return 5  # Premium Priority
        elif 'exp' in name or 'express' in name or 'mail' in name: 
            return 3  # Medium Priority
        return 1      # Standard Freight/Local
    
    corridor_df['financial_weight'] = corridor_df['train name'].apply(assign_weight)
    
    # 4. Clean time data for algorithmic processing
    corridor_df['arr_min'] = pd.to_numeric(corridor_df['arr_min'], errors='coerce').fillna(0).astype(int)
    corridor_df['dep_min'] = pd.to_numeric(corridor_df['dep_min'], errors='coerce').fillna(0).astype(int)
    
    return corridor_df

# ==========================================
# VERIFICATION BLOCK
# ==========================================
if __name__ == "__main__":
    print("Testing Data Engine Extraction...")
    sample_df = get_corridor_schedule('MAO')
    
    if not sample_df.empty:
        print(f"✅ Successfully loaded {len(sample_df)} trains for the corridor.")
        print("-" * 50)
        print(sample_df[['train no', 'train name', 'financial_weight', 'arr_min', 'dep_min']].head())
    else:
        print("❌ Extraction failed.")