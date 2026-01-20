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

def processCat1():
	for region in CATEGORY_1:
		files = glob.glob(f"scrap/{region}/*.json")
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

			if (titleid.startswith("0100") == True):
				if (os.path.isfile(f"titledb_filtered/output/titleid/{titleid}.json") == True):
					continue
			else:
				if (os.path.isfile(f"titledb_filtered/output2/titleid/{titleid}.json") == True):
					continue
			try:
				file_old = open(f"output/titleid/{titleid}.json", "r", encoding="UTF-8")
			except:
				pass
			else:
				old_entry = json.load(file_old)
				file_old.close()

				if (entry["name"][0] not in old_entry["name"]):
					old_entry["name"].append(entry["name"][0])
				
				entry = old_entry

			if (titleid in TITLEIDS_REGIONS.keys()):
				if (region not in TITLEIDS_REGIONS[titleid]):
					TITLEIDS_REGIONS[titleid].append(region)
			else:
				TITLEIDS_REGIONS[titleid] = [region]
			
			with open(f"output/titleid/{titleid}.json", "w", encoding="UTF-8") as f:
				json.dump(entry, f, indent="\t", ensure_ascii=True)

def processCat2():
	for region in CATEGORY_2:
		files = glob.glob(f"scrap/{region}/*.json")
		print(f"Processing {region} {len(files)} files...")
		for i in range(len(files)):
			print(files[i])
			with open(files[i], "r", encoding="UTF-8") as f:
				DUMP = json.load(f)
			if len(DUMP["applications"]) != 1:
				print("Other than 1 titleid detected!")
				sys.exit(1)
			titleid = DUMP["applications"][0]["id"].upper()

			if (titleid.startswith("0100") == True):
				if (os.path.isfile(f"titledb_filtered/output/titleid/{titleid}.json") == True):
					continue
			else:
				if (os.path.isfile(f"titledb_filtered/output2/titleid/{titleid}.json") == True):
					continue
			
			entry = {}
			entry["name"] = [DUMP["formal_name"]]
			entry["publisher"] = DUMP["publisher"]["name"]
			entry["bannerUrl"] = DUMP["hero_banner_url"]
			entry["iconUrl"] = ""
			entry["screenshots"] = []
			for x in range(len(DUMP["screenshots"])):
				entry["screenshots"].append(DUMP["screenshots"][x]["images"][0]["url"])
			date_obj = datetime.strptime(DUMP["release_date_on_eshop"], "%Y-%m-%d")
			entry["releaseDate"] = int(date_obj.strftime("%Y%m%d"))
			size = (DUMP["rom_size_infos"][0]["total_rom_size"] / 1048576) if titleid.startswith("0100") else (DUMP["rom_size_infos"][1]["total_rom_size"] / 1048576)
			entry["size"] = "%.0f MiB" % size if size < 1000 else "%.2f GiB" % (size / 1024)


			try:
				file_old = open(f"output/titleid/{titleid}.json", "r", encoding="UTF-8")
			except:
				pass
			else:
				old_entry = json.load(file_old)
				file_old.close()

				if (entry["name"][0] not in old_entry["name"]):
					old_entry["name"].append(entry["name"][0])

				if (old_entry["releaseDate"] == 0):
					old_entry["releaseDate"] = entry["releaseDate"]

				if (old_entry["size"] == 0):
					old_entry["size"] = entry["size"]
				
				entry = old_entry
			
			if (titleid in TITLEIDS_REGIONS.keys()):
				if (region not in TITLEIDS_REGIONS[titleid]):
					TITLEIDS_REGIONS[titleid].append(region)
			else:
				TITLEIDS_REGIONS[titleid] = [region]
			
			with open(f"output/titleid/{titleid}.json", "w", encoding="UTF-8") as f:
				json.dump(entry, f, indent="\t", ensure_ascii=True)

