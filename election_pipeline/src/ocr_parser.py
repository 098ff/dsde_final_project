import re

from validation.linguistic_validator import clean_score_to_int, thai_word_to_int  # noqa: F401


class ElectionOCRParser:
    def clean_score_to_int(self, score_str):
        """Delegate to validation.linguistic_validator.clean_score_to_int.

        Returns an integer for valid numeric strings (Arabic or Thai digits),
        or ``numpy.nan`` for missing-data sentinels ('-', '—', '.', empty).
        """
        return clean_score_to_int(score_str)

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

    def extract_number(self, pattern, text):
        match = re.search(pattern, text)
        return self.clean_score_to_int(match.group(1)) if match else clean_score_to_int(None)
