import os
import cv2
import numpy as np
import pypdfium2 as pdfium

def convert_pdf_to_images(pdf_path, dpi=300):
    """Converts PDF pages to PIL images using pypdfium2."""
    print(f"Converting {pdf_path} to images using pypdfium2...")
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        images = []
        for page in pdf:
            # Render page to PIL image
            bitmap = page.render(scale=dpi/72) # 72 is default PDF DPI
            pil_image = bitmap.to_pil()
            images.append(pil_image)
        return images
    except Exception as e:
        print(f"Error converting {pdf_path}: {e}")
        return []

def optimize_image(pil_image):
    """Applies Grayscale conversion and Adaptive Thresholding."""
    # Convert PIL to OpenCV format
    open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    # Convert to Grayscale
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian Adaptive Thresholding
    optimized = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    return optimized

def chunk_image(optimized_image, split_ratio=0.3):
    """Splits image horizontally into Header and Table."""
    h, w = optimized_image.shape
    split_point = int(h * split_ratio)
    
    header = optimized_image[0:split_point, 0:w]
    table = optimized_image[split_point:h, 0:w]
    
    return header, table

def process_pdf(pdf_path, output_dir="data/processed"):
    """Full preprocessing pipeline for a single PDF."""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    unit_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(unit_dir, exist_ok=True)
    
    images = convert_pdf_to_images(pdf_path)
    
    for i, img in enumerate(images):
        optimized = optimize_image(img)
        header, table = chunk_image(optimized)
        
        # Save chunks
        header_path = os.path.join(unit_dir, f"page_{i+1}_header.png")
        table_path = os.path.join(unit_dir, f"page_{i+1}_table.png")
        
        cv2.imwrite(header_path, header)
        cv2.imwrite(table_path, table)
        
        print(f"Saved: {header_path}, {table_path}")

def main():
    root_dir = "."
    output_base = "data/processed"
    
    # Scan for PDFs
    pdfs = [f for f in os.listdir(root_dir) if f.endswith(".pdf")]
    
    if not pdfs:
        print("No PDF files found in the root directory.")
        return
        
    for pdf in pdfs:
        process_pdf(pdf, output_base)

if __name__ == "__main__":
    main()
