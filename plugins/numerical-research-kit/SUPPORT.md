# Support

Report reproducible software problems through this project's GitHub Issues.
Use a small synthetic input, the package version, Python version, exact command,
expected result and actual result. Do not include personal data, credentials or
unpublished research. There is no guaranteed response time or paid support SLA.

Version 0.3.1 uses record version 0.2.0. Reports affected by the corrected
comparison underflow now return INVALID even though their record format is
unchanged. Older development record formats are not accepted. Keep original
records and the original verifier for historical inspection; never relabel an
old record as a new result. Changes to inputs, code or gates should produce a
new comparison directory. See [CHANGELOG.md](CHANGELOG.md) and the
[format notes](skills/compare-numerical-methods/references/FORMAT.md).

The supported scope is finite one-dimensional numerical vectors with uniform
within-case MSE and equal case weighting. Use domain-specific tests in addition
to this toolkit. Scientific validity, reference correctness, cost measurement
and distribution shift require evidence beyond these records.
