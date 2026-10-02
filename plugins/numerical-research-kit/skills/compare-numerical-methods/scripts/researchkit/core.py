"""Pure numeric and record APIs. No file, network, model, or process access."""
import hashlib
import json
import math

VERSION = "0.2.0"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name, minimum=None):
    require(type(value) in (int, float), name + " must be a number, not bool")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(name + " is out of range") from exc
    require(math.isfinite(value), name + " must be finite")
    require(minimum is None or value >= minimum, name + " below minimum")
    return value


def vector(values, name):
    require(isinstance(values, list) and len(values) > 0, name + " must be a nonempty list")
    return [number(x, name) for x in values]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sealed(payload):
    # JSON roundtrip detaches mutable caller-owned objects.
    return {"sha256": digest(payload), "payload": json.loads(canonical(payload))}


def unseal(record):
    require(isinstance(record, dict) and set(record) == {"sha256", "payload"}, "invalid sealed record")
    require(digest(record["payload"]) == record["sha256"], "record content hash mismatch")
    return record["payload"]


def ratio(numerator, denominator):
    return number(numerator / denominator, "computed ratio") if denominator > 0 else None


def average(values):
    answer = math.fsum(values) / len(values)
    require(math.isfinite(answer), "numeric overflow in average")
    return answer


def compare_vectors(baseline, candidate, reference):
    """One case, uniform coordinate weights. Ratios are null if baseline MSE=0."""
    a, b, y = [vector(v, name) for v, name in
               [(baseline, "baseline"), (candidate, "candidate"), (reference, "reference")]]
    require(len(a) == len(b) == len(y), "vector length mismatch")
    try:
        e = [x-t for x, t in zip(a, y)]
        d = [z-x for x, z in zip(a, b)]
        native = average([x*x for x in e])
        proposed = average([(z-t)**2 for z, t in zip(b, y)])
        energy = average([x*x for x in d])
        cross = 2*average([x*z for x, z in zip(e, d)])
        identity_error = proposed-native-cross-energy
        scale = max(native, proposed, abs(cross), energy, 1e-300)
        require(abs(identity_error) <= 1e-12*scale, "MSE decomposition exceeds tolerance")
        r = ratio(proposed, native)
        return {"size": len(a), "baseline_mse": native, "candidate_mse": proposed,
                "mse_ratio": r, "cross_term": cross, "update_energy": energy,
                "delta_rms": math.sqrt(energy), "identity_error": identity_error,
                "extra_cost_fraction_at_break_even": number(1/r-1, "break-even fraction") if r is not None and r > 0 else None,
                "sign_reversed_mse": average([(x-delta-t)**2 for x, delta, t in zip(a, d, y)])}
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("numeric range exceeded") from exc


def correction_bound(baseline_mse, delta_rms, cost_multiplier_ratio=1.0):
    """Conservative bound for one fixed update against the same reference.

    The multiplier ratio is caller-supplied, e.g. candidate_cost/baseline_cost
    for a linear MSE*cost metric. This does not implement any contest score.
    """
    mse = number(baseline_mse, "baseline_mse", 0)
    delta = number(delta_rms, "delta_rms", 0)
    cost = number(cost_multiplier_ratio, "cost multiplier ratio", 0)
    lower = max(0, math.sqrt(mse)-delta)**2
    return {"mse_lower_bound": lower, "mse_ratio_lower_bound": ratio(lower, mse),
            "weighted_ratio_lower_bound": number(ratio(lower, mse)*cost, "weighted bound") if mse else None,
            "scope": "Fixed update and same reference norm; not an observed error or population bound."}


def case_list(rows, name):
    require(isinstance(rows, list) and len(rows) > 0, name + " must be a nonempty list")
    ids = []
    for row in rows:
        require(isinstance(row, dict), name + " cases must be objects")
        ident = row.get("id")
        require(isinstance(ident, str) and ident.strip(), name + " case id is required")
        ids.append(ident)
    require(len(ids) == len(set(ids)), name + " duplicate case id")
    return ids


