# Numerical Research Kit

A local skill and Python toolkit for comparing numerical approximations. It turns
supplied baseline, candidate and reference values into checkable error measurements,
declared-cost comparisons and saved reports.

**Version 0.2.1 · Python 3.9+ · standard library only**

Use it to evaluate a solver change, inspect whether a correction is large enough
to justify its cost, or preserve the inputs behind a reported result. It handles
case matching, failure reporting, arithmetic and record verification. It does not
supply the estimator being evaluated.

## Ask the skill

After installation, start a new Codex chat and choose `compare-numerical-methods`
from the skill picker, or ask:

> Use $compare-numerical-methods to compare my baseline and candidate predictions against this reference.

> Check whether a correction with RMS 0.1 could offset twice the cost when baseline MSE is 1.

> Verify this frozen comparison and report every failed case.

The plugin supplies one skill with bundled scripts. It requires a host that can
run Python and access the selected files. It has no MCP server or hosted service.
Other hosts can read the skill; execution support depends on their environment.

## Run directly

From this plugin directory, create a new demonstration directory:

```sh
python3 -B skills/compare-numerical-methods/scripts/examples/ode.py --out ./first-run
python3 -B skills/compare-numerical-methods/scripts/cli.py verify --frozen first-run/intended_frozen.json --references first-run/intended_references.json --report first-run/intended_report.json
```

Expected: the ordinary solver comparison passes its declared gates; the
wrong-sign solver fails. Both reports verify. The example uses Euler and Heun
on three exponential-decay equations with eight RHS evaluations each. Those
counts are neither wall time nor full FLOPs, and the analytic reference is public.
No new numerical method is claimed.

For your own vectors, save `vectors.json`:

```json
{"baseline":[1,1],"candidate":[0.5,0.5],"reference":[0,0]}
```

```sh
python3 -B skills/compare-numerical-methods/scripts/cli.py compare --input vectors.json --out metrics.json
python3 -B skills/compare-numerical-methods/scripts/cli.py bound --baseline-mse 1 --delta-rms 0.1 --cost-multiplier-ratio 2 --out bound.json
```

The vector comparison gives baseline MSE 1, candidate MSE 0.25. The separate
bound example gives weighted-ratio lower bound 1.62: that fixed correction cannot
pay for twice the cost under the supplied linear error-times-cost metric.

For multiple cases and acceptance criteria, follow the
[input contract](skills/compare-numerical-methods/references/FORMAT.md).
Commands `freeze`, `score`, and `verify` bind predictions, references and reports.
Output files must be new. Inputs are UTF-8 JSON, at most 16 MiB per file.

## Reusable API

The `researchkit` module is in `skills/compare-numerical-methods/scripts`.
From that directory, Python code can import:

```python
from researchkit import compare_vectors, correction_bound, freeze, score, verify_report
assert compare_vectors([1, 1], [0.5, 0.5], [0, 0])["mse_ratio"] == 0.25
```

There is no dependency installation or API key. The public package contains the
comparison module, commands, input contract, tests and synthetic example.

## Read results accurately

| Result | Meaning |
| --- | --- |
| PASS | Supplied values satisfy the declared gates. |
| FAIL | A declared gate or execution-failure rule failed. |
| MEASURED | No acceptance gates were requested. |
| INVALID | Inputs or file operations were invalid. |
| Integrity PASS | Saved arithmetic recomputes, even if the comparison failed. |

Exit codes: 0 for successful operations/PASS/MEASURED; 1 for scored FAIL;
2 for invalid input or file errors. Failed cases are retained and prevent a
partial average from being reported as the full comparison.

Costs and reference correctness remain the caller's responsibility. Hashes
establish content consistency, not trusted timestamps or reference isolation.
The tool does not rerun predictors, measure memory/FLOPs/time, calculate
uncertainty intervals, certify scientific results, or guarantee improvement.
Arithmetic is binary64; very small values can underflow. Choose suitable units.

## Development and support

```sh
cd skills/compare-numerical-methods/scripts
python3 -S -B -m unittest discover -s tests -v
```

See [provenance](PROVENANCE.md), [privacy](PRIVACY.md), [support](SUPPORT.md),
and the [MIT license](LICENSE). This is independently developed software.
No OpenAI endorsement is implied.
