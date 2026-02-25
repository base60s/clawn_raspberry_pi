# Release process (SafeClaw)

## Pre-release checklist

- Ensure `main` branch is clean:
  - `git status`
  - latest commit message is meaningful
- Validate `README.md` reflects current commands and defaults.
- Ensure `CHANGELOG.md` has an unreleased entry for next version.
- Confirm `docs/*` and `SECURITY.md` match current behavior.
- Verify `pyproject.toml` version is incremented correctly.

## Build + publish steps

```bash
python -m pip install -e .
python -m compileall -q src
python -m saferclaw --help
```

Create and push a release tag:

```bash
git tag vX.Y.Z
git push --tags
```

Optional:

```bash
python -m build
```

## Versioning

SafeClaw uses Semantic Versioning.

- **Patch**: docs, defaults wording, metadata updates.
- **Minor**: new non-breaking features (e.g., new optional tools or queue fields).
- **Major**: breaking changes to policy semantics or command behavior.

## Post-release

- Open a GitHub release and attach the tag.
- Mention security-impacting changes in the release notes.
- Keep `CHANGELOG.md` aligned with release notes.

