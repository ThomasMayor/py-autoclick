# CLAUDE.md — py-autoclick engineering rules

This file is loaded automatically by Claude Code at session start. It captures
the **non-negotiable rules** and the **specific pitfalls** discovered while
building this codebase. Follow it strictly — these are not preferences,
they are mandatory operating procedures distilled from real bugs.

The bar is **CAC 40 enterprise quality**: every rule below was added because
violating it caused a production-grade incident (CI red, lost user data,
silent fallback, broken cross-platform support, etc.).

---

## 1. Hard rules — never violate

### 1.1 Never commit when local tests are not 100% green

Before any `git commit`, you MUST run the full suite **in every environment
combination CI will run**, and observe each run green. The mistake to never
make again: testing in only one mode locally and assuming the others "are
the same".

Mandatory commands (in order):

```bash
# (a) Headless mode — real pynput unavailable, conftest fakes it
DISPLAY= python3 -m pytest tests/ -q

# (b) Display mode — real pynput available; conftest still forces the fake
#     for determinism, BUT we also verify the imports don't crash with a
#     real backend loaded
python3 -m pytest tests/ -q

# (c) Optional integration mode — opt-in to the real pynput
PYAUTOCLICK_TESTS_REAL_PYNPUT=1 python3 -m pytest tests/ -q -k "smoke"
```

If `(a)` and `(b)` are not BOTH green, do not push. **No exceptions.**

Pushing red CI for the team to see is a CAC 40-grade quality offense.

### 1.1.1 The "DISPLAY trap" — why this rule exists

Pynput's behavior changes drastically based on what's loaded at import time:

| Local DISPLAY | What loads | What `HotKey.parse("a")` returns |
|---|---|---|
| unset (`DISPLAY=`) | **Fake** pynput (conftest fallback) | `["a"]` (string list) |
| set (`DISPLAY=:0`) | **Real** pynput xorg backend | `frozenset({KeyCode("a")})` |
| CI under `xvfb-run` | **Real** pynput xorg backend | `frozenset({KeyCode("a")})` |

A test that pushes string keys (`hm._on_press("a")`) and asserts the
callback fires will work with the **fake** but silently fail with the
**real** pynput, because `frozenset({KeyCode("a")}).issubset({"a"})` is
`False` (different hash).

Our defense: `tests/conftest.py` **always** installs the fake (unless
`PYAUTOCLICK_TESTS_REAL_PYNPUT=1`). This guarantees test determinism. But
it also means a developer must verify with the real pynput at least once
(mode `b` above) to catch incompatibilities — typically import-time crashes
on platforms without input devices.

### 1.2 Never import `pynput` at module load time outside `core/clicker.py` and `ui/`

`pynput`'s xorg backend tries to acquire an X display **at import time**. On
headless CI (or any container without `Xvfb`), `from pynput.mouse import Button`
raises `ImportError: failed to acquire X connection`.

The fix already in place: `pyautoclick/core/buttons.py` exposes button maps
through a `_ButtonMap` lazy proxy that only imports `pynput` on first
`__getitem__`. **Do not introduce new top-level `pynput` imports in
`core/`, `persistence/`, `i18n/`, or `services/`.**

If you add a helper that depends on `pynput`, decide:
- It's a runtime engine path → put it in `core/clicker.py` (already imports pynput).
- It's a pure helper → put it in `core/timing.py` or a new no-pynput module.
- It's a button mapping → extend `_ButtonMap` in `core/buttons.py`.

### 1.3 Never use bare `except Exception:`

Two acceptable forms only:

```python
# Form A — narrow exception with logging
try:
    risky_op()
except (OSError, ValueError):
    logger.exception("risky_op failed")

# Form B — wrap a user callback that must not crash the listener thread
try:
    user_callback()
except Exception:    # never let a UI callback kill the listener
    logger.exception("user callback raised")
```

Form B requires the **inline comment** explaining why. Without it, a code
reviewer will mark it as a smell.

### 1.4 Never block the Tk main thread from a worker thread

Always marshal back via `root.after(0, lambda: ...)`. Direct `Tk` widget
modification from `pynput.Listener` callbacks or `AutoClicker` loops is a
race condition waiting to happen. The pattern is enforced in
`AutoClicker.on_button_seen` and `__main__._signal_handler`.

