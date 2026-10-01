# Input format and interpretation

All JSON files use finite numbers, unique keys and unique case IDs. API numeric
values are `int` or `float`, never booleans. Predictions and references are
nonempty Python lists. The CLI rejects NaN, infinity and duplicate JSON keys.
Computation uses Python floating point (binary64 on the tested interpreters).
Float32 predictions can be supplied as their exactly represented float values.

Protocol:

```json
{
  "schema": 1,
  "name": "fixed comparison",
  "cases": [{"id": "case_a", "size": 2, "parameters": {}}],
  "aggregation": "equal_case_mean_mse",
  "reference_visibility": "previously exposed synthetic example",
  "claim_boundary": "one demonstration, no generalization claim",
  "cost_unit": "declared operations",
  "cost_basis": "caller supplied count including specified setup and readout",
  "provenance": {"source_sha256": "supply real source hash", "data": "describe source and exposure"},
  "gates": {"max_case_mse_ratio": 1, "max_mean_mse_ratio": 1, "max_cost_ratio": 1}
}
```

Predictions:

```json
{"cases": [{"id": "case_a",
  "baseline": {"values": [1,1], "cost": 8, "failure": null},
  "candidate": {"values": [0.5,0.5], "cost": 8, "failure": null}
}]}
```

Reference record:

```json
{"frozen_sha256": "copy the hash from frozen.json",
 "cases": [{"id": "case_a", "values": [0,0]}]}
```

Ordering and lengths must match exactly. There is no truncating zip or numeric
broadcasting. A failed arm uses `failure: "description"`, `values: null` and
known positive cost or null. Any declared failure makes the overall verdict
FAIL; failed cases never disappear from an average. Invalid records return
INVALID instead of a scientific verdict. Missing/unknown costs with an active
cost gate produce FAIL with a reason. Zero cost is unsupported; use null if
there is no comparable meaningful positive cost.

Gate values are nonnegative maximum ratios, inclusive (`<=`); null disables a
gate. All-null gates produce MEASURED, with no accuracy or cost requirement.
PASS applies only to enabled declared gates. A
baseline MSE of0 has null ratio; direct inequalities still reject a candidate
with positive error when an accuracy gate is active. Two exact outputs satisfy
any nonnegative error ratio threshold. Numeric range overflow is rejected.

For each case: `e = baseline-reference`, `d = candidate-baseline`.
The reported identity is `MSEcandidate = MSEbaseline + 2 mean(e*d) + mean(d*d)`.
The identity check uses relative tolerance1e-12 against the largest involved
term (minimum scale1e-300). `1/ratio-1` is a conditional extra-cost allowance
for a linear error-times-cost metric; negative values require cost savings.
It is null for undefined or zero ratios; zero candidate MSE is not presented
as an infinite practical speedup.

Aggregation is explicitly the arithmetic mean of each case's MSE. The report
divides candidate mean MSE by baseline mean MSE, never averages case ratios.
Cases of different lengths still have equal weight. This differs from pooling
every scalar error with equal weight; select only this supported convention.
The cost gate checks each case and the ratio of total declared costs.

The reverse-triangle bound is conservative for one fixed update and a supplied
baseline MSE against the same reference. It excludes impossible gains before
decoding new labels when that baseline norm is already known. It does not
discover update alignment, validate uncertain references or predict another
network. Any cost multiplier must be supplied under the caller's actual metric.
