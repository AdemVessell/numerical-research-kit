"""Range regressions: exact dyadic controls, not numerical-method benchmarks."""
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from researchkit import bind_references, compare_vectors, freeze, score, templates
from researchkit.core import ratio


ROOT = Path(__file__).resolve().parents[1]


def comparison(cases):
    """Make a gate-1 comparison with equal declared costs and zero references."""
    p, x, y = templates([(ident, len(a)) for ident, a, b in cases])
    p.update(name="range control", claim_boundary="exact arithmetic control",
             reference_visibility="zero reference exposed", cost_unit="unit",
             cost_basis="equal declared cost", provenance={"source": __file__},
             gates=dict.fromkeys(p["gates"], 1))
    for row, ref, (_, a, b) in zip(x["cases"], y["cases"], cases):
        row["baseline"].update(values=a, cost=1)
        row["candidate"].update(values=b, cost=1)
        ref["values"] = [0.0] * len(a)
    frozen = freeze(p, x)
    return frozen, bind_references(frozen, y)


class NumericRangeTests(unittest.TestCase):
    def test_tiny_worse_candidate_cannot_pass(self):
        a, b = 1e-200, 2e-200
        exact_a, exact_b = Fraction.from_float(a), Fraction.from_float(b)
        self.assertEqual(exact_b**2 / exact_a**2, 4)
        with self.assertRaisesRegex(ValueError, "underflow"):
            compare_vectors([a], [b], [0.0])
        frozen, reference = comparison([("tiny", [a], [b])])
        with self.assertRaisesRegex(ValueError, "underflow"):
            score(frozen, reference)

    def test_each_nonzero_square_path(self):
        tiny = math.ldexp(1.0, -600)
        adjacent = math.nextafter(math.ldexp(1.0, -500), math.inf)
        cases = [([tiny], [0.0], [0.0]),
                 ([0.0], [tiny], [0.0]),
                 # Both MSEs representable; only the update square underflows.
                 ([math.ldexp(1.0, -500)], [adjacent], [0.0]),
                 # Baseline, candidate and update squares are representable;
                 # the sign-reversed residual's square underflows.
                 ([math.ldexp(1.0, -500)],
                  [math.nextafter(math.ldexp(1.0, -499), math.inf)], [0.0])]
        for a, b, y in cases:
            with self.subTest(a=a, b=b), self.assertRaisesRegex(ValueError, "underflow"):
                compare_vectors(a, b, y)

    def test_mean_underflow_with_representable_square(self):
        x = math.ldexp(1.0, -537)
        self.assertEqual(Fraction.from_float(x)**2, Fraction(1, 2**1074))
        self.assertGreater(x*x, 0)
        with self.assertRaisesRegex(ValueError, "underflow"):
            compare_vectors([x, 0.0], [x, 0.0], [0.0, 0.0])

    def test_summary_mean_underflow(self):
        x = math.ldexp(1.0, -537)
        frozen, reference = comparison([("nonzero", [x], [x]),
                                        ("zero", [0.0], [0.0])])
        with self.assertRaisesRegex(ValueError, "underflow"):
            score(frozen, reference)

    def test_positive_ratio_underflow_and_true_zero(self):
        with self.assertRaisesRegex(ValueError, "underflow"):
            ratio(math.ldexp(1.0, -1074), 2.0)
        self.assertEqual(ratio(0.0, 2.0), 0.0)
        self.assertIsNone(ratio(1.0, 0.0))

    def test_supported_subnormal_and_true_zero_remain_valid(self):
        x = math.ldexp(1.0, -537)
        r = compare_vectors([x], [x], [0.0])
        self.assertEqual(r["baseline_mse"], math.ldexp(1.0, -1074))
        self.assertEqual(r["mse_ratio"], 1.0)
        for value in (x, 0.0, -0.0):
            frozen, reference = comparison([("valid", [value], [value])])
            self.assertEqual(score(frozen, reference)["payload"]["verdict"], "PASS")

    def test_score_cli_rejects_without_report(self):
        frozen, reference = comparison([("tiny", [1e-200], [2e-200])])
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            for name, record in (("freeze.json", frozen), ("reference.json", reference)):
                (folder/name).write_text(json.dumps(record))
            result = subprocess.run([sys.executable, "-S", "-B", str(ROOT/"cli.py"),
                "score", "--frozen", str(folder/"freeze.json"),
                "--references", str(folder/"reference.json"),
                "--out", str(folder/"report.json")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)["status"], "INVALID")
            self.assertIn("underflow", result.stderr)
            self.assertFalse((folder/"report.json").exists())


if __name__ == "__main__":
    unittest.main()
