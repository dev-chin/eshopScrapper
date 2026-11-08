import json
import glob
import os
import sys
from datetime import datetime
from pathlib import Path

CATEGORY_1 = ["JP"]
CATEGORY_2 = ["HK", "AU", "NZ"]
CATEGORY_3 = ["US", "AR", "BR", "CA", "CL", "CO", "MX", "PE"]
CATEGORY_4 = ["EU"]

TITLEIDS_REGIONS = {}

# Entries built from this run's scrap files. Output files are only consulted at the end,
# so newer scrap data replaces outdated values (links, dates, sizes...).
ENTRIES = {}
EU_TITLEIDS = set()

def isCoveredByTitledb(titleid):
	"""True if titledb already has this title, so we don't need to produce it.
	titledb_filtered also imports this repo's own output, so a title we already
	produced is never treated as covered - otherwise it would never be updated again."""
	if (os.path.isfile(f"output/titleid/{titleid}.json")):
		return False
	folder = "output" if titleid.startswith("0100") else "output2"
	return os.path.isfile(f"titledb_filtered/{folder}/titleid/{titleid}.json")

def isEmpty(value):
	return value is None or value == 0 or value == "" or value == []

def mergeEntry(titleid, entry, override=False):
	"""Combine entry with one built earlier this run. Earlier regions win unless override=True (EU)."""
	if (override):
		EU_TITLEIDS.add(titleid)
	if (titleid not in ENTRIES):
		ENTRIES[titleid] = entry
		return
	current = ENTRIES[titleid]
	for key, value in entry.items():
		if (key == "name" and not override):
			for name in value:
				if (name not in current["name"]):
					current["name"].append(name)
		elif (isEmpty(value)):
			continue
		elif (override or isEmpty(current.get(key))):
			current[key] = value

def writeEntries():
	written = 0
	for titleid, entry in ENTRIES.items():
		path = f"output/titleid/{titleid}.json"
		old_entry = None
		try:
			with open(path, "r", encoding="UTF-8") as f:
				old_entry = json.load(f)
		except (FileNotFoundError, json.JSONDecodeError):
			pass
		if (old_entry is not None):
			# Keep previously known names (EU entries use the EU name list as before)
			if (titleid not in EU_TITLEIDS):
				entry["name"] = old_entry.get("name", []) + [name for name in entry["name"] if name not in old_entry.get("name", [])]
			# Fall back to old values only where the fresh scrape has nothing
			for key, value in old_entry.items():
				if (key != "name" and isEmpty(entry.get(key)) and not isEmpty(value)):
					entry[key] = value
			if (entry == old_entry):
				continue
		with open(path, "w", encoding="UTF-8") as f:
			json.dump(entry, f, indent="\t", ensure_ascii=False)
		written += 1
	print(f"Updated {written} of {len(ENTRIES)} titleid files")

def processCat1():
	for region in CATEGORY_1:
		files = sorted(glob.glob(f"scrap/{region}/*.json"))
		print(f"Processing {region} {len(files)} files...")
		for i in range(len(files)):
			print(files[i])
			with open(files[i], "r", encoding="UTF-8") as f:
				DUMP = json.load(f)
			data = DUMP["__PRELOADED_STATE__"]["__reactQuery"]["queries"]
			entry = {}
			for i in range(len(data)):
				if ("/products/" not in data[i]["queryKey"]):
					continue
				entry["titleid"] = data[i]["state"]["data"]["c_applicationId"].upper()
				entry["name"] = [data[i]["state"]["data"]["c_original_productName"]]
				entry["publisher"] = data[i]["state"]["data"]["manufacturerName"]
				images = data[i]["state"]["data"]["imageGroups"]
				for x in range(len(images)):
					match(images[x]["viewType"]):
						case "heroBanner":
							entry["bannerUrl"] = images[x]["images"][0]["disBaseLink"]
						case "squareHeroBanner":
							entry["iconUrl"] = images[x]["images"][0]["disBaseLink"]
						case "screenShot":
							entry["screenshots"] = []
							for y in range(len(images[x]["images"])):
								entry["screenshots"].append(images[x]["images"][y]["disBaseLink"])
				entry["releaseDate"] = 0
				entry["size"] = 0
			
			titleid = entry["titleid"]
			entry.pop("titleid")

			if (isCoveredByTitledb(titleid)):
				continue

			if (titleid in TITLEIDS_REGIONS.keys()):
				if (region not in TITLEIDS_REGIONS[titleid]):
					TITLEIDS_REGIONS[titleid].append(region)
			else:
				TITLEIDS_REGIONS[titleid] = [region]
			
			mergeEntry(titleid, entry)