### 1.5 Never write to user-controlled config files non-atomically

`Settings.save()` uses `tempfile.mkstemp` + `os.fsync` + `os.replace` so a
crash mid-write cannot corrupt `config.json`. Any new persistence path
must follow the same pattern. A truncated file will silently revert the
user's preferences.

### 1.6 Never run risky Git or remote operations on behalf of the user

This project follows the global rules in `~/.claude/CLAUDE.md`:
- No `git init`, `git add`, `git commit`, `git push`, `git tag`.
- No `gh` write commands (PR create/merge, issue comment, release).
- No `pip install` to user environment without consent.
- No PyPI uploads.

Always **propose the exact command in chat**; let the user run it.

---

## 2. General Python engineering rules (template — applies to any modern Python project)

This section is intentionally **project-agnostic** — copy it as-is into the
`CLAUDE.md` of a new project. It distills enterprise Python practices used
in CAC 40 / FAANG codebases.

### 2.1 Type system

**Rule**: every public function and class attribute is fully typed. Run
`mypy --strict` in CI. Use `from __future__ import annotations` at the top
of every module.

```python
# Bad
def fetch(url, timeout=10):
    ...

# Good
def fetch(url: str, *, timeout: float = 10.0) -> Response:
    ...
```

Use `typing.Literal`, `typing.Final`, `typing.Protocol`, `typing.NewType`
liberally. They cost nothing at runtime and lock invariants.

```python
# Discriminate string types that look identical
UserId = NewType("UserId", str)
ProductId = NewType("ProductId", str)

def get_orders(user: UserId) -> list[Order]: ...

# Caller mistake caught by mypy:
get_orders(some_product_id)  # type error
```

### 2.2 Naming conventions (PEP 8 + project conventions)

| Kind | Convention | Example |
|---|---|---|
| Module | `snake_case` | `single_instance.py` |
| Class | `PascalCase` | `AutoClicker`, `Settings` |
| Function / variable | `snake_case` | `set_cps()`, `click_count` |
| Constant | `UPPER_SNAKE` | `CONFIG_FILE`, `MAX_RETRIES` |
| Private | leading `_` | `_resolve_plural()` |
| Type alias | `PascalCase` | `Position`, `LanguageCode` |
| Test function | `test_<unit>_<scenario>_<expected>` | `test_load_rejects_unknown_trigger` |

### 2.3 Docstrings

Every public class and function has a docstring. Module-level docstrings
explain the module's *role* in the system. Style: Google or NumPy — pick
one and stay consistent.

```python
def jittered(value_ms: float, jitter_ms: float) -> float:
    """Return ``value_ms`` plus a uniform jitter in ``[-jitter_ms, +jitter_ms]``.

    Always clamped to a non-negative value (a negative sleep would raise).
    When ``jitter_ms <= 0`` the function is the identity (modulo the floor).
    """
    ...
```

Don't restate WHAT the code does (the type signature already does). Explain
WHY: invariants, edge cases, justifications for non-obvious choices.

### 2.4 Pure functions over methods with side effects

Prefer functions that take their inputs as arguments and return new values
over methods that mutate hidden state.

```python
# Bad — mutation by side effect, hard to test
class Cart:
    def add(self, item): self.items.append(item)
    def total(self): return sum(i.price for i in self.items)

# Better — separates state from logic
def total(items: Iterable[Item]) -> Decimal:
    return sum(i.price for i in items)
```

When mutation is needed (engines, caches), encapsulate it behind a class
with explicit setters and a `RLock`/`Lock` if cross-thread.

### 2.5 Dataclasses for data, classes for behavior

```python
# Pure data: dataclass (or attrs / pydantic for richer needs)
@dataclass(frozen=True)
class Point:
    x: int
    y: int

# Behavior + state: regular class
class Cache:
    def __init__(self, max_size: int) -> None: ...
    def get(self, key: str) -> Value | None: ...
```

Use `frozen=True` whenever the data is logically immutable — catches bugs
where someone mutates a "constant".

### 2.6 Resource management with context managers

Files, sockets, locks, subprocess pipes, database connections — never use
the bare `open()` / `acquire()` / `connect()` form. Use `with` or
`contextlib.contextmanager`:

