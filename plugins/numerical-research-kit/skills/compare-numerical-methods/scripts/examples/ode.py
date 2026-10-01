"""Known ODE methods demonstrate the record API on synthetic equations."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from researchkit import freeze, score, verify_report
from researchkit.__main__ import write


def euler(rate, steps=8):
    y = 1.0
    for _ in range(steps):
        y += -rate*y/steps
    return y


def heun(rate, steps=4, broken=False):
    y = 1.0
    for _ in range(steps):
        k1 = -rate*y
        k2 = -rate*(y+k1/steps)
        y += (-1 if broken else 1)*(k1+k2)/(2*steps)
    return y


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="New directory; never overwrite a previous run")
    args = ap.parse_args(argv)
    directory = Path(args.out);directory.mkdir(parents=True, exist_ok=False)
    rates = [0.5, 1.0, 2.0]
    protocol = {"schema": 1, "name": "exponential decay, Euler8 vs Heun4",
        "cases": [{"id": "rate_"+str(r), "size": 1, "parameters": {"rate": r, "initial": 1, "endpoint": 1}} for r in rates],
        "aggregation": "equal_case_mean_mse", "cost_unit": "RHS evaluations",
        "cost_basis": "Declared exact counts: Euler8 uses8, Heun4 uses8. Not FLOPs or wall time.",
        "reference_visibility": "Public analytic solution. Generated after record freeze; not blind or held out.",
        "claim_boundary": "Engineering portability demonstration with established solvers; no new numerical method or general speed claim.",
        "provenance": {"source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "reference": "math.exp(-rate*endpoint) with initial=1"},
        "gates": {"max_case_mse_ratio": 1, "max_mean_mse_ratio": 1, "max_cost_ratio": 1}}
    freezes = {}
    # Both intended and broken arms are frozen before generating the references.
    for name, broken in [("intended", False), ("wrong_sign", True)]:
        p = dict(protocol, name=protocol["name"]+" / "+name)
        predictions = {"cases": [{"id": spec["id"],
            "baseline": {"values": [euler(rate)], "cost": 8, "failure": None},
            "candidate": {"values": [heun(rate, broken=broken)], "cost": 8, "failure": None}}
            for rate, spec in zip(rates, p["cases"])]}
        write(directory/(name+"_protocol.json"), p)
        write(directory/(name+"_predictions.json"), predictions)
        freezes[name] = freeze(p, predictions)
        write(directory/(name+"_frozen.json"), freezes[name])
    verdicts = {}
    for name, frozen in freezes.items():
        references = {"frozen_sha256": frozen["sha256"], "cases": [
            {"id": spec["id"], "values": [math.exp(-rate)]} for rate, spec in zip(rates, protocol["cases"])]}
        write(directory/(name+"_references.json"), references)
        report = score(frozen, references);write(directory/(name+"_report.json"), report)
        verify_report(report, frozen, references)
        verdicts[name] = report["payload"]["verdict"]
    passed = verdicts == {"intended": "PASS", "wrong_sign": "FAIL"}
    result = {"demo_checks_pass": passed, "verdicts": verdicts, "expected_negative_control": "wrong_sign must fail",
              "meaning": "Record API and controls work on this synthetic fixture; no comparative toolkit/agent superiority established."}
    write(directory/"RESULT.json", result);print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