def processCat2():
	for region in CATEGORY_2:
		files = sorted(glob.glob(f"scrap/{region}/*.json"))
		print(f"Processing {region} {len(files)} files...")
		for i in range(len(files)):
			print(files[i])
			with open(files[i], "r", encoding="UTF-8") as f:
				DUMP = json.load(f)
			if len(DUMP["applications"]) != 1:
				print("Other than 1 titleid detected!")
				sys.exit(1)
			titleid = DUMP["applications"][0]["id"].upper()

			if (isCoveredByTitledb(titleid)):
				continue
			
			entry = {}
			entry["name"] = [DUMP["formal_name"]]
			entry["publisher"] = DUMP["publisher"]["name"]
			entry["bannerUrl"] = DUMP["hero_banner_url"]
			entry["iconUrl"] = ""
			entry["screenshots"] = []
			for x in range(len(DUMP["screenshots"])):
				entry["screenshots"].append(DUMP["screenshots"][x]["images"][0]["url"])
			try:
				date_obj = datetime.strptime(DUMP["release_date_on_eshop"], "%Y-%m-%d")
			except (ValueError, TypeError):
				entry["releaseDate"] = 0 # e.g. "TBD"
			else: entry["releaseDate"] = int(date_obj.strftime("%Y%m%d"))
			size = (DUMP["rom_size_infos"][0]["total_rom_size"] / 1048576) if titleid.startswith("0100") else (DUMP["rom_size_infos"][1]["total_rom_size"] / 1048576)
			entry["size"] = "%.0f MiB" % size if size < 1000 else "%.2f GiB" % (size / 1024)


			
			if (titleid in TITLEIDS_REGIONS.keys()):
				if (region not in TITLEIDS_REGIONS[titleid]):
					TITLEIDS_REGIONS[titleid].append(region)
			else:
				TITLEIDS_REGIONS[titleid] = [region]
			
			mergeEntry(titleid, entry)

def processCat3():
	for region in CATEGORY_3:
		files = sorted(glob.glob(f"scrap/{region}/*.json"))
		print(f"Processing {region} {len(files)} files...")
		for i in range(len(files)):
			print(files[i])
			with open(files[i], "r", encoding="UTF-8") as f:
				DUMP = json.load(f)

			sku = DUMP["props"]["pageProps"]["analytics"]["product"]["sku"]
			productSku = DUMP["props"]["pageProps"]["initialApolloState"]["Product:{\"sku\":\"%s\"}" % sku]

			titleid = productSku["applicationId"].upper()

			if (isCoveredByTitledb(titleid)):
				continue

			entry = {}
			entry["name"] = [DUMP["props"]["pageProps"]["analytics"]["product"]["name"]]
			entry["publisher"] = productSku["softwarePublisher"]
			entry["bannerUrl"] = productSku["productImage"]["url"] + ".jpg"
			icon = productSku["productImage({\"shape\":\"square\"})"]
			entry["iconUrl"] =  icon["url"] if icon != None else ""
			entry["screenshots"] = []
			productGallery = productSku["productGallery"]
			for x in range(len(productGallery)):
				if (productGallery[x]["resourceType"] == "image"):
					entry["screenshots"].append("https://assets.nintendo.com/image/upload/q_auto:best/f_auto/dpr_2.0/" + productGallery[x]["publicId"] + ".jpg")
			if (productSku["releaseDate"] != None):
				date_obj = datetime.strptime(productSku["releaseDate"][:10], "%Y-%m-%d")
				entry["releaseDate"] = int(date_obj.strftime("%Y%m%d"))
			else: entry["releaseDate"] = 0
			size_temp = productSku["softwareDetails"]["romSizes"]
			if (size_temp != None): size_temp = size_temp[0]["totalRomSize"] if titleid.startswith("0100") else size_temp[1]["totalRomSize"]
			if (size_temp != None):
				size = int(size_temp) / 1048576
				entry["size"] = "%.0f MiB" % size if size < 1000 else "%.2f GiB" % (size / 1024)
			else: entry["size"] = 0

			
			if (titleid in TITLEIDS_REGIONS.keys()):
				if (region not in TITLEIDS_REGIONS[titleid]):
					TITLEIDS_REGIONS[titleid].append(region)
			else:
				TITLEIDS_REGIONS[titleid] = [region]
			
			mergeEntry(titleid, entry)

def processCat4():
	for region in CATEGORY_4:
		files = sorted(glob.glob(f"scrap/{region}/*.json"))
		print(f"Processing {region} {len(files)} files...")
		for i in range(len(files)):
			print(files[i])
			with open(files[i], "r", encoding="UTF-8") as f:
				DUMP = json.load(f)

			titleid = Path(files[i]).stem

			if (isCoveredByTitledb(titleid)):
				continue

			entry = {}
			# The EU scraper skips fields it could not find (e.g. TBD release date), so none are guaranteed.
			# Empty values are ignored when merging, so other regions / the old output fill them in.
			entry["name"] = DUMP.get("name", [])
			entry["publisher"] = DUMP.get("publisher", "")
			entry["bannerUrl"] = DUMP.get("bannerUrl", "")
			entry["iconUrl"] = DUMP.get("iconUrl", "")
			entry["screenshots"] = DUMP.get("screenshots", [])
			entry["releaseDate"] = DUMP.get("releaseDate", 0)
			
			if ("size" not in DUMP.keys() or DUMP["size"] == 0):
				entry["size"] = 0
			else: entry["size"] = DUMP["size"] if DUMP["size"].endswith("GiB") else DUMP["size"].replace(".0", "")
			
			if (titleid in TITLEIDS_REGIONS.keys()):
				for x in DUMP["Regions"]["True"]:
					if (x not in TITLEIDS_REGIONS[titleid]):
						TITLEIDS_REGIONS[titleid].append(x)
			else:
				TITLEIDS_REGIONS[titleid] = DUMP["Regions"]["True"]
			
			mergeEntry(titleid, entry, override=True)

try:
	file = open(f"output/main_regions_alt.json", "r", encoding="UTF-8")
except:
	pass
else:
	TITLEIDS_REGIONS = json.load(file)
	file.close()

os.makedirs("output/titleid", exist_ok=True)
processCat3()
processCat2()
processCat1()
processCat4()
writeEntries()

with open(f"output/main_regions_alt.json", "w", encoding="UTF-8") as f:
	json.dump(TITLEIDS_REGIONS, f, ensure_ascii=False)
