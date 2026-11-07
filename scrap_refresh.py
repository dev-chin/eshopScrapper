"""Tracks when each scrap file was last downloaded, so scrapers can
periodically re-download old entries instead of keeping them forever.

Timestamps are stored in scrap/last_scraped.json as
{"<REGION>": {"<id>": <unix time>}}. Files with no recorded time are
treated as the oldest and get refreshed first.

Tuning (environment variables):
  REFRESH_PER_REGION     max existing entries re-scraped per region per run (default 100)
  REFRESH_PER_REGION_EU  same for the EU scraper, which is ~30x more requests per title (default 25)
  REFRESH_MAX_AGE_DAYS   only re-scrape entries older than this (default 7)
"""
import json
import os
import threading
import time

INDEX_FILE = "scrap/last_scraped.json"

_lock = threading.Lock()
_index = None


def _load():
	global _index
	if _index is None:
		try:
			with open(INDEX_FILE, "r", encoding="UTF-8") as f:
				_index = json.load(f)
		except (FileNotFoundError, json.JSONDecodeError):
			_index = {}
	return _index


def pick_stale(region: str, existing_ids, limit_env: str = "REFRESH_PER_REGION", default_limit: int = 100):
	"""Return up to N ids (from existing_ids) whose scrap file is the oldest and past max age."""
	limit = int(os.environ.get(limit_env, default_limit))
	max_age = float(os.environ.get("REFRESH_MAX_AGE_DAYS", 7)) * 86400
	if limit <= 0:
		return []
	times = _load().get(region, {})
	now = time.time()
	stale = [i for i in existing_ids if now - times.get(str(i), 0) >= max_age]
	stale.sort(key=lambda i: times.get(str(i), 0))
	return stale[:limit]


def mark(region: str, id_) -> None:
	"""Record that id_ in region was just scraped (call only after a successful save)."""
	with _lock:
		_load().setdefault(region, {})[str(id_)] = int(time.time())


def save() -> None:
	with _lock:
		if _index is None:
			return
		os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
		tmp = INDEX_FILE + ".tmp"
		with open(tmp, "w", encoding="UTF-8") as f:
			json.dump(_index, f, sort_keys=True, separators=(",", ":"))
		os.replace(tmp, INDEX_FILE)
