# Git Companion CLI

This guide is for contributors. The [main README](../README.md) is the short installation guide for artists and other app users.

## Repository layout

```text
setup-windows.cmd       Windows setup (generated)
setup-macos.command     macOS setup (generated)
setup-linux.sh          Linux setup (generated)
src/git_companion/      Application, styles and command guidance
dev/tests/              Automated checks
dev/tools/              Installer builder and preview renderer
dev/packaging/          Setup templates and standalone entry point
dev/artifacts/          Generated wheels, previews and setup checksum manifest
dev/.cache/             Test and lint caches
```

Every catalog action has one hint of at most 90 characters and two validated examples in `src/git_companion/guidance.py`. The list and details show its hint; the description and examples live in a collapsed panel. F2 opens a help dialog at any terminal size and toggles examples within a review dialog. Changing actions closes the examples; idle refreshes preserve an open panel. Example values are used only to build displayed sample commands; they do not populate forms or execute anything.

Command discovery indexes every action's ID, friendly name, hint, description, full `git` syntax, flags, workflow name and examples. Full command and prefix matches rank above descriptive matches; otherwise equivalent matches prefer previews over destructive actions. `CommandSearch` uses Textual's inline suggestion renderer, with Tab/Right acceptance and Down navigation to the live results. Ctrl+F opens the complete catalog even with an empty query. Enter only opens the selected action's review form; no typed search text is passed to a shell. Argument placeholders are left to the review fields, rather than being filled by autocomplete.

Each execution opens a `ResultsScreen` backed by a `CommandResult` retaining up to 2,000 sanitized lines for the latest command. Both stdout and stderr stream into it and into the embedded terminal; unterminated output is shown live in a separate partial-line area. Exit code, duration and explicit success/failure/stopped states remain visible. Silent commands receive a no-output message. F3 reopens the latest result, including while its process is still running. Results are retained in memory for this app session only. Compact layout hides decorative panels so the embedded terminal remains within an 80×24 viewport. End-to-end UI tests run actual Git commands through review and execution at both compact and wide sizes.

A colorful, keyboard-first terminal cockpit for **Git + Git LFS**, built around what you want to do next.

Branch artwork, a lavender/mint/amber palette, live repository metrics, searchable actions, command previews, mouse support, responsive panels, dark/light themes, and streamed command output. Works from a terminal on Windows, Linux, and macOS. Setup handles Python and the app's dependencies automatically.

## Install once, then just type git-companion

Choose the setup for your operating system from the **project root**:

| Operating system | Setup file | Run once |
| --- | --- | --- |
| Windows | [setup-windows.cmd](../setup-windows.cmd) | Double-click the file |
| macOS | [setup-macos.command](../setup-macos.command) | Open the executable file in Terminal, or run `sh setup-macos.command` |
| Linux | [setup-linux.sh](../setup-linux.sh) | Run `sh setup-linux.sh` |

**After setup finishes, close and reopen your terminal.** Open any project directory and type:

```text
git-companion
```

The app opens in your terminal's **current directory**, without changing directories. You do not need to install Python yourself, use pip, activate an environment, keep the downloaded setup file, or keep a copy of this source project.

