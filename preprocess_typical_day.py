"""
Preprocessing script to calculate and save typical day averages as percentages
This calculates the average value for each 15-minute period of the day
across all available data, then converts to percentage of maximum for each parameter.
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

# Identify numeric parameters (excluding the date column and Unnamed: 6)
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
# Filter out Unnamed: 6
numeric_cols = [col for col in numeric_cols if 'unnamed' not in col.lower()]
print(f"Found {len(numeric_cols)} numeric parameters: {numeric_cols}")

# Create 15-minute time slots from 06:00 to 23:45 (72 slots, excluding 00:00-06:00)
time_slots = pd.date_range('06:00', '23:45', freq='15min').time
time_slot_labels = [t.strftime('%H:%M') for t in time_slots]

print("Calculating typical day averages (06:00-23:45 only)...")

# Create a dataframe to store results
results = pd.DataFrame({'Time': time_slot_labels})

# Calculate average for each parameter and convert to percentage
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
    
    # Convert to percentage between minimum and maximum value
    min_val = avg_by_slot.min()
    max_val = avg_by_slot.max()
    
    if max_val > min_val:
        # Normalize to 0-100% between min and max
        percent_values = ((avg_by_slot - min_val) / (max_val - min_val)) * 100
        print(f"    Min: {min_val:.2f}, Max: {max_val:.2f}, normalized to 0-100% scale")
    else:
        # If min equals max, set all to 50%
        percent_values = avg_by_slot * 0 + 50
        print(f"    Min equals Max ({min_val:.2f}), using 50%")
    
    # Add to results dataframe
    results[param] = percent_values.values

# Save to Excel
print(f"Saving results to {OUTPUT_FILE}...")
results.to_excel(OUTPUT_FILE, index=False)

print("Done!")
print(f"\nTypical day averages (as % of range) saved to: {OUTPUT_FILE}")
print(f"Shape: {results.shape} (72 time slots from 06:00-23:45 × {len(numeric_cols)} parameters)")
print("All values are now percentages (0-100%) between min and max for each parameter (06:00-23:45 range).")
