from airflow.decorators import dag, task
from airflow.models.param import Param
from datetime import datetime
import pandas as pd


@dag(
    schedule_interval=None,
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['election', 'audit'],
    params={
        "amphoe": Param("อำเภอบ้านไร่", type="string", description="ชื่ออำเภอ — ใช้กรองเฉพาะแถวที่ต้องการ (เว้นว่างเพื่อตรวจทุกแถว)"),
    }
)
def structural_audit_pipeline():

    @task
    def load_summary(**kwargs):
        """อ่าน master_summary_log.csv ที่ election_ocr_pipeline สร้างไว้"""
        import os
        log_path = "/opt/airflow/output_data/master_summary_log.csv"
        if not os.path.exists(log_path):
            raise FileNotFoundError(
                f"ไม่พบ {log_path} — รัน election_ocr_pipeline ก่อนแล้วค่อยรัน DAG นี้"
            )

        df = pd.read_csv(log_path, encoding="utf-8-sig")

        # กรองตามอำเภอถ้าระบุมา
        amphoe = kwargs["params"].get("amphoe", "").strip()
        if amphoe and "amphoe" in df.columns:
            df = df[df["amphoe"] == amphoe]

        records = [
            {
                "Tambon": row["tambon"],
                "Unit": str(row["unit"]),
                "form_type": "Party List" if row["type"] == "บัญชีรายชื่อ" else "Constituency",
            }
            for _, row in df.iterrows()
        ]
        print(f"📋 โหลด {len(records)} รายการจาก master_summary_log.csv")
        return records

    @task
    def run_audit(records):
        """ตรวจสอบว่าแต่ละหน่วยมีครบทั้ง 2 ประเภทบัตรหรือไม่"""
        from validation.structural_auditor import audit_units, generate_missing_report

        missing = audit_units(records)
        output_path = "/opt/airflow/output_data/missing_units.csv"
        generate_missing_report(missing, output_path)

        if missing:
            print(f"⚠ พบ {len(missing)} หน่วยที่ขาดเอกสาร — ดูรายละเอียดที่ {output_path}")
            for item in missing:
                print(f"  ตำบล {item['Tambon']} หน่วย {item['Unit']} — ขาด {item['missing_form']}")
        else:
            print("✓ ทุกหน่วยมีบัตรเลือกตั้งครบทั้ง 2 ประเภท")

        return {"missing_count": len(missing), "output": output_path}

    records = load_summary()
    run_audit(records)


structural_audit_dag = structural_audit_pipeline()
