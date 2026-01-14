import json
import re
import requests
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import sys

REGIONS = ["US", "BR", "CA", "AR", "CL", "CO", "PE", "MX"]
LANGS = ["en", "pt", "en", "es", "es", "es", "es", "es"]
DEFAULT_PAGES = ["us", "pt-br", "en-ca", "es-ar", "es-cl", "es-co", "es-pe", "es-mx"]

default_page = ""
base_url = ""
region = ""

def scrapEshop(nsu_id: int):
    global default_page
    global base_url
    # Create the URL
    url = f"{base_url}{nsu_id}"
    
    print(f"Processing {region} {nsu_id}...")

    try:
        # Download the HTML page
        response = requests.head(url, timeout=30, stream=True)
        if (response.url == default_page):
            return
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        # Find the line containing "NXSTORE.titleDetail.jsonData ="
        pattern = r'type="application/json">(.+?)(?:</script>)'
        match = re.search(pattern, html_content, re.DOTALL)
        
        if match:
            # Extract the JSON data (everything after the = sign, removing trailing semicolon)
            json_line = match.group(1).strip()

            # Check if that line contains valid title data
            if json_line.find("\"applicationId\"") == -1:
                return
            
            # Parse and re-save as proper JSON to ensure it's valid
            json_data = json.loads(json_line)
            
            # Save to file
            output_file = f"scrap/{region}/{nsu_id}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Saved {region} {nsu_id}.json")
        else:
            print(f"✗ Could not find jsonData in {region} {nsu_id}")

    except requests.exceptions.HTTPError as httperror:
        http_err = httperror.response.status_code
        if (http_err == 403):
            print(f"✗ Rate exhaustion reached. Aborting...")
            sys.exit(1)
        elif (http_err == 404):
            print(f"✗ Site not found for {region} {nsu_id}")
        else: 
            print(f"✗ Error {http_err} downloading {region} {nsu_id}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error downloading {region} {nsu_id}: {e}")
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing JSON for {region} {nsu_id}: {e}")
    except Exception as e:
        print(f"✗ Unexpected error for {region} {nsu_id}: {e}")

for x in range(len(REGIONS)):
    # Create output directory if it doesn't exist
    Path(f"scrap/{REGIONS[x]}").mkdir(parents=True, exist_ok=True)
    
    # Load the JSON file with NSU IDs
    with open(f"ValidNsuIds/{REGIONS[x]}.json", "r", encoding="utf-8") as f:
        nsu_ids = json.load(f)
    
    # Load the JSON file with NSU IDs
    with open(f"{REGIONS[x]}.{LANGS[x]}.json", "r", encoding="utf-8") as f:
        titledb_IDs = list(json.load(f).keys())
        titledb_IDs[:] = [int(s) for s in titledb_IDs if s.startswith("7001")]

    print(f"nsu_ids {REGIONS[x]} count: {len(nsu_ids)}")
    nsu_ids_filtered_temp = [s for s in nsu_ids if s not in titledb_IDs]
    print(f"nsu_ids_filtered_temp {REGIONS[x]} count: {len(nsu_ids_filtered_temp)}")
    nsu_ids_filtered = [s for s in nsu_ids_filtered_temp if (os.path.isfile(f"scrap/{REGIONS[x]}/{s}.json") == False)]
    print(f"nsu_ids_filtered {REGIONS[x]} count: {len(nsu_ids_filtered)}")

    default_page = f"https://www.nintendo.com/{DEFAULT_PAGES[x]}/store/games/"
    base_url = f"https://ec.nintendo.com/{REGIONS[x]}/{LANGS[x]}/titles/"
    region = REGIONS[x]

    with ThreadPoolExecutor(max_workers=2) as executor: #Setting more is risky because rate limits can kick in
        executor.map(scrapEshop, nsu_ids_filtered)
