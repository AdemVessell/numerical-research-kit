import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from researchkit import freeze, score
from researchkit.__main__ import read, write
from test_core import fixture, refs

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_exclusive_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"receipt.json";write(p,{"first":True})
            with self.assertRaises(FileExistsError):write(p,{"second":True})
            self.assertEqual(read(p),{"first":True})

    def test_json_rejects_duplicates_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            for data in ('{"a":1,"a":2}', '{"a":NaN}'):
                p.write_text(data)
                with self.assertRaises(ValueError):read(p)

    def test_standalone_cli_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);protocol,pred=fixture();f=freeze(protocol,pred);y=refs(f)
            for name,value in [("protocol",protocol),("pred",pred),("frozen",f),("refs",y)]:write(p/(name+".json"),value)
            def run(*args):
                return subprocess.run([sys.executable,"-B",str(ROOT/"cli.py"),*map(str,args)],cwd=td,capture_output=True,text=True)
            r=run("score","--frozen",p/"frozen.json","--references",p/"refs.json","--out",p/"report.json")
            self.assertEqual(r.returncode,0,r.stderr)
            r=run("verify","--frozen",p/"frozen.json","--references",p/"refs.json","--report",p/"report.json")
            self.assertEqual(r.returncode,0,r.stderr)
            r=run("score","--frozen",p/"frozen.json","--references",p/"refs.json","--out",p/"report.json")
            self.assertEqual(r.returncode,2)
            pred["cases"][0]["candidate"]["values"]=[2.,2.];bad=freeze(protocol,pred);write(p/"bad.json",bad);write(p/"badrefs.json",refs(bad))
            r=run("score","--frozen",p/"bad.json","--references",p/"badrefs.json","--out",p/"fail.json")
            self.assertEqual(r.returncode,1,r.stderr)


if __name__ == "__main__":unittest.main()
