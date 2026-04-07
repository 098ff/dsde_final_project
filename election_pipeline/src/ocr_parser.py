import re
from thefuzz import fuzz

class ElectionOCRParser:
    def clean_score_to_int(self, score_str):
        """แปลงคะแนนให้เป็น Int เท่านั้น ถ้าเป็น '-' หรืออักขระอื่น ให้เป็น 0"""
        if not score_str: return 0
        score_str = score_str.strip()
        if score_str in ['-', '—', '.', '']: return 0
        
        # ดึงเฉพาะตัวเลข (Arabic และ Thai)
        digits = re.sub(r'[^\d๑-๙]', '', score_str)
        if digits:
            # แปลงเลขไทยเป็นอารบิกก่อนแปลงเป็น int
            thai_digits = "๐๑๒๓๔๕๖๗๘๙"
            for i, d in enumerate(thai_digits):
                digits = digits.replace(d, str(i))
            return int(digits)
        return 0
        
    def parse_markdown(self, markdown_text):
        data = {
            "eligible_voters": self.extract_number(r'ผู้มีสิทธิเลือกตั้ง.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "voters_showed_up": self.extract_number(r'มาแสดงตน.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "ballots_allocated": self.extract_number(r'ได้รับจัดสรร.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "ballots_used": self.extract_number(r'บัตรเลือกตั้งที่ใช้.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "valid_ballots": self.extract_number(r'บัตรดี.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "invalid_ballots": self.extract_number(r'บัตรเสีย.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "no_vote_ballots": self.extract_number(r'ไม่เลือก.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "ballots_remaining": self.extract_number(r'บัตรเลือกตั้งที่เหลือ.*?จำนวน\s*([\d,๑-๙]+)', markdown_text),
            "scores": {}
        }
        
        # ค้นหาตาราง (รองรับทั้ง MD และ HTML)
        rows = re.findall(r'\|\s*[\d๑-๙]+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', markdown_text)
        if not rows:
            rows = re.findall(r'<tr>.*?<td>.*?</td><td>(.*?)</td><td>(.*?)</td>.*?</tr>', markdown_text, re.DOTALL)

        for name, score in rows:
            clean_name = re.sub(r'<[^>]+>', '', name).strip()
            if "ชื่อ" in clean_name or "พรรค" in clean_name: continue
            data['scores'][clean_name] = self.clean_score_to_int(score)
            
        return data

    def validate_data(self, data, file_type, master_list=None, threshold=80):
        flags = {"flag_math_total_used": False, "flag_math_valid_score": False, 
                 "flag_name_mismatch": False, "flag_details": []}
        
        # --- 1. Similarity Mapping ---
        normalized_scores = {}
        if master_list:
            for name, score in data['scores'].items():
                best_match, score_ratio = None, 0
                for m_name in master_list:
                    ratio = fuzz.ratio(name, m_name)
                    if ratio > score_ratio:
                        best_match, score_ratio = m_name, ratio
                
                if score_ratio >= threshold:
                    normalized_scores[best_match] = normalized_scores.get(best_match, 0) + score
                else:
                    normalized_scores[name] = score
                    flags["flag_name_mismatch"] = True
            data['scores'] = normalized_scores

        # --- 2. Math Validation ---
        sum_ballots = data['valid_ballots'] + data['invalid_ballots'] + data['no_vote_ballots']
        if data['ballots_used'] != sum_ballots:
            flags["flag_math_total_used"] = True
            flags["flag_details"].append(f"บัตรใช้({data['ballots_used']}) != รวมย่อย({sum_ballots})")
            
        sum_scores = sum(data['scores'].values())
        if data['valid_ballots'] != sum_scores:
            flags["flag_math_valid_score"] = True
            flags["flag_details"].append(f"บัตรดี({data['valid_ballots']}) != รวมคะแนน({sum_scores})")
            
        flags["needs_manual_check"] = any([flags["flag_math_total_used"], flags["flag_math_valid_score"], flags["flag_name_mismatch"]])
        flags["flag_details"] = " | ".join(flags["flag_details"]) if flags["flag_details"] else "OK"
        return flags

    def extract_number(self, pattern, text):
        match = re.search(pattern, text)
        return self.clean_score_to_int(match.group(1)) if match else 0