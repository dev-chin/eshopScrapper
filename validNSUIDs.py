# This can take up to 3 hours on github servers

import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor
import threading

# Authorization token
glob_headers = {}

callcount = 0

url = "https://api.ec.nintendo.com/v1/price"

base_nsuid = 70010000000000

REGIONS = ["JP", "US", "HK", "BR", "CA", "AR", "CL", "CO", "PE", "MX", "AU", "NZ"]

#Regions that we currently don't know how to extract titleids from
#REGIONS += ["BG", "CH", "CY", "EE", "HR", "IE", "LT", "LU", "LV", "MT", "RO", "SI", "SK", "AT", "BE", "CZ", "DK", "ES", "FI", "GR", "HU", "NL", "NO", "PL", "PT", "RU", "ZA", "SE", "IT", "FR", "DE", "GB"]

os.makedirs("ValidNsuIds", exist_ok=True)

check_at_once = 50 # Max before site returns "Over ids limit number"

def addToNSUIDs(region: str):
    params = {
        "country": region,
        "ids": [],
        "lang": "jp"
    }
    NSUIDs = []
    print("Processing %s eshop" % region)
    for i in range(0, 200000, check_at_once):
        params["ids"] = []
        for x in range(check_at_once):
            params["ids"].append(str(base_nsuid + i + x))
    
        try:
            response = requests.get(url, params=params, timeout=10)
        except:
            print("Error while requesting!")
            print(response.url)
            break
        
        if response.status_code == 200:
            data = response.json()["prices"]
            for x in range(len(data)):
                if (data[x]["sales_status"] != "not_found"):
                    NSUIDs.append(data[x]["title_id"])

    if (len(NSUIDs) == 0): 
        print("Not even one valid NSUID was found for %s! Error" % region)
        continue
    file = open("ValidNsuIds/%s.json" % region, "w", encoding="UTF-8")
    json.dump(NSUIDs, file, indent="\t", ensure_ascii=False)
    file.close()

with ThreadPoolExecutor(max_workers=2) as executor:
    executor.map(addToNSUIDs, REGIONS)
