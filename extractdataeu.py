import json
import re
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import time
import datetime

REGIONS = ["GB", "DE", "FR", "IT", "BG", "CH", "CY", "EE", "HR", "IE", "LT", "LU", "LV", "MT", "RO", "SI", "SK", "AT", "BE", "CZ", "DK", "ES", "FI", "GR", "HU", "NL", "NO", "PL", "PT", "ZA", "SE"]

LIST_REGION = {}

def scrapEshop(titleid: str):
	print(f"Processing {titleid}...")
	if (os.path.isfile(f"scrap/EU/{titleid}.json") == True):
		with open(f"scrap/EU/{titleid}.json", "r", encoding="UTF-8") as f:
			DUMP = json.load(f)
	else: DUMP = {"Regions": {"True": [], "False": []}}

	for region in REGIONS:
		if (region in DUMP["Regions"]["True"] or region in DUMP["Regions"]["False"]):
			continue
		# Create the URL
		url = f"https://ec.nintendo.com/apps/{titleid}/{region}"
		response = requests.head(url, timeout=10, allow_redirects=False)
		match(response.status_code):
			case 404:
				print(f"✗ {region} {titleid}")
				DUMP["Regions"]["False"].append(region)
				time.sleep(0.1)
				continue
			case 403:
				print("Hit rate limit, aborting...")
				os._exit(1)
			case 303:
				pass
			case _:
				print(f"UNEXPECTED HTTP CODE: {response.status_code}, aborting...")
				os._exit(2)

		response = requests.head(url, timeout=10, allow_redirects=True)
		if (response.url.find("/404.html") != -1):
			print(f"✗ {region} {titleid}")
			DUMP["Regions"]["False"].append(region)
			time.sleep(0.1)
			continue
		
		DUMP["Regions"]["True"].append(region)
		try:
			# Download the HTML page
			print(f"✓ {region} {titleid}")
			response = requests.get(url, timeout=30)
			response.raise_for_status()
			html_content = response.text
				
		except requests.exceptions.RequestException as e:
			print(f"✗ Error downloading {region} {titleid}: {e}")
		except json.JSONDecodeError as e:
			print(f"✗ Error parsing JSON for {region} {titleid}: {e}")
		except Exception as e:
			print(f"✗ Unexpected error for {region} {titleid}: {e}")
		else:
			# Find the line containing "NXSTORE.titleDetail.jsonData ="
			pattern = r'gameTitle: "(.+?)(?:",)'
			match = re.search(pattern, html_content)

			if match:
				name = match.group(1).strip()
				if ("name" in DUMP.keys()):
					if (name not in DUMP["name"]): DUMP["name"].append(name)
				else: DUMP["name"] = [name]

			else:
				print(f"✗ Could not find title in {region} {titleid}")

			if ("publisher" not in DUMP.keys()):
				pattern = r'publisher: "(.+?)(?:",)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["publisher"] = match.group(1).strip()

				else:
					print(f"✗ Could not find publisher in {region} {titleid}")

			if ("bannerUrl" not in DUMP.keys()):
				pattern = r'<meta name="twitter:image" content="(.+?)(?:">)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["bannerUrl"] = match.group(1).strip()

				else:
					print(f"✗ Could not find bannerUrl in {region} {titleid}")

			if ("iconUrl" not in DUMP.keys()):
				DUMP["iconUrl"] = ""

			print("PING 5")
			if ("releaseDate" not in DUMP.keys()):
				pattern = r'releaseDate: "(.+?)"'
				match = re.search(pattern, html_content)
				
				if match:
					captured_date = match.group(1).strip()
					print(f"DEBUG: Captured date string: '{captured_date}' (repr: {repr(captured_date)})")
					date_obj = datetime.strptime(captured_date, "%d/%m/%Y")
					print("PING 5-1")
					DUMP["releaseDate"] = int(date_obj.strftime("%Y%m%d"))

				else:
					print(f"✗ Could not find releaseDate in {region} {titleid}")

			print("PING 6")
			if ("size" not in DUMP.keys()):
				pattern = r'<p class="game_info_title">Download size</p>\n\s*<p class="game_info_text">(.+?)(?:</p>)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["size"] = match.group(1).strip().replace("GB", "GiB").replace("MB", "MiB")

				else:
					print(f"✗ Could not find size in {region} {titleid}")

			print("PING 7")
			if ("screenshots" not in DUMP.keys()):
				pattern = r"'image_url':\s*'([^']+\.jpg)'"
				matches = re.finditer(pattern, html_content)

				if len(list(matches)) > 0:
					DUMP["screenshots"] = []
				
					for match in matches:
						DUMP["screenshots"].append(match.group(1).strip())

				else:
					print(f"✗ Could not find screenshots in {region} {titleid}")

	if ("name" not in DUMP.keys()):
		print(f"✗✗ {titleid} No data was found!")
		return
	with open(f"scrap/EU/{titleid}.json", "w", encoding="UTF-8") as f:
		json.dump(DUMP, f, indent="\t", ensure_ascii=True)
	print(f"✓✓ {titleid} saved!")

os.makedirs("scrap/EU", exist_ok=True)

with open("version_dump/version_dump.txt", "r", encoding="UTF-8") as f:
	titleids = [(line.split('|')[0][:13] + "000") for line in f.readlines()[1:]]

titleids[:] = [x for x in titleids if ((os.path.isfile(f"titledb_filtered/output/titleid/{x}.json") == False) and (os.path.isfile(f"titledb_filtered/output2/titleid/{x}.json") == False))]

to_check = len(titleids)
print(f"To check: {to_check} titleids, expected lines: around {(len(REGIONS) * to_check) + (to_check * 2)}")

"""
for titleid in titleids:
	scrapEshop(titleid)
"""

with ThreadPoolExecutor(max_workers=2) as executor: #Setting more is risky because rate limits can kick in
	executor.map(scrapEshop, titleids)
