import json
import re
import requests
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

REGIONS = ["HK", "AU", "NZ"]
LANGS = ["zh", "en", "en"]

def scrapEshop(nsu_id: int):
    region = REGIONS[itr]
    lang = LANGS[itr]
    # Create the URL
    url = f"https://ec.nintendo.com/{region}/{lang}/titles/{nsu_id}"
    
    print(f"Processing {region} {nsu_id}...")
    
    try:
        # Download the HTML page
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        # Find the line containing "NXSTORE.titleDetail.jsonData ="
        pattern = r'<script id="mobify-data" type="application/json">(.+?)(?:</script>)'
        match = re.search(pattern, html_content, re.DOTALL)
        
        if match:
            json_line = match.group(1).strip()

            # Check if that line contains valid title data
            if json_line.find("c_applicationId") == -1:
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
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error downloading {region} {nsu_id}: {e}")
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing JSON for {region} {nsu_id}: {e}")
    except Exception as e:
        print(f"✗ Unexpected error for {region} {nsu_id}: {e}")
scrapEshop.itr = 0

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

    printf(f"nsu_ids count: {len(nsu_ids)}")
    nsu_ids_filtered = [s for s in nsu_ids if s not in titledb_IDs]
    printf(f"nsu_ids_filtered count: {len(nsu_ids_filtered)}")
    #nsu_ids_filtered = [s for s in nsu_ids_filtered_temp if (os.path.isfile(f"scrap/{REGIONS[x]}/{s}.json") == False)]

    scrapEshop.itr = x

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(scrapEshop, nsu_ids_filtered)




