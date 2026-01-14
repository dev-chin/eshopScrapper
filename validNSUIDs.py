# This can take up to 3 hours on github servers

import requests
import json
import os

url = "https://api.ec.nintendo.com/v1/price"
base_nsuid = 70010000000000
check_at_once = 50 # Max before site returns "Over ids limit number"

REGIONS = ["JP", "US", "HK", "BR", "CA", "AR", "CL", "CO", "PE", "MX", "AU", "NZ"]
#Regions that we currently don't know how to extract titleids from
#REGIONS += ["BG", "CH", "CY", "EE", "HR", "IE", "LT", "LU", "LV", "MT", "RO", "SI", "SK", "AT", "BE", "CZ", "DK", "ES", "FI", "GR", "HU", "NL", "NO", "PL", "PT", "RU", "ZA", "SE", "IT", "FR", "DE", "GB", "TH", "KR"]


os.makedirs("ValidNsuIds", exist_ok=True)
for a in range(len(REGIONS)):
    print("Processing %s eshop" % REGIONS[a])
    try:
        file = open(f"ValidNsuIds/{REGIONS[a]}.json", "w", encoding="UTF-8")
    except:
        NSUIDs = []
    else:
        NSUIDs = json.load(file)
        file.close()
    
    for i in range(0, 200000, check_at_once):
        values = [(base_nsuid + i + x) for x in range(check_at_once)]
        params = {
            "country": REGIONS[a],
            "ids": [str(s) in s in values if s not in NSUIDs],
            "lang": "jp"
        }
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
        print("Not even one valid NSUID was found! Error")
        continue
    file = open(f"ValidNsuIds/{REGIONS[a]}.json", "w", encoding="UTF-8")
    json.dump(NSUIDs, file, indent="\t", ensure_ascii=False)
    file.close()
