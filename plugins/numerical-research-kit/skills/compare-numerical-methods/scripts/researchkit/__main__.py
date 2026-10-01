"""Local numerical comparisons and records; no predictor execution."""
import argparse
import json
import sys
from pathlib import Path
from .core import compare_vectors, correction_bound, freeze, score, verify_report


def pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ValueError("duplicate JSON key: " + k)
        result[k] = v
    return result


def read(path):
    def reject(value):
        raise ValueError("nonfinite JSON constant: " + value)
    with Path(path).open("rb") as handle:
        data = handle.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("JSON input exceeds the 16 MiB per-file limit")
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)


def write(path, value):
    data = json.dumps(value, indent=2, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8") as f:
        f.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Portable numerical comparison records; declared costs, no official scoring.")
    sub = parser.add_subparsers(dest="command", required=True)
    co = sub.add_parser("compare", help="Compare three same-length lists; save descriptive metrics")
    co.add_argument("--input", required=True);co.add_argument("--out", required=True)
    bo = sub.add_parser("bound", help="Lower bound for one fixed update under supplied norms")
    bo.add_argument("--baseline-mse", type=float, required=True)
    bo.add_argument("--delta-rms", type=float, required=True)
    bo.add_argument("--cost-multiplier-ratio", type=float, default=1.0)
    bo.add_argument("--out", required=True)
    fr = sub.add_parser("freeze");fr.add_argument("--protocol", required=True);fr.add_argument("--predictions", required=True);fr.add_argument("--out", required=True)
    sc = sub.add_parser("score");sc.add_argument("--frozen", required=True);sc.add_argument("--references", required=True);sc.add_argument("--out", required=True)
    ve = sub.add_parser("verify");ve.add_argument("--frozen", required=True);ve.add_argument("--references", required=True);ve.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "compare":
            inputs = read(args.input)
            if not isinstance(inputs, dict) or set(inputs) != {"baseline", "candidate", "reference"}:
                raise ValueError("compare input needs exactly baseline, candidate and reference")
            result = compare_vectors(**inputs);write(args.out, result)
            print(json.dumps({"status": "MEASURED", **result}, allow_nan=False));return 0
        if args.command == "bound":
            result = correction_bound(args.baseline_mse, args.delta_rms, args.cost_multiplier_ratio)
            write(args.out, result);print(json.dumps(result, allow_nan=False));return 0
        if args.command == "freeze":
            result = freeze(read(args.protocol), read(args.predictions));write(args.out, result)
            print(json.dumps({"status": "FROZEN", "sha256": result["sha256"]}));return 0
        if args.command == "score":
            result = score(read(args.frozen), read(args.references));write(args.out, result)
            print(json.dumps({"verdict": result["payload"]["verdict"], "reasons": result["payload"]["reasons"]}))
            return 1 if result["payload"]["verdict"] == "FAIL" else 0
        verify_report(read(args.report), read(args.frozen), read(args.references))
        print(json.dumps({"integrity": "PASS", "meaning": "Saved arithmetic agrees; inspect the report verdict separately."}));return 0
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}), file=sys.stderr);return 2


if __name__ == "__main__":
    raise SystemExit(main())
