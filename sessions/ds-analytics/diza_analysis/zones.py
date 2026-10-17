"""Space/time DBSCAN with distinct callers and a human-controlled crisis state."""

import hashlib
import math
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .config import load_config
from .timeutil import timestamp

HAZARD_CATEGORIES = {"fire", "smoke", "gas", "flood", "power", "infrastructure"}


@dataclass(frozen=True)
class Cluster:
    id: str
    zone_id: str
    category: str
    distinct_callers: int
    report_count: int
    lat: float
    lon: float
    first_seen: float
    last_seen: float


def distance_m(a: Mapping, b: Mapping) -> float:
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat = lat2 - lat1
    dlon = math.radians(b["lon"] - a["lon"])
    hav = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.asin(min(1, math.sqrt(hav)))


def _eligible(zone_id: str, reports: Sequence[Mapping], now: float, settings: Mapping) -> list:
    rows = []
    for report in reports:
        ts = timestamp(report.get("ts", report.get("created")))
        if ts is None or not now - settings["window_min"] * 60 <= ts <= now:
            continue
        if report.get("zone_id") != zone_id or not report.get("caller_hash"):
            continue
        if report.get("severity") not in {"P0", "P1"}:
            continue
        category = report.get("category", report.get("hazard"))
        if category not in HAZARD_CATEGORIES or report.get("hazard_here_now") is not True:
            continue
        lat, lon = report.get("lat"), report.get("lon")
        if not isinstance(lat, int | float) or not isinstance(lon, int | float):
            continue
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            continue
        rows.append({**report, "category": category, "ts": ts})
    # Rate-limit to one vote per caller/category/window, using the earliest observation.
    unique = {}
    for row in sorted(rows, key=lambda r: (r["ts"], str(r.get("id", "")))):
        unique.setdefault((row["caller_hash"], row["category"]), row)
    return list(unique.values())


def cluster_reports(
    zone_id: str,
    *,
    reports: Sequence[Mapping],
    now,
    settings: Mapping | None = None,
) -> list[Cluster]:
    """DBSCAN using a spatial radius AND temporal radius, with unique-caller core counts.

    A latitude/longitude grid limits neighbor searches; exact distance uses haversine.
    Missing identities/coordinates are excluded, never replaced by report IDs.
    """
    settings = {**load_config("settings"), **(settings or {})}
    now = timestamp(now)
    if now is None:
        raise ValueError("now is required")
    radius, time_s = settings["cluster_radius_m"], settings["cluster_time_s"]
    if radius <= 0 or time_s <= 0 or settings["cluster_min_callers"] < 1:
        raise ValueError("Cluster radius, time and minimum callers must be positive")
    rows = _eligible(zone_id, reports, now, settings)
    if not rows:
        return []
    # Use conservative longitude bins even at high latitudes.
    max_lat = max(abs(row["lat"]) for row in rows)
    lat_step = radius / 111_195
    lon_step = lat_step / max(0.00001, math.cos(math.radians(max_lat)))
    grid = defaultdict(list)

    def cell(row):
        return (
            row["category"],
            math.floor(row["lat"] / lat_step),
            math.floor(row["lon"] / lon_step),
        )

    for i, row in enumerate(rows):
        grid[cell(row)].append(i)

    def neighbors(i):
        category, x, y = cell(rows[i])
        nearby = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((category, x + dx, y + dy), []):
                    if abs(rows[i]["ts"] - rows[j]["ts"]) <= time_s:
                        if distance_m(rows[i], rows[j]) <= radius:
                            nearby.append(j)
        return nearby

    visited, assigned, clusters = set(), set(), []
    for i in range(len(rows)):
        if i in visited:
            continue
        visited.add(i)
        adjacent = neighbors(i)
        if len(adjacent) < settings["cluster_min_callers"]:
            continue
        members, queued = set(), set(adjacent)
        queue = deque(adjacent)
        while queue:
            j = queue.popleft()
            if j not in visited:
                visited.add(j)
                more = neighbors(j)
                if len(more) >= settings["cluster_min_callers"]:
                    for k in more:
                        if k not in queued:
                            queued.add(k)
                            queue.append(k)
            if j not in assigned:
                assigned.add(j)
                members.add(j)
        group = [rows[j] for j in sorted(members)]
        identity = "|".join(sorted(str(r.get("id", r["caller_hash"])) for r in group))
        clusters.append(
            Cluster(
                hashlib.sha256(identity.encode()).hexdigest()[:16],
                zone_id,
                group[0]["category"],
                len({r["caller_hash"] for r in group}),
                len(group),
                sum(r["lat"] for r in group) / len(group),
                sum(r["lon"] for r in group) / len(group),
                min(r["ts"] for r in group),
                max(r["ts"] for r in group),
            )
        )
    return sorted(clusters, key=lambda c: (-c.distinct_callers, c.id))


