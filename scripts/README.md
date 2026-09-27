# scripts/

## pre-commit

A git hook that blocks any commit whose staged content contains what looks
like a private key or a Google service-account credential — matched by
*content*, not filename, so it still catches a renamed key file (e.g.
Google's own download format `<project-id>-<key-id>.json`).

Git hooks live in `.git/hooks/` and are **not** version-controlled, so every
clone of this repo needs to install it once:

```bash
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

See `docs/refinement-plan.md` (item 1) for why this exists.
