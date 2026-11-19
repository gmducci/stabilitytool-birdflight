# Baseline environment (Stage 1)

The reference outputs in `baseline/data/` were produced from the **unmodified
upstream code** (tag `upstream-v1.1`, upstream GitHub commit
`67a29ecd78884cabfef1a0487dc418b599ef2e42`) in this environment.

## Machine

| Item     | Value                                      |
|----------|--------------------------------------------|
| Hardware | Apple M4, 10 cores, 24 GB RAM (arm64)      |
| OS       | macOS 26.6.2 (build 25G83)                 |

## Python and packages

| Package    | Version |
|------------|---------|
| Python     | 3.12.7 (pyenv build, Clang 17.0.0) |
| numpy      | 1.26.4 (PyPI wheel, OpenBLAS ILP64) |
| scipy      | 1.17.1  |
| matplotlib | 3.11.2  |

Full list of installed packages: `baseline/requirements-baseline.txt`.
The upstream package is **not** installed; the generator extracts the
`upstream-v1.1` tag to a temporary directory and puts it (toy systems,
`import multiflap`) or its `multiflap/` folder (bird model, like `main.py`) on
`sys.path`.

## Recreate

Since Stage 2 the baseline environment lives in `.venv-baseline` (`.venv` is
the uv project environment, see the top-level README).

```bash
uv venv --python 3.12 .venv-baseline
uv pip install --python .venv-baseline/bin/python -r baseline/requirements-baseline.txt
.venv-baseline/bin/python baseline/generate_baseline.py --out baseline/data --jobs 6
```

The upstream code is taken from the `upstream-v1.1` tag with `git archive`, so
this works from any checkout.

Since Stage 4 the package needs PyYAML, so package checks on numpy 1.26 use a
separate environment, `.venv-np126` (keep `.venv-baseline` unchanged):

```bash
uv venv --python 3.12 .venv-np126
uv pip install --python .venv-np126/bin/python -r baseline/requirements-baseline.txt pyyaml==6.0.3 pytest==9.2.0
uv pip install --python .venv-np126/bin/python --no-deps -e .
```

## Run settings

Every case runs in a fresh subprocess with:

- `MPLBACKEND=Agg`
- `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` (only small matrices are
  involved, so this should not affect results; set for determinism)
- `PYTHONDONTWRITEBYTECODE=1`

Each `<case>.json` also records these versions, the repository commit and a
dirty-tree flag. The Stage 1 files additionally record
`upstream_code_unmodified_vs_tag: true`; since Stage 2 the generator records
`target` and `upstream_source` instead.
