# ใช้ Official Image ของ Airflow (Python 3.11)
FROM apache/airflow:2.8.1-python3.11

# ติดตั้ง OS Dependencies เผื่อ PyMuPDF หรือ Library จัดการภาพต้องการใช้
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     gcc \
     python3-dev \
     libgl1 \
     libglib2.0-0 \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

# ก๊อปปี้ไฟล์ requirements.txt และติดตั้ง Library
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt