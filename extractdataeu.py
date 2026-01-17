import json
import re
import requests
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys

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
				if ("name" in DUMP.keys()):
					DUMP["name"].append(match.group(1).strip())
				else: DUMP["name"] = [match.group(1).strip()]

			else:
				print(f"✗ Could not find title in {region} {titleid}")

			if ("publisher" not in DUMP.keys()):
				pattern = r'publisher: "(.+?)(?:",)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["publisher"] = [match.group(1).strip()]

				else:
					print(f"✗ Could not find publisher in {region} {titleid}")

			if ("bannerUrl" not in DUMP.keys()):
				pattern = r'<meta name="twitter:image" content="(.+?)(?:">)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["bannerUrl"] = [match.group(1).strip()]

				else:
					print(f"✗ Could not find bannerUrl in {region} {titleid}")

			if ("iconUrl" not in DUMP.keys()):
				DUMP["iconUrl"] = ""

			if ("releaseDate" not in DUMP.keys()):
				pattern = r'releaseDate: "(.+?)(?:",)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["releaseDate"] = [match.group(1).strip()]

				else:
					print(f"✗ Could not find releaseDate in {region} {titleid}")

			if ("size" not in DUMP.keys()):
				pattern = r'<p class="game_info_title">Download size</p>\n\t\t\t\t\t\t<p class="game_info_text">(.+?)(?:</p>)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["size"] = [match.group(1).strip().replace("GB", "GiB")]

				else:
					print(f"✗ Could not find size in {region} {titleid}")

			if ("screenshots" not in DUMP.keys()):
				pattern = r"',\n\t\t\t\t\t\t'image_url': '(.+?)(?:')"
				matches = re.finditer(pattern, html_content)

				if len(list(matches)) > 0:
					DUMP["screenshots"] = []
				
					for match in matches:
						string = match.group(1).strip()
						if (string.endswith(".jpg") == False):
							continue
						DUMP["screenshots"].append(string)

				else:
					print(f"✗ Could not find screenshots in {region} {titleid}")

	if ("name" not in DUMP.keys()):
		print("No data was found!")
		return
	with open(f"scrap/EU/{titleid}.json", "w", encoding="UTF-8") as f:
		json.dump(DUMP, f, indent="\t", ensure_ascii=True)

os.makedirs("scrap/EU", exist_ok=True)

with open("version_dump/version_dump.txt", "r", encoding="UTF-8") as f:
	titleids = [(line.split('|')[0][:13] + "000") for line in f.readlines()[1:]]

titleids[:] = [x for x in titleids if ((os.path.isfile(f"titledb_filtered/output/titleid/{x}.json") == False) and (os.path.isfile(f"titledb_filtered/output2/titleid/{x}.json") == False))]

"""
for titleid in titleids:
	scrapEshop(titleid)
"""

with ThreadPoolExecutor(max_workers=2) as executor: #Setting more is risky because rate limits can kick in
	executor.map(scrapEshop, titleids)