def detect_zone_level(
    zone_id: str,
    now,
    *,
    reports: Sequence[Mapping],
    current_level: str = "normal",
    baseline: Mapping | None = None,
    official_events: Sequence[Mapping] = (),
    previous_evidence: Mapping | None = None,
    settings: Mapping | None = None,
) -> tuple[str, dict]:
    """Suggest normal/watch/ask. Crisis and stand-down always require a human."""
    settings = {**load_config("settings"), **(settings or {})}
    if current_level not in {"normal", "watch", "ask", "crisis"}:
        raise ValueError("Invalid current zone level")
    now = timestamp(now)
    if now is None:
        raise ValueError("now is required")
    clusters = cluster_reports(zone_id, reports=reports, now=now, settings=settings)
    largest = max((c.distinct_callers for c in clusters), default=0)
    category_counts = defaultdict(int)
    for cluster in clusters:
        category_counts[cluster.category] = max(
            category_counts[cluster.category], cluster.distinct_callers
        )
    # A service-request baseline cannot establish a voice-call surge without calibration.
    z_score = None
    eligible = _eligible(zone_id, reports, now, settings)
    if baseline and baseline.get("metric") == "distinct_hazard_callers_per_window":
        mean, std = float(baseline["mean"]), float(baseline["std"])
        if mean < 0 or std < 0 or not math.isfinite(mean + std):
            raise ValueError("Baseline mean/std must be finite and nonnegative")
        count = len({r["caller_hash"] for r in eligible})
        z_score = (count - mean) / max(std, 1.0)
    feeds = []
    for event in official_events:
        start, end = timestamp(event.get("starts_at")), timestamp(event.get("expires_at"))
        if (
            event.get("verified") is True
            and event.get("zone_id") == zone_id
            and start is not None
            and end is not None
            and start <= now < end
            and event.get("category") in category_counts
        ):
            feeds.append(str(event.get("source", "official")))
    watch = largest >= settings["watch_distinct_callers"] or (
        z_score is not None and z_score >= settings["watch_z_score"]
    )
    previous_evidence = previous_evidence or {}
    previous_at = timestamp(previous_evidence.get("as_of"))
    growing = (
        watch
        and previous_at is not None
        and settings["window_min"] * 60 <= now - previous_at <= settings["window_min"] * 120
        and previous_evidence.get("zone_id") == zone_id
        and any(
            count > previous_evidence.get("category_counts", {}).get(category, 0) >= 3
            for category, count in category_counts.items()
        )
    )
    suggested = "normal"
    if watch:
        suggested = "watch"
    if largest >= settings["ask_distinct_callers"] or (watch and feeds) or growing:
        suggested = "ask"
    levels = ["normal", "watch", "ask", "crisis"]
    level = max((current_level, suggested), key=levels.index)
    evidence = {
        "zone_id": zone_id,
        "as_of": now,
        "largest_distinct_cluster": largest,
        "category_counts": dict(category_counts),
        "volume_z_score": z_score,
        "official_sources": sorted(set(feeds)),
        "growing_over_two_windows": bool(growing),
        "clusters": len(clusters),
        "suggested_level": suggested,
        "human_declaration_required": level != "crisis",
        "stand_down_requires_human": True,
    }
    return level, evidence
