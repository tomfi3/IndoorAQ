"""
Preprocessing script to calculate and save typical day averages
This calculates the average value for each 15-minute period of the day
across all available data, for each parameter.
"""

import pandas as pd
import numpy as np

# Input and output files
INPUT_FILE = "attached_assets/73 Oldfield Road - Full Data_1763474740403.xlsx"
OUTPUT_FILE = "attached_assets/typical_day_averages.xlsx"

print("Loading data...")
df = pd.read_excel(INPUT_FILE)

# Identify date column
date_columns = []
for col in df.columns:
    if df[col].dtype in ['datetime64[ns]', 'object']:
        try:
            pd.to_datetime(df[col])
            date_columns.append(col)
        except:
            pass

if not date_columns:
    raise ValueError("No date column found in the data")

date_col = date_columns[0]
df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

print(f"Using date column: {date_col}")

# Identify numeric parameters (excluding the date column)
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
print(f"Found {len(numeric_cols)} numeric parameters: {numeric_cols}")

# Create 15-minute time slots for the entire day (96 slots)
time_slots = pd.date_range('00:00', '23:45', freq='15min').time
time_slot_labels = [t.strftime('%H:%M') for t in time_slots]

print("Calculating typical day averages...")

# Create a dataframe to store results
results = pd.DataFrame({'Time': time_slot_labels})

# Calculate average for each parameter
for param in numeric_cols:
    print(f"  Processing {param}...")
    
    # Create temporary dataframe with date and parameter
    temp_df = df[[date_col, param]].copy()
    
    # Floor to 15-minute intervals
    temp_df['time_slot'] = temp_df[date_col].dt.floor('15min').dt.time
    
    # Group by time slot and calculate mean
    avg_by_slot = temp_df.groupby('time_slot')[param].mean()
    
    # Reindex to include all 96 time slots
    avg_by_slot = avg_by_slot.reindex(time_slots)
    
    # Add to results dataframe
    results[param] = avg_by_slot.values

# Save to Excel
print(f"Saving results to {OUTPUT_FILE}...")
results.to_excel(OUTPUT_FILE, index=False)

print("Done!")
print(f"\nTypical day averages saved to: {OUTPUT_FILE}")
print(f"Shape: {results.shape} (96 time slots × {len(numeric_cols)} parameters)")
