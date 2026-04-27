from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
import os
import shutil
import time

# ---------------------------------------------------------------------------
# Rate-limit config
# ---------------------------------------------------------------------------
RATE_LIMIT = os.getenv("RATE_LIMIT", "false").lower() == "true"
_CONCURRENCY = 1 if RATE_LIMIT else 5
_SLEEP_SECS  = 3 if RATE_LIMIT else 0

from src.gdrive_client import get_gdrive_service, list_folders_in_folder, download_files_from_folder
from src.processor import merge_pdfs, detect_and_route, process_pages
from src.ocr_parser import ElectionOCRParser
# from src.exporter import export_individual_result, export_summary_report
from src.exporter import export_individual_result
from src.config import MASTER_PARTIES, MASTER_CANDIDATES, GDRIVE_ROOT_FOLDER_ID

from validation.structural_auditor import audit_units
from validation.form_identifier import FORM_CONSTITUENCY, FORM_PARTY_LIST

_TYPE_MAP = {
    "บัญชีรายชื่อ": FORM_PARTY_LIST,
    "แบ่งเขต":      FORM_CONSTITUENCY,
}

@dag(
    schedule_interval=None,
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['election', 'ocr'],
    default_args={"execution_timeout": timedelta(seconds=300)},
    params={
        # ตอน Trigger สามารถพิมพ์แค่ "บ้านไร่", "นอกเขต", "ในเขต" ได้เลย
        "amphoe": Param("อำเภอบ้านไร่", type="string"),
        "tambons": Param([], type=["array", "null"], description="เว้นว่างไว้เพื่อรันทุกตำบลในโฟลเดอร์นั้น")
    }
)
def election_ocr_pipeline():

    @task
    def discover_units(**kwargs):
        """Task 1: ค้นหาว่ามี 'หน่วยเลือกตั้ง' อะไรบ้างที่ต้องรัน"""
        params = kwargs['params']
        target_amphoe = params['amphoe']
        target_tambons = params['tambons']

        service = get_gdrive_service()

        # 1. หาโฟลเดอร์เป้าหมาย (ด้วย keyword)
        amphoe_folders = list_folders_in_folder(service, GDRIVE_ROOT_FOLDER_ID, target_amphoe)
        if not amphoe_folders: 
            raise ValueError(f"ไม่พบโฟลเดอร์ที่มีคำว่า: {target_amphoe}")
        
        # ดึง ID และชื่อเต็มๆ ของโฟลเดอร์ที่ค้นเจอ
        amphoe_id = amphoe_folders[0]['id']
        actual_amphoe_name = amphoe_folders[0]['name']
        print(f"📂 Found Target Folder: {actual_amphoe_name}")

        units_to_process = []

        # ----------------------------------------------------
        # SPECIAL CASE CHECK (ข้ามการหา Tambon และ Unit)
        # ----------------------------------------------------
        if actual_amphoe_name in ["ล่วงหน้าในเขต", "ล่วงหน้านอกเขตและนอกราชอาณาจักร"]:
            units_to_process.append({
                "amphoe": actual_amphoe_name,
                "tambon": "",
                "unit": "",
                "folder_id": amphoe_id,
                "special_type": actual_amphoe_name
            })
            return units_to_process

        # 2. หาโฟลเดอร์ตำบล (หรือโฟลเดอร์ระดับกลาง)
        tambon_folders = list_folders_in_folder(service, amphoe_id)
        if target_tambons:
            tambon_folders = [t for t in tambon_folders if t['name'] in target_tambons]

        units_to_process = []

        # 3. หาโฟลเดอร์หน่วยเลือกตั้ง
        for tambon in tambon_folders:
            unit_folders = list_folders_in_folder(service, tambon['id'])
            for unit in unit_folders:
                units_to_process.append({
                    "amphoe": actual_amphoe_name, # ใช้ชื่อเต็มที่หาเจอ
                    "tambon": tambon['name'],
                    "unit": unit['name'],
                    "folder_id": unit['id']
                })

        return units_to_process

    @task(max_active_tis_per_dag=_CONCURRENCY)
    def process_unit(unit_info):
        """Task 2: ทำ OCR สำหรับ '1 หน่วยเลือกตั้ง'"""
        if _SLEEP_SECS:
            print(f"⏳ Rate-limit mode: waiting {_SLEEP_SECS}s before OCR request...")
            time.sleep(_SLEEP_SECS)

        service = get_gdrive_service()
        parser = ElectionOCRParser()

        temp_dir = f"/tmp/election_data/{unit_info['amphoe']}/{unit_info['tambon']}/{unit_info['unit']}"
        pdf_paths = download_files_from_folder(service, unit_info['folder_id'], temp_dir)
        
        prefix = f"[{unit_info['amphoe']}/{unit_info['tambon']}/{unit_info['unit']}]"

        if not pdf_paths:
            print(f"{prefix} ⚠️ No PDF files found")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        special_type = unit_info.get("special_type")

        # ฟังก์ชันย่อยสำหรับจัดการแต่ละ Route (ลด code ซ้ำ)
        def _process_and_export_routes(routes, doc_obj, chunk_suffix=""):
            for page_indices, file_type in routes:
                print(f"{prefix} 🚀 Start OCR | Pages={page_indices} | Type={file_type}")
                try:
                    parsed_data, flags_data = process_pages(
                        doc_obj, page_indices, file_type, parser,
                        master_candidates=MASTER_CANDIDATES,
                        master_parties=MASTER_PARTIES,
                    )
                except Exception as e:
                    print(f"{prefix} ❌ OCR FAILED | Pages={page_indices} | Type={file_type} | Error={str(e)}")
                    raise

                output_name = f"summary_{file_type}{chunk_suffix}"

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
                export_individual_result(full_record, unit_info['amphoe'], unit_info['tambon'], unit_info['unit'], output_name)

        if special_type == "ล่วงหน้านอกเขตและนอกราชอาณาจักร":
            import fitz
            # Processing each PDF separately, chunking into 2-page sub-documents
            for pdf_path in pdf_paths:
                base_pdf_name = os.path.basename(pdf_path)
                print(f"{prefix} 📄 SPLIT | File: {base_pdf_name}")
                doc = fitz.open(pdf_path)
                num_pages = len(doc)

                for chunk_idx, start_page in enumerate(range(0, num_pages, 2)):
                    end_page = min(start_page + 1, num_pages - 1)
                    sub_doc = fitz.open()
                    sub_doc.insert_pdf(doc, from_page=start_page, to_page=end_page)
                    
                    try:
                        routes = detect_and_route(sub_doc)
                    except ValueError as e:
                        print(f"{prefix} ⚠️ Chunk {chunk_idx+1} ({start_page} to {end_page}): {str(e)}")
                        sub_doc.close()
                        continue

                    chunk_suffix = f"-{chunk_idx + 1}"
                    _process_and_export_routes(routes, sub_doc, chunk_suffix)
                    
                    sub_doc.close()
                doc.close()

        else:
            # NORMAL CASE or "ล่วงหน้าในเขต" (merge all)
            combined_doc = merge_pdfs(pdf_paths)
            print(f"{prefix} 📄 MERGE | Files={len(pdf_paths)} -> Pages={len(combined_doc)}")

            try:
                routes = detect_and_route(combined_doc)
            except ValueError as e:
                print(f"{prefix} ⚠️ {str(e)}")
                combined_doc.close()
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise e

            _process_and_export_routes(routes, combined_doc)
            
            combined_doc.close()

        shutil.rmtree(temp_dir, ignore_errors=True)

    units_list = discover_units()
    process_unit.expand(unit_info=units_list)

election_dag = election_ocr_pipeline()