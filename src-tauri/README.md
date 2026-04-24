# Tauri Desktop Shell

This directory is the desktop packaging boundary for the smart opportunity crawler.

The Vue control panel is built from `../frontend` and loaded from `../frontend/dist`.
The Python backend and Agent are expected to be packaged as named sidecars:

- `opportunity-crawler-control-plane`
- `opportunity-crawler-agent`
- `opportunity-crawler-all-in-one`

Tauri sidecar binaries must use the platform target-triple suffix required by Tauri
when copied into `src-tauri/binaries`. The capability file allows only these named
sidecars with `--config <toml path>` arguments; it does not grant arbitrary shell
execution.

