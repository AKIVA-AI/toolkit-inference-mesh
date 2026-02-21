# Releasing (Toolkit Inference Mesh)

## Pre-flight

- Update `UPSTREAM.md` if you re-vendored upstream.
- Run:
  - `python -m compileall src`
  - `pytest`

## Version bump

- Update `pyproject.toml` version.
- Update `CHANGELOG.md`.

## Build and publish

From `enterprise-tools/inference-mesh/`:

```bash
python -m pip install -U build twine
python -m build
python -m twine upload dist/*
```

## Tagging (recommended)

- Create a tag: `toolkit-inference-mesh/vX.Y.Z`



