import os
import fitz
import tempfile
import time
import cv2
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typhoon_ocr import ocr_document

from validation.engine import ElectionValidator

try:
    from airflow.exceptions import AirflowTaskTimeout as _AirflowTaskTimeout
except ImportError:
    _AirflowTaskTimeout = None  # running outside Airflow (tests, scripts)

# Hard cap per individual OCR API call — prevents the OpenAI client from blocking
# indefinitely when the server accepts the connection but never returns a response.
# 3 retries × 80s = 240s max per image chunk, well within the 300s task timeout.
_OCR_CALL_TIMEOUT = 80


def _ocr_with_timeout(image_path: str) -> str:
    """Call ocr_document() with a hard per-call timeout via a thread pool.

    IMPORTANT: does NOT use the ``with`` context manager for ThreadPoolExecutor
    because ``__exit__`` calls ``shutdown(wait=True)``, which would block until
    the hung thread finishes and neutralise the timeout entirely.  Instead we
    call ``shutdown(wait=False)`` to abandon the thread on timeout.
    """
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(ocr_document, pdf_or_image_path=image_path)
    try:
        result = future.result(timeout=_OCR_CALL_TIMEOUT)
        pool.shutdown(wait=False)
        return result
    except FuturesTimeout:
        pool.shutdown(wait=False)  # abandon the hung thread; do not block
        raise


# table detection
def has_table(page, threshold=15):
    pix = page.get_pixmap(dpi=150)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

    if pix.n == 4:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
    elif pix.n == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    _, bw = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    # horizontal
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=2)
    cnts_h, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # vertical
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel, iterations=2)
    cnts_v, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    total_lines = len(cnts_h) + len(cnts_v)
    return total_lines > threshold

def merge_pdfs(pdf_paths):
    sorted_paths = sorted(pdf_paths, key=lambda p: os.path.basename(p))
    combined = fitz.open() 

    # sort filename frist
    for path in sorted_paths:
        doc = fitz.open(path)
        combined.insert_pdf(doc)
        doc.close()

    return combined


def detect_and_route(doc):
    total_pages = len(doc)
    valid_counts = {2, 4, 6}

    if total_pages not in valid_counts:
        raise ValueError(f"⚠️ [Processor] Invalid page count ({total_pages} pages). Expected 2, 4, or 6.")

    page1_has_table = has_table(doc.load_page(0))
    page2_has_table = has_table(doc.load_page(1)) if total_pages >= 2 else False

    routes = []

    if total_pages == 2:
        if page1_has_table and page2_has_table: 
            raise ValueError("⚠️ [Processor] Anomaly: 2 pages detected but both have tables. Cannot determine route.")
        else:
            routes.append(([0], "แบ่งเขต"))

    elif total_pages == 4:
        if page1_has_table and page2_has_table: 
            routes.append(([0, 1, 2], "บัญชีรายชื่อ"))
        else:
            raise ValueError("⚠️ [Processor] Anomaly: 4 pages detected but missing expected table pattern. Cannot determine route.")

    elif total_pages == 6:
        if page1_has_table and page2_has_table:
            # Party List first (0,1,2 skip 3) + Constituency (4 skip 5)
            routes.append(([0, 1, 2], "บัญชีรายชื่อ"))
            routes.append(([4], "แบ่งเขต"))
        else:
            # Constituency first (0 skip 1) + Party List (2,3,4 skip 5)
            routes.append(([0], "แบ่งเขต"))
            routes.append(([2, 3, 4], "บัญชีรายชื่อ"))

    return routes


def process_pages(doc, page_indices, file_type, parser, master_candidates, master_parties):
    full_text = ""
    ocr_timeout_occurred = False
    timeout_details = []

    for page_idx in page_indices:
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 📐 ปรับขนาดภาพถ้าใหญ่เกินไปเพื่อป้องกัน Timeout โดยไม่ทำให้โครงสร้างพัง (ไม่ตัดครึ่ง)
        w, h = img.size
        # กำหนดขนาดสูงสุดที่ 2000 pixel
        if max(w, h) > 2000:
            ratio = 2000 / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            img.convert('L').save(tmp.name, "JPEG", quality=75)
            tmp_path = tmp.name

        for attempt in range(3):
            try:
                extracted_text = _ocr_with_timeout(tmp_path)
                full_text += "\n" + extracted_text
                break
            except FuturesTimeout:
                print(f"⚠️ [Processor] OCR call timed out after {_OCR_CALL_TIMEOUT}s (attempt {attempt+1}/3)")
                if attempt == 2:
                    ocr_timeout_occurred = True
                    timeout_details.append(f"Page {page_idx}")
                    print(f"⚠️ [Processor] Skipping page {page_idx} due to timeout")
            except Exception as e:
                if _AirflowTaskTimeout and isinstance(e, _AirflowTaskTimeout):
                    raise  # task-level timeout — never retry
                print(f"⚠️ [Processor] OCR error attempt {attempt+1}: {e}")
                if attempt == 2:
                    raise
                time.sleep(3)

        os.remove(tmp_path)

    # นำ Text ที่ได้ไปเข้ากระบวนการ Parser (สกัดตัวเลข) แล้ว Validate ด้วย ElectionValidator
    parsed_data = parser.parse_markdown(full_text)
    validator = ElectionValidator(master_candidates, master_parties)
    cleaned_data, flags_data = validator.validate(parsed_data, form_type=file_type)

    # Add OCR timeout flag to the flags_data
    if ocr_timeout_occurred:
        flags_data["flag_ocr_timeout"] = True
        flags_data["flag_ocr_timeout_detail"] = " | ".join(timeout_details)
    else:
        flags_data["flag_ocr_timeout"] = False
        flags_data["flag_ocr_timeout_detail"] = "OK"

    return cleaned_data, flags_data