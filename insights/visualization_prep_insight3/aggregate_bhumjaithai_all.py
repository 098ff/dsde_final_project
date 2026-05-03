import os
import pandas as pd
import glob

def aggregate_bhumjaithai_ratio(base_path):
    # Get all district directories
    districts = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    
    all_results = []
    
    for district_name in districts:
        district_path = os.path.join(base_path, district_name)
        sub_districts = [d for d in os.listdir(district_path) if os.path.isdir(os.path.join(district_path, d))]
        
        for sub in sub_districts:
            sub_path = os.path.join(district_path, sub)
            # Find all summary_บัญชีรายชื่อ.csv files in this sub-district
            csv_files = glob.glob(os.path.join(sub_path, "หน่วยเลือกตั้งที่ */summary_บัญชีรายชื่อ.csv"))
            
            total_bhumjaithai_votes = 0
            total_valid_ballots = 0
            
            for f in csv_files:
                try:
                    df = pd.read_csv(f)
                    if 'scores.ภูมิใจไทย' in df.columns:
                        total_bhumjaithai_votes += df['scores.ภูมิใจไทย'].sum()
                    if 'valid_ballots' in df.columns:
                        total_valid_ballots += df['valid_ballots'].sum()
                except Exception as e:
                    print(f"Error reading {f}: {e}")
            
            ratio = total_bhumjaithai_votes / total_valid_ballots if total_valid_ballots > 0 else 0
            all_results.append({
                "amphoe": district_name,
                "tambon": sub,
                "bhumjaithai_votes": total_bhumjaithai_votes,
                "total_valid_ballots": total_valid_ballots,
                "ratio": ratio
            })
    
    return pd.DataFrame(all_results)

if __name__ == "__main__":
    base_dir = "vote-data"
    output_file = "visualization_prep/all_districts_bhumjaithai_ratio.csv"
    
    df_result = aggregate_bhumjaithai_ratio(base_dir)
    df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"All-in-one aggregation complete. Results saved to {output_file}")
    print(df_result)
