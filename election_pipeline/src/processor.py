import os
import fitz
import tempfile
import time
import cv2
import numpy as np
from PIL import Image
from typhoon_ocr import ocr_document


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
        print(f"⚠️ [Processor] Invalid page count ({total_pages} pages). Expected 2, 4, or 6.")
        return None

    page1_has_table = has_table(doc.load_page(0))
    page2_has_table = has_table(doc.load_page(1)) if total_pages >= 2 else False

    routes = []

    if total_pages == 2:
        if page1_has_table and page2_has_table: 
            print("⚠️ [Processor] Anomaly: 2 pages detected but both have tables. Skipping.")
            return None
        else:
            routes.append(([0], "แบ่งเขต"))

    elif total_pages == 4:
        if page1_has_table and page2_has_table: 
            routes.append(([0, 1, 2], "บัญชีรายชื่อ"))
        else:
            print("⚠️ [Processor] Anomaly: 4 pages detected but missing expected table pattern. Skipping.")
            return None

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


def process_pages(doc, page_indices, file_type, parser, master_list):
    full_text = ""

    for page_idx in page_indices:
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if file_type == "แบ่งเขต":
            # ✂️ ตัดรูปครึ่งบน-ครึ่งล่าง ป้องกัน Timeout
            w, h = img.size
            chunks = [img.crop((0, 0, w, h//2)), img.crop((0, h//2, w, h))]

            for chunk in chunks:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    chunk.convert('L').save(tmp.name, "JPEG", quality=75)

                    # Retry Logic 3 ครั้งต่อ 1 ท่อน
                    for attempt in range(3):
                        try:
                            extracted_text = ocr_document(pdf_or_image_path=tmp.name)
                            full_text += "\n" + extracted_text
                            break
                        except Exception as e:
                            print(f"⚠️ [Processor] Timeout attempt {attempt+1}: {e}")
                            time.sleep(3)

                    os.remove(tmp.name)
        else:
            # 📄 บัญชีรายชื่อ: ส่งทั้งหน้า (ย่อเป็นขาวดำ)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                img.convert('L').save(tmp.name, "JPEG", quality=75)
                for attempt in range(3):
                    try:
                        extracted_text = ocr_document(pdf_or_image_path=tmp.name)
                        full_text += "\n" + extracted_text
                        break
                    except Exception as e:
                        time.sleep(3)
                os.remove(tmp.name)

    # นำ Text ที่ได้ไปเข้ากระบวนการ Parser (สกัดตัวเลขและเช็คความถูกต้อง)
    parsed_data = parser.parse_markdown(full_text)
    flags_data = parser.validate_data(parsed_data, file_type, master_list=master_list)

    return parsed_data, flags_data