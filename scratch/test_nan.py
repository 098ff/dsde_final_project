import pandas as pd
import numpy as np
import json

# Sample data with NaN
data = {
    "valid_ballots": 100,
    "invalid_ballots": np.nan,
    "no_vote_ballots": 5,
    "ballots_used": 105,
    "scores": {"Candidate A": 95, "Candidate B": np.nan}
}

# 1. Math Propagation
sum_ballots = data['valid_ballots'] + data['invalid_ballots'] + data['no_vote_ballots']
print(f"Sum Ballots (with NaN): {sum_ballots}")
print(f"Is NaN? {np.isnan(sum_ballots)}")

# 2. CSV Export with MISSING
df = pd.json_normalize([data])
csv_path = "scratch_test.csv"
df.to_csv(csv_path, index=False, na_rep="MISSING")
with open(csv_path, 'r') as f:
    print("\nCSV Output:")
    print(f.read())

# 3. JSON Export with NaN
try:
    print("\nJSON Output (json.dump):")
    print(json.dumps(data, indent=4))
except Exception as e:
    print(f"Error in json.dumps: {e}")

# 4. JSON Export (df.to_json)
print("\nJSON Output (df.to_json):")
print(df.to_json(orient='records', indent=4))