Each setup is a standalone **online installer** with this version of the app embedded inside it. Setup supports Intel/AMD 64-bit and ARM64 processors. It checks for compatible Python (3.10–3.14), reuses it when available, and downloads/installs a private Python runtime when missing. A small pinned copy of [uv](https://docs.astral.sh/uv/) handles runtime discovery, background Python installation, and package installation. The setup tool and embedded app are checked against SHA-256 digests before use. Internet access is required for the runtime and UI dependencies. Application packages come from PyPI.

The setup creates a private application environment automatically and registers a `git-companion` launcher. Python installed by setup lives inside the app's own directory, leaving the OS Python alone. If an existing Python installation is reused, it must remain installed. You can rerun setup to repair the app or install a newer setup file to update it; an existing launcher is kept until the new environment passes its import/version checks.

| OS | Default app folder | Command registration |
| --- | --- | --- |
| Windows | `%LOCALAPPDATA%\GitCompanion` | Adds the app's `bin` folder to your user PATH |
| macOS | `~/Library/Application Support/GitCompanion` | `~/.local/bin/git-companion`; configures Bash, Zsh and Fish PATH |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/git-companion` | `~/.local/bin/git-companion`; configures Bash, Zsh and Fish PATH |

App installation needs no administrator account. Git/Git LFS installation can still require OS authorization. Your terminal may need to be fully quit and relaunched on Windows to inherit the updated user PATH. On macOS, a downloaded `.command` file may need permission to execute; `sh setup-macos.command` runs the same installer without changing its executable permission. These are script setup files, rather than signed native `.exe` or `.pkg` installers.

```sh
git-companion --no-install  # inspect without automatic dependency installation
git-companion --ascii      # ASCII decoration for limited fonts
git-companion --help
```

## Workflow map

| Workspace | What belongs here |
| --- | --- |
| For you | Deterministic suggestions from staged files, edits, conflicts, in-progress merge/rebase, and upstream divergence |
| Look around | Status, commit graph, diffs, blame, tags |
| Save your work | Stage, unstage, commit, amend, stash |
| Try ideas | Create/switch/rename/delete branches, merge, rebase, cherry-pick, worktrees |
| Share & sync | Fetch, fast-forward pull, push, force-with-lease, remotes, release tags |
| Large files | LFS tracking, inventory, downloads, uploads, integrity, locks, migration analysis/import |
| Reclaim space | LFS prune previews, verified prune, force-prune, clean previews, Git GC and size |
| Recover | Reflog, restore, soft reset, hard reset, revert |
| Set up | Init, clone, configuration, identity, LFS activation |

Search matches across **all** categories. Suggestions are local rules, with no AI service, account, API key, or network request involved. Actual Git/LFS operations can contact your configured remotes.

LFS has dedicated `prune --dry-run`, `prune --force --dry-run`, `prune --verify-remote`, and `prune --force` workflows. Force-prune can remove local objects needed by checked-out references, while preserving unpushed objects. Avoid pruning if multiple repositories share a custom `lfs.storage` directory. History migration is an advanced operation and needs a repository backup.

## First launch and installation

On launch the app checks `git --version` and `git lfs version`. Missing tools are installed automatically, with progress in the live terminal:

| OS | Installation strategy |
| --- | --- |
| Windows | WinGet exact package IDs `Git.Git` and `GitHub.GitLFS`; silent installers; recheck for bundled LFS after Git installation |
| macOS | Homebrew (`brew install`), or MacPorts if installed |
| Linux | Detect apt-get, dnf, yum, pacman, zypper or apk; install distro `git` and `git-lfs` packages |

Installation uses the existing package manager. It does not bootstrap Homebrew or WinGet, download and execute arbitrary installer scripts, or bypass OS elevation. Windows may display an OS elevation prompt. Linux and MacPorts use `sudo -n`, so an unprivileged installation fails promptly with instructions if administrator authorization isn't cached. Package availability depends on the configured repositories and network access. Install those prerequisites manually if the package manager is absent. A restart may be needed if the OS has not exposed the new executable on PATH.

After successful installation the app enables user-level LFS filters. Existing installations are checked without changing user configuration; use **Set up → Enable Git LFS** when needed. Checks are repeated on later launches so tools removed after setup can be detected.

The setup files handle Python and application installation before this first-launch Git/Git LFS check. Native standalone executable builds remain available as an alternative distribution format.

## Controls

| Key | Action |
| --- | --- |
| Tab / Shift+Tab | Move between panels and fields |
| Up / Down | Browse actions or categories |
| Enter | Open command review or activate a control |
| Ctrl+F | Search every action |
| Escape | Close a dialog / clear search |
| Ctrl+O | Open another workspace |
| Ctrl+R | Refresh repository state |
| Ctrl+X | Stop the running process and its process tree |
| Ctrl+T | Toggle dark/light theme |
| F1 | Print help to the live terminal |
| Ctrl+Q | Stop the operation and quit |

Every action opens a review form with the actual command. Destructive operations require typing `RUN`. The app passes arguments directly to the executable, without invoking a shell. Quoting, globs, spaces and shell metacharacters are not shell-interpreted. Pattern expansion is performed by Git where the command supports it.

Output is bounded to 2,000 lines and terminal control codes are removed before display. Only one action runs at a time. Repository metrics refresh every five seconds while idle. Run Git Companion inside a trusted repository: Git itself can invoke repository hooks, filters and credential helpers.

Authentication uses your existing Git credential helper or SSH agent. Interactive password prompts and editors are disabled in the embedded runner so they cannot trap the UI. Configure credentials in your normal terminal first. Set messages in the app's forms. If a merge/rebase conflicts, resolve the files in your editor, stage them, then use the continuation workflows. Stopping a Git operation can leave a merge/rebase in progress; inspect status before continuing.

## How the rich terminal UI works

This is a real TUI, not a web page drawn to look like a terminal:

- **Textual** supplies the layout engine, CSS-like styles, widgets, focus handling, keyboard/mouse events, resize handling and application lifecycle.
- **Rich** represents colored text and renders terminal output. Textual updates the terminal with control sequences and efficient screen repainting.
- **Unicode box drawing and branch art** provide shapes. ASCII mode substitutes basic characters in the decorative art and command icons. Textual's own widget borders still use terminal drawing glyphs.
- **Asyncio and Textual workers** keep subprocess I/O and repository inspection responsive.
- **Subprocess argument arrays** let the app wrap the installed Git and Git LFS tools without reimplementing their repository semantics.

The terminal emulator owns the font. A TUI can request bold, italic and colors; it cannot reliably assign a custom font to one panel. Choose your preferred monospace font in Windows Terminal, iTerm2, Kitty, WezTerm, or another terminal. Nerd Fonts can add private-use glyphs, but requiring one would reduce portability, so this app does not depend on them. Emoji appearance and cell width vary by OS/font, which is why the main layout uses predictable text and symbols. Textual's built-in command palette and notifications may use their own glyphs.

For comparable tools: the official Codex CLI documentation describes its Rust implementation; its public TUI source uses Ratatui. [Codex CLI documentation](https://developers.openai.com/codex/cli/) and [TUI source](https://github.com/openai/codex/blob/main/codex-rs/tui/src/tui.rs). Ink is a React-based terminal renderer used in the broader JavaScript TUI ecosystem; see its [official repository](https://github.com/vadimdemedes/ink). This project does not assume Claude Code or Antigravity's current internal implementation: public interfaces alone do not establish their rendering stack.

## Development and validation

The following commands are **for developers working on this source code**, not for app users:

```sh
python -m pip install -e '.[dev]'
python -m pytest
ruff check src dev
```

Tests cover command construction and option injection, OS installer plans, porcelain status parsing (including rename/newline filenames), real Git stage/commit operations in temporary repositories, subprocess cancellation, and headless Textual search/dialog/resize flows. Setup tests check all three embedded wheel payloads, checksum manifests, PATH configuration idempotence, preservation of shell configuration, and argument forwarding from another directory. Cross-platform CI runs the tests and installer smoke checks on Windows, Ubuntu and macOS.

To regenerate the three setup files after changing the app:

```sh
python -m pip install hatchling
python -m hatchling build -t wheel -d dev/artifacts
python -m dev.tools.build_installers dev/artifacts/git_companion_cli-0.1.0-py3-none-any.whl
```

The build workflow uploads the three scripts and their checksum manifest together. It also packages an archive that preserves the macOS/Linux executable bits. End-user setup files embed a regular wheel, **not** an editable installation tied to this source folder. A wheel (`.whl`) is Python's package archive format; it is an internal setup payload here, not something beginners need to install manually.

The CLI has no embedded file editor, interactive Git patch selection, or general-purpose shell. The forms expose curated, frequently useful workflows rather than every possible Git flag. Native OS installs and packaged executables should be validated on clean machines before a release.

## Video teasers

Both finished teasers, animated README previews and captions are in `dev/media/`. See the [media guide](media/README.md) for production methods and reproducible rendering commands. The second edit uses original sound effects only and highlights the sidebar command library, search, autocomplete, command results and expandable examples. Rendering tools stay in `dev/tools/`, with intermediate assets ignored under `dev/artifacts/`.