def processCat3():
	for region in CATEGORY_3:
		files = glob.glob(f"scrap/{region}/*.json")
		print(f"Processing {region} {len(files)} files...")
		for i in range(len(files)):
			print(files[i])
			with open(files[i], "r", encoding="UTF-8") as f:
				DUMP = json.load(f)

			sku = DUMP["props"]["pageProps"]["analytics"]["product"]["sku"]
			productSku = DUMP["props"]["pageProps"]["initialApolloState"]["Product:{\"sku\":\"%s\"}" % sku]

			titleid = productSku["applicationId"].upper()

			if (titleid.startswith("0100") == True):
				if (os.path.isfile(f"titledb_filtered/output/titleid/{titleid}.json") == True):
					continue
			else:
				if (os.path.isfile(f"titledb_filtered/output2/titleid/{titleid}.json") == True):
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
			date_obj = datetime.strptime(productSku["releaseDate"][:10], "%Y-%m-%d")
			entry["releaseDate"] = int(date_obj.strftime("%Y%m%d"))
			size_temp = productSku["softwareDetails"]["romSizes"][0]["totalRomSize"] if titleid.startswith("0100") else productSku["softwareDetails"]["romSizes"][1]["totalRomSize"]
			if (size_temp != None):
				size = int(size_temp) / 1048576
				entry["size"] = "%.0f MiB" % size if size < 1000 else "%.2f GiB" % (size / 1024)
			else: entry["size"] = 0

			try:
				file_old = open(f"output/titleid/{titleid}.json", "r", encoding="UTF-8")
			except:
				pass
			else:
				old_entry = json.load(file_old)
				file_old.close()

				if (entry["name"][0] not in old_entry["name"]):
					old_entry["name"].append(entry["name"][0])

				if (old_entry["releaseDate"] == 0):
					old_entry["releaseDate"] = entry["releaseDate"]

				if (old_entry["size"] == 0):
					old_entry["size"] = entry["size"]
				
				if (old_entry["iconUrl"] == ""):
					old_entry["iconUrl"] = entry["iconUrl"]
				
				entry = old_entry
			
			if (titleid in TITLEIDS_REGIONS.keys()):
				if (region not in TITLEIDS_REGIONS[titleid]):
					TITLEIDS_REGIONS[titleid].append(region)
			else:
				TITLEIDS_REGIONS[titleid] = [region]
			
			with open(f"output/titleid/{titleid}.json", "w", encoding="UTF-8") as f:
				json.dump(entry, f, indent="\t", ensure_ascii=True)

def processCat4():
	for region in CATEGORY_4:
		files = glob.glob(f"scrap/{region}/*.json")
		print(f"Processing {region} {len(files)} files...")
		for i in range(len(files)):
			print(files[i])
			with open(files[i], "r", encoding="UTF-8") as f:
				DUMP = json.load(f)

			titleid = Path(files[i]).stem

			if (titleid.startswith("0100") == True):
				if (os.path.isfile(f"titledb_filtered/output/titleid/{titleid}.json") == True):
					continue
			else:
				if (os.path.isfile(f"titledb_filtered/output2/titleid/{titleid}.json") == True):
					continue

			entry = {}
			entry["name"] = DUMP["name"]
			entry["publisher"] = DUMP["publisher"]
			entry["bannerUrl"] = DUMP["bannerUrl"]
			entry["iconUrl"] =  DUMP["iconUrl"]
			entry["screenshots"] = DUMP["screenshots"]
			entry["releaseDate"] = DUMP["releaseDate"]
			
			if (size not in DUMP.keys() or DUMP["size"] == 0):
				entry["size"] = 0
			else: entry["size"] = DUMP["size"] if DUMP["size"].endswith("GiB") else DUMP["size"].replace(".0", "")
			
			if (titleid in TITLEIDS_REGIONS.keys()):
				for x in DUMP["Regions"]["True"]:
					if (x not in TITLEIDS_REGIONS[titleid]):
						TITLEIDS_REGIONS[titleid].append(x)
			else:
				TITLEIDS_REGIONS[titleid] = DUMP["Regions"]["True"]
			
			with open(f"output/titleid/{titleid}.json", "w", encoding="UTF-8") as f:
				json.dump(entry, f, indent="\t", ensure_ascii=True)

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

with open(f"output/main_regions_alt.json", "w", encoding="UTF-8") as f:
	json.dump(TITLEIDS_REGIONS, f, ensure_ascii=True)


