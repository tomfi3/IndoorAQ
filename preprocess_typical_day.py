"""
Preprocessing script to calculate and save typical day averages as percentages.
Calculates the average value for each 15-minute period of the day
across all available data, then converts to percentage of maximum for each parameter.

Usage: python preprocess_typical_day.py [session1|session2|all]
"""

import pandas as pd
import numpy as np
import sys

SESSIONS = {
    "session1": {
        "input": "attached_assets/session1/data.xlsx",
        "output": "attached_assets/session1/typical_day_averages.xlsx",
    },
    "session2": {
        "input": "attached_assets/session2/data.xlsx",
        "output": "attached_assets/session2/typical_day_averages.xlsx",
    },
}


def process_session(name, input_file, output_file):
    print(f"\n=== Processing {name} ===")
    print(f"Loading data from {input_file}...")
    df = pd.read_excel(input_file)

    # Identify date column
    date_columns = []
    for col in df.columns:
        if df[col].dtype in ['datetime64[ns]', 'datetime64[us]', 'object']:
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

    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    numeric_cols = [col for col in numeric_cols if 'unnamed' not in col.lower()]
    print(f"Found {len(numeric_cols)} numeric parameters: {numeric_cols}")

    # Create 15-minute time slots from 06:00 to 23:45
    time_slots = pd.date_range('06:00', '23:45', freq='15min').time
    time_slot_labels = [t.strftime('%H:%M') for t in time_slots]

    print("Calculating typical day averages (06:00-23:45 only)...")
    results = pd.DataFrame({'Time': time_slot_labels})

    for param in numeric_cols:
        print(f"  Processing {param}...")
        temp_df = df[[date_col, param]].copy()
        temp_df['time_slot'] = temp_df[date_col].dt.floor('15min').dt.time
        avg_by_slot = temp_df.groupby('time_slot')[param].mean()
        avg_by_slot = avg_by_slot.reindex(time_slots)

        min_val = avg_by_slot.min()
        max_val = avg_by_slot.max()

        if max_val > min_val:
            percent_values = ((avg_by_slot - min_val) / (max_val - min_val)) * 100
            print(f"    Min: {min_val:.2f}, Max: {max_val:.2f}, normalized to 0-100%")
        else:
            percent_values = avg_by_slot * 0 + 50
            print(f"    Min equals Max ({min_val:.2f}), using 50%")

        results[param] = percent_values.values

    print(f"Saving results to {output_file}...")
    results.to_excel(output_file, index=False)
    print(f"Done! Shape: {results.shape}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target == "all":
        for name, config in SESSIONS.items():
            process_session(name, config["input"], config["output"])
    elif target in SESSIONS:
        config = SESSIONS[target]
        process_session(target, config["input"], config["output"])
    else:
        print(f"Unknown session: {target}. Use: session1, session2, or all")
        sys.exit(1)