def validate_inputs(protocol, predictions):
    require(isinstance(protocol, dict) and type(protocol.get("schema")) is int and protocol["schema"] == 1, "protocol schema must be integer 1")
    for key in ("name", "claim_boundary", "reference_visibility", "cost_unit", "cost_basis"):
        require(isinstance(protocol.get(key), str) and protocol[key].strip(), "missing protocol " + key)
    require(protocol.get("aggregation") == "equal_case_mean_mse", "unsupported aggregation")
    require(isinstance(protocol.get("provenance"), dict) and protocol["provenance"], "provenance required")
    require(isinstance(predictions, dict), "predictions must be an object")
    ids = case_list(protocol.get("cases"), "protocol")
    require(case_list(predictions.get("cases"), "predictions") == ids, "prediction case order mismatch")
    gates = protocol.get("gates")
    require(isinstance(gates, dict) and set(gates) == {"max_case_mse_ratio", "max_mean_mse_ratio", "max_cost_ratio"}, "invalid gate fields")
    for k, v in gates.items():
        if v is not None:
            number(v, k, 0)
    for spec, row in zip(protocol["cases"], predictions["cases"]):
        size = spec.get("size")
        require(type(size) is int and size > 0, "case size must be a positive integer")
        require(isinstance(spec.get("parameters"), dict), "case parameters required")
        for arm in ("baseline", "candidate"):
            item = row.get(arm)
            require(isinstance(item, dict) and set(item) == {"values", "cost", "failure"}, "invalid arm fields")
            failure = item["failure"]
            require(failure is None or isinstance(failure, str) and bool(failure.strip()), "failure must be null or nonempty text")
            if failure is None:
                require(len(vector(item["values"], arm)) == size, "prediction shape mismatch")
            else:
                require(item["values"] is None, "failed arm must use null values")
            if item["cost"] is not None:
                require(number(item["cost"], "cost") > 0, "known costs must be positive")


PLACEHOLDER = "TODO:"


def placeholders(value, path):
    if isinstance(value, str):
        return [path] if value.startswith(PLACEHOLDER) else []
    items = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else []
    return [hit for key, item in items for hit in placeholders(item, path + "." + str(key))]


def templates(cases):
    """Fill-in protocol, predictions and unbound references for (id, size) pairs.

    Unfilled templates cannot be frozen: protocol text starts with TODO: and
    prediction values are null.
    """
    require(isinstance(cases, list) and len(cases) > 0, "at least one case is required")
    for ident, size in cases:
        require(isinstance(ident, str) and ident.strip(), "case id is required")
        require(type(size) is int and size > 0, "case size must be a positive integer")
    require(len({ident for ident, _ in cases}) == len(cases), "duplicate case id")
    protocol = {"schema": 1, "name": PLACEHOLDER + " short name",
                "cases": [{"id": ident, "size": size, "parameters": {}} for ident, size in cases],
                "aggregation": "equal_case_mean_mse",
                "reference_visibility": PLACEHOLDER + " reference source and who saw it before freeze",
                "claim_boundary": PLACEHOLDER + " what this comparison does not show",
                "cost_unit": PLACEHOLDER + " unit, e.g. RHS evaluations",
                "cost_basis": PLACEHOLDER + " how each cost is counted, including setup and readout",
                "provenance": {"source_sha256": PLACEHOLDER + " hash of the code that produced the predictions",
                               "data": PLACEHOLDER + " inputs and their exposure"},
                "gates": {"max_case_mse_ratio": None, "max_mean_mse_ratio": None, "max_cost_ratio": None}}
    arm = {"values": None, "cost": None, "failure": None}
    predictions = {"cases": [{"id": ident, "baseline": dict(arm), "candidate": dict(arm)} for ident, _ in cases]}
    references = {"cases": [{"id": ident, "values": None} for ident, _ in cases]}
    return protocol, predictions, references


def freeze(protocol, predictions):
    """Bind an explicit protocol and predictions; caller supplies provenance."""
    validate_inputs(protocol, predictions)
    left = placeholders(protocol, "protocol")
    require(not left, "unfilled template field: " + ", ".join(left))
    return sealed({"kind": "prediction_freeze", "version": VERSION,
                   "protocol": protocol, "predictions": predictions})