```python
# Bad
f = open(path)
data = f.read()
f.close()  # not run if read() raises

# Good
with open(path) as f:
    data = f.read()

# For your own resources
@contextmanager
def acquired_lock(lock: Lock):
    lock.acquire()
    try:
        yield
    finally:
        lock.release()
```

The exception is when a resource must outlive the function scope (e.g. an
`fcntl.flock` held for the lifetime of the process — see
`acquire_single_instance_lock` in this codebase).

### 2.7 Exception handling

| Pattern | When |
|---|---|
| Specific `except (TypeA, TypeB):` | Default. Catch only what you can handle. |
| `except Exception:` with `logger.exception()` | Only at thread boundaries (callbacks, listeners) |
| `try/except/raise from` | Re-raise with context preserved |
| `contextlib.suppress(SomeError)` | When ignoring is the correct semantic |

```python
# Bad
try:
    parse(data)
except:        # bare except — catches KeyboardInterrupt, SystemExit too
    pass

# Bad
try:
    parse(data)
except Exception:    # too broad, no log
    return None

# Good
try:
    return parse(data)
except (ValueError, TypeError) as exc:
    logger.warning("parse failed for %r: %s", data, exc)
    return None

# Re-raise with chained context
try:
    fetch(url)
except OSError as exc:
    raise FetchError(f"could not fetch {url}") from exc
```

### 2.8 Logging, never `print()`

```python
# Bad
print(f"Error: {exc}")

# Good
import logging
logger = logging.getLogger(__name__)
logger.error("operation failed: %s", exc, exc_info=True)
```

Configure logging once at the application entry point (see
`pyautoclick/logging_config.py`). Use lazy `%s` formatting — the string is
only built if the level is enabled.

Levels:
- `DEBUG` — developer details
- `INFO` — lifecycle (startup, shutdown, config reload)
- `WARNING` — recoverable issues, fallbacks taken
- `ERROR` — operation failed but app continues
- `CRITICAL` — app cannot continue

### 2.9 Pathlib over `os.path`

```python
# Bad
import os
path = os.path.join(os.path.expanduser("~"), ".config", "app", "config.json")
if os.path.exists(path):
    with open(path) as f: ...

# Good
from pathlib import Path
path = Path.home() / ".config" / "app" / "config.json"
if path.exists():
    with path.open() as f: ...
```

`pathlib.Path` is cross-platform, immutable, and has clean methods for all
common operations.

### 2.10 f-strings over `%` and `.format()`

```python
# Acceptable in user-facing translations only (must support reorderable args)
"User {name} has {n} clicks".format(name=u, n=c)

# Preferred everywhere else
f"User {u.name} has {c} clicks"

# In logging — keep `%s` for lazy evaluation
logger.info("User %s has %d clicks", u.name, c)
```

### 2.11 No mutable default arguments

```python
# Bad — the same list is shared across all calls
def append_to(item, target=[]):
    target.append(item)
    return target

# Good
def append_to(item, target: list | None = None) -> list:
    if target is None:
        target = []
    target.append(item)
    return target

# Or with dataclasses
@dataclass
class Thing:
    items: list = field(default_factory=list)
```

### 2.12 Enums for fixed sets

```python
# Bad — string typo will not be caught
def set_status(status: str): ...
set_status("activ")   # silent bug

# Good
from enum import Enum
class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

def set_status(status: Status): ...
set_status(Status.ACTIVE)
```

`Literal["active", "inactive"]` is also acceptable when an enum feels heavy.

### 2.13 Composition over inheritance

Inheritance ties subclasses to the parent's implementation, not just its
interface. Prefer:
- Composition (hold the dependency as an attribute)
- Protocols (`typing.Protocol`) for duck-typed interfaces
- `dataclass` mixins for data, abstract base classes for contracts

Inheritance is appropriate for true "is-a" relationships (`HoldTab` IS-A
`BaseTab` IS-A `ttk.Frame`).

### 2.14 Concurrency: pick one model and stay with it

| Model | Use when |
|---|---|
| `threading` | Blocking I/O, GIL-bound, mixing with sync libraries (this project) |
| `asyncio` | High-concurrency I/O, network servers, modern web stacks |
| `multiprocessing` | CPU-bound parallelism, isolation needed |

