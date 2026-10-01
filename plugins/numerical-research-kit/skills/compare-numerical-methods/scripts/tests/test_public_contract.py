import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from researchkit import compare_vectors, freeze, score
from researchkit.__main__ import read, write
from test_core import fixture, refs

ROOT = Path(__file__).resolve().parents[1]


class PublicContractTests(unittest.TestCase):
    def test_schema_is_integer(self):
        for value in (True, 1.0, "1", None):
            p, x = fixture();p["schema"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                freeze(p, x)

    def test_measurement_without_gates_is_not_pass(self):
        p, x = fixture();p["gates"] = dict.fromkeys(p["gates"], None)
        f = freeze(p, x)
        self.assertEqual(score(f, refs(f))["payload"]["verdict"], "MEASURED")
        x["cases"][0]["candidate"].update(values=None, failure="solver failed")
        f = freeze(p, x)
        self.assertEqual(score(f, refs(f))["payload"]["verdict"], "FAIL")

    def test_unrepresentable_ratios_rejected(self):
        with self.assertRaises(ValueError):
            compare_vectors([1e-160], [1e150], [0.0])
        with self.assertRaises(ValueError):
            compare_vectors([1.0], [1e-160], [0.0])
        p, x = fixture()
        x["cases"][0]["baseline"]["cost"] = 1e-320
        f = freeze(p, x)
        with self.assertRaises(ValueError):score(f, refs(f))

    def test_direct_commands_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            write(p/"vectors.json", {"baseline": [1, 1], "candidate": [.5, .5], "reference": [0, 0]})
            def run(*args):
                return subprocess.run([sys.executable, "-S", "-B", str(ROOT/"cli.py"), *map(str,args)], cwd=td, capture_output=True, text=True)
            args=("compare", "--input", p/"vectors.json", "--out", p/"metrics.json")
            r=run(*args);self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(read(p/"metrics.json")["mse_ratio"], .25)
            before=(p/"metrics.json").read_bytes()
            self.assertEqual(run(*args).returncode, 2)
            self.assertEqual((p/"metrics.json").read_bytes(), before)
            r=run("bound", "--baseline-mse", "1", "--delta-rms", ".1", "--cost-multiplier-ratio", "2", "--out", p/"bound.json")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertAlmostEqual(read(p/"bound.json")["weighted_ratio_lower_bound"], 1.62)
            r=run("bound", "--baseline-mse", "nan", "--delta-rms", ".1", "--out", p/"bad.json")
            self.assertEqual(r.returncode, 2)
            self.assertFalse((p/"bad.json").exists())

    def test_malformed_files_report_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for value in (b"\xff", b"["*3000, b'{"baseline":[]}'):
                (p/"bad.json").write_bytes(value)
                r=subprocess.run([sys.executable,"-S","-B",str(ROOT/"cli.py"),"compare","--input",str(p/"bad.json"),"--out",str(p/"output.json")],cwd=td,capture_output=True,text=True)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertEqual(json.loads(r.stderr)["status"], "INVALID")
                self.assertFalse((p/"output.json").exists())

    def test_input_size_limit(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"large.json"
            p.write_bytes(b" "*(16*1024*1024+1))
            with self.assertRaisesRegex(ValueError, "16 MiB"):
                read(p)


if __name__ == "__main__":unittest.main()