def frozen_protocol(frozen):
    payload = unseal(frozen)
    require(payload.get("kind") == "prediction_freeze" and payload.get("version") == VERSION, "unsupported freeze version")
    validate_inputs(payload["protocol"], payload["predictions"])
    return payload["protocol"], payload["predictions"]


def check_references(protocol, references):
    require(case_list(references.get("cases"), "references") == [x["id"] for x in protocol["cases"]], "reference case order mismatch")
    # Validate ALL references before calculating metrics.
    for spec, ref in zip(protocol["cases"], references["cases"]):
        require(len(vector(ref.get("values"), "reference")) == spec["size"], "reference shape mismatch")


def bind_references(frozen, references):
    """Return references bound to this frozen record, after the checks score applies."""
    p, _ = frozen_protocol(frozen)
    require(isinstance(references, dict), "references must be an object")
    require(references.get("frozen_sha256") in (None, frozen["sha256"]), "references are already bound to a different frozen record")
    check_references(p, references)
    return json.loads(canonical({**references, "frozen_sha256": frozen["sha256"]}))


def score(frozen, references):
    p, predictions = frozen_protocol(frozen)
    require(isinstance(references, dict) and references.get("frozen_sha256") == frozen["sha256"], "reference binding mismatch")
    check_references(p, references)
    rows = []
    for pred, ref in zip(predictions["cases"], references["cases"]):
        a, b = pred["baseline"], pred["candidate"]
        failures = {arm: pred[arm]["failure"] for arm in ("baseline", "candidate") if pred[arm]["failure"] is not None}
        if failures:
            rows.append({"id": pred["id"], "status": "FAILED", "failures": failures})
            continue
        row = compare_vectors(a["values"], b["values"], ref["values"])
        row.update(id=pred["id"], status="OK", baseline_cost=a["cost"], candidate_cost=b["cost"],
                   cost_ratio=ratio(b["cost"], a["cost"]) if a["cost"] is not None and b["cost"] is not None else None)
        rows.append(row)
    reasons = []
    if any(r["status"] != "OK" for r in rows):
        reasons.append("one or more declared execution failures")
        summary = None
    else:
        a = average([r["baseline_mse"] for r in rows]);b = average([r["candidate_mse"] for r in rows])
        known_cost = all(r["cost_ratio"] is not None for r in rows)
        ca = average([r["baseline_cost"] for r in rows]) if known_cost else None
        cb = average([r["candidate_cost"] for r in rows]) if known_cost else None
        summary = {"baseline_mean_mse": a, "candidate_mean_mse": b, "mean_mse_ratio": ratio(b, a),
                   "total_cost_ratio": ratio(cb, ca) if known_cost else None}
        g = p["gates"]
        if g["max_case_mse_ratio"] is not None and any(r["candidate_mse"] > g["max_case_mse_ratio"]*r["baseline_mse"] for r in rows):
            reasons.append("per-case MSE gate failed")
        if g["max_mean_mse_ratio"] is not None and b > g["max_mean_mse_ratio"]*a:
            reasons.append("mean MSE gate failed")
        if g["max_cost_ratio"] is not None:
            if not known_cost:
                reasons.append("cost gate requested but costs are unknown")
            elif any(r["cost_ratio"] > g["max_cost_ratio"] for r in rows) or cb > g["max_cost_ratio"]*ca:
                reasons.append("declared cost gate failed")
    return sealed({"kind": "comparison_report", "version": VERSION, "frozen_sha256": frozen["sha256"],
                   "reference_sha256": digest(references), "rows": rows, "summary": summary,
                   "verdict": "FAIL" if reasons else ("PASS" if any(v is not None for v in p["gates"].values()) else "MEASURED"), "reasons": reasons,
                   "claim_boundary": p["claim_boundary"], "aggregation": p["aggregation"],
                   "cost_unit": p["cost_unit"], "cost_basis": p["cost_basis"]})


def verify_report(report, frozen, references):
    unseal(report)
    require(report == score(frozen, references), "report differs from recomputation")
    return True
