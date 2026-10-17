import unittest

from diza_analysis import (
    Label,
    allowed_pools,
    classify,
    lexicon_hits,
    match_responder,
    score_priority,
)
from diza_analysis.evaluation import evaluate, load_cases


class TriageTests(unittest.TestCase):
    def test_forty_golden_cases(self):
        result = evaluate(load_cases())
        self.assertEqual(result["cases"], 40)
        self.assertEqual(result["passed"], 40)
        self.assertEqual(result["p0_recall"]["value"], 1)
        self.assertFalse(result["publish_allowed"])
        self.assertIsNone(result["safety_compliance"]["value"])

    def test_p0_never_downgraded_by_context(self):
        for text in ("me quiero morir", "No chest pain during this drill", "I am not trapped"):
            with self.subTest(text=text):
                label = classify(text, {"severity": "P3", "hazard_here_now": False})
                self.assertEqual(label.severity, "P0")
                self.assertEqual(allowed_pools(label.category, label.severity), [])

    def test_structured_and_previous_urgency_are_preserved(self):
        self.assertEqual(classify("Everything is fine", {"severity": "P0"}).severity, "P0")
        self.assertEqual(classify("", {"injured_or_trapped": True}).severity, "P0")
        with self.assertRaises(ValueError):
            classify("", {"severity": "routine"})

    def test_context_guards_are_local_and_auditable(self):
        for text in (
            "no smoke here",
            "fire alarm test",
            "I heard that smoke was reported",
            "That fire mixtape",
        ):
            with self.subTest(text=text):
                self.assertEqual(classify(text).severity, "P3")
                self.assertTrue(any(hit.guards for hit in lexicon_hits(text)))
        for text in ("No smoke here, but fire next door", "fire alarm test but real smoke now"):
            self.assertEqual(classify(text).severity, "P1")

    def test_drill_code_only_overrides_drill_guard(self):
        self.assertEqual(classify("fire drill", {"drill_code": "DIZA-1"}).severity, "P1")
        self.assertEqual(classify("no smoke during test", {"drill_code": "DIZA-1"}).severity, "P3")

    def test_accents_contractions_boundaries_and_code_switching(self):
        self.assertEqual(classify("I can’t breathe").severity, "P0")
        self.assertEqual(classify("Inundación afuera", {"language": "es-MX"}).severity, "P1")
        self.assertEqual(classify("There is humo", {"language": "en"}).category, "smoke")
        self.assertEqual(classify("firefighter gunner smokehouse").severity, "P3")

    def test_unrelated_test_and_routine_infrastructure_keep_their_context(self):
        self.assertEqual(classify("I see smoke while taking a test").severity, "P1")
        self.assertEqual(
            classify("heater maintenance", {"category": "infrastructure"}).severity, "P3"
        )

    def test_wheelchair_boosts_and_adds_evacuation_skill(self):
        label = classify("Hay humo, uso silla de ruedas", {"language": "es"})
        self.assertIn("mobility", label.vulnerability)
        self.assertIn("evac_logistics", label.skills_needed)
        self.assertGreater(score_priority(label), score_priority(Label(severity="P1")))

    def test_priority_monotonic_and_severity_bands_preserved(self):
        for severity in ("P0", "P1", "P2", "P3"):
            last = 0
            for n in range(20):
                score = score_priority(
                    {"severity": severity, "vulnerability": list(range(n))},
                    [str(i) for i in range(n)],
                )
                self.assertGreaterEqual(score, last)
                last = score
        self.assertLess(score_priority(Label(severity="P1"), list("abcdefghij")), 100)
        self.assertEqual(score_priority({"severity": "P0"}), 100)

    def test_candidate_eligibility_precedes_ranking(self):
        base = {
            "skills": ["medical"],
            "languages": ["es"],
            "pools": ["trained_responder"],
            "status": "available",
            "verified": True,
        }
        responders = [
            {**base, "id": "eligible"},
            {**base, "id": "unverified", "verified": False},
            {**base, "id": "busy", "status": "busy"},
            {**base, "id": "overloaded", "active_calls": 2},
            {**base, "id": "wrong-skill", "skills": ["general"]},
            {**base, "id": "wrong-pool", "pools": ["general_helper"]},
        ]
        result = match_responder(
            ["medical"], "es", "P1", ["trained_responder"], responders=responders
        )
        self.assertEqual([r.responder_id for r in result], ["eligible"])
        self.assertEqual(
            match_responder([], "en", "P0", ["trained_responder"], responders=responders), []
        )

    def test_language_load_fatigue_and_tie_break(self):
        base = {
            "skills": ["medical"],
            "pools": ["trained_responder"],
            "status": "available",
            "verified": True,
            "languages": ["en"],
        }
        rows = [
            {**base, "id": "b"},
            {**base, "id": "a"},
            {**base, "id": "es", "languages": ["es"]},
            {**base, "id": "loaded", "active_calls": 1, "calls_this_shift": 10},
        ]
        result = match_responder(["medical"], "es", "P2", ["trained_responder"], responders=rows)
        self.assertEqual([r.responder_id for r in result], ["es", "a", "b", "loaded"])


if __name__ == "__main__":
    unittest.main()
