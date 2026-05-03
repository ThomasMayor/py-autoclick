# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
