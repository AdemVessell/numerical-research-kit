import copy
import math
import unittest
from researchkit.core import bind_references, compare_vectors, correction_bound, freeze, score, templates, verify_report, sealed


def fixture():
    p = {"schema": 1, "name": "test", "cases": [{"id": "a", "size": 2, "parameters": {}}],
         "aggregation": "equal_case_mean_mse", "reference_visibility": "synthetic known fixture",
         "claim_boundary": "unit test", "cost_unit": "declared operations", "cost_basis": "fixture",
         "provenance": {"source": "test_core.py"},
         "gates": {"max_case_mse_ratio": 1, "max_mean_mse_ratio": 1, "max_cost_ratio": 1}}
    x = {"cases": [{"id": "a", "baseline": {"values": [1., 1.], "cost": 4, "failure": None},
                    "candidate": {"values": [0.5, 0.5], "cost": 4, "failure": None}}]}
    return p, x


def refs(f, values=None):
    return {"frozen_sha256": f["sha256"], "cases": [{"id": "a", "values": [0., 0.] if values is None else values}]}


class CoreTests(unittest.TestCase):
    def test_exact_metrics(self):
        r = compare_vectors([1., 1.], [.5, .5], [0., 0.])
        self.assertEqual((r["baseline_mse"], r["candidate_mse"], r["cross_term"], r["update_energy"]), (1., .25, -1., .25))
        self.assertEqual(r["extra_cost_fraction_at_break_even"], 3.)

    def test_zero_baseline(self):
        p, x = fixture();x["cases"][0]["baseline"]["values"] = [0., 0.]
        f = freeze(p, x);r = score(f, refs(f))["payload"]
        self.assertEqual(r["verdict"], "FAIL");self.assertIsNone(r["summary"]["mean_mse_ratio"])
        x["cases"][0]["candidate"]["values"] = [0., 0.];f = freeze(p, x)
        self.assertEqual(score(f, refs(f))["payload"]["verdict"], "PASS")

    def test_numeric_input_guards(self):
        for values in ([True], [math.nan], [math.inf], [], [1e308]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                compare_vectors(values, [0.], [0.])
        with self.assertRaises(ValueError):compare_vectors([1,2], [1], [1])

    def test_bound_and_limit(self):
        self.assertAlmostEqual(correction_bound(1., .1, 2.)["weighted_ratio_lower_bound"], 1.62)
        self.assertEqual(correction_bound(1., 2.)["mse_lower_bound"], 0.)
        self.assertIsNone(correction_bound(0., 0.)["mse_ratio_lower_bound"])
        for args in [(-1,0), (1,-1), (1,0,-1)]:
            with self.assertRaises(ValueError):correction_bound(*args)

    def test_freeze_detaches(self):
        p, x = fixture();f = freeze(p, x);x["cases"][0]["candidate"]["values"][0] = 999
        self.assertEqual(score(f, refs(f))["payload"]["verdict"], "PASS")

    def test_tamper_detected(self):
        f = freeze(*fixture());f["payload"]["predictions"]["cases"][0]["candidate"]["values"][0] = 2
        with self.assertRaises(ValueError):score(f, refs(f))

    def test_report_recompute(self):
        f = freeze(*fixture());y = refs(f);r = score(f, y)
        self.assertTrue(verify_report(r, f, y))
        r["payload"]["rows"][0]["candidate_mse"] = 999
        # Even a freshly rehashed wrong report fails arithmetic recomputation.
        with self.assertRaises(ValueError):verify_report(sealed(r["payload"]), f, y)

    def test_reference_guards(self):
        f = freeze(*fixture())
        for mutate in [lambda y:y.update(frozen_sha256="wrong"), lambda y:y["cases"][0].update(id="b"),
                       lambda y:y["cases"].append(y["cases"][0]), lambda y:y["cases"][0].update(values=[0.])]:
            y = refs(f);mutate(y)
            with self.assertRaises(ValueError):score(f, y)

    def test_bind_adds_hash_and_scores(self):
        f = freeze(*fixture());y = {"cases": [{"id": "a", "values": [0., 0.]}]}
        b = bind_references(f, y)
        self.assertEqual(b, refs(f));self.assertNotIn("frozen_sha256", y)
        self.assertEqual(score(f, b)["payload"]["verdict"], "PASS")
        self.assertEqual(bind_references(f, b), b)

    def test_bind_applies_score_guards(self):
        f = freeze(*fixture());other = freeze(*fixture()[:1], {"cases": [{"id": "a",
            "baseline": {"values": [2., 2.], "cost": 4, "failure": None},
            "candidate": {"values": [1., 1.], "cost": 4, "failure": None}}]})
        for mutate in [lambda y:y.update(frozen_sha256=other["sha256"]), lambda y:y["cases"][0].update(id="b"),
                       lambda y:y["cases"].append(y["cases"][0]), lambda y:y["cases"][0].update(values=[0.]),
                       lambda y:y["cases"][0].update(values=None), lambda y:y["cases"][0].update(values=[0., math.nan])]:
            y = {"cases": [{"id": "a", "values": [0., 0.]}]};mutate(y)
            with self.assertRaises(ValueError):bind_references(f, y)
        f["payload"]["predictions"]["cases"][0]["candidate"]["values"][0] = 2
        with self.assertRaises(ValueError):bind_references(f, {"cases": [{"id": "a", "values": [0., 0.]}]})

    def test_templates_refuse_freeze_until_filled(self):
        p, x, y = templates([("a", 2), ("b", 1)])
        self.assertEqual([c["id"] for c in y["cases"]], ["a", "b"])
        with self.assertRaises(ValueError):freeze(p, x)
        filled, _ = fixture();filled["cases"] = p["cases"]
        x["cases"][0]["baseline"].update(values=[1., 1.]);x["cases"][0]["candidate"].update(values=[.5, .5])
        x["cases"][1]["baseline"].update(values=[1.]);x["cases"][1]["candidate"].update(values=[.5])
        freeze(filled, x)
        filled["provenance"]["note"] = "TODO: say where this came from"
        with self.assertRaisesRegex(ValueError, "protocol.provenance.note"):freeze(filled, x)
        for bad in ([], [("a", 0)], [("a", 1), ("a", 2)], [(" ", 1)]):
            with self.assertRaises(ValueError):templates(bad)

    def test_protocol_shape_and_identity_guards(self):
        for mutate in [lambda p,x:p["cases"].append(p["cases"][0]), lambda p,x:x["cases"][0].update(id="b"),
                       lambda p,x:x["cases"][0]["candidate"].update(values=[1.]),
                       lambda p,x:p["cases"][0].update(size=True)]:
            p,x = fixture();mutate(p,x)
            with self.assertRaises(ValueError):freeze(p,x)

    def test_cost_and_failure_guards(self):
        for cost in (0, -1, True, math.inf):
            p,x = fixture();x["cases"][0]["candidate"]["cost"] = cost
            with self.assertRaises(ValueError):freeze(p,x)
        for changes in ({"cost": None}, {"cost": 5}, {"failure": "solver failed", "values": None}):
            p,x = fixture();x["cases"][0]["candidate"].update(changes);f = freeze(p,x)
            self.assertEqual(score(f,refs(f))["payload"]["verdict"], "FAIL")

    def test_explicit_equal_case_aggregation(self):
        p,x = fixture()
        p["gates"] = dict.fromkeys(p["gates"], None)
        p["cases"].append({"id": "b", "size": 1, "parameters": {}})
        x["cases"].append({"id": "b", "baseline": {"values": [2.], "cost": 4, "failure": None},
                           "candidate": {"values": [1.], "cost": 4, "failure": None}})
        f=freeze(p,x);y=refs(f);y["cases"].append({"id":"b","values":[0.]})
        r=score(f,y)["payload"]
        self.assertEqual(r["summary"]["baseline_mean_mse"], 2.5)
        self.assertEqual(r["summary"]["candidate_mean_mse"], .625)


if __name__ == "__main__":unittest.main()
