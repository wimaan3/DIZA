import unittest
from unittest.mock import MagicMock, patch

from diza_analysis.sources import (
    ACS_CODES,
    acs_profile,
    fetch_acs,
    fetch_myla311,
    get_json,
    myla311_baseline,
    point_in_polygon,
)


class SourceTests(unittest.TestCase):
    def test_acs_language_denominator_and_other_languages(self):
        headers = ["B16001_001E", *ACS_CODES.values()]
        profile = acs_profile(
            [headers, ["100", "50", "20", "5", "5", "5", "5"]], source="census-test"
        )
        self.assertEqual(profile["language_weights"]["und"], 0.1)
        self.assertEqual(profile["non_en_es_at_home_share"], 0.3)
        self.assertAlmostEqual(sum(profile["language_weights"].values()), 1)
        with self.assertRaises(ValueError):
            acs_profile([headers, ["-666666666", *(["1"] * 6)]], source="test")

    def test_acs_fetch_validates_geography_before_network(self):
        with patch("diza_analysis.sources.get_json") as get:
            with self.assertRaises(ValueError):
                fetch_acs(year=2024, state="06", county="037", tract="invalid")
            get.assert_not_called()

    def test_census_missing_key_html_has_an_actionable_error(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"<title>Missing Key</title>"
        with patch("diza_analysis.sources.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "CENSUS_API_KEY"):
                get_json("https://api.census.gov/data/test")

    def test_census_key_never_appears_in_profile_provenance(self):
        headers = ["NAME", "B16001_001E", *ACS_CODES.values(), "B01001_001E"]
        headers += [f"B01001_{i:03d}E" for i in (*range(20, 26), *range(44, 50))]
        values = ["Test tract", "100", "50", "20", "5", "5", "5", "5", "100"] + ["1"] * 12
        with patch.dict("os.environ", {"CENSUS_API_KEY": "dummy-key-for-tests"}):
            with patch("diza_analysis.sources.get_json", return_value=[headers, values]) as get:
                profile = fetch_acs(year=2024, state="06", county="037", tract="460100")
        self.assertIn("key=dummy-key-for-tests", get.call_args.args[0])
        self.assertNotIn("key=", profile["source"])
        self.assertEqual(profile["age_65_share"], 0.12)

    def test_baseline_includes_zero_days_and_deduplicates_requests(self):
        polygon = [[-119, 33], [-117, 33], [-117, 35], [-119, 35], [-119, 33]]
        zones = [{"id": "test", "polygon": polygon}]
        row = {
            "srnumber": "one",
            "createddate": "2025-01-01T09:30:00.000",
            "latitude": "34",
            "longitude": "-118",
            "requesttype": "Debris",
        }
        result = myla311_baseline([row, row], start="2025-01-01", end="2025-01-03", zones=zones)
        hour = next(row for row in result["hours"] if row["hour"] == 9)
        self.assertEqual(hour["mean"], 0.5)
        self.assertEqual(hour["std"], 0.5)
        self.assertEqual(result["topics"]["test"]["Debris"], 1)
        self.assertEqual(result["metric"], "service_requests_per_hour")
        self.assertTrue(point_in_polygon(34, -118, polygon))
        self.assertFalse(point_in_polygon(40, -118, polygon))

    def test_timezone_aware_service_request_uses_los_angeles_hour(self):
        row = {
            "srnumber": "one",
            "createddate": "2025-01-01T09:00:00Z",
            "latitude": "34.022",
            "longitude": "-118.285",
        }
        result = myla311_baseline([row], start="2025-01-01", end="2025-01-02")
        hour = next(
            row for row in result["hours"] if row["zone_id"] == "usc_campus" and row["hour"] == 1
        )
        self.assertEqual(hour["mean"], 1)

    def test_network_row_cap_fails_instead_of_silently_biasing_baseline(self):
        with patch("diza_analysis.sources.get_json", return_value=[{}, {}]):
            with self.assertRaisesRegex(ValueError, "exceeds max_rows"):
                fetch_myla311(start="2025-01-01", end="2025-01-02", max_rows=1)

    def test_myla311_year_and_date_validation(self):
        for start, end in (
            ("2026-01-01", "2026-01-02"),
            ("2025-01-03", "2025-01-01"),
            ("2025-99-01", "2025-01-03"),
        ):
            with self.assertRaises(ValueError):
                fetch_myla311(start=start, end=end)


if __name__ == "__main__":
    unittest.main()
