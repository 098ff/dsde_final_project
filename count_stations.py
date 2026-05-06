import os
from pathlib import Path

def count_election_stations(data_dir):
    """
    Counts the number of election stations in the given directory.
    An election station is considered to be any directory containing .csv files.
    """
    station_dirs = set()
    for root, _, files in os.walk(data_dir):
        # Check if there are any CSV files in this directory
        if any(f.endswith('.csv') for f in files):
            station_dirs.add(root)
            
    return len(station_dirs)

if __name__ == "__main__":
    # Note: Using the exact spelling from the directory structure
    data_path = 'election_pipeline/verfied_ocr_data'
    
    if os.path.exists(data_path):
        count = count_election_stations(data_path)
        print(f"Total election stations found: {count}")
    else:
        print(f"Error: Directory '{data_path}' not found.")
