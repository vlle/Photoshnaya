# Changelog

## 2026-02-22

### Changed
- Migrated Python dependency management from `requirements.txt` to `uv` using `pyproject.toml` and `uv.lock`.
- Split container builds into `Dockerfile.prod` and `Dockerfile.dev` for production vs development/testing workflows.
- Updated compose files to use explicit Dockerfiles and local builds.
- Updated CI to Python 3.11 and uv-based dependency syncing.
- Added a Makefile with one-command local/dev/test operations.

### Why
- Reproducible dependency resolution with a checked-in lockfile.
- Better Docker layer caching by installing dependencies before application code.
- Clear separation between production runtime dependencies and dev/test tooling.

### Tradeoffs
- `requirements.txt` is temporarily retained for compatibility and now marked deprecated.
- Dev/test images include extra tools, which increases image size compared to production.
