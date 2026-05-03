# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.3] — 2026-05-03

### Fixed
- **UI: tab labels were clipped** at the right edge of the notebook with 6
  tabs (after the Settings tab landed in v0.3.1) when running in long-label
  languages (French / Italian / German). Window width bumped from 660 to
  880 (min size 820) so all 6 tab labels fit in every locale.
- **CI annotation: `actions/github-script` Node 20 deprecation** was raised
  even with `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` because the var only
  forces *runtime*, not the manifest-level annotation. Replaced
  `codecov/codecov-action@v5` (which transitively pulls
  `actions/github-script`) with a direct call to the Codecov CLI binary
  via `curl`. No JS action, no transitive dep, no annotation.

### Known issues (upstream, accepted)
- macOS runner still raises `WARNING: Cache entry deserialization failed,
  entry ignored`. The warning comes from `actions/setup-python@v6`'s
  *internal* manifest cache (not the pip cache we already disabled), which
  has no public toggle. Job remains green; the warning is cosmetic. Will
  self-resolve when `setup-python` ships a fix.

## [0.3.2] — 2026-05-03

> Committed to main but never tagged / published to PyPI. Content shipped
> via 0.3.3.

### Changed
- **CI: `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`** at workflow level —
  forces every action including transitive dependencies (e.g.
  `actions/github-script` pulled in by `codecov-action`) to run under
  Node 24. Catches Node-20 deprecation leaks even when our top-level
  action pins are correct.
- **CI: pip cache disabled on macOS** — the cache action's
  deserialization fails sporadically on macOS runners and triggers a
  failure-level annotation even when the job itself succeeds. Linux and
  Windows still benefit from the cache.

## [0.3.1] — 2026-05-03

> Committed to main but never tagged / published to PyPI. Content shipped
> via 0.3.2.

### Added
- **Settings tab** — new dedicated tab grouping app-wide preferences
  (language, system notifications toggle). Designed to grow as new
  preferences are added.
- New translation key `tab_settings` in all 11 locales.
- Fixed: `pyautoclick.__version__` was stuck at `0.2.0` while the package
  metadata read `0.3.0`; both now read consistently.

### Changed
- **Shortcuts tab** is now focused on its single responsibility: the three
  global hotkeys + the platform caveat banner + the invalid-combo error
  label. The notification toggle and the language picker moved to the new
  Settings tab.
- **CI: GitHub Actions bumped** to Node 24-compatible versions:
  `actions/checkout@v5`, `actions/setup-python@v6`, `codecov/codecov-action@v5`.
  Node 20 is being removed from runners on 2026-09-16.
- **CI: Codecov upload no longer double-bypassed.** Removed the redundant
  `continue-on-error: true` (kept `fail_ci_if_error: false` to tolerate
  Codecov outages, gated the step on `coverage.xml` existing). A real
  workflow misconfiguration is no longer silently swallowed.

## [0.3.0] — 2026-05-03

### Added
- **Internationalization** with 10 languages: English, French, Spanish, Portuguese, German, Italian, Russian, Chinese, Japanese, Arabic. JSON locale files, ICU-style plurals (`{n, plural, one {…} other {…}}`), locale-aware number formatting.
- **Right-to-left (RTL) layout support**: Arabic UI mirrors automatically (label/control columns swap, status bar mirrors). Detection via `_meta.direction` in locale JSON.
- **Theme switcher** in the status bar (☀ / ☾ glyph), persisted to config.
- **Cross-platform foundation**: `single_instance` abstracts POSIX (`fcntl` + `AF_UNIX`) vs Windows (`msvcrt` + TCP loopback). Notifications dispatch to `notify-send` / `osascript` / PowerShell BurntToast.
- **Wayland detection** via `core/platform_capabilities.py`: amber warning banner in the *Shortcuts* tab when global hotkeys are unavailable.
- **Atomic config save** via `tempfile.mkstemp` + `os.fsync` + `os.replace` — crash mid-write cannot corrupt JSON.
- **Settings validation** with field-level validators; invalid values fall back to defaults (logged as warnings) instead of crashing.
- **Schema versioning** (`config_version`) with extensible migration registry.
- **Structured logging** to stderr + rotating file (`~/.config/autoclicker/pyautoclick.log`, 1 MiB × 3). Level via `PYAUTOCLICK_LOG_LEVEL` env var.
- **Signal handling**: SIGINT and SIGTERM trigger a graceful shutdown via the existing window-close path.
- **`AppContext` split** into 3 typed sub-contexts (`StateContext`, `ServicesContext`, `LifecycleContext`).
- **`BaseTab(ABC)`** for tab subclasses with `@abstractmethod build()`.
- **Tests**: 6 single-instance tests including a cross-process verification.
- **Tooling config** in `pyproject.toml`: ruff (9 rule sets), mypy strict, pytest + coverage.
- **Hot-reload of UI** on language change (preserves clicker, hotkey listener, settings).
- **Single instance focus**: launching a second instance brings the existing window to the foreground via Unix socket IPC instead of failing.
- **Sun Valley theme** (`sv-ttk`) integration.
- **Position cycling** for auto mode: record (x, y) screen positions, cycle through them.
- **Click jitter** (± ms) on both modes for human-like irregularity.
- **Click count limit** for auto mode.
- **Hotkey momentary mode**: auto mode runs while a combination is held.
- **Emergency stop hotkey**.
- **Mouse-event test panel** for identifying side buttons.

### Changed
- **Refactored from a single 1300-line `.pyw` file into a layered package** (`pyautoclick/`) with 7 sub-modules (`core`, `persistence`, `i18n`, `services`, `ui`, plus `paths` and `logging_config`).
- **Settings storage** moved from raw dict to dataclass with `Literal` types.
- **`TRIGGERS` / `ACTIONS`** dicts split into language-agnostic stable keys (`"button8"`, `"left"`) + i18n-driven labels. Legacy French labels in old configs are migrated transparently.
- **Strict typing** throughout, `from __future__ import annotations` standardized in every module.
- **License**: GPLv3 (was unlicensed).
- **Constants and colors** centralized in `pyautoclick/ui/constants.py` and `pyautoclick/ui/colors.py`.
- **Icon redesigned** for visual modernization (gradient + ripple animation feel + cursor at click center).

### Fixed
- **`mouse.Listener` cleanup** at shutdown (previously orphaned the listener thread).
- **Race conditions** in `AutoClicker`: explicit `RLock` on all setters, snapshots in loops.

### Security
- Replaced broad `except Exception:` with specific exception types except for documented user-callback wrappers (which log via `logger.exception`).

## [0.2.0] — 2026-05-02

Initial layered architecture extracted from the monolithic `.pyw` script.

## [0.1.0] — initial

Single-file `py-autoclick.pyw` with hold-mode + auto-mode + 3 hotkeys + positions + i18n FR/EN.
