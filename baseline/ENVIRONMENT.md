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
The upstream package is **not** installed; the generator puts the repository
root (toy systems, `import multiflap`) or `multiflap/` (bird model, like
`main.py`) on `sys.path`.

## Recreate

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r baseline/requirements-baseline.txt
.venv/bin/python baseline/generate_baseline.py --out baseline/data --jobs 4
```

## Run settings

Every case runs in a fresh subprocess with:

- `MPLBACKEND=Agg`
- `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` (only small matrices are
  involved, so this should not affect results; set for determinism)
- `PYTHONDONTWRITEBYTECODE=1`

Each `<case>.json` also records these versions, the repository commit, a
dirty-tree flag and a check that `multiflap/`, `examples/` and `setup.py` are
identical to the `upstream-v1.1` tag.
