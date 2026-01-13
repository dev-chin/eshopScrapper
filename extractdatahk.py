import json
import re
import requests
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

REGIONS = ["HK", "AU", "NZ"]
LANGS = ["zh", "en", "en"]

def scrapEshop(region: str, lang: str):
    # Create output directory if it doesn't exist
    Path(f"scrap/{region}").mkdir(parents=True, exist_ok=True)
    
    # Load the JSON file with NSU IDs
    with open(f"ValidNsuIds/{region}.json", "r", encoding="utf-8") as f:
        nsu_ids = json.load(f)
    
    # Load the JSON file with NSU IDs
    with open(f"{region}.{lang}.json", "r", encoding="utf-8") as f:
        titledb_IDs = list(json.load(f).keys())
        titledb_IDs[:] = [int(s) for s in titledb_IDs if s.startswith("7001")]
    
    # Iterate through each ID
    for nsu_id in nsu_ids:
        if (nsu_id in titledb_IDs): 
            continue
        if (os.path.isfile(f"scrap/{region}/{nsu_id}.json") == True):
            continue
        # Create the URL
        url = f"https://ec.nintendo.com/{region}/{language}/titles/{nsu_id}"
        
        print(f"Processing {region} {nsu_id}...")
        
        try:
            # Download the HTML page
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            # Find the line containing "NXSTORE.titleDetail.jsonData ="
            pattern = r'NXSTORE\.titleDetail\.jsonData = (.+)'
            match = re.search(pattern, html_content)
            
            if match:
                # Extract the JSON data (everything after the = sign, removing trailing semicolon)
                json_line = match.group(1).strip()
                if json_line.endswith(';'):
                    json_line = json_line[:-1].strip()
                
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


        print(f"\nScraping {region} completed!")

with ThreadPoolExecutor(max_workers=2) as executor:
    executor.map(scrapEshop, REGIONS, LANGS)
