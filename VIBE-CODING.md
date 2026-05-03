# VIBE-CODING.md — A candid retrospective on shipping enterprise-quality software in a language I don't know

This is the story of how I built `py-autoclick` — a small but deliberately
over-engineered cross-platform autoclicker — almost entirely by
conversational pair-programming with [Claude](https://claude.com), Anthropic's
coding-assistant LLM, in a language I had never seriously written before
this project.

This is not a "look how easy it is" doc. It's the opposite: a careful, honest
account of what worked, what failed, and — most importantly — *why this
approach is not transferable to someone who doesn't already know how to ship
software*. Read it as a field report from one engineer who tested vibe-coding
seriously, with full notes.

---

## Who I am (and why this is the central caveat)

I'm a Swiss full-stack web developer with **28 years of industry experience**.
I started writing code in 1998 — Turbo Pascal and C — during a Swiss vocational
informatics qualification. Microsoft and Java certifications in the early
2000s. C# / VB.NET for about six years. Then PHP/JS, mobile (Angular/Ionic),
Node.js, MongoDB. I've also taught Node.js, Express, MongoDB, and Docker
workshops.

For the last seven years I've been the **most senior developer, member of the
board, and shareholder** (the equity earned over years of accumulated effort,
not granted on day one) of a Swiss healthcare booking platform. The codebase
is several hundred thousand lines of code across multiple services — a Rails
monolith (Ruby + JS / ERB views) and a separate TypeScript / React
application, plus Node.js services. I work day-to-day across the whole stack:
Rails, TypeScript, Node, React. Beyond writing code, I'm responsible for
technical strategy, operations, integrations (medical billing standards, SMS
gateways, payment processors, patient records, third-party clinic software),
schema design, security, and CI/CD. I do advanced technical support for our
largest clients — clinics where downtime is expensive and where the
integration surface with external systems is fragile — and I mentor and
train new developers and support staff so they can become productive as fast
as possible. On a typical business day the platform handles around twelve
thousand newly created appointments and serves more than six thousand
distinct end-users (patients), across roughly twenty-six hundred active
practitioner and clinic agendas in any given month. Cumulatively it has
processed close to twenty-four million appointments and stores records for
some three and a half million end-users.

**Python? I've never seriously practised it before this project.** I can
read it — modern Python isn't far from any other typed object-oriented
language a polyglot has crossed paths with — but I had never used it for
a real project before. I would not call myself fluent.

This biographical detail is the load-bearing assumption of this document.
The vibe-coding experiment described below worked because I knew, at every
step, what good looked like — what "atomic save" meant before I asked for it,
what a race condition under pynput callbacks would look like, what a layered
architecture should enforce, where to refuse Claude's defaults. **Take that
away and the same conversation produces plausible-looking garbage.** I'll come
back to this point at the end. Hold on to it now.

---

## How this actually started

A note on the origin, because honesty matters here. **This project began as
a tiny personal tool.** I wanted to auto-click in idle and incremental
("clicker") games, and nothing existing fit my exact needs — modifier-key
triggers, multi-position cycling, configurable inter-click jitter, the kind
of small details that only matter to one person. So I wrote a single-file
`.pyw` for myself, on my laptop, with no plan of ever sharing it.

Then a familiar tendency of mine kicked in: **I have trouble leaving things
half-finished.** The honest reason underneath is simpler: 28 years in, I'm
still fundamentally passionate about the craft of writing software, and a
side project is the rare place where I can take that passion all the way
without anyone asking about deadlines, scope, or ROI. A working-but-rough
script became "what if I made this into a real package?" became "what if it
had tests?" became "what if it shipped to PyPI, with multi-OS standalone
binaries, in eleven languages including right-to-left ones, gated at 80%
coverage, mypy strict?" — and here we are, writing a multi-page retrospective
about what was supposed to be a weekend toy.

That arc is part of the experiment too. Not every personal tool needs to grow
into a 226-test release pipeline. But I wanted to see what happened if I let
the "go all the way" instinct run, with an LLM as the typing partner. The
deliberate over-engineering of a small project is what made it a useful
test-bench: every enterprise practice we'd normally cut for "it's just a side
project" got built anyway, precisely because the project was small enough
that we could afford to. A test-bench you'd never apply to your day job, but
a test-bench whose lessons absolutely apply to it.

---

## The premise

Vibe-coding, as I tested it, means: **specifying the desired outcome and the
quality bar in natural language, then iterating with an LLM that does most of
the typing**. Not "let the AI decide what to build." Not "click accept on
every diff." More like pair-programming where I'm the architect-reviewer and
the LLM is a fast, opinionated, occasionally-wrong typist with strong
domain breadth.

I picked Python deliberately, for two reasons. First, I wanted a language I
have *never* seriously written, to honestly stress-test how far an LLM could
carry me when my own intuition for idioms was effectively zero. Second,
Python's ecosystem
(typing, pytest, ruff, mypy, packaging, GitHub Actions) is mature enough that
"enterprise quality" is well-defined: types, tests, coverage gates, multi-OS
CI, atomic persistence, structured logging.

The goal was: take that 1300-line single-file `.pyw` and ship it as a
production-grade Python package — multi-platform standalone binaries,
internationalised in eleven languages including right-to-left ones,
mypy-strict, 80% coverage gate, atomic config persistence, cross-platform
single-instance handling, the works. CAC 40 quality.

22 hours of wall-clock time later, in **one continuous conversation**, that
package was on PyPI. This document is the post-mortem.

---

## The starting point

The original `py-autoclick.pyw` was honest hobbyware. It had:

- The core feature set already (hold mode, auto mode with click count limits,
  position cycling, three global hotkeys, French + English UI).
- One file, ~1300 lines.
- Zero tests.
- Zero type annotations.
- A bare `except Exception: pass` swallowing anything.
- Config saved with `open() + .write()` — non-atomic, prone to corruption
  on crash mid-write.
- `pynput` imported at module load (broke any headless environment).
- UI and engine logic mixed in the same module.
- No license.

It worked on my machine. Anything beyond that was wishful thinking.

---

## The transformation arc

In 22 hours we went from that to:

- **Layered package** — `ui → services → core → i18n + persistence + paths +
  logging_config`, with a strictly enforced one-way dependency direction
  (`grep` audit verifies it before merge).
- **226 tests, 83.4% coverage**, 80% gate enforced in CI on every push.
- **`mypy --strict`** on `core/persistence/i18n/services` (UI layer is
  pragmatically lenient — Tk widget callbacks resist clean typing).
- **9 ruff rule sets** active, every ignore documented in `pyproject.toml`
  with a one-line reason.
- **11 languages**: English, French, Spanish, Portuguese, German, Italian,
  Russian, Chinese, Japanese, Arabic, Hebrew. Two RTL.
- **Dynamic right-to-left layout mirroring** for Arabic and Hebrew (label and
  control columns swap, status bar mirrors), driven by a `_meta.direction`
  field in the locale JSON.
- **ICU-style plural support** with a custom mini-parser (`{n, plural,
  one {…} other {…}}`).
- **Atomic config save** via `tempfile.mkstemp` + `os.fsync` + `os.replace`
  so a crash mid-write cannot corrupt JSON.
- **Settings validation** with field-level validators; invalid values fall
  back to defaults (logged as warnings) instead of crashing.
- **Schema versioning** with an extensible migration registry that runs
  *before* validation (more on that below — there's a story).
- **Cross-platform single-instance handling**: POSIX uses `fcntl + AF_UNIX`,
  Windows uses `msvcrt + TCP loopback`; launching a second instance brings
  the existing window to the foreground via IPC instead of failing.
- **Structured logging** to stderr + rotating file, level via env var.
- **Signal handling**: SIGINT and SIGTERM trigger a graceful shutdown
  through the existing window-close path.
- **Wayland detection** with a user-facing amber warning banner when global
  hotkeys are unavailable on the current session type.
- **Sun Valley theme** (light/dark switcher persisted to config).
- **Hot-reload of UI** on language change — preserves engine state, hotkey
  listener, and settings, so toggling Arabic ↔ English doesn't reset the user.
- **GitHub Actions matrix CI**: 3 OS × 3 Python versions = 9 jobs per push.
- **PyPI auto-publish** via OIDC trusted publishing on every `v*.*.*` tag.
- **GitHub Releases with PyInstaller-built standalone binaries** for Linux
  x86_64, Windows x86_64, and macOS arm64.

That's the destination. The journey there is what the rest of this document
is about.

---

## Pitfalls catalogue (with code)

These are concrete failures that survived past Claude's first attempt — the
kind of thing that separates demo-ware from production. Each was an actual
incident that prompted a rule, a test, or a structural change. Each has a
lesson that generalises beyond Python.

### Pitfall 1 — `pynput` breaks at module-load time on headless

Claude's first cut of the button mapping looked like this:

```python
# pyautoclick/core/buttons.py — broken in CI
from pynput.mouse import Button

BUTTONS = {"left": Button.left, "right": Button.right, ...}
```

This works on a laptop with a desktop session. On CI without `Xvfb`, the
import alone crashes with `ImportError: failed to acquire X connection`
because `pynput`'s xorg backend tries to open `:0` *at import time*. The
test runner never even reaches the first test.

The fix is a lazy proxy:

```python
class _ButtonMap:
    def __init__(self) -> None:
        self._cache: dict[str, Button] | None = None

    def __getitem__(self, key: str) -> Button:
        if self._cache is None:
            from pynput.mouse import Button
            self._cache = {"left": Button.left, "right": Button.right, ...}
        return self._cache[key]

BUTTONS = _ButtonMap()
```

Now import is free; the X connection only happens when we actually need a
button. Pure helpers like `jittered()` (random-jitter sleep) live in a
separate `core/timing.py` with no `pynput` dependency at all, so they can
be unit-tested headless.

**Generalisable lesson**: any third-party library that has side effects at
import time (DLL loading, X connections, GPU init, network calls) leaks
those side effects into the modules that import it transitively. The fix
is always the same: **defer the import** to the first use, and isolate the
side-effecting code in its own module.

### Pitfall 2 — The DISPLAY trap (the worst one)

This one shipped red CI to the world. I ran tests locally on a desktop
session, all green. Pushed. CI red. 12 hotkey tests broken.

The cause was a divergence between the *fake* `pynput` we inject for
headless testing and the *real* `pynput` loaded under `xvfb-run`:

| Local environment        | What loads                       | `HotKey.parse("a")` returns       |
|--------------------------|----------------------------------|-----------------------------------|
| `DISPLAY=` unset         | Fake (conftest fallback)         | `["a"]` (string list)             |
| `DISPLAY=:0` set         | Real `pynput` xorg backend       | `frozenset({KeyCode("a")})`       |
| CI under `xvfb-run`      | Real `pynput` xorg backend       | `frozenset({KeyCode("a")})`       |

A test that pushed string keys (`hm._on_press("a")`) and asserted the
callback fires would *work with the fake* (because `"a" in {"a"}` is
True) and *silently fail with the real backend* (because
`KeyCode("a") != "a"` — different hash, different equality). My local run
loaded the fake (because of the fallback path); CI loaded the real one.
Same code, different observable behaviour.

The fix wasn't in production code. It was in test infrastructure:

```python
# tests/conftest.py
if not os.environ.get("PYAUTOCLICK_TESTS_REAL_PYNPUT"):
    _install_fake_pynput()  # always, regardless of DISPLAY
```

Then I added a hard rule to the project `CLAUDE.md` (the file Claude reads
at session start): **before any commit, run pytest in both display modes**.
Local "green" with DISPLAY set isn't sufficient.

```bash
DISPLAY= python3 -m pytest tests/ -q     # headless mode
python3 -m pytest tests/ -q              # display mode
```

**Generalisable lesson**: when you write a fake of a third-party API,
document explicitly which observable behaviours of the real thing it
emulates and which it doesn't. Better: build test inputs through the same
parser the production code uses, so divergence between mock and real is
structurally impossible.

### Pitfall 3 — Migration ordering destroyed legacy data

A v0.1 user's config had `"action": "Clic droit"` (the French label that
v0.1 stored verbatim). After upgrading to the typed-enum world of v0.3,
that field came back as `"left"` — the default — instead of the migrated
`"right"`.

The migration logic existed: `migrate_legacy()` correctly mapped "Clic
droit" → "right". But it ran *after* validation. The validator saw "Clic
droit", didn't recognise it, fell back to default ("left"), and the
migration target was now the default value, not the original. The user's
preference was silently lost.

The fix was structural — split the migration into two phases:

```python
def load() -> Settings:
    raw = _read_json()
    raw = migrate_legacy_data(raw)   # phase 1: rewrite legacy values
    s = _validate_and_construct(raw) # phase 2: type-check the new shape
    s = migrate_legacy(s)            # phase 3: defensive second pass
    return s
```

**Generalisable lesson**: data normalisation (renaming, type coercion,
mapping legacy values) MUST run on the raw input *before* any semantic
validation rejects unknowns. Otherwise validation itself becomes the bug.

### Pitfall 4 — PyInstaller icon (the failure that delayed v0.3.4)

We built v0.3.4 with a single `.png` icon, expecting PyInstaller to
fall back to the default if it couldn't use the PNG natively. Linux passed.
Windows and macOS jobs went red.

The actual error:

```
ValueError: Received icon image '...py-autoclick.png' which exists but is
not in the correct format. On this platform, only ('exe', 'ico') images
may be used as icons. If Pillow is installed, automatic conversion will
be attempted.
```

The Claude-generated comment in the spec file had said *"without these,
PyInstaller falls back to the default icon."* That was wrong. PyInstaller
*raises*. The comment was based on a documentation reading that didn't
match empirical behaviour. CI told the truth.

The fix was one line — adding `pillow` to the workflow's pip install:

```yaml
python -m pip install "pyinstaller>=6.0" pillow
```

Pillow is a build-time dependency only (not in `pyproject.toml`); it
auto-converts PNG to `.ico` and `.icns` at build time so the same single
icon source feeds all three OSes.

**Generalisable lesson**: comments based on documentation are hypotheses,
not facts. Only what CI actually does is truth. When you find a stale
"helpful" comment, treat it like a stale assertion in test code: it's
worse than no comment, because it actively misleads future readers.

### Pitfall 5 — I refused 142 `# type: ignore` instances

When I turned on `mypy --strict`, the project produced 142 errors. Claude's
first reflex was to silence each one with `# type: ignore`. I refused
every time and pushed for the structural fix instead. Three examples:

```python
# Before — implicit-bool narrowing fails, mypy complains, Claude wants # type: ignore
_IS_WINDOWS = sys.platform == "win32"
if _IS_WINDOWS:
    import msvcrt   # mypy: error on Linux, msvcrt is Windows-only

# After — direct literal narrowing, mypy sees the platform on each side
if sys.platform == "win32":
    import msvcrt   # mypy: ok, branch is unreachable on Linux
```

```python
# Before — mypy thinks the fallback branch is unreachable
if sys.platform == "linux": ...
elif sys.platform == "darwin": ...
else: log("unsupported")  # mypy: warn-unreachable triggers

# After — widen the type so the else branch is reachable
platform: str = sys.platform
if platform == "linux": ...
elif platform == "darwin": ...
else: log("unsupported")  # ok
```

```python
# Before — defensive isinstance check that mypy correctly flagged as dead
def _safe_lookup(value, table):
    if not isinstance(value, str): return None  # unreachable: validation guarantees str
    return table.get(value)

# After — trust upstream guarantees, remove the dead check
def _safe_lookup(value: str, table: dict[str, T]) -> T | None:
    return table.get(value)
```

Final result: 0 mypy errors, 0 `# type: ignore`. It took longer than mass
silencing. It was worth it.

**Generalisable lesson**: type ignores hide bugs. Every `# type: ignore`
is a small interest-bearing loan against future debugging. The whole
point of strict typing is to surface assumptions; covering them with
ignores defeats the exercise.

---

## What worked well with Claude

- **Mass refactoring with surgical control.** I could say "extract this
  into a `core/` module with these constraints" and Claude would produce
  hundreds of lines of consistent, idiomatic Python. With careful review,
  this is *easily* 5–10× faster than typing it myself.

- **Documentation that maintains itself.** I asked Claude to keep
  `CLAUDE.md` (project rules + pitfalls catalogue) and `CHANGELOG.md`
  current as we worked. Each pitfall we hit became a documented rule.
  The `CLAUDE.md` is now ~900 lines and reads like a senior-engineer's
  playbook for this codebase. Future me, or any contributor, can pick up
  where we left off without an oral handover.

- **Cross-platform abstraction discipline.** I described what I wanted
  ("single-instance lock that works on Linux + Windows; bring-existing-
  window-to-front on second launch"). Claude designed the POSIX vs
  Windows split — `fcntl + AF_UNIX` vs `msvcrt + TCP loopback` — including
  the rationale for each choice. I would not have produced that split as
  fast on my own in a language entirely new to me.

- **Unblocking when I don't know the idiom.** "What's the Python
  equivalent of `X`?" — Claude answers in seconds, with the trade-offs I'd
  expect a domain expert to articulate. Not just "use `pathlib`," but
  "use `pathlib` because it's immutable, cross-platform, and has clean
  methods for the operations you'll do most often."

- **Test scaffolding.** I didn't have to manually write mocks, conftests,
  parametrised tests, fixtures. Claude wrote them, I reviewed and adjusted.
  The 226-test suite would have taken me twice as long alone.

---

## What didn't work — and what I had to enforce

These are the rules I had to write into `CLAUDE.md` because Claude's
defaults pulled the wrong way until I explicitly disagreed.

- **Default to broad `except Exception:`.** Claude's reflex on any
  "this might fail" is to wrap broadly. I had to enforce: only narrow
  exceptions, with `logger.exception()`, with one acceptable broad form
  (callback wrappers at thread boundaries, where you genuinely cannot
  let an exception kill the listener) and an inline comment explaining
  why.

- **Default to `# type: ignore`.** Covered above — I refused every one
  and asked for the structural fix.

- **Default to over-commenting.** Claude wants to comment every line.
  My rule, written into `CLAUDE.md`: comment WHY, never WHAT. Don't
  reference the current task ("added for the X flow"). If removing the
  comment wouldn't confuse a future reader, don't write it.

- **Default to feature-flag everything.** Claude wants to add
  backward-compatibility layers, env vars, escape hatches "just in case."
  For a small project, no. Just change the code. Backwards compat is not
  free.

- **Forgetting the consequences of a refactor.** When I asked to add a
  new locale, Claude would update `LANGUAGES` and the corresponding JSON
  but forget the `Literal` `LanguageCode` in `settings.py`. Result: v0.3.0
  silently rejected `language="es"` configs and reset them to default.
  The fix had to be structural: a checklist in `CLAUDE.md` listing every
  place a new language must touch, and a smoke test asserting that every
  declared language is accepted by `Settings.load`.

- **Testing in only one mode.** The DISPLAY trap. After that, I made
  the rule explicit and added it to the pre-commit checklist.

- **Confident comments based on docs, not behaviour.** The PyInstaller
  icon-fallback comment that turned out to be wrong. I now treat
  Claude-written explanatory comments as hypotheses to verify.

The pattern across all of these: Claude is excellent at producing code
that *looks correct*; my job is to push for code that *is correct under
the constraints I care about*. The constraints have to come from me.

---

## The honest numbers

| Measure                          | Value                              |
|----------------------------------|------------------------------------|
| Conversations                    | 1 (continuous, via auto-compaction)|
| Wall-clock time                  | ~22 hours over 2 days              |
| User turns                       | 674                                |
| Assistant turns                  | 1 165                              |
| Transcript size                  | 8.6 MB JSON                        |
| Git commits                      | 13                                 |
| PyPI releases                    | 5 (0.3.0 → 0.3.5)                  |
| Production Python files          | 51                                 |
| Production lines of code         | 3 451                              |
| Test lines of code               | 1 941                              |
| Tests                            | 226                                |
| Coverage                         | 83.4% (gate at 80%)                |
| Locales                          | 11 (incl. 2 RTL)                   |
| OS × Python CI matrix            | 3 × 3 = 9 jobs per push            |

It is one conversation. Not many sessions. Auto-compaction lets a long
context survive past the model's window — when you see "this session is
being continued from a previous conversation" at the start of a turn,
that's compaction kicking in, not a fresh start. I never "re-explained
the project to Claude." The thread held for 22 hours.

---

## The honest reflection

### For whom this approach actually works

- **Senior engineers comfortable with software design at the
  architecture level**, who don't know the target language well but want
  to ship in it without spending weeks on the language ramp-up.
- **Engineers building side-projects** who want enterprise-style
  discipline without spending weeks on tooling, CI, and packaging.
- **Anyone who can internalise the rule**: I am the architect; the LLM
  is the typist with strong opinions; I decide which opinions are right.

### For whom this is misleading

- **Beginners**, full stop. Without an internal compass for "is this
  idiomatic," "is this safe under concurrency," "is this testable," you
  cannot reliably catch when Claude is generating plausible-looking
  garbage. The DISPLAY trap, the migration ordering bug, the PyInstaller
  icon false-fallback comment — each of these required a sceptical
  senior engineer to *not* trust the output. A beginner would have
  shipped each of them. I would never recommend this workflow to someone
  whose first project this is.
- **Anyone outsourcing judgement to the LLM.** The pattern that worked is
  "review every diff, approve no commit unread, write the rules down so
  the LLM follows them next time." If you're skipping reviews, you're
  doing something different from what's described here, and I have no
  evidence about how that goes.
- **Anyone who thinks vibe-coding scales linearly with project size.** A
  3 500-line Python package is not a 100 000-line distributed system.
  The pitfalls I caught here are tractable because the codebase is small
  enough that I could read the whole diff every time. At ten times the
  scale, the review burden grows non-linearly with the loss of memory
  per turn. I have no reason to believe the same approach works for
  arbitrarily large projects.

### What surprised me

- **The amount of test infrastructure required to keep 22 hours of
  changes from breaking previous work.** Tests are the safety net, and
  Claude is happy to write them — but only if I ask. The first time you
  cut tests as "we'll add them later," the LLM happily complies and you
  pay for it twice over the next day.

- **How much of the work was *not* writing code.** Maintaining `CLAUDE.md`,
  building test conftests, configuring CI workflows, writing the
  CHANGELOG. Easily 30–40% of the conversation was meta-engineering.

- **How fast pre-existing experience pays off.** I knew what "atomic
  save" meant before I asked. I knew what "narrow exception" meant. I
  knew that race conditions in pynput callbacks were a real risk and
  asked for `RLock` snapshots up-front. Without that priming, I wouldn't
  have known to ask, and Claude wouldn't have volunteered any of it.

### What I'd do differently next time

- **Set up the strict-mypy / ruff / coverage gates first**, before any
  feature code. We accumulated typing debt and paid it back in a single
  142-error batch. Doing it incrementally would have been cheaper.
- **Run pytest in both DISPLAY modes from day one.** The DISPLAY trap
  was preventable.
- **Treat every LLM-generated comment as a hypothesis.** Verify against
  empirical behaviour before committing it.
- **Write `CLAUDE.md` rules as soon as a pattern emerges**, not after
  the second incident. I learned this the hard way; the rule against
  broad `except Exception:` should have been written on hour 3, not
  hour 14.

---

## Final note

The product I shipped is good. Tests, types, multi-platform binaries,
internationalisation with right-to-left support, atomic persistence,
single-instance handling, structured logging, schema-versioned config —
that's not "vibe quality." That's enterprise quality, by every objective
measure I can apply.

But the vibe-coding part of this experiment is the *journey*, not the
destination. Claude didn't ship enterprise quality; **I shipped
enterprise quality, with Claude doing the typing**. The distinction
matters. The output is real; the methodology generalises poorly.

If you take one thing from this document, take this: an LLM is a power
tool. Power tools are wonderful in the hands of someone who knows what
they're building and what could go wrong. They are dangerous in the
hands of someone who doesn't.

Decide which one you are before you start.
