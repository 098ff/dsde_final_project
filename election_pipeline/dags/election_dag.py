from airflow.decorators import dag, task
from airflow.models.param import Param
from datetime import datetime, timedelta
import os
import shutil
import time

# ---------------------------------------------------------------------------
# Rate-limit config — set RATE_LIMIT=true in .env to enable
# When True: 1 concurrent OCR task, 3-second gap between requests (20 req/min)
# When False: 5 concurrent OCR tasks, no delay (default)
# ---------------------------------------------------------------------------
RATE_LIMIT = os.getenv("RATE_LIMIT", "false").lower() == "true"
_CONCURRENCY = 1 if RATE_LIMIT else 5
_SLEEP_SECS  = 3 if RATE_LIMIT else 0

from src.gdrive_client import get_gdrive_service, list_folders_in_folder, download_files_from_folder
from src.processor import merge_pdfs, detect_and_route, process_pages
from src.ocr_parser import ElectionOCRParser
from src.exporter import export_individual_result, export_summary_report
from src.config import MASTER_PARTIES, MASTER_CANDIDATES, GDRIVE_ROOT_FOLDER_ID

from validation.structural_auditor import audit_units
from validation.form_identifier import FORM_CONSTITUENCY, FORM_PARTY_LIST

_TYPE_MAP = {
    "บัญชีรายชื่อ": FORM_PARTY_LIST,
    "แบ่งเขต":      FORM_CONSTITUENCY,
}

# กำหนดให้รับ Parameter ตอนกด Trigger DAG
@dag(
    schedule_interval=None,
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['election', 'ocr'],
    default_args={"execution_timeout": timedelta(seconds=60)},
    params={
        "amphoe": Param("อำเภอบ้านไร่", type="string"),
        "tambons": Param([], type=["array", "null"], description="เว้นว่างไว้เพื่อรันทุกตำบลในอำเภอนั้น")
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
        if target_tambons:
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

        return units_to_process

    @task(max_active_tis_per_dag=_CONCURRENCY)
    def process_unit(unit_info):
        """Task 2: โหลดไฟล์ รวม PDF วิเคราะห์โครงสร้าง และทำ OCR สำหรับ '1 หน่วยเลือกตั้ง' (รันขนานกัน)"""
        if _SLEEP_SECS:
            print(f"⏳ Rate-limit mode: waiting {_SLEEP_SECS}s before OCR request...")
            time.sleep(_SLEEP_SECS)

        service = get_gdrive_service()
        parser = ElectionOCRParser()

        temp_dir = f"/tmp/election_data/{unit_info['amphoe']}/{unit_info['tambon']}/{unit_info['unit']}"
        pdf_paths = download_files_from_folder(service, unit_info['folder_id'], temp_dir)

        unit_summary_logs = []

        if not pdf_paths:
            print(f"⚠️ No PDF files found in unit: {unit_info['unit']}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return unit_summary_logs

        # 1. Merge all PDF files into a single document (sorted by filename)
        combined_doc = merge_pdfs(pdf_paths)
        print(f"📄 Merged {len(pdf_paths)} files -> {len(combined_doc)} pages | Unit: {unit_info['unit']}")

        # 2. Analyze page structure and determine OCR routes
        routes = detect_and_route(combined_doc)

        if routes is None:
            print(f"⚠️ Skipping unit {unit_info['unit']} due to unexpected page count/structure ({len(combined_doc)} pages)")
            combined_doc.close()
            shutil.rmtree(temp_dir, ignore_errors=True)
            return unit_summary_logs

        # 3. Process each route
        for page_indices, file_type in routes:
            parsed_data, flags_data = process_pages(
                combined_doc, page_indices, file_type, parser,
                master_candidates=MASTER_CANDIDATES,
                master_parties=MASTER_PARTIES,
            )

            output_name = f"summary_{file_type}"

            full_record = {
                "metadata": {
                    "amphoe": unit_info['amphoe'],
                    "tambon": unit_info['tambon'],
                    "unit": unit_info['unit'],
                    "file": output_name
                },
                **parsed_data,
                **flags_data
            }
            export_individual_result(full_record, unit_info['tambon'], unit_info['unit'], output_name)

            needs_manual_check = any([
                flags_data.get("flag_math_total_used", False),
                flags_data.get("flag_math_valid_score", False),
                flags_data.get("flag_name_mismatch", False),
                flags_data.get("flag_missing_data", False),
                flags_data.get("flag_linguistic_mismatch", False),
            ])
            detail_parts = [
                flags_data.get("flag_math_total_used_detail", ""),
                flags_data.get("flag_math_valid_score_detail", ""),
            ]
            details = " | ".join(p for p in detail_parts if p and p != "OK") or "OK"

            unit_summary_logs.append({
                "amphoe": unit_info['amphoe'],
                "tambon": unit_info['tambon'],
                "unit": unit_info['unit'],
                "type": file_type,
                "file": output_name,
                "needs_manual_check": needs_manual_check,
                "flag_math_total_used": flags_data.get("flag_math_total_used", False),
                "flag_math_valid_score": flags_data.get("flag_math_valid_score", False),
                "flag_name_mismatch": flags_data.get("flag_name_mismatch", False),
                "flag_missing_data": flags_data.get("flag_missing_data", False),
                "flag_linguistic_mismatch": flags_data.get("flag_linguistic_mismatch", False),
                "details": details,
            })

        combined_doc.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
        return unit_summary_logs

    @task
    def aggregate_summaries(all_unit_logs):
        """Task 3: รวบรวม Log + ตรวจสอบความครบถ้วนของแบบฟอร์ม แล้วเซฟเป็น master_summary_log.csv"""
        flat_logs = [log for unit_logs in all_unit_logs for log in unit_logs]

        # --- Structural audit: stamp flag_missing_counterpart on every row ---
        records = [
            {
                "Tambon": log["tambon"],
                "Unit":   log["unit"],
                "form_type": _TYPE_MAP.get(log["type"], "Unknown"),
            }
            for log in flat_logs
        ]
        missing_items = audit_units(records)

        # Build a set of (tambon, unit) pairs that are missing their counterpart
        incomplete_stations = {
            (item["Tambon"], item["Unit"])
            for item in missing_items
        }

        for log in flat_logs:
            log["flag_missing_counterpart"] = (
                log["tambon"], log["unit"]
            ) in incomplete_stations

        export_summary_report(flat_logs, format_type='csv')

        missing_count = len({(i["Tambon"], i["Unit"]) for i in missing_items})
        print(
            f"Pipeline finished. Processed {len(flat_logs)} records. "
            f"{missing_count} station(s) flagged with flag_missing_counterpart=True."
        )

    # กำหนด Pipeline Flow
    units_list = discover_units()
    processed_logs = process_unit.expand(unit_info=units_list)
    aggregate_summaries(processed_logs)

election_dag = election_ocr_pipeline()
