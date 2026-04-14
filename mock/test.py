import fitz
import cv2
import numpy as np
import os

mock_dir = "."
files = sorted([f for f in os.listdir(mock_dir) if f.endswith('.pdf')])

page_counter = 1
for file in files:
    doc = fitz.open(os.path.join(mock_dir, file))
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(dpi=150)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        if pix.n == 4:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
        elif pix.n == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
            
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines_p = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        total_hough = len(lines_p) if lines_p is not None else 0
        
        _, bw = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        detect_horizontal = cv2.morphologyEx(bw, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        cnts_h = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts_h = cnts_h[0] if len(cnts_h) == 2 else cnts_h[1]
        
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        detect_vertical = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        cnts_v = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts_v = cnts_v[0] if len(cnts_v) == 2 else cnts_v[1]
        
        print(f"Page {page_counter} | Source: {file} (Page {page_idx+1}/{len(doc)}) | Hough: {total_hough} | Contours (H, V): ({len(cnts_h)}, {len(cnts_v)}) | Total H+V: {len(cnts_h)+len(cnts_v)}")
        page_counter += 1

