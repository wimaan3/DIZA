import unittest

from diza_analysis import cluster_reports, detect_zone_level

NOW = 100_000


def reports(count=6):
    return [
        {
            "id": str(i),
            "caller_hash": f"caller-{i}",
            "zone_id": "altadena",
            "severity": "P1",
            "category": "smoke",
            "hazard_here_now": True,
            "ts": NOW - 10 - i,
            "lat": 34.19 + i * 0.00001,
            "lon": -118.13,
        }
        for i in range(count)
    ]


class ZoneTests(unittest.TestCase):
    def test_watch_ask_and_never_automatic_crisis(self):
        for count, expected in ((2, "normal"), (3, "watch"), (6, "ask"), (100, "ask")):
            with self.subTest(count=count):
                level, evidence = detect_zone_level("altadena", NOW, reports=reports(count))
                self.assertEqual(level, expected)
                self.assertEqual(evidence["largest_distinct_cluster"], count if count >= 3 else 0)

    def test_repeated_caller_does_not_form_density_cluster(self):
        rows = [{**r, "caller_hash": "one-person"} for r in reports(200)]
        self.assertEqual(cluster_reports("altadena", reports=rows, now=NOW), [])
        self.assertEqual(detect_zone_level("altadena", NOW, reports=rows)[0], "normal")

    def test_missing_identity_location_or_current_evidence_does_not_corroborate(self):
        variants = (
            {"caller_hash": None},
            {"lat": None},
            {"lat": 100},
            {"ts": NOW + 1},
            {"ts": NOW - 601},
            {"severity": "P3"},
            {"hazard_here_now": False},
        )
        for variant in variants:
            with self.subTest(variant=variant):
                rows = [{**r, **variant} for r in reports()]
                self.assertEqual(detect_zone_level("altadena", NOW, reports=rows)[0], "normal")

    def test_categories_zones_spatial_and_temporal_neighbors_stay_separate(self):
        for key, value in (
            ("zone_id", "usc_campus"),
            ("category", "fire"),
            ("lat", 34.25),
            ("ts", NOW - 550),
        ):
            rows = reports(3)
            rows[-1][key] = value
            self.assertEqual(cluster_reports("altadena", reports=rows, now=NOW), [])

    def test_two_spatial_clusters_do_not_sum_to_false_ask(self):
        first, second = reports(3), reports(3)
        for row in second:
            row.update(id="far-" + row["id"], caller_hash="far-" + row["caller_hash"], lat=34.25)
        clusters = cluster_reports("altadena", reports=first + second, now=NOW)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(detect_zone_level("altadena", NOW, reports=first + second)[0], "watch")

    def test_official_evidence_requires_zone_category_verification_and_validity(self):
        feed = {
            "zone_id": "altadena",
            "category": "smoke",
            "verified": True,
            "starts_at": NOW - 10,
            "expires_at": NOW + 10,
            "source": "NWS",
        }
        self.assertEqual(
            detect_zone_level("altadena", NOW, reports=reports(3), official_events=[feed])[0], "ask"
        )
        for change in (
            {"verified": False},
            {"zone_id": "usc_campus"},
            {"category": "flood"},
            {"expires_at": NOW},
        ):
            self.assertEqual(
                detect_zone_level(
                    "altadena", NOW, reports=reports(3), official_events=[{**feed, **change}]
                )[0],
                "watch",
            )

    def test_cannot_automatically_stand_down(self):
        for current in ("watch", "ask", "crisis"):
            self.assertEqual(
                detect_zone_level("altadena", NOW, reports=[], current_level=current)[0], current
            )

    def test_baseline_units_and_zero_variance(self):
        baseline = {"metric": "service_requests_per_hour", "mean": 0, "std": 0}
        level, evidence = detect_zone_level("altadena", NOW, reports=reports(2), baseline=baseline)
        self.assertEqual(level, "normal")
        self.assertIsNone(evidence["volume_z_score"])
        baseline["metric"] = "distinct_hazard_callers_per_window"
        # Three dispersed callers may trigger volume watch, not a spatial cluster.
        rows = [{**r, "lat": 34.19 + i * 0.02} for i, r in enumerate(reports(3))]
        level, evidence = detect_zone_level("altadena", NOW, reports=rows, baseline=baseline)
        self.assertEqual(level, "watch")
        self.assertEqual(evidence["volume_z_score"], 3)

    def test_growth_requires_a_separate_window_and_same_category(self):
        previous = {"zone_id": "altadena", "as_of": NOW - 600, "category_counts": {"smoke": 3}}
        self.assertEqual(
            detect_zone_level("altadena", NOW, reports=reports(4), previous_evidence=previous)[0],
            "ask",
        )
        previous["as_of"] = NOW - 1
        self.assertEqual(
            detect_zone_level("altadena", NOW, reports=reports(4), previous_evidence=previous)[0],
            "watch",
        )


if __name__ == "__main__":
    unittest.main()
