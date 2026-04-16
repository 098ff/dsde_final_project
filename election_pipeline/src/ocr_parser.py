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
        tr_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', markdown_text, re.DOTALL | re.IGNORECASE)
        if tr_matches:
            for tr in tr_matches:
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.DOTALL | re.IGNORECASE)
                if len(cells) >= 3:
                    clean_name = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    clean_score = re.sub(r'<[^>]+>', '', cells[-1]).strip()
                    if "ชื่อ" in clean_name or "พรรค" in clean_name: continue
                    data['scores'][clean_name] = self.clean_score_to_int(clean_score)
        else:
            lines = markdown_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('|') and line.endswith('|'):
                    cells = [c.strip() for c in line.split('|') if c.strip()]
                    if len(cells) >= 3 and not all(c == '-' for c in cells[0].replace(' ', '')):
                        if re.search(r'[\d๑-๙]', cells[0]):
                            clean_name = re.sub(r'<[^>]+>', '', cells[1]).strip()
                            clean_score = re.sub(r'<[^>]+>', '', cells[-1]).strip()
                            if "ชื่อ" in clean_name or "พรรค" in clean_name: continue
                            data['scores'][clean_name] = self.clean_score_to_int(clean_score)

        return data

    def extract_number(self, pattern, text):
        match = re.search(pattern, text)
        return self.clean_score_to_int(match.group(1)) if match else clean_score_to_int(None)
