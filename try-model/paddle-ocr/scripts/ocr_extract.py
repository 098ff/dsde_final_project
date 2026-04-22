import os
import json
import time
import cv2
import numpy as np
from paddleocr import PaddleOCR

def resize_image(image_path, max_dim=1500):
    """Resizes image if its largest dimension exceeds max_dim."""
    img = cv2.imread(image_path)
    if img is None:
        return None, None
        
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        print(f"Resizing image from {w}x{h} to {new_w}x{new_h} (scale={scale:.2f})")
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return img, scale
    return img, 1.0

def run_ocr(image_cv, lang='th'):
    """Initializes PaddleOCR and runs extraction on the given CV2 image."""
    print(f"Initializing PaddleOCR (lang={lang})...")
    start_init = time.time()
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    
    # Initialize PaddleOCR with speed-focused parameters
    ocr = PaddleOCR(
        lang=lang,
        text_det_thresh=0.3,
        text_det_box_thresh=0.5
    )
    print(f"Initialization took {time.time() - start_init:.2f}s")
    
    print(f"Running OCR extraction...")
    start_ocr = time.time()
    # Latest PaddleOCR returns a list of OCRResult objects
    result = ocr.ocr(image_cv)
    print(f"Extraction took {time.time() - start_ocr:.2f}s")
    
    return result

def save_ocr_results(result, output_path, scale=1.0):
    """Saves raw OCR results to a JSON file, adjusting coords for scale."""
    processed_results = []
    
    if result and len(result) > 0:
        obj = result[0]
        # Check if it's the new OCRResult object (dictionary-like)
        if isinstance(obj, dict) or hasattr(obj, 'keys'):
            texts = obj.get('rec_texts', [])
            scores = obj.get('rec_scores', [])
            boxes = obj.get('dt_polys', [])
            
            for i in range(len(texts)):
                bbox = boxes[i]
                original_bbox = [[float(coord) / scale for coord in pt] for pt in bbox]
                
                processed_results.append({
                    "text": texts[i],
                    "confidence": float(scores[i]),
                    "bbox": original_bbox
                })
        else:
            # Fallback for older PaddleOCR list-of-lists format
            print("Falling back to legacy OCR result format...")
            for line in obj:
                bbox = line[0]
                text_info = line[1]
                original_bbox = [[float(coord) / scale for coord in pt] for pt in bbox]
                processed_results.append({
                    "text": text_info[0],
                    "confidence": float(text_info[1]),
                    "bbox": original_bbox
                })
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_results, f, ensure_ascii=False, indent=2)
    
    return processed_results

def main():
    image_path = "data/processed/สส. 5 ทับ 18 ห้วยคต ชุดที่ 2/page_1_table.png"
    output_path = "data/ocr_raw/page_1_table.json"
    
    if not os.path.exists(image_path):
        print(f"Error: Target image not found at {image_path}")
        return
        
    try:
        # 1. Resize for speed
        img_cv, scale = resize_image(image_path)
        if img_cv is None:
            print(f"Failed to load image at {image_path}")
            return
            
        # 2. Run OCR
        raw_result = run_ocr(img_cv)
        
        # 3. Save and report
        processed = save_ocr_results(raw_result, output_path, scale)
        
        print(f"Successfully extracted {len(processed)} blocks.")
        if processed:
            mean_conf = sum(d['confidence'] for d in processed) / len(processed)
            print(f"Mean Confidence Score: {mean_conf:.4f}")
            
    except Exception as e:
        print(f"OCR failed: {e}")

if __name__ == "__main__":
    main()
