import requests
import json
import os
import threading

REGIONS = ["JP", "US", "HK", "BR", "CA", "AR", "CL", "CO", "PE", "MX", "AU", "NZ"]
#Regions that we currently don't know how to extract titleids from
#REGIONS += ["BG", "CH", "CY", "EE", "HR", "IE", "LT", "LU", "LV", "MT", "RO", "SI", "SK", "AT", "BE", "CZ", "DK", "ES", "FI", "GR", "HU", "NL", "NO", "PL", "PT", "RU", "ZA", "SE", "IT", "FR", "DE", "GB"]

check_at_once = 50 # Max before site returns "Over ids limit number"

semaphore = threading.Semaphore(2)
threads = []

def addToNSUIDs(region: str):
    m_region = region
    base_nsuid = 70010000000000
    url = "https://api.ec.nintendo.com/v1/price"
    NSUIDs = []
    print("Processing %s eshop" % region)
    for i in range(0, 200000, check_at_once):
        params = {
            "country": m_region,
            "ids": [str(base_nsuid + i + x) for x in range(check_at_once)],
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
        print("Not even one valid NSUID was found for %s! Error" % region)
        return
    file = open(f"ValidNsuIds/{region}.json", "w", encoding="UTF-8")
    json.dump(NSUIDs, file, indent="\t", ensure_ascii=False)
    file.close()

def wrapper(region):
    with semaphore:  # Acquire semaphore, blocks if 2 threads already running
        print(f"Thread {threading.current_thread().name} processing {region}")
        try:
            addToNSUIDs(region)
            print(f"✓ {region} completed by {threading.current_thread().name}")
        except Exception as e:
            print(f"✗ {region} failed: {e}")

os.makedirs("ValidNsuIds", exist_ok=True)
# Create all threads but semaphore limits concurrent execution
for region in REGIONS:
    thread = threading.Thread(target=wrapper, args=(region,), name=f"Thread-{region}")
    thread.start()
    threads.append(thread)

# Wait for all to complete
for thread in threads:
    thread.join()
