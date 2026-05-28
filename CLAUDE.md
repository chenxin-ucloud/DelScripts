# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run in development mode:**
```bash
cd gui && python3 main.py
```

**Build macOS .app (Apple Silicon only):**
```bash
./build.sh
# Output: dist/UCloudCleaner.app
```

**Run the built app:**
```bash
open dist/UCloudCleaner.app
```

No test suite or linter is configured.

## Architecture

The project is a macOS GUI tool (`UCloudCleaner.app`) that wraps a UCloud API cleanup script. It has two layers:

### `sdk/delete_all_resources.py`
The core deletion engine. Can run standalone via CLI or be imported by the GUI. Key points:
- `get_client(region, project_id, public_key, private_key, base_url=None)` — constructs the UCloud `Client`; `base_url` is only set for the test environment (`http://api-test03.ucloudadmin.com`)
- `DELETE_OPERATIONS` — module-level list of `(resource_name, delete_func)` tuples; the GUI filters this list based on user selection
- `logger` has **no handlers at module level** — the GUI attaches a `QueueHandler`; CLI callers call `setup_file_logging()`
- Deletion order matters: UHost → UDisk (15-second wait after UHost to let disks detach) → NATGW → ... → VPC
- `PROJECTS_CONFIG` at module level contains hardcoded test credentials; the GUI overrides these via `get_client()` arguments

### `gui/` — tkinter GUI
Entry point is `gui/main.py` → `gui/app.py` (`App(tk.Tk)`).

**State flow:** `AppState` (dataclass in `core/state.py`) is the single source of truth. Tabs read from it on startup and write back via `get_values()` before running.

**Tab structure:**
- `ConfigTab` — API environment dropdown (正式环境 / 测试环境), public key, private key, project IDs. Environment selection fires callbacks that tell `ResourceTab` which region file to load.
- `ResourceTab` — Region checkboxes (multi-column grid; Canvas+scroll only for >56 regions) + resource type checkboxes. Region file: `assets/region.json` (production, 25 regions) or `assets/region_test.json` (test, 2 regions).
- `LogTab` — Launches `run_deletion()` in a background thread. Uses `queue.Queue` + `tk.after()` polling (100ms) to safely push log lines to the UI. Tracks `_poll_id` to avoid duplicate polling loops.

**Thread-safety pattern:** `runner.run_deletion()` runs in a daemon thread. It writes to `log_queue`; `LogTab._poll()` drains the queue on the main thread. `on_done()` is called inside a `try/finally` to guarantee UI reset even on exceptions, routed back to main thread via `self.after(0, self._finish)`.

**Environment → region file mapping** happens in two places (must stay in sync):
1. `app.py` `_on_env_changed` callback — triggers `resource_tab.load_regions()`
2. `runner.py` `run_deletion()` — uses `state.env_name` to pick the region file for actual deletion

**Config persistence:** `core/config_store.py` saves to `~/.ucloud_cleaner/config.json`. `private_key` is in `SENSITIVE_FIELDS` and **must never be written to disk**. Config is saved on "开始清理" and on window close; loaded on startup.

### `gui/assets/`
- `region.json` — production regions, format: `{"区域名": {"Region": "cn-bj2", "Zone": "cn-bj2-02"}}`
- `region_test.json` — test regions (same format)

To add/remove regions, edit only these JSON files. The CLI (`sdk/delete_all_resources.py`) also reads from `../gui/assets/region.json`.

### PyInstaller packaging
`UCloudCleaner.spec` bundles:
- `gui/assets/region.json` → `assets/region.json` (in bundle)
- `gui/assets/region_test.json` → `assets/region_test.json`
- `sdk/delete_all_resources.py` → `sdk/delete_all_resources.py`

Both `_get_assets_dir()` (in tabs) and `_resolve_sdk_path()` / `_resolve_assets_path()` (in runner) check `sys.frozen` to switch between dev and bundle paths. Any new bundled file must be added to `datas` in the spec.

Target: Apple Silicon Mac, macOS 11.0+.
