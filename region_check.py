import json
import os
import re
import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Regions checked for every title (0100 titles get region info for the scraped regions elsewhere)
REGIONS = ["BG", "CH", "CY", "EE", "HR", "IE", "LT", "LU", "LV", "MT", "RO", "SI", "SK", "AT", "BE", "CZ", "DK", "ES", "FI", "GR", "HU", "NL", "NO", "PL", "PT", "ZA", "SE", "IT", "FR", "DE", "GB", "TH", "KR", "SG", "MY", "TW"]
# Our other source has no region info for 0400 (Switch 2) titles, so check every region for them
REGIONS_0400 = ["US", "CA", "MX", "BR", "AR", "CL", "CO", "PE", "JP", "HK", "AU", "NZ"] + REGIONS

# ec.nintendo.com serves the same page for any titleid in these regions, so they can't be checked
UNCHECKABLE = {"TH", "SG", "MY", "TW"}
# KR redirects available titles to a generic store page (no NSUID in the link); unknown ones get 404
REDIRECT_IS_ENOUGH = {"KR"}

# Bump when the checking rules change, so old results get re-checked
CHECK_VERSION = 2
# Max number of already-known titles re-checked per run (new titles are always checked)
RECHECK_PER_RUN = int(os.environ.get("REGION_RECHECK_PER_RUN", 200))

NSUID_RE = re.compile(r'70\d{12}')
delay_in_s = 0.1

OUTPUT_FILE = "output/main_regions_alt2.json"
lock = threading.Lock()


def checkRegion(titleid: str, region: str):
	"""True/False if the title is (not) sold in region, None if it couldn't be determined."""
	url = f"https://ec.nintendo.com/apps/{titleid}/{region}"
	try:
		response = requests.head(url, allow_redirects=False, timeout=20)
	except requests.exceptions.RequestException as e:
		print(f"? {region} {titleid}: {e}")
		return None
	status_code = response.status_code
	if (status_code == 403):
		print("✗ Hit rate limit. Aborting...")
		saveOutput()
		os._exit(1)
	time.sleep(delay_in_s)
	if (status_code == 404):
		return False
	# Available titles redirect to their store page, which carries the region's NSUID.
	# (This used to be 303; it is 307 now. Unknown titles redirect to a generic page in HK.)
	if (status_code in (301, 302, 303, 307, 308)):
		if (NSUID_RE.search(response.headers.get("Location", "")) or region in REDIRECT_IS_ENOUGH):
			return True
		return False
	print(f"? {region} {titleid}: HTTP {status_code}")
	return None


def checkTitleid(titleid: str):
	regions = REGIONS_0400 if titleid.startswith("0400") else REGIONS
	result = {"True": [], "False": [], "v": CHECK_VERSION}
	for region in regions:
		if (region in UNCHECKABLE):
			continue
		available = checkRegion(titleid, region)
		if (available is True):
			result["True"].append(region)
		elif (available is False):
			result["False"].append(region)
		else:
			# Couldn't tell: keep the previous answer if there is one, and re-check next run
			previous = OUTPUT.get(titleid, {})
			if (region in previous.get("True", [])):
				result["True"].append(region)
			elif (region in previous.get("False", [])):
				result["False"].append(region)
			result["v"] = 0
	with lock:
		OUTPUT[titleid] = result
	print(f"✓ {titleid}: {' '.join(result['True']) or '-'}")


def needsRecheck(titleid: str, entry: dict):
	if (entry.get("v") == CHECK_VERSION):
		return False
	if (entry.get("v") == 0):
		return True # some regions couldn't be checked last time
	# Results from before v2 missed every region after the 303 -> 307 change.
	# 0400 titles also need the extra regions; 0100 titles that found regions back then are fine.
	return titleid.startswith("0400") or not entry.get("True")


def saveOutput():
	with lock:
		tmp = OUTPUT_FILE + ".tmp"
		with open(tmp, "w", encoding="UTF-8") as f:
			json.dump(OUTPUT, f)
		os.replace(tmp, OUTPUT_FILE)


with open("output/main_regions_alt.json", "r", encoding="UTF-8") as f:
	titleids = list(json.load(f).keys())

try:
	with open(OUTPUT_FILE, "r", encoding="UTF-8") as f:
		OUTPUT = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
	OUTPUT = {}

new_titleids = [x for x in titleids if x not in OUTPUT]
# 0400 titles first, since they have no other source of region info
recheck = sorted((x for x in titleids if x in OUTPUT and needsRecheck(x, OUTPUT[x])), key=lambda x: not x.startswith("0400"))
print(f"New titleids: {len(new_titleids)}, waiting for re-check: {len(recheck)}, re-checking now: {min(len(recheck), RECHECK_PER_RUN)}")

to_check = new_titleids + recheck[:RECHECK_PER_RUN]
done = 0
with ThreadPoolExecutor(max_workers=2) as executor: #Setting more is risky because rate limits can kick in
	for _ in executor.map(checkTitleid, to_check):
		done += 1
		if (done % 50 == 0):
			saveOutput()

saveOutput()
