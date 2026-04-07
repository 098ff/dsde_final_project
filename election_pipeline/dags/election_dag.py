from airflow.decorators import dag, task
from airflow.models.param import Param
from datetime import datetime
import os
import shutil

from src.gdrive_client import get_gdrive_service, list_folders_in_folder, download_files_from_folder
from src.processor import process_pdf
from src.ocr_parser import ElectionOCRParser
from src.exporter import export_individual_result, export_summary_report
from src.config import MASTER_PARTIES, MASTER_CANDIDATES, GDRIVE_ROOT_FOLDER_ID

# กำหนดให้รับ Parameter ตอนกด Trigger DAG
@dag(
    schedule_interval=None,
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['election', 'ocr'],
    params={
        "amphoe": Param("อำเภอบ้านไร่", type="string"),
        "tambons": Param([], type="array", description="เว้นว่างไว้เพื่อรันทุกตำบลในอำเภอนั้น")
    }
)
def election_ocr_pipeline():

    @task
    def discover_units(**kwargs):
        """Task 1: ค้นหาว่ามี 'หน่วยเลือกตั้ง' อะไรบ้างที่ต้องรัน (เพื่อเอาไปรันขนานกัน)"""
        params = kwargs['params']
        target_amphoe = params['amphoe']
        target_tambons = params['tambons']
        
        service = get_gdrive_service()
        
        # 1. หาโฟลเดอร์อำเภอ
        amphoe_folders = list_folders_in_folder(service, GDRIVE_ROOT_FOLDER_ID, target_amphoe)
        if not amphoe_folders: raise ValueError(f"ไม่พบโฟลเดอร์อำเภอ {target_amphoe}")
        amphoe_id = amphoe_folders[0]['id']
        
        # 2. หาโฟลเดอร์ตำบล
        tambon_folders = list_folders_in_folder(service, amphoe_id)
        if target_tambons: # ถ้าระบุมาให้ Filter
            tambon_folders = [t for t in tambon_folders if t['name'] in target_tambons]
            
        units_to_process = []
        
        # 3. หาโฟลเดอร์หน่วยเลือกตั้งในแต่ละตำบล
        for tambon in tambon_folders:
            unit_folders = list_folders_in_folder(service, tambon['id'])
            for unit in unit_folders:
                units_to_process.append({
                    "amphoe": target_amphoe,
                    "tambon": tambon['name'],
                    "unit": unit['name'],
                    "folder_id": unit['id']
                })
                
        # Return ลิสต์ของหน่วยทั้งหมด เพื่อให้ Airflow เอาไปแตก Task ขนานกัน
        return units_to_process

    @task(max_active_tis_per_dag=5) # จำกัดรันขนานพร้อมกัน 5 หน่วย 
    def process_unit(unit_info):
        """Task 2: โหลดไฟล์และทำ OCR สำหรับ '1 หน่วยเลือกตั้ง' (รันขนานกัน)"""
        service = get_gdrive_service()
        parser = ElectionOCRParser()
        
        temp_dir = f"/tmp/election_data/{unit_info['amphoe']}/{unit_info['tambon']}/{unit_info['unit']}"
        pdf_paths = download_files_from_folder(service, unit_info['folder_id'], temp_dir)
        
        unit_summary_logs = []
        
        for pdf_path in pdf_paths:
            file_name = os.path.basename(pdf_path)
            file_type = "บัญชีรายชื่อ" if "บช" in file_name else "แบ่งเขต"
            current_master = MASTER_PARTIES if file_type == "บัญชีรายชื่อ" else MASTER_CANDIDATES
            
            # Process & Validate
            parsed_data, flags_data = process_pdf(pdf_path, file_type, parser, current_master)
            
            # Save CSV/JSON ลงเครื่อง
            full_record = {
                "metadata": {"amphoe": unit_info['amphoe'], "tambon": unit_info['tambon'], "unit": unit_info['unit'], "file": file_name},
                **parsed_data,
                **flags_data
            }
            export_individual_result(full_record, unit_info['tambon'], unit_info['unit'], file_name)
            
            # เก็บ Log ส่งต่อให้ Task 3
            unit_summary_logs.append({
                "tambon": unit_info['tambon'],
                "unit": unit_info['unit'],
                "type": file_type,
                "file": file_name,
                "needs_manual_check": flags_data["needs_manual_check"],
                "flag_math_total_used": flags_data["flag_math_total_used"],
                "flag_math_valid_score": flags_data["flag_math_valid_score"],
                "flag_name_mismatch": flags_data["flag_name_mismatch"],
                "details": flags_data["flag_details"]
            })
            
        # ลบไฟล์ Temp ทิ้งเพื่อประหยัดพื้นที่
        shutil.rmtree(temp_dir)
        return unit_summary_logs

    @task
    def aggregate_summaries(all_unit_logs):
        """Task 3: รวบรวม Log จากทุกๆ หน่วย (ที่รันขนานกันเสร็จแล้ว) มาเซฟเป็น Master Log ไฟล์เดียว"""
        # all_unit_logs จะเป็น List of Lists -> ต้อง Flatten
        flat_logs = [log for unit_logs in all_unit_logs for log in unit_logs]
        export_summary_report(flat_logs, format_type='csv')
        print(f"🎉 Pipeline finished. Processed {len(flat_logs)} files.")

    # กำหนด Pipeline Flow
    units_list = discover_units()
    # ใช้ .expand() เพื่อสร้าง Task `process_unit` ขนานกันตามจำนวนหน่วยที่ค้นเจอ
    processed_logs = process_unit.expand(unit_info=units_list) 
    aggregate_summaries(processed_logs)

election_dag = election_ocr_pipeline()