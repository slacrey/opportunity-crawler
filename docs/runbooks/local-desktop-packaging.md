# Local Desktop Packaging

## Purpose

The desktop package loads the Vue control panel as static assets and runs the Python
control plane and collection Agent as Tauri sidecar binaries.

## Build Inputs

- Frontend static assets: `frontend/dist`
- Default configs: `packaging/defaults/*.toml`
- Database migrations: `migrations/versions`
- PyInstaller specs: `packaging/pyinstaller/*.spec`
- Tauri config: `src-tauri/tauri.conf.json`
- Tauri sidecar capabilities: `src-tauri/capabilities/default.json`

## Python Sidecars

Build the sidecar candidates with PyInstaller specs:

```bash
pyinstaller packaging/pyinstaller/control_plane.spec
pyinstaller packaging/pyinstaller/agent.spec
pyinstaller packaging/pyinstaller/all_in_one.spec
```

The sidecar names are:

- `opportunity-crawler-control-plane`
- `opportunity-crawler-agent`
- `opportunity-crawler-all-in-one`

When copying sidecars into `src-tauri/binaries`, apply the target-triple suffix that
Tauri expects for the current platform. A missing or mismatched target-triple name
should be treated as a packaging error before release.

## Data Directories

Packaged configs must keep runtime data outside the application bundle:

- database: `shared.database_path`
- logs: `shared.log_dir`
- temp files: `shared.tmp_dir`
- evidence files: `shared.evidence_dir`
- screenshots: `shared.screenshots_dir`
- browser profiles: `shared.browser_profiles_dir`

## Security Contract

The Tauri capability grants only `shell:allow-execute` for the named sidecars and
only with `--config <toml path>` arguments. Do not add broad shell, open, or wildcard
permissions for production packaging.

## Startup Checks

Before packaging release, verify:

- Vue static build exists in `frontend/dist`.
- Control plane health endpoint reports database and migrations ready.
- Agent can register with the control plane WebSocket.
- Browser runtime dependencies are available on the target machine.
- Sidecar names match the target platform naming convention.
