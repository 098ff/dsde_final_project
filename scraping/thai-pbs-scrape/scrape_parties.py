import argparse
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def normalize_label(text):
    if not text:
        return ""
    # Remove whitespace, zero-width chars, and dots for robust matching
    text = re.sub(r"[\s\u200b\u200c\u200d]", "", text)
    return text.replace(".", "")


def extract_aria_numbers(soup, min_value=1000000):
    values = []
    for ac in soup.find_all(attrs={"aria-label": True}):
        al = ac.attrs.get("aria-label", "")
        if re.search(r"\d{1,3}(?:,\d{3})+", al):
            val = int(re.sub(r"[^0-9]", "", al))
            if val >= min_value:
                values.append(val)
    return values


def extract_party_name(soup):
    # Primary: find the header block that contains the party name (text-xl font-bold)
    for span in soup.select("span.text-xl.font-bold, span.text-xl.font-semibold"):
        txt = span.get_text(strip=True)
        if re.search(r"[\u0E00-\u0E7F]", txt):
            return txt

    # Fallback: find any Thai text inside the rank/name header card
    for div in soup.find_all(
        "div", class_=lambda c: c and "min-h-12" in c and "bg-white" in c
    ):
        for span in div.find_all("span"):
            txt = span.get_text(strip=True)
            if re.search(r"[\u0E00-\u0E7F]", txt):
                if txt not in {
                    "อันดับ",
                    "คะแนน",
                    "ที่นั่ง",
                    "สส.เขต",
                    "สส.บัญชีรายชื่อ",
                }:
                    return txt

    # Last fallback: any Thai text in a prominent span
    for span in soup.select("span.text-lg, span.text-xl"):
        txt = span.get_text(strip=True)
        if re.search(r"[\u0E00-\u0E7F]", txt):
            if txt not in {"อันดับ", "คะแนน", "ที่นั่ง", "สส.เขต", "สส.บัญชีรายชื่อ"}:
                return txt

    return None


def extract_value(soup, label):
    # Prefer structured lookup: find the element containing the label text,
    # then search its ancestors for aria-label vote numbers.
    label_tag = None
    target = normalize_label(label)
    for node in soup.find_all(string=True):
        if target and target in normalize_label(node):
            label_tag = node.parent
            break

    if label_tag:
        anc = label_tag.parent
        steps = 0
        while anc is not None and steps < 5:
            # 1) prefer aria-label values with comma groups (clean vote numbers)
            try:
                aria_candidates = anc.find_all(attrs={"aria-label": True})
            except Exception:
                aria_candidates = []
            for ac in aria_candidates:
                al = ac.attrs.get("aria-label", "")
                if re.search(r"\d{1,3}(?:,\d{3})+", al):
                    return int(re.sub(r"[^0-9]", "", al))

            # 2) search nearby text nodes that look like comma-separated numbers
            try:
                txts = anc.find_all(string=re.compile(r"\d{1,3}(?:,\d{3})+"))
            except Exception:
                txts = []
            for t in txts:
                digits = re.sub(r"[^0-9]", "", t)
                if 4 <= len(digits) <= 12:
                    return int(digits)

            anc = anc.parent
            steps += 1

    return None


def sanitize_filename(name):
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def scrape_party(party_code, session=None, debug=False):
    url = (
        f"https://www.thaipbs.or.th/election69/result/party/{party_code}"
        "?tab=constituency&minitab=map&option=all"
    )
    s = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Scraper/1.0; +https://example.com)"
    }
    resp = s.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    if debug:
        print(f"Fetched {party_code}: status={resp.status_code} html_len={len(html)}")

    party_name = extract_party_name(soup)
    district = extract_value(soup, "สส.เขต")
    list_votes = extract_value(soup, "สส.บัญชีรายชื่อ")

    # Fallback: use large aria-label numbers in page order
    votes = []
    if district is None or list_votes is None:
        votes = extract_aria_numbers(soup)
        if votes:
            if district is None and len(votes) >= 1:
                district = votes[0]
            if list_votes is None and len(votes) >= 2:
                list_votes = votes[1]

    if debug and (district is None or list_votes is None):
        preview = ", ".join([format(v, ",d") for v in votes[:4]])
        print(f"Missing values for {party_code}. aria_votes=[{preview}]")

    return {
        "party": party_code,
        "party_name": party_name,
        "url": url,
        "district": district,
        "list": list_votes,
    }


def write_party_csv(row, out_dir):
    party_code = row.get("party") or "PARTY-UNKNOWN"
    party_num = party_code.split("-")[-1] if "-" in party_code else party_code
    party_name = row.get("party_name") or "unknown"
    safe_name = sanitize_filename(party_name) or "unknown"
    file_name = f"{party_num}-{safe_name}.csv"
    path = out_dir / file_name
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["district_votes", "list_votes"])
        writer.writerow([row.get("district") or "", row.get("list") or ""])
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=60)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--out-dir", default="party_csv")
    args = parser.parse_args()

    session = requests.Session()
    results = []
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(args.start, args.end + 1):
        code = f"PARTY-{i:04d}"
        try:
            row = scrape_party(code, session=session, debug=args.debug)
        except Exception as e:
            row = {
                "party": code,
                "party_name": None,
                "url": None,
                "district": None,
                "list": None,
            }
            print(f"Error fetching {code}: {e}")

        results.append(row)
        write_party_csv(row, out_dir)
        # polite pause
        time.sleep(0.4)

    # Print a simple table
    hdr = f"{'party':12} {'party_name':20} {'district_votes':>16} {'list_votes':>16}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        d = format(r["district"], ",d") if r["district"] is not None else "-"
        l = format(r["list"], ",d") if r["list"] is not None else "-"
        name = r.get("party_name") or "-"
        print(f"{r['party']:12} {name:20} {d:>16} {l:>16}")


if __name__ == "__main__":
    main()
