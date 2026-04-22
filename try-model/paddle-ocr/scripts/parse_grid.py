import json
import os
import re

def clean_numeral(text):
    """
    Extracts numbers (Arabic/Thai) and converts Thai digits to Arabic.
    Example: '๑๒๓' -> '123', '20บัตร' -> '20'
    """
    if not text:
        return ""
    
    # Thai to Arabic mapping
    thai_map = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')
    
    # Keep only numeric characters (Arabic and Thai)
    # This regex matches digits 0-9 and Thai digits \u0e50-\u0e59
    numbers = re.findall(r'[0-9\u0e50-\u0e59]+', text)
    if not numbers:
        return ""
    
    combined = "".join(numbers)
    return combined.translate(thai_map)

def cluster_rows(ocr_data, y_threshold=20):
    """
    Groups OCR blocks into rows based on Y-coordinate centroids.
    """
    if not ocr_data:
        return []
        
    # Sort by Y-coordinate first
    sorted_blocks = sorted(ocr_data, key=lambda x: x['bbox'][0][1])
    
    rows = []
    if not sorted_blocks:
        return rows
        
    current_row = [sorted_blocks[0]]
    prev_y = sorted_blocks[0]['bbox'][0][1]
    
    for block in sorted_blocks[1:]:
        curr_y = block['bbox'][0][1]
        if abs(curr_y - prev_y) <= y_threshold:
            current_row.append(block)
        else:
            # Sort current row by X-coordinate
            rows.append(sorted(current_row, key=lambda x: x['bbox'][0][0]))
            current_row = [block]
            prev_y = curr_y
            
    if current_row:
        rows.append(sorted(current_row, key=lambda x: x['bbox'][0][0]))
        
    return rows

def parse_unit_data(rows):
    """
    Maps clustered rows to structured fields.
    """
    structured = {
        "metadata": {},
        "candidates": {},
        "summary_marks": {}
    }
    
    # Simplified mapping for Phase 3 prototype
    # Logic: Look for keywords in the first column of the row
    for i, row in enumerate(rows):
        row_text = " ".join([b['text'] for b in row])
        
        # 1. Metadata: Total Voters (1.1)
        if "๑.๑" in row_text or "จำนวนผู้มีสิทธิ" in row_text:
            val = next((clean_numeral(b['text']) for b in row if clean_numeral(b['text'])), "")
            structured["metadata"]["total_voters"] = {
                "raw": row_text,
                "val": int(val) if val.isdigit() else 0,
                "confidence": sum(b['confidence'] for b in row) / len(row)
            }
            
        # 2. Metadata: Attendees (1.2)
        elif "๑.๒" in row_text or "จำนวนผู้มาแสดงตน" in row_text:
             val = next((clean_numeral(b['text']) for b in row if clean_numeral(b['text'])), "")
             structured["metadata"]["attendees"] = {
                "raw": row_text,
                "val": int(val) if val.isdigit() else 0,
                "confidence": sum(b['confidence'] for b in row) / len(row)
            }
            
        # 3. Ballots (2.2.1 Good, 2.2.2 Bad, 2.3 NoVote)
        elif "๒.๒.๑" in row_text or "บัตรดี" in row_text:
             val = next((clean_numeral(b['text']) for b in row if clean_numeral(b['text'])), "")
             structured["summary_marks"]["good_ballots"] = {"val": int(val) if val.isdigit() else 0, "confidence": sum(b['confidence'] for b in row) / len(row)}
        
        elif "๒.๒.๒" in row_text or "บัตรเสีย" in row_text:
             val = next((clean_numeral(b['text']) for b in row if clean_numeral(b['text'])), "")
             structured["summary_marks"]["bad_ballots"] = {"val": int(val) if val.isdigit() else 0, "confidence": sum(b['confidence'] for b in row) / len(row)}
             
        elif "๒.๓" in row_text or "บัตรที่ไม่เลือก" in row_text:
             val = next((clean_numeral(b['text']) for b in row if clean_numeral(b['text'])), "")
             structured["summary_marks"]["novote_ballots"] = {"val": int(val) if val.isdigit() else 0, "confidence": sum(b['confidence'] for b in row) / len(row)}

    return structured

def main():
    input_file = "data/ocr_raw/page_1_table.json"
    output_file = "data/processed/parsed_unit.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    with open(input_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
        
    # 1. Cluster rows
    rows = cluster_rows(ocr_data)
    print(f"Detected {len(rows)} logical rows.")
    
    # 2. Parse into structure
    structured_data = parse_unit_data(rows)
    
    # 3. Save
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=2)
        
    print(f"Structure analysis saved to {output_file}")
    print("\nExtraction Summary:")
    print(f"Total Voters: {structured_data['metadata'].get('total_voters', {}).get('val', 'N/A')}")
    print(f"Attendees:    {structured_data['metadata'].get('attendees', {}).get('val', 'N/A')}")
    print(f"Good Ballots: {structured_data['summary_marks'].get('good_ballots', {}).get('val', 'N/A')}")
    print(f"Bad Ballots:  {structured_data['summary_marks'].get('bad_ballots', {}).get('val', 'N/A')}")
    print(f"No Vote:      {structured_data['summary_marks'].get('novote_ballots', {}).get('val', 'N/A')}")

if __name__ == "__main__":
    main()
