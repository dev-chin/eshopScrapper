import json
import requests
from concurrent.futures import ThreadPoolExecutor
import sys

REGIONS = ["BG", "CH", "CY", "EE", "HR", "IE", "LT", "LU", "LV", "MT", "RO", "SI", "SK", "AT", "BE", "CZ", "DK", "ES", "FI", "GR", "HU", "NL", "NO", "PL", "PT", "ZA", "SE", "IT", "FR", "DE", "GB", "TH", "KR", "SG", "MY", "TW"]

region = ""

OUTPUT = {}

def checkTitleid(titleid: str):
    url = f"https://ec.nintendo.com/apps/{titleid}/{region}"
    with requests.head(url, stream=True, allow_redirects=False) as response:
        status_code = response.status_code
        if (status_code == 303):
            OUTPUT[f"{titleid}"]["True"].append(region)
            print(f"✓ {region} {titleid}")
        elif (status_code == 403):
            print("✗ Hit rate limit. Aborting...")
            sys.exit(1)
        else: 
            print(f"✗ {region} {titleid}: {status_code}")
            OUTPUT[f"{titleid}"]["False"].append(region)

with open("output/main_regions_alt.json", "r", encoding="UTF-8") as f:
    titleids = list(json.load(f).keys())

try:
    with open("output/main_regions_alt2.json", "r", encoding="UTF-8") as f:
        OUTPUT = json.load(f)
except:
    pass

checkedtitleids = list(OUTPUT.keys())

titleids[:] = [x for x in titleids if x not in checkedtitleids]

for x in range(len(titleids)):
    OUTPUT[f"{titleids[x]}"] = {"True": [], "False": []}

for m_region in REGIONS:
    region = m_region
    with ThreadPoolExecutor(max_workers=1) as executor: #Setting more is risky because rate limits can kick in
        executor.map(checkTitleid, titleids)

with open("output/main_regions_alt2.json", "w", encoding="UTF-8") as f:
    json.dump(OUTPUT, f, indent="\t")

