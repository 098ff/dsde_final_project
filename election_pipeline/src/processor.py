import os
import fitz
import tempfile
import time
from PIL import Image
from typhoon_ocr import ocr_document

def process_pdf(pdf_path, file_type, parser, master_list):
    """
    อ่าน PDF -> ทำ Image Chunking (ถ้าแบ่งเขต) -> ยิง API Typhoon -> ส่งให้ Parser จัดการ
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    
    # เงื่อนไข: แบ่งเขตเอาเฉพาะหน้า 1 (Index 0), บัญชีรายชื่อเอาทุกหน้า
    pages_to_process = [0] if file_type == "แบ่งเขต" else range(len(doc))
    
    for page_idx in pages_to_process:
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
                
    doc.close()
    
    # นำ Text ที่ได้ไปเข้ากระบวนการ Parser (สกัดตัวเลขและเช็คความถูกต้อง)
    parsed_data = parser.parse_markdown(full_text)
    flags_data = parser.validate_data(parsed_data, file_type, master_list=master_list)
    
    return parsed_data, flags_data