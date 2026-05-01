"""
One-off script: geocode Thai tambon names via Google Maps Geocoding API
and print the updated _TAMBON_COORDS dict for copy-paste into data_loader.py.

Usage:
    python fetch_tambon_coords.py --api-key YOUR_API_KEY

Requires: requests (already in project deps)
"""

import argparse
import time
import requests

TAMBON_NAMES = [
    # อำเภอบ้านไร่
    "ตำบลบ้านไร่",
    "ตำบลคอกควาย",
    "ตำบลหนองจอก",
    "ตำบลเจ้าวัด",
    "ตำบลวังหิน",
    "ตำบลทัพหลวง",
    "ตำบลบ้านบึง",
    "ตำบลหูช้าง",
    "ตำบลเมืองการุ้ง",
    "ตำบลแก่นมะกรูด",
    "ตำบลห้วยแห้ง",
    "ตำบลหนองบ่มกล้วย",
    "ตำบลบ้านใหม่คลองเคียน",
    # อำเภอลานสัก
    "ตำบลลานสัก",
    "ตำบลทุ่งนางาม",
    "ตำบลน้ำรอบ",
    "ตำบลประดู่ยืน",
    "ตำบลป่าอ้อ",
    "ตำบลระบำ",
    # อำเภอหนองฉาง
    "ตำบลทุ่งโพ",
    "ตำบลเขากวางทอง",
    "ตำบลเขาบางแกรก",
    # อำเภอห้วยคต
    "ตำบลทองหลาง",
    "ตำบลห้วยคต",
    "ตำบลสุขฤทัย",
]

PROVINCE_CONTEXT = "อุทัยธานี ประเทศไทย"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def _call_api(query: str, api_key: str) -> dict:
    resp = requests.get(
        GEOCODE_URL,
        params={"address": query, "key": api_key, "language": "th"},
        timeout=10,
    )
    return resp.json()


def geocode(name: str, api_key: str) -> tuple[float, float] | None:
    # Attempt 1: full Thai tambon name + province
    data = _call_api(f"{name} {PROVINCE_CONTEXT}", api_key)
    if data.get("status") == "OK" and data["results"]:
        loc = data["results"][0]["geometry"]["location"]
        return round(loc["lat"], 6), round(loc["lng"], 6)

    status1 = data.get("status")
    err1 = data.get("error_message", "")

    # Attempt 2: drop "ตำบล" prefix — some names resolve better without it
    short_name = name.removeprefix("ตำบล")
    data2 = _call_api(f"{short_name} {PROVINCE_CONTEXT}", api_key)
    if data2.get("status") == "OK" and data2["results"]:
        loc = data2["results"][0]["geometry"]["location"]
        print(f"  [RETRY-OK] '{name}' resolved via short name '{short_name}'")
        return round(loc["lat"], 6), round(loc["lng"], 6)

    status2 = data2.get("status")
    err2 = data2.get("error_message", "")
    print(
        f"  [FAIL] '{name}': "
        f"attempt1={status1!r} {err1!r}, attempt2={status2!r} {err2!r}"
    )
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True, help="Google Maps Geocoding API key")
    args = parser.parse_args()

    results: dict[str, tuple[float, float]] = {}
    fallbacks: list[str] = []

    for name in TAMBON_NAMES:
        coords = geocode(name, args.api_key)
        if coords:
            results[name] = coords
            print(f"  OK  {name}: {coords}")
        else:
            fallbacks.append(name)
        time.sleep(0.2)  # stay well under 10 req/s free-tier rate limit

    print("\n\n# ---- paste this into data_loader.py ----\n")
    print("_TAMBON_COORDS: dict[str, tuple[float, float]] = {")
    for name, (lat, lon) in results.items():
        padded = f'"{name}":'
        print(f"    {padded:<36} ({lat}, {lon}),")
    print("}")

    if fallbacks:
        print(f"\n# [WARN] Could not geocode {len(fallbacks)} tambons — keep old values:")
        for name in fallbacks:
            print(f"#   {name}")


if __name__ == "__main__":
    main()
