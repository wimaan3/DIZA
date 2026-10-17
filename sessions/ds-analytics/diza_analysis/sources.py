"""Explicit, bounded loaders for public ACS and MyLA311 data.

No data is fetched at import time. No public service-request record is interpreted
as a voice call, clinical ground truth, or an official incident declaration.
"""

import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean, pstdev
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .config import load_config

MYLA311_DATASET = "h73f-gn57"
ACS_CODES = {
    "en": "B16001_002E",
    "es": "B16001_003E",
    "hy": "B16001_039E",
    "zh": "B16001_075E",
    "ko": "B16001_081E",
    "tl": "B16001_099E",
}


def get_json(url: str):
    request = Request(url, headers={"User-Agent": "DIZA-analysis/0.1 (hackathon research)"})
    with urlopen(request, timeout=20) as response:
        data = response.read(20_000_001)
    if len(data) > 20_000_000:
        raise ValueError("Public data response exceeded 20 MB limit")
    if b"Missing Key" in data[:2000]:
        raise ValueError("Census data API requires CENSUS_API_KEY; set it in your environment")
    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError("Public data provider returned a non-JSON response") from exc


def acs_profile(payload: list, *, source: str) -> dict:
    if not payload or len(payload) < 2:
        raise ValueError("ACS response contained no geography")
    counts = Counter()
    total = 0
    for values in payload[1:]:
        row = dict(zip(payload[0], values, strict=True))
        estimate = int(row["B16001_001E"])
        if estimate < 0:
            raise ValueError("ACS language estimate is unavailable")
        total += estimate
        for language, code in ACS_CODES.items():
            value = int(row[code])
            if value < 0:
                raise ValueError("ACS language estimate is unavailable")
            counts[language] += value
    if total <= 0 or sum(counts.values()) > total:
        raise ValueError("ACS language counts are inconsistent")
    counts["und"] = total - sum(counts.values())
    return {
        "source": source,
        "population_5_plus": total,
        "language_weights": {k: v / total for k, v in counts.items()},
        "non_en_es_at_home_share": (total - counts["en"] - counts["es"]) / total,
        "interpretation": "Language at home, not English comprehension or alert reach",
    }


def fetch_acs(*, year: int, state: str, county: str, tract: str) -> dict:
    if (
        not 2010 <= year <= 2100
        or not re.fullmatch(r"\d{2}", state)
        or not re.fullmatch(r"\d{3}", county)
        or not re.fullmatch(r"\d{6}", tract)
    ):
        raise ValueError("Supply a four-digit year and state/county/tract FIPS (2/3/6 digits)")
    variables = ["NAME", "B16001_001E", *ACS_CODES.values()]
    variables += ["B01001_001E"] + [f"B01001_{i:03d}E" for i in (*range(20, 26), *range(44, 50))]
    url = f"https://api.census.gov/data/{year}/acs/acs5?" + urlencode(
        {
            "get": ",".join(variables),
            "for": f"tract:{tract}",
            "in": f"state:{state} county:{county}",
        }
    )
    api_key = os.environ.get("CENSUS_API_KEY")
    request_url = url + "&" + urlencode({"key": api_key}) if api_key else url
    payload = get_json(request_url)
    profile = acs_profile(payload, source=url)
    row = dict(zip(payload[0], payload[1], strict=True))
    population = int(row["B01001_001E"])
    ages = [int(row[f"B01001_{i:03d}E"]) for i in (*range(20, 26), *range(44, 50))]
    if population <= 0 or any(value < 0 for value in ages):
        raise ValueError("ACS age estimates are unavailable")
    profile["age_65_share"] = sum(ages) / population
    profile["geography"] = row["NAME"]
    return profile


def point_in_polygon(lat: float, lon: float, polygon: list) -> bool:
    inside = False
    for first, second in zip(polygon, polygon[1:] + polygon[:1], strict=False):
        x1, y1 = first
        x2, y2 = second
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def myla311_baseline(records: list, *, start: str, end: str, zones: list | None = None) -> dict:
    """Area/hour topic baselines, including zero-request days in each denominator."""
    start_day, end_day = datetime.fromisoformat(start).date(), datetime.fromisoformat(end).date()
    if end_day <= start_day:
        raise ValueError("Baseline range is [start, end), with end after start")
    zones = zones if zones is not None else load_config("zones")
    counts, topics, seen = Counter(), defaultdict(Counter), set()
    discarded = 0
    for row in records:
        identity = row.get("srnumber")
        if not identity or identity in seen:
            continue
        seen.add(identity)
        try:
            dt = datetime.fromisoformat(row["createddate"].replace("Z", "+00:00"))
            # Socrata floating timestamps are local Los Angeles time.
            if dt.tzinfo is not None:
                dt = dt.astimezone(ZoneInfo("America/Los_Angeles"))
            lat, lon = float(row["latitude"]), float(row["longitude"])
            if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError("invalid coordinates")
        except (KeyError, TypeError, ValueError):
            discarded += 1
            continue
        if not start_day <= dt.date() < end_day:
            continue
        for zone in zones:
            if point_in_polygon(lat, lon, zone["polygon"]):
                counts[(zone["id"], dt.date(), dt.hour)] += 1
                topics[zone["id"]][row.get("requesttype", "Unknown")] += 1
                break
    days = (end_day - start_day).days
    output = []
    for zone in zones:
        for hour in range(24):
            values = [
                counts[(zone["id"], start_day + timedelta(days=d), hour)] for d in range(days)
            ]
            output.append(
                {
                    "zone_id": zone["id"],
                    "hour": hour,
                    "days": days,
                    "mean": mean(values),
                    "std": pstdev(values),
                }
            )
    return {
        "metric": "service_requests_per_hour",
        "start": start,
        "end_exclusive": end,
        "timezone": "America/Los_Angeles",
        "hours": output,
        "topics": {zone: dict(counter) for zone, counter in topics.items()},
        "discarded_invalid": discarded,
        "limitation": "Not a calibrated voice-call baseline; MyLA311 excludes Altadena",
        "source": f"https://data.lacity.org/resource/{MYLA311_DATASET}.json",
    }


def fetch_myla311(*, start: str, end: str, max_rows: int = 100_000) -> list:
    if max_rows < 1 or max_rows > 1_000_000:
        raise ValueError("max_rows must be between 1 and 1000000")
    # The pinned dataset is the verified 2025 resource, not a misleading latest alias.
    for value in (start, end):
        if not re.fullmatch(r"2025-\d{2}-\d{2}", value):
            raise ValueError("The pinned MyLA311 dataset covers 2025; use 2025 dates")
        datetime.fromisoformat(value)
    if end <= start:
        raise ValueError("end must follow start")
    rows, offset = [], 0
    while True:
        remaining = max_rows - len(rows)
        page_size = min(5000, remaining + 1)
        query = urlencode(
            {
                "$select": "srnumber,createddate,requesttype,latitude,longitude",
                "$where": f"createddate >= '{start}T00:00:00' AND createddate < '{end}T00:00:00'",
                "$order": "createddate,srnumber",
                "$limit": page_size,
                "$offset": offset,
            }
        )
        page = get_json(f"https://data.lacity.org/resource/{MYLA311_DATASET}.json?{query}")
        if not isinstance(page, list):
            raise ValueError("Unexpected MyLA311 response")
        rows.extend(page)
        if len(rows) > max_rows:
            raise ValueError("MyLA311 range exceeds max_rows; narrow the date range")
        if len(page) < page_size:
            return rows
        offset += len(page)
