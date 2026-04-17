import pandas as pd
import json
import os
from pathlib import Path
from src.config import BASE_OUTPUT_DIR

def export_individual_result(data, amphoe, tambon, unit, file_name, format_type='csv'):
    """บันทึกไฟล์รายหน่วยลงในโฟลเดอร์ output_data/ตำบล/หน่วย/ (หรือ output_data/อำเภอ/ สำหรับเคสพิเศษ)"""
    
    # สร้างโครงสร้าง Folder
    if not tambon and not unit:
        target_dir = BASE_OUTPUT_DIR / amphoe
    else:
        target_dir = BASE_OUTPUT_DIR / tambon / unit
        
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # กำหนดชื่อไฟล์ output
    base_name = Path(file_name).stem
    output_filename = f"{base_name}.{format_type}"
    save_path = target_dir / output_filename
    
    if format_type == 'csv':
        df = pd.json_normalize([data])
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
    else:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
    return save_path

def export_summary_report(summary_list, format_type='csv'):
    """บันทึกไฟล์ Master Log หลังจากรันครบทุกหน่วย"""
    BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    df_summary = pd.DataFrame(summary_list)
    save_path = BASE_OUTPUT_DIR / f"master_summary_log.{format_type}"
    
    if format_type == 'csv':
        df_summary.to_csv(save_path, index=False, encoding='utf-8-sig')
    else:
        df_summary.to_json(save_path, orient='records', force_ascii=False, indent=4)
        
    print(f"📊 [Exporter] บันทึก Master Summary เรียบร้อยที่: {save_path}")