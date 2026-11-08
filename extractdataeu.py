import json
import re
import requests
import os
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime
import copy
import scrap_refresh

REGIONS = ["GB", "DE", "FR", "IT", "BG", "CH", "CY", "EE", "HR", "IE", "LT", "LU", "LV", "MT", "RO", "SI", "SK", "AT", "BE", "CZ", "DK", "ES", "FI", "GR", "HU", "NL", "NO", "PL", "PT", "ZA", "SE"]

LIST_REGION = {}

EU_REFRESH = set()

# Regions whose ec.nintendo.com pages contain titleids (EU pages don't)
DEMO_CHECK_REGIONS = ["US", "AU", "HK", "JP"]
TITLEID_RE = re.compile(r'(?<![0-9A-Fa-f])0[14]00[0-9A-Fa-f]{12}(?![0-9A-Fa-f])')
DEMO_WORD_RE = re.compile(r'\bDEMO\b', re.IGNORECASE)

def detectDemo(titleid: str):
	"""ec.nintendo.com/apps/<titleid> redirects a demo to its full game's page, so that page
	lists titleids, but not the demo's. Returns True/False, or None if no region could tell."""
	for region in DEMO_CHECK_REGIONS:
		try:
			response = requests.get(f"https://ec.nintendo.com/apps/{titleid}/{region}", timeout=30)
		except requests.exceptions.RequestException:
			continue
		if (response.status_code == 403):
			print("Hit rate limit, aborting...")
			os._exit(1)
		time.sleep(delay_in_s)
		if (response.status_code != 200 or response.url.find("/404") != -1):
			continue
		found = {match.upper() for match in TITLEID_RE.findall(response.text)}
		if (found):
			return titleid.upper() not in found
	return None

def fixMojibake(value):
	"""Repair text saved before pages were decoded as UTF-8 (e.g. "TrÃ¤ume" -> "Träume").
	Only text that really was mis-decoded survives the round trip, so correct text is untouched."""
	if (isinstance(value, str)):
		try:
			return value.encode("latin-1").decode("utf-8")
		except (UnicodeEncodeError, UnicodeDecodeError):
			return value
	if (isinstance(value, list)):
		fixed = []
		for item in value:
			item = fixMojibake(item)
			if (item not in fixed): fixed.append(item)
		return fixed
	return value

def isMarkedDemo(name: str):
	"""Names flagged as demo by hand ("X DEMO") or by Nintendo ("X (DEMO)")."""
	return name.endswith(" DEMO") or "(DEMO)" in name.upper()

delay_in_s = 0.2

def scrapEshop(titleid: str):
	print(f"Processing {titleid}...")
	if (os.path.isfile(f"scrap/EU/{titleid}.json") == True):
		with open(f"scrap/EU/{titleid}.json", "r", encoding="UTF-8") as f:
			DUMP = json.load(f)
	else: DUMP = {"Regions": {"True": [], "False": []}}

	# File as saved, to decide whether anything changed
	SAVED = copy.deepcopy(DUMP)
	for key in ["name", "publisher"]:
		if (key in DUMP.keys()): DUMP[key] = fixMojibake(DUMP[key])

	# Must be a copy: a plain assignment aliases DUMP, so "DUMP == CLONE" was always True and nothing got saved
	CLONE = copy.deepcopy(DUMP)

	# Stale entry: re-scrape every region from scratch (old file is kept if nothing is found)
	if (titleid in EU_REFRESH):
		DUMP = {"Regions": {"True": [], "False": []}}

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
				time.sleep(delay_in_s)
				continue
			case 403:
				print("Hit rate limit, aborting...")
				os._exit(1)
			case 303:
				pass
			case 307:
				pass
			case _:
				print(f"UNEXPECTED HTTP CODE: {response.status_code}, aborting...")
				os._exit(2)

		response = requests.head(url, timeout=10, allow_redirects=True)
		if (response.url.find("/404.html") != -1):
			print(f"✗ {region} {titleid}")
			DUMP["Regions"]["False"].append(region)
			time.sleep(delay_in_s)
			continue
		
		DUMP["Regions"]["True"].append(region)
		try:
			# Download the HTML page
			print(f"✓ {region} {titleid}")
			response = requests.get(url, timeout=30)
			response.raise_for_status()
			# Header has no charset, so requests would decode as ISO-8859-1 and garble non-ASCII text
			response.encoding = "utf-8"
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

			if ("releaseDate" not in DUMP.keys()):
				pattern = r'releaseDate: "(.+?)"'
				match = re.search(pattern, html_content)
				
				if match:
					captured_date = match.group(1).strip()
					if (len(captured_date) == 4): 
						captured_date = "01/01/" + captured_date
					try:
						date_obj = datetime.strptime(captured_date.replace(".", "/").replace("-", "/"), "%d/%m/%Y")
					except Exception as e:
						if (captured_date in ["TBD", "n. n. b.", "Date à déterminer", "Da determinare", "Nader te bepalen", "Por determinar", "A decidir"]):
							print(f"✗ Release date in {region} {titleid} is TBD.")
						else:
							print(f"DEBUG: Captured date string: '{captured_date}' (repr: {repr(captured_date)})")
							print(f"Exception: {e}")
							os._exit(3)
					else: DUMP["releaseDate"] = int(date_obj.strftime("%Y%m%d"))

				else:
					print(f"✗ Could not find releaseDate in {region} {titleid}")

			if ("size" not in DUMP.keys()):
				pattern = r'<p class="game_info_title">Download size</p>\n\s*<p class="game_info_text">(.+?)(?:</p>)'
				match = re.search(pattern, html_content)
				
				if match:
					DUMP["size"] = match.group(1).strip().replace("GB", "GiB").replace("MB", "MiB")

				else:
					print(f"✗ Could not find size in {region} {titleid}")

			if ("screenshots" not in DUMP.keys()):
				pattern = r"'image_url':\s*'([^']+\.jpg)'"
				matches = re.finditer(pattern, html_content)

				if matches:
					DUMP["screenshots"] = []
				
					for match in matches:
						DUMP["screenshots"].append(match.group(1).strip())

				else:
					print(f"✗ Could not find screenshots in {region} {titleid}")

	if ("name" not in DUMP.keys()):
		print(f"✗✗ {titleid} No data was found!")
		return
	# Refresh: keep any field the new scrape could not find
	if (titleid in EU_REFRESH):
		for key, value in CLONE.items():
			if (key not in DUMP.keys()): DUMP[key] = value
	# Demo flag is decided once and stored as "isDemo" (set it to false by hand to override).
	# Demo pages are the full game's page, so scraped names must get " DEMO" appended.
	if ("isDemo" not in DUMP.keys()):
		if (any(isMarkedDemo(name) for name in CLONE.get("name", []))):
			DUMP["isDemo"] = True
		else:
			is_demo = detectDemo(titleid)
			if (is_demo is not None):
				DUMP["isDemo"] = is_demo
				print(f"{'✓ DEMO' if is_demo else '✓ not a demo'}: {titleid}")
	if (DUMP.get("isDemo") == True):
		DUMP["name"] = [name if DEMO_WORD_RE.search(name) else f"{name} DEMO" for name in DUMP["name"]]
	if (DUMP == SAVED):
		print(f"✗✓ {titleid} Nothing was changed!")
		return
	with open(f"scrap/EU/{titleid}.json", "w", encoding="UTF-8") as f:
		json.dump(DUMP, f, indent="\t", ensure_ascii=True)
		print(f"✓✓ {titleid} saved!")
	scrap_refresh.mark("EU", titleid)

os.makedirs("scrap/EU", exist_ok=True)

with open("version_dump/version_dump.txt", "r", encoding="UTF-8") as f:
	titleids = [(line.split('|')[0][:13] + "000") for line in f.readlines()[1:]]

# titledb_filtered also imports this repo's own output, so keep titles we already scraped
titleids[:] = [x for x in titleids if (os.path.isfile(f"scrap/EU/{x}.json") or ((os.path.isfile(f"titledb_filtered/output/titleid/{x}.json") == False) and (os.path.isfile(f"titledb_filtered/output2/titleid/{x}.json") == False)))]

# Also re-scrape the oldest already-scraped entries so their data does not go stale
EU_REFRESH.update(scrap_refresh.pick_stale("EU", [x for x in titleids if os.path.isfile(f"scrap/EU/{x}.json")], "REFRESH_PER_REGION_EU", 25))
print(f"Refreshing {len(EU_REFRESH)} existing EU entries")

to_check = len(titleids)
print(f"To check: {to_check} titleids, expected lines: around {(len(REGIONS) * to_check) + (to_check * 2)}")

"""
for titleid in titleids:
	scrapEshop(titleid)
"""

with ThreadPoolExecutor(max_workers=2) as executor: #Setting more is risky because rate limits can kick in
	executor.map(scrapEshop, titleids)

# Mark refresh attempts even if the page is gone, so delisted titles don't block the queue
for x in EU_REFRESH: scrap_refresh.mark("EU", x)
scrap_refresh.save()
