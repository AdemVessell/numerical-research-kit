# Numerical Research Kit

A Codex skill with local Python tools for comparing numerical error and declared
cost, bounding a fixed correction, and verifying saved comparison records.

## Install from this checkout

Requires a Codex client with plugin support and Python 3.9 or later.
From this repository's root:

```sh
codex plugin marketplace add .
codex plugin add numerical-research-kit@numerical-research-kit-marketplace
```

Start a new chat and invoke `$compare-numerical-methods` through the skill picker.
In desktop clients, the repository marketplace can also appear in the plugin
directory after a refresh/restart. Client support can vary.

The repository marketplace is separate from the universal public plugin directory.
Source distribution does not imply directory review or approval.

## Try without installing

```sh
python3 -B plugins/numerical-research-kit/skills/compare-numerical-methods/scripts/examples/ode.py --out ./first-run
```

Expected: `intended: PASS`, `wrong_sign: FAIL`, `demo_checks_pass: true`.

Read the [usage guide](plugins/numerical-research-kit/README.md) for commands,
examples and limits. Python code runs in the host execution environment and
requires no API key, account, network access or external Python packages.

## Remove the local installation

```sh
codex plugin remove numerical-research-kit@numerical-research-kit-marketplace
codex plugin marketplace remove numerical-research-kit-marketplace
```

MIT licensed. Developed by Adem Vessell with AI assistance; see
[provenance](plugins/numerical-research-kit/PROVENANCE.md),
[privacy](plugins/numerical-research-kit/PRIVACY.md), and
[support](plugins/numerical-research-kit/SUPPORT.md).