**Never mix asyncio and threading carelessly.** If you must, use
`asyncio.to_thread()` or `loop.run_in_executor()`.

When using `threading`:
- Always shutdown threads explicitly (no daemon-only patterns for shutdown order)
- Use `threading.Event` for signaling, `threading.RLock` for reentrant locks
- Snapshot mutable state at the start of a loop iteration (don't read it again under lock for every use)

### 2.15 Dependency management

- Pin both lower and upper bounds: `pynput>=1.7,<2`. Never `pynput` alone
  (uncontrolled upgrade) and never `pynput==1.7.6` (no security patches).
- Separate runtime vs dev dependencies. Use `[project.optional-dependencies]` in `pyproject.toml`.
- Lock file (`pip-tools`, `poetry.lock`, `uv.lock`) for reproducible installs in CI/prod.
- Run `pip-audit` or `safety` periodically to detect known CVEs.

### 2.16 SemVer + CHANGELOG

- Version strings follow `MAJOR.MINOR.PATCH` ([semver.org](https://semver.org/)).
- Every user-facing change goes in `CHANGELOG.md` under `## [Unreleased]`,
  using [Keep a Changelog](https://keepachangelog.com/) format.
- Tag releases with `git tag vX.Y.Z`; CI publishes from tags.

### 2.17 Testing pyramid

```
        /\
       /e2\        <- few, slow, expensive (UI smoke, packaged install test)
      /----\
     / int. \      <- some, moderate (cross-module, with real subprocesses)
    /--------\
   /   unit   \   <- many, fast, isolated (pure functions, mocked I/O)
  /____________\
```

- 70-80% unit tests
- 15-25% integration tests
- 5% end-to-end tests

Mark them: `@pytest.mark.unit` (default), `@pytest.mark.integration`,
`@pytest.mark.e2e`. CI runs unit always, integration on PRs, e2e nightly.

### 2.18 Test structure: AAA (Arrange-Act-Assert)

```python
def test_settings_save_then_load_is_identity(tmp_config_dir):
    # Arrange
    s = Settings.load()
    s.cps = 33
    s.theme = "light"

    # Act
    s.save()
    reloaded = Settings.load()

    # Assert
    assert reloaded == s, "roundtrip lost data"
```

A test that mixes arrange/act/assert in interleaved fashion is hard to
review. Use blank lines to separate the three phases.

### 2.19 Property-based testing for parsers and validators

When testing a function that processes structured input, complement
example-based tests with [Hypothesis](https://hypothesis.readthedocs.io/):

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_t_never_raises_on_arbitrary_key(key):
    """t() must never crash on any string key — fallback to raw key."""
    result = t(key, "fr")
    assert isinstance(result, str)
```

Hypothesis finds edge cases human imagination misses (empty string,
huge string, mixed scripts, surrogate pairs).

### 2.20 Avoid global mutable state

```python
# Bad — global mutable state
CACHE = {}
def get(key):
    if key not in CACHE: CACHE[key] = expensive(key)
    return CACHE[key]

# Better — encapsulate in a class with explicit lifecycle
class Cache:
    def __init__(self): self._store = {}
    def get(self, key): ...

# Acceptable — module-level singleton with explicit reset for tests
_TABLES: dict | None = None
def reset_cache() -> None:
    global _TABLES
    _TABLES = None
```

The third form is what `pyautoclick/i18n/core.py` uses. The `reset_cache()`
function is mandatory for testability — without it, tests pollute each
other.

### 2.21 "Functional core, imperative shell"

Push side effects to the **edges** of your application:

```
┌─────────────────────────────────────────────┐
│  Imperative shell (UI, IO, network, time)   │  ← handles side effects
│  ┌───────────────────────────────────────┐  │
│  │   Functional core (pure logic)        │  │  ← takes inputs, returns outputs
│  │   - data transformations              │  │
│  │   - validation                        │  │
│  │   - calculations                      │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

The pure core is trivial to test (no mocks needed). The shell is small
enough to test with a few integration tests.

`pyautoclick/core/timing.py` is pure (no I/O). `pyautoclick/core/clicker.py`
is the shell (threads, mouse listener, controller).

### 2.22 Avoid premature optimization, profile first

```python
# Don't write
result = sum(map(lambda x: x ** 2, large_list))   # "faster than for loop"

# Until you've measured. The for loop is often faster in CPython:
total = 0
for x in large_list:
    total += x ** 2

# When you do optimize, profile:
import cProfile
cProfile.run("expensive_call()")
```

Use `timeit`, `cProfile`, `py-spy`, or `scalene` before optimizing. Most
performance "fixes" without a profile make the code slower or unreadable.

### 2.23 Imports order (enforced by `ruff` / `isort`)

```python
"""Module docstring."""

from __future__ import annotations

# 1. Standard library
import json
import logging
from pathlib import Path

# 2. Third-party
import pytest
from pynput import mouse

# 3. First-party (this project)
from pyautoclick.core.timing import jittered
from pyautoclick.persistence.settings import Settings
```

Each group separated by a blank line, alphabetical inside the group.

### 2.24 Avoid `if __name__ == "__main__":` for anything but the entry point

CLI wrappers, debug snippets, demo code — these don't belong inside a
library module. They make the module heavier to import and obscure the
real API. Keep them in dedicated `__main__.py` or `examples/` files.

### 2.25 Configuration via dataclass, not module-level globals

```python
# Bad
CACHE_SIZE = 100
TIMEOUT = 30
def fetch(url): use(CACHE_SIZE, TIMEOUT)

# Good
@dataclass(frozen=True)
class Config:
    cache_size: int = 100
    timeout: float = 30.0

def fetch(url: str, config: Config): ...
```

The dataclass version is testable (pass a Config with custom values),
documented (one place to see all options), and validatable.

---

## 3. Architecture invariants

### 2.1 Layer dependency direction (one-way only)

```
ui  →  services  →  core  →  i18n + persistence + paths + logging_config
```

A layer may import from layers to its right but never to its left.
**Verify before merging**: a quick `grep -rn "from pyautoclick.ui" pyautoclick/core pyautoclick/persistence pyautoclick/i18n pyautoclick/services` must return zero results.

### 2.2 No `tkinter` import in `core/`, `persistence/`, `i18n/`, `services/`

These layers must remain UI-agnostic so they're testable headless and
reusable from a future CLI / daemon mode.

### 2.3 Each tab is a `BaseTab` subclass

`pyautoclick/ui/tabs/base.py` is an `abc.ABC` with `@abstractmethod build()`.
A new tab must inherit, declare `title_key`, and implement `build()`. It
must use the RTL helpers (`self.col(0)`, `self.col(1)`, `self.side("left")`,
`self.sticky_label`) instead of hardcoding `column=0`/`column=1` and
`sticky="w"`/`sticky="e"`. RTL languages mirror the layout dynamically;
hardcoded directions break Arabic/Hebrew users.

### 2.4 Settings is the source of truth

UI controls write to `Settings`, not directly to `AutoClicker`:

```python
# Correct
self.settings.cps = v
self.clicker.set_cps(v)
self.commit()

# Wrong — Settings would not reflect the change, persistence breaks
self.clicker.set_cps(v)
```

When a user-typed value is invalid, the fallback comes from `Settings`,
not from the clicker's internal state.

---

## 4. Tests requirements (CAC 40 standard)

### 3.1 Headless by default

Every test runs without `DISPLAY`. If a new test imports a module that
loads `pynput`, either:
- Add a `pytest.mark.linux_only` marker AND ensure there's a non-marked
  alternative covering the same logic via mocks.
- Refactor the production code so the import is lazy (preferred).

### 3.2 Coverage gate

Target: **80 %+ on `core/`, `persistence/`, `i18n/`, `services/`**. UI
modules are excluded (require Tk). When adding a new module to those
folders, add corresponding tests in the same PR.

### 3.3 No `time.sleep()` in tests

`time.sleep` is the #1 cause of flaky tests. Use `threading.Event` to
synchronize between threads or processes:

```python
# Bad — race condition under CI load
p = multiprocessing.Process(target=child)
p.start()
time.sleep(0.1)
assert ...

# Good
ready = multiprocessing.Event()
p = multiprocessing.Process(target=child, args=(ready,))
p.start()
assert ready.wait(timeout=5), "child failed to signal ready"
assert ...
```

### 3.4 Every assertion has a message

```python
# Bad
assert s.cps == 15

# Good
assert s.cps == 15, "default cps must be 15"
```

The message is what the failure log shows; without it, debugging requires
a checkout + local reproduction.

### 3.5 Tests are organized by module under test

Mirror the source tree:

```
tests/persistence/test_settings.py     ←→ pyautoclick/persistence/settings.py
tests/i18n/test_translation.py         ←→ pyautoclick/i18n/core.py
tests/core/single_instance/test_lock.py ←→ pyautoclick/core/single_instance.py
tests/test_smoke.py                     ←→ cross-cutting smoke tests
```

**No `__init__.py` in `tests/` subdirectories** — they break
`pytest-xdist` partitioning and conflict with rootdir-based discovery.

### 3.6 Markers must match `pyproject.toml`

Currently registered: `linux_only`, `integration`. Adding a new marker
requires a line in `[tool.pytest.ini_options].markers` (we use
`--strict-markers` so unknown markers fail collection).

### 3.7 Edge cases to always cover for input-handling code

1. None / empty input
2. Type mismatch (str where int expected, list where dict expected)
3. Unhashable input (list / dict where a key is expected — see `_safe_lookup`)
4. Out-of-range numeric (negative, zero, max + 1)
5. Unicode (RTL strings, emoji, combining characters)
6. Malicious input (path traversal, code injection in JSON)

Every PR adding a new validator or parser must add tests for these 6
families.

### 3.8 Mock at the boundary, not within the unit

Mock `subprocess.Popen`, `socket.socket`, `os.environ` — never mock our
own internal functions. If a test requires mocking an internal helper,
the production code is too coupled and needs refactoring.

---

## 5. Pre-commit checklist

Run **all of these** locally before any push:

- [ ] `ruff check pyautoclick tests` → no errors
- [ ] `ruff format --check pyautoclick tests` → no diff
- [ ] `mypy pyautoclick` → `Success: no issues found`
- [ ] **`DISPLAY= python3 -m pytest tests/ -q`** → all green (headless mode)
- [ ] **`python3 -m pytest tests/ -q`** → all green (display mode — catches
  fake/real divergence, see §1.1)
- [ ] `find pyautoclick -name '*.py' -exec python3 -m py_compile {} +` → no SyntaxError
- [ ] `CHANGELOG.md` updated under `## [Unreleased]` if user-visible change
- [ ] If a new translation key was added, all 11 locales contain it
  (`tests/test_smoke.py::test_locale_key_parity_with_english` enforces this)
- [ ] If a new language was added: `LANGUAGES`, `LANG_LABELS`, and the
  `LanguageCode` `Literal` in `persistence/settings.py` are all updated
- [ ] If a new platform-specific path was added, both POSIX and Windows
  branches in `core/single_instance.py` and `services/notifications.py`
  handle it
- [ ] If a new exception type was added, no broad `except Exception:`
  swallowing it without `logger.exception()`

---

## 6. Pitfalls catalogue (what bit us, how to avoid)

### Pitfall #1 — pynput requires DISPLAY at import time

**Symptom**: tests pass locally with X11 but fail with
`ImportError: failed to acquire X connection` on CI.

**Cause**: `from pynput.mouse import Button` at the top of
`core/buttons.py` triggered `pynput/__init__.py` which loaded the xorg
backend, which tried to open `:0` and failed.

**Fix**: `_ButtonMap` lazy proxy in `core/buttons.py` defers the import
to the first `__getitem__` call. Pure helpers like `jittered()` live in
`core/timing.py` (no pynput).

**Prevention**: when adding code in `core/`/`persistence/`/`i18n/`, run
`DISPLAY= python3 -c "from <new_module> import *"` to verify
import-time independence from pynput.

### Pitfall #2 — `LanguageCode` Literal out of sync with `LANGUAGES`

**Symptom**: a perfectly valid config with `language="es"` is silently
reset to None on load.

**Cause**: `Literal["en", "fr"]` was hardcoded in `settings.py` and
forgotten when 9 new languages were added to `i18n.core.LANGUAGES`.

**Fix**: `LanguageCode = Literal["en", "fr", "es", "pt", ...]` now lists
all 11. The validator in `_validate("language", ...)` reads from this
single source.

**Prevention**: whenever you add `"<code>"` to `LANGUAGES`, immediately
add it to the `LanguageCode` `Literal`. Add a test to
`tests/i18n/test_translation.py` that asserts the language is accepted
by `Settings.load`.

### Pitfall #3 — Migration ordering: legacy values lost

**Symptom**: a v0 config with `"action": "Clic droit"` (French label)
loads with `action == "left"` (default) instead of `action == "right"`
(the migrated value).

**Cause**: `_assign_validated` rejected the unknown value before
`migrate_legacy(s)` had a chance to map it.

**Fix**: introduced `migrate_legacy_data(raw_dict)` that runs **before**
field-by-field validation. The post-validation `migrate_legacy(s)`
remains as a defensive second pass.

**Prevention**: any data normalization (renaming, mapping, type
coercion of legacy values) MUST run on the raw input before semantic
validation rejects unknowns.

### Pitfall #4 — `unittest.mock.patch` swallows the real ImportError

**Symptom**: `AttributeError: module 'pyautoclick.persistence' has no
attribute 'settings'` even though `pyautoclick/persistence/settings.py`
clearly exists.

**Cause**: `mock.patch("pyautoclick.persistence.settings.X")` calls
`importlib.import_module("pyautoclick.persistence.settings")`. If that
import raises `ImportError` (because of a transitive pynput issue, for
example), `mock` catches it silently and falls back to
`getattr(persistence, "settings")`, which fails with `AttributeError`.

**Fix**: always reproduce the import directly to get the real error:

```bash
DISPLAY= python3 -c "import pyautoclick.persistence.settings"
```

### Pitfall #5 — `template.format(...)` crashes on unresolved ICU plural

**Symptom**: `ValueError: unexpected '{' in field name`.

**Cause**: when the plural dispatch can't determine `one`/`other` (e.g.
because the kwarg `n` is missing or non-int), the template still
contains `{n, plural, one {...} other {...}}`. Calling `str.format` on
this string fails because `n,` is not a valid field name.

**Fix**: catch `ValueError` alongside `KeyError`/`IndexError` in `t()`.

**Prevention**: when adding new templating syntax, write at least one
test where the kwargs do not match what the template expects.

### Pitfall #6 — Empty `__init__.py` in `tests/` subdirs blocks `pytest-xdist`

**Symptom**: `pytest -n auto` fails with mysterious
`AttributeError: module 'pyautoclick' has no attribute '__path__'`.

**Cause**: empty `__init__.py` files turn `tests/foo/` into a package,
which fights pytest's rootdir-based discovery and breaks
parallelization.

**Fix**: don't create `__init__.py` in `tests/` unless there's an
explicit `tests/foo/conftest.py` that needs to be a package.

### Pitfall #7 — Magic numbers and colors duplicated across UI files

**Cause**: `padding=20`, `pady=8`, `#cc4444`, `"☀"` were repeated in 8
files; changing one required 8 edits.

**Fix**: `pyautoclick/ui/constants.py` and `pyautoclick/ui/colors.py`
centralize them. The CI lint config doesn't catch this — it's a code
review responsibility.

**Prevention**: any new numeric UI constant or color string goes into
the centralized files first, then is imported. If you find yourself
typing `padding=` or `#xxxxxx` in a tab file, stop and add the constant.

### Pitfall #8 — GitHub topics input is one-at-a-time

**Symptom**: pasting "autoclicker python tkinter ..." in the Topics
field gets the whole string treated as one tag and rejected for length.

**Fix**: type each topic + Enter. GitHub recognizes Enter, space, and
comma as separators.

### Pitfall #9 — pyproject URL case sensitivity matters

**Symptom**: GitHub URL renders as `thomasmayor/py-autoclick` instead
of `ThomasMayor/py-autoclick` even though the routing works either way.

**Fix**: use the exact case as displayed on the GitHub profile.

### Pitfall #10 — Forgetting `ruff format` after creating a new file

**Symptom**: lint job fails on CI even though `ruff check` passes.

**Cause**: `ruff check` and `ruff format --check` are two distinct
gates. New files written without going through `ruff format` will fail
the format check even if the lint check passes.

**Fix**: after writing any new `.py` file, run `ruff format <file>` (or
`ruff format pyautoclick tests` for everything) before the pre-commit
checklist.

### Pitfall #11 — Tests filtered by marker → exit 5 (no tests collected)

**Symptom**: `pytest -m "not linux_only"` exits with code 5 on Win/Mac
because every test in the suite carries `pytest.mark.linux_only`.

**Fix**: maintain a baseline of cross-platform tests in
`tests/test_smoke.py` (no markers) so the runner always finds something
to execute regardless of the marker filter.

### Pitfall #12 — Race conditions silently absorbed by the GIL

**Symptom**: tests pass locally on CPython but fail on PyPy or under
heavy load.

**Cause**: cross-thread state in `AutoClicker` was originally read/written
without explicit locks. CPython's GIL hides the bug for ints/floats but
it's still UB.

**Fix**: `AutoClicker` uses an `RLock` and snapshots all loop variables
at the start of each iteration. Setters go through `set_xxx` methods
that take the lock.

**Prevention**: any new field on `AutoClicker` that might be read by a
loop while written by the UI thread must follow the snapshot+lock
pattern.

### Pitfall #13 — Mock divergence: tests pass with the fake but fail with the real dependency

**Symptom**: 226 tests pass locally with `DISPLAY=` (fake pynput injected
by conftest fallback), then 12 fail on CI under `xvfb-run` where the real
pynput loads.

**Cause**: the fake's `HotKey.parse("a")` returned `["a"]` (string list)
while the real one returns `frozenset({KeyCode("a")})` (objects with
different hash). Tests pushing `hm._on_press("a")` worked with the fake
because `"a" in {"a"}` is `True`, but with the real backend
`KeyCode("a") != "a"` so the combo never matched and callbacks never
fired. Local runs and CI **disagreed silently** because each loaded a
different backend.

**Fix**: `tests/conftest.py` now **always** installs the fake (unless
`PYAUTOCLICK_TESTS_REAL_PYNPUT=1`). Tests are deterministic regardless of
the local DISPLAY state.

**Prevention** — the rule that prevents future occurrences:

1. The pre-commit checklist (§5) MUST run pytest in **both** display modes
   (with and without DISPLAY set), as documented in §1.1. A passing run
   in only one mode is a false-green.
2. When a test uses a manually-built input (here: a string key), prefer
   building it via the same code path the production uses (here:
   `keyboard.HotKey.parse(combo)`) — that way mock and real diverge less.
3. When you write a fake for a third-party library, add a comment
   documenting EXACTLY which observable behaviors of the real library it
   does and does not emulate. The fake in `tests/conftest.py` now lists
   its limitations explicitly.

---

## 7. When in doubt

- **Read this file first**, then `~/.claude/CLAUDE.md` (global rules).
- For architectural decisions, prefer batched edits over scattered ones
  — touch a file once per PR ideally.
- Use Agent-based audits at checkpoints (layer purity, i18n parity,
  import cycles, test coverage). The history shows these caught bugs
  that human review missed.
- Bias toward **fixing the root cause** rather than `# noqa` on the
  symptom. The 4 ruff `# noqa`-eligible patterns in this codebase are
  documented in `pyproject.toml` `[tool.ruff.lint] ignore` with reasons.
- When you find a new pitfall during work, add it to section 5 of this
  file in the same PR.

---

## 8. Tooling reference

| Tool | Purpose | Command |
|---|---|---|
| `ruff check` | Lint | `ruff check pyautoclick tests` |
| `ruff format` | Format | `ruff format pyautoclick tests` |
| `mypy` | Type check | `mypy pyautoclick` |
| `pytest` | Tests | `DISPLAY= python3 -m pytest tests/ --no-cov -q` |
| `pytest --cov` | Coverage | `DISPLAY= python3 -m pytest tests/ --cov=pyautoclick --cov-report=term-missing` |
| `python -m build` | Build wheel + sdist | `python -m build` |
| `python -m py_compile` | Syntax check | `find pyautoclick -name '*.py' -exec python3 -m py_compile {} +` |

CI mirrors all of these on every push (Linux/Win/macOS × Python
3.10/3.11/3.12). A green local run does not guarantee a green CI run
because of OS differences — but a red local run guarantees a red CI run.
