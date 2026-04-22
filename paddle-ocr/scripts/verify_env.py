import sys
import importlib

def check_library(lib_name):
    try:
        importlib.import_module(lib_name)
        print(f"[SUCCESS] {lib_name} is installed.")
        return True
    except ImportError:
        print(f"[FAILURE] {lib_name} is NOT installed.")
        return False

def main():
    print(f"Python Version: {sys.version}")
    
    libs = ['paddleocr', 'cv2', 'pdf2image', 'PIL', 'pandas']
    all_success = True
    
    for lib in libs:
        if not check_library(lib):
            all_success = False
            
    if all_success:
        print("\nAll core libraries verified.")
    else:
        print("\nSome libraries are missing. Run: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
