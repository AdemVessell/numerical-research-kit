# Changes

## 0.3.1 — reject comparison underflow

- Reject nonzero comparison squares, positive means of nonnegative terms and
  positive ratios that round to zero instead of accepting a false PASS.
- Cover per-case, aggregate, update and sign-reversed paths; preserve genuine
  zeros and supported subnormal results. CLI returns INVALID without a report.
- Record format stays 0.2.0. Affected old reports no longer verify with the
  corrected arithmetic; preserve original records and the historical verifier.
- Seven regression tests cover the failure and valid boundary controls.
- No new commands or dependencies; Python 3.9+ and existing attribution retained.

## 0.3.0 — init and bind commands

- `init` writes fill-in protocol, predictions and references templates.
- `bind` checks references against a frozen record and adds its hash, replacing
  the manual copy step. It refuses references bound to a different record.
- `freeze` rejects protocols that still contain `TODO:` template placeholders.
- Record version stays 0.2.0; existing records verify unchanged.

## 0.2.1 — documentation fix

- Claude Code plugin and marketplace manifests alongside the Codex ones.
- Clarify that `references.json` binds to the `sha256` printed by `freeze`
  (the top-level `sha256` in `frozen.json`).
- Record version stays 0.2.0; existing records verify unchanged.

## 0.2.0 — initial public package

- Portable plugin manifest, repository marketplace and one callable Codex skill.
- Standard-library comparison, correction bound, freeze, score and verification.
- Direct `compare` and `bound` commands.
- `MEASURED` verdict when no acceptance criteria were requested.
- Strict integer schema version, finite computed ratios, UTF-8 inputs and a
  16 MiB per-file JSON limit.
- Synthetic ODE example with a deliberately broken control; tests and input contract.
- Public documentation, privacy statement and MIT license.

This release derives from an internal 0.1.0 comparison toolkit. Record version
0.2.0 is explicit; old records must use their original verifier.
