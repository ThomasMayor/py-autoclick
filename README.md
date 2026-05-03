# py-autoclick

A Linux desktop auto-clicker with a hold mode (clicks while a mouse button is held)
and an auto mode (clicks at a configurable rate, optionally cycling through
predefined screen positions). Both modes can be triggered by global keyboard
shortcuts that work even when the app does not have focus.

Built with **tkinter + sv-ttk**, **pynput** for global input, and a clean layered
architecture (UI / services / core / persistence / i18n).

## Features

- **Hold mode** — auto-clicks while a configurable mouse button (e.g. side button 8/9, middle, right) is held down. Configurable click rate (1-200 cps), action button, and timing jitter.
- **Auto mode** — free-running clicker with configurable interval, click duration, jitter, optional click count limit, and optional position cycling.
- **Multi-position cycling** — record a list of (x, y) screen positions and have auto mode rotate through them.
- **Global hotkeys** — three configurable shortcuts (toggle auto, momentary auto, emergency stop) that work without window focus. Capture combinations interactively.
- **Internationalization** — UI in English and French, system language auto-detected on first launch, switchable at runtime.
- **Themes** — dark and light variants via [sv-ttk](https://github.com/rdbende/Sun-Valley-ttk-theme), togglable from the status bar.
- **Single instance** — second launch attempt brings the existing window to the foreground via Unix socket IPC instead of spawning a duplicate.
- **Desktop notifications** — optional `notify-send` integration for start/stop/limit/panic events.
- **Test panel** — live display of the last mouse event seen, useful for identifying side-button identifiers on a new mouse.

## Installation

### Pre-built binaries (no Python required)

Download the standalone binary for your OS from the [latest GitHub
Release](https://github.com/ThomasMayor/py-autoclick/releases/latest):

| Platform | File | Notes |
|---|---|---|
| Linux x86_64 | `pyautoclick-linux-x86_64` | `chmod +x` then double-click or run from terminal |
| Windows x86_64 | `pyautoclick-windows-x86_64.exe` | Double-click. SmartScreen may warn (binary is unsigned) — click "More info → Run anyway" |
| macOS arm64 | `pyautoclick-macos-arm64.zip` | Unzip → drag `PyAutoClick.app` into `/Applications`. First launch: right-click → Open (Gatekeeper warning is expected, the binary is unsigned) |

Linux additionally needs to grant input access if running via Wayland — see
the Wayland section below.

### From PyPI

```bash
pip install --user pyautoclick
pyautoclick
```

### Development (editable)

```bash
git clone <this repo>
cd py-autoclick
pip install --user -e .
```

This creates the `pyautoclick` console script in `~/.local/bin/`.

### Direct launch (no install)

```bash
python3 py-autoclick.pyw
```

The `.pyw` shim adds the project directory to `sys.path` so the package resolves without an install.

### Desktop launcher (GNOME / KDE / etc.)

A `.desktop` file pointing to either the installed script or the `.pyw` shim works. Example:

```ini
[Desktop Entry]
Type=Application
Name=Py-Auto-click
Exec=/home/<you>/.local/bin/pyautoclick
Icon=/path/to/py-autoclick.png
Terminal=false
StartupNotify=true
StartupWMClass=PyAutoClick
```

Place it in `~/.local/share/applications/`.

## Configuration

Settings are stored in `~/.config/autoclicker/config.json`. The file is created on first launch with sensible defaults and written every time you change a setting in the UI. Manual edits are honored on next launch.

Lock and IPC socket files live in the same directory:
- `app.lock` — fcntl exclusive lock for single-instance enforcement
- `app.sock` — Unix socket for receiving "focus" requests from second-instance attempts

## Architecture

Layered package, one-way dependencies:

```
ui  →  services  →  core  →  i18n + persistence + paths
```

| Layer | Path | Responsibility |
|---|---|---|
| `paths` | `pyautoclick/paths.py` | Filesystem locations |
| `i18n` | `pyautoclick/i18n/` | Translation tables + locale detection |
| `persistence` | `pyautoclick/persistence/` | `Settings` dataclass + JSON IO + legacy migrations |
| `core` | `pyautoclick/core/` | `AutoClicker` engine, `HotkeyManager`, single-instance lock + IPC |
| `services` | `pyautoclick/services/` | OS-side adapters (notifications) |
| `ui` | `pyautoclick/ui/` | Tk app, status bar, tabs (one class per tab), widgets |

The core layer has **zero tkinter import** and is safe to use from non-UI contexts (CLI, tests, future headless mode).

UI tabs are independent classes inheriting from `BaseTab`. The `App` orchestrator passes them an `AppContext` (typed dataclass) carrying the settings, translation function, clicker, and lifecycle callbacks.

## Requirements

- Python 3.10+
- Linux (X11 fully supported; Wayland with limitations — see below)
- `pynput`, `sv-ttk` (installed automatically via pip)
- Optional: `notify-send` (`libnotify-bin` on Debian/Ubuntu) for desktop notifications

### Platform support summary

This project was **initially developed for Linux X11**, where everything works out of the box. Support for other platforms was added incrementally and ranges from "fully working" to "fully working with one manual permission step":

| Platform | Status | Notes |
|---|---|---|
| Linux X11 | ✅ **Reference platform** | All features work, no caveats. |
| Linux Wayland | ⚠️ Partial | Global keyboard hotkeys blocked by Wayland security model. See below. |
| Windows 10 / 11 | ✅ Should work, untested by the author | All abstractions in place (msvcrt lock, TCP loopback IPC, PowerShell BurntToast notifications). Reports welcome. |
| macOS 12+ | ✅ Should work with one-time permission grant | Requires Accessibility permission for global input. See below. |

### Linux: X11 vs Wayland

On **Linux X11**: global mouse trigger, global keyboard hotkeys (toggle / momentary / panic), and live mouse-event capture in the Test tab — all work without configuration.

Under **Wayland**, the security model intentionally blocks global keyboard grabbing. The app detects the session type at startup and shows an amber warning banner in the *Shortcuts* tab. Practical consequences on Wayland:

| Feature | Status under Wayland |
|---|---|
| Hold-mode mouse trigger | Partial — works only when an X11 / XWayland window is focused |
| Global keyboard hotkeys (toggle / panic / momentary) | **Not supported** — Wayland blocks the input grab |
| Auto mode (timer-driven clicks) | Works fully — does not need event capture |
| Test tab live mouse display | Partial (XWayland windows only) |

Workarounds if you need full hotkey support:
1. **Switch to an X11 session** at the login screen (most distros offer "GNOME on Xorg" or "Plasma X11").
2. Use the in-app *Activate* checkbox on the Auto tab instead of a global shortcut.
3. (Advanced) Bind a Wayland compositor shortcut to `pyautoclick --toggle` if you script around `signal_existing_instance` — not provided out of the box.

### Windows

```powershell
# Recommended: install via pip
pip install --user pyautoclick

# Or directly from a clone
git clone https://github.com/ThomasMayor/py-autoclick
cd py-autoclick
pip install --user -e .

# Launch
pyautoclick
# or
python -Xutf8 py-autoclick.pyw
```

Windows specifics:
- **Lock & IPC** : `msvcrt.locking` for the single-instance lock, TCP loopback (`127.0.0.1:<random_port>`) instead of Unix domain socket. The chosen port is written to `%APPDATA%\autoclicker\app.port` so the second instance can find it.
- **Config location** : `%APPDATA%\autoclicker\config.json` (typically `C:\Users\<you>\AppData\Roaming\autoclicker\`).
- **Notifications** (optional) : install [BurntToast](https://github.com/Windos/BurntToast) PowerShell module for native toasts — `Install-Module -Name BurntToast -Scope CurrentUser`. Without it, notifications are silently skipped.
- **Side mouse buttons (8/9)** : pynput reports them on Windows. Use the *Test* tab to identify which event your specific mouse emits.
- **No `notify-send`** ; the cross-platform dispatcher in `services/notifications.py` falls back to PowerShell automatically.

Known untested edge cases on Windows (PRs / bug reports welcome):
- High-DPI scaling at 150 % / 200 % — Tk usually adapts via `tk.call('tk', 'scaling', ...)`, not yet wired.
- Behavior under Windows Sandbox / WSLg / Hyper-V isolation.
- Antivirus heuristics flagging `pynput` keyboard hooks (rare but reported by some users on other projects).

### macOS

```bash
# Install
pip install --user pyautoclick
# or
git clone https://github.com/ThomasMayor/py-autoclick
cd py-autoclick
pip install --user -e .

# Launch
pyautoclick
```

**Mandatory one-time setup**: macOS sandboxes input capture for security. After the first launch:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button and add the Python interpreter (or your terminal app if you're launching from a shell, or the bundled app if you packaged it).
3. **Restart the app** — pynput will not retroactively pick up the permission.

Without this step, the global hotkeys and the hold-mode trigger won't fire even though the app appears to launch normally. The Test tab is a reliable way to confirm input capture is working.

macOS specifics:
- **Lock & IPC** : standard POSIX (`fcntl.flock` + `AF_UNIX` socket).
- **Config location** : `~/.config/autoclicker/config.json` (XDG-style, the app does not currently use `~/Library/Application Support`).
- **Notifications** : delivered via `osascript display notification`. Native, no extra install.
- **Side mouse buttons** : depending on the mouse driver (Logitech Options, etc.), buttons 8/9 may be intercepted by the driver before pynput sees them. Use the *Test* tab to confirm.

Known limitations on macOS:
- Tk on macOS uses the system Tk, which can lag behind the Linux/Windows version. UI looks slightly different but functional.
- The icon at `pyautoclick/assets/py-autoclick.png` is a generic PNG, not a `.icns` bundle. For a proper Dock icon, build with `py2app` or `briefcase` (out of scope here).
- Tested only on macOS 12+ in theory; the author does not own a Mac for end-to-end validation.

## Roadmap

See the open issues and the in-repo `TODO` comments for upcoming work. Cross-platform packaging (Windows, macOS) is on the medium-term roadmap.

## About this project — a vibe-coding experiment

This project started as an experiment in **vibe-coding** — building a non-trivial application in a language the author (Thomas) does not know deeply (Python). The goal was to see how far an LLM-driven workflow could go on real, production-quality code: layered architecture, tests, i18n with RTL support, cross-platform abstractions, atomic persistence, structured logging, packaging.

The output is honest about its origin: most of the code was *generated* through dialogue, *refined* through iteration, and *validated* through automated audits — but every architectural decision was reviewed and approved by a human, and every change passed compile + smoke checks.

### Techniques used

- **Conversational pair-programming** with Claude (Anthropic) via Claude Code CLI. The author drives intent, the model drafts code, the author validates and redirects.
- **Batched, ordered edits**: each "feature batch" lists all affected files and applies them in dependency order, so no file is rewritten twice.
- **Multi-agent audits** between major refactor steps: independent specialized agents check (a) layer purity (no `tkinter` import in `core/`), (b) i18n key coverage, (c) import-graph cycles, (d) backward-compatibility of config migrations. Bugs found during audit are fixed before moving on.
- **Layered package architecture** (`ui → services → core → i18n + persistence + paths`) extracted from an initial 1300-line monolith over 6 phases, each with a checkpoint.
- **Strict typing**: `dataclass` settings with `Literal` types for languages and themes, validators that fall back to defaults instead of crashing, mypy strict mode in `pyproject.toml`.
- **Atomic persistence**: settings written via `tempfile.mkstemp` + `os.fsync` + `os.replace`, so a crash mid-write cannot corrupt the JSON config.
- **i18n as data, not code**: locales live in JSON files (one per language), parity checked automatically. RTL detection from a `_meta.direction` field; UI mirrors layout dynamically when switching from a LTR to RTL language.
- **Cross-platform abstractions**: lock + IPC use `fcntl` + `AF_UNIX` on POSIX, `msvcrt` + TCP loopback on Windows; notifications dispatch to `notify-send` / `osascript` / PowerShell BurntToast.
- **Tests where it matters most**: the single-instance lock contract is covered by 6 tests including a cross-process test that proves the lock is truly OS-level. Other test categories are listed but mostly not yet implemented — testing was prioritized for the riskiest invariant.
- **Graceful shutdown**: SIGINT / SIGTERM handlers that route through the existing window-close path (`root.after(0, app._on_close)`), so the clicker, hotkey listener, and IPC socket all clean up properly.

### Honest limitations

- **Translation quality**: 8 of the 10 languages were machine-generated (`_meta.machine_translated: true` in each JSON). Native speaker contributions welcome.
- **Plural rules**: simplified to `one`/`other` even for languages with richer rules (Russian, Arabic, Polish). Acceptable for the small string volume; would need extension for a translation-heavy app.
- **Wayland**: global keyboard hotkeys are blocked by Wayland's security model — see the Wayland section above.
- **Test coverage**: only the single-instance contract is covered. The list of tests-to-write is in the audit notes, not yet implemented.

The full conversation thread that produced this code is preserved as part of the development history — feel free to reach out if you'd like the technique walkthrough.

## License

GPLv3 (or later) — see [LICENSE](LICENSE). You may use, modify, redistribute,
and sell this software, but derivative works must remain GPLv3-compatible.
