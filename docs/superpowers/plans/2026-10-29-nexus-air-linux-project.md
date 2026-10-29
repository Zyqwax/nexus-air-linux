# Nexus Air Linux Driver & Control App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package and structure the reverse-engineered Claw's Nexus Air V1 wireless/wired mouse driver and control panel as a standalone, production-ready open source Linux application (`nexus-air`) with Git versioning, multi-distro packaging (AppImage, Arch PKGBUILD, Debian/Ubuntu .deb, RPM), automated GitHub Actions release workflow, and comprehensive documentation crediting REA tools and Gemini 4 Argon Medium.

**Architecture:** A modular Python 3 package (`src/nexus_air`) separating protocol/hardware HID logic (`core.py`, `constants.py`) from CLI commands (`cli.py`) and GTK4 GUI (`gui.py`), with a setuptools/pyproject.toml build system, standard Linux desktop integration (XDG `.desktop`, scalable SVG icon, udev rule), AppImage packaging script via `appimagetool` / `linuxdeploy`, and GitHub Actions CI/CD to build and publish release assets.

**Tech Stack:** Python 3.10+, GTK4 (PyGObject), Linux HID (`/dev/hidraw*`), udev, setuptools/flit, AppImage, GitHub Actions.

**Spec:** User request specifying target directory `/home/zyqwax/Projects/my-mouse-claws`, Git versioning, AppImage + popular distro support, GitHub Releases automation, clean modular project structure, comprehensive README stating supported mouse models and crediting REA tools and Gemini 4 Argon Medium.

## Global Constraints
- Target workspace: `/home/zyqwax/Projects/my-mouse-claws`.
- Hardware target: Claw's Technology / Compx Nexus Air V1 Wireless/Wired Gaming Mouse (VID: `0x3554`, PIDs: `0xF512`, `0xF5D5`, `0xF5A7`).
- Zero external Python package dependencies for CLI (standard library only: `os`, `sys`, `select`, `argparse`, `json`, `glob`, `subprocess`).
- GUI dependencies: `PyGObject` (GTK4).
- Distro compatibility: Arch/CachyOS, Ubuntu/Debian, Fedora, AppImage universal binary.
- Documentation requirement: README must explicitly document REA (Reverse Engineer Anything) and Gemini 4 Argon Medium.

## Review Focus
1. Non-root user running without udev rule -> Friendly error directing user to `nexus-air udev` or `sudo`.
2. Wireless mouse sleeping or dongle disconnected -> Clear timeout and reconnection instructions instead of crash.
3. GTK4 theme quirks (negative slider size on Breeze) -> High-priority CSS provider and GLib log handler to suppress harmless warnings.
4. Left-click disable protection -> Prevent user from bricking mouse click navigation by locking Left Click to "left".
5. AppImage desktop integration -> AppStream metadata and icon installation working out-of-the-box.

---

### Task 1: Initialize Git Repository and Project Scaffolding

**Files:**
- Create: `/home/zyqwax/Projects/my-mouse-claws/.gitignore`
- Create: `/home/zyqwax/Projects/my-mouse-claws/pyproject.toml`
- Create: `/home/zyqwax/Projects/my-mouse-claws/LICENSE`
- Create: `/home/zyqwax/Projects/my-mouse-claws/src/nexus_air/__init__.py`

**Interfaces:**
- Produces: `nexus_air.__version__`, package metadata for setuptools/pip installation.

- [ ] **Step 1: Initialize Git repository**
Run: `git init /home/zyqwax/Projects/my-mouse-claws`

- [ ] **Step 2: Create .gitignore and LICENSE (GPL-3.0 or MIT)**
Create standard `.gitignore` covering `__pycache__`, `*.pyc`, `build/`, `dist/`, `*.egg-info/`, `.pytest_cache/`, `*.AppImage`.

- [ ] **Step 3: Create pyproject.toml**
Define package `nexus-air`, version `1.0.0`, scripts entry points `nexus-air = "nexus_air.cli:main"` and `nexus-air-gui = "nexus_air.gui:main"`.

- [ ] **Step 4: Commit**
```bash
git add .gitignore pyproject.toml LICENSE src/nexus_air/__init__.py
git commit -m "chore: initialize project structure and git repository"
```

---

### Task 2: Modularize Core HID Protocol and Hardware Logic

**Files:**
- Create: `/home/zyqwax/Projects/my-mouse-claws/src/nexus_air/constants.py`
- Create: `/home/zyqwax/Projects/my-mouse-claws/src/nexus_air/protocol.py`
- Create: `/home/zyqwax/Projects/my-mouse-claws/src/nexus_air/device.py`
- Create: `/home/zyqwax/Projects/my-mouse-claws/tests/test_protocol.py`

**Interfaces:**
- Consumes: Standard library (`os`, `select`, `time`, `glob`).
- Produces:
  - `calc_checksum(data: bytes | list[int]) -> int`
  - `make_field(values: list[int]) -> bytes`
  - `encode_dpi(dpi: int) -> tuple[int, int, int]`
  - `decode_dpi(val_x: int, _val_y: int, scale: int) -> int`
  - `NexusAirDevice` class with `read_all_settings()`, `set_led_bar()`, `set_dpi_led()`, `set_profile()`, `set_stage_dpi()`, etc.

- [ ] **Step 1: Write protocol unit tests in `tests/test_protocol.py`**
Include checksum tests, DPI PAW3325 math roundtrip tests, battery mV interpolation tests, and packet building tests.

- [ ] **Step 2: Run tests to verify they fail initially**
Run: `python3 -m unittest discover tests/`

- [ ] **Step 3: Extract constants, protocol functions, and `NexusAirDevice` from `nexus_air.py`**
Split into `constants.py` (VID, PIDs, opcodes, tables, UDEV_RULE), `protocol.py` (checksum, encode/decode DPI, build_packet), and `device.py` (`NexusAirDevice`, `find_devices`).

- [ ] **Step 4: Run unit tests to verify they pass**
Run: `python3 -m unittest discover tests/`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/nexus_air/ tests/
git commit -m "feat(core): implement modular hid protocol and device layer"
```

---

### Task 3: Implement CLI and GTK4 GUI Entry Points

**Files:**
- Create: `/home/zyqwax/Projects/my-mouse-claws/src/nexus_air/cli.py`
- Create: `/home/zyqwax/Projects/my-mouse-claws/src/nexus_air/gui.py`
- Create: `/home/zyqwax/Projects/my-mouse-claws/data/org.cachyos.NexusAirV1.desktop`
- Create: `/home/zyqwax/Projects/my-mouse-claws/data/icons/nexus-air.svg`
- Create: `/home/zyqwax/Projects/my-mouse-claws/data/99-nexus-air.rules`

**Interfaces:**
- Consumes: `nexus_air.device.NexusAirDevice`, `nexus_air.constants`, `nexus_air.protocol`.
- Produces:
  - `nexus_air.cli.main()` CLI runner supporting `status`, `dpi`, `led`, `profile`, `rate`, `button`, `reset`, `udev`, `gui`.
  - `nexus_air.gui.main()` GTK4 graphical control center.

- [ ] **Step 1: Implement `cli.py`**
Provide clean argparse CLI with commands for status, DPI stages/colors, RGB strip, DPI indicator LED, polling rate, debounce, motion sync, angle snap, and profiles.

- [ ] **Step 2: Implement `gui.py`**
Provide full GTK4 notebook UI with DPI & Sensor tab, per-stage color pickers (`Gtk.ColorDialogButton`), RGB strip tab, button remap tab, profile selector (1-4), Breeze-Dark slider warning fixes, and udev installer.

- [ ] **Step 3: Create desktop integration assets**
Generate scalable SVG icon `data/icons/nexus-air.svg` representing the gaming mouse and create standard FreeDesktop `.desktop` entry.

- [ ] **Step 4: Verify local CLI execution with live mouse**
Run: `python3 -m nexus_air.cli status`
Expected: Shows connected mouse status, battery, profile, and DPI stages.

- [ ] **Step 5: Commit**
```bash
git add src/nexus_air/cli.py src/nexus_air/gui.py data/
git commit -m "feat(ui): add modular cli, gtk4 gui and desktop integration assets"
```

---

### Task 4: Packaging Support (AppImage, Arch PKGBUILD, Debian/Ubuntu, RPM)

**Files:**
- Create: `/home/zyqwax/Projects/my-mouse-claws/packaging/appimage/AppRun`
- Create: `/home/zyqwax/Projects/my-mouse-claws/packaging/appimage/build-appimage.sh`
- Create: `/home/zyqwax/Projects/my-mouse-claws/packaging/arch/PKGBUILD`
- Create: `/home/zyqwax/Projects/my-mouse-claws/packaging/debian/control`
- Create: `/home/zyqwax/Projects/my-mouse-claws/packaging/rpm/nexus-air.spec`

**Interfaces:**
- Produces: Standalone AppImage build script and distribution spec files for Arch, Debian/Ubuntu, and Fedora.

- [ ] **Step 1: Create AppRun and AppImage build script**
Script creates an AppDir containing python, desktop file, icon, and bundle launcher using `appimagetool` or portable python runtime.

- [ ] **Step 2: Create Arch Linux PKGBUILD**
Standard Arch/CachyOS PKGBUILD building from source and installing udev rules + desktop entry.

- [ ] **Step 3: Create Debian/Ubuntu and RPM package specs**
Define dependencies (`python3`, `python3-gi`, `gir1.2-gtk-4.0`) and file installation paths (`/usr/bin/nexus-air`, `/usr/share/applications/`, `/etc/udev/rules.d/`).

- [ ] **Step 4: Commit**
```bash
git add packaging/
git commit -m "chore(packaging): add appimage build script and distro packaging specs"
```

---

### Task 5: GitHub Actions CI/CD for Automated Release Builds

**Files:**
- Create: `/home/zyqwax/Projects/my-mouse-claws/.github/workflows/ci.yml`
- Create: `/home/zyqwax/Projects/my-mouse-claws/.github/workflows/release.yml`

**Interfaces:**
- Produces:
  - CI workflow running unittest on every push/PR.
  - Release workflow triggered on `v*` tags building AppImage and sdist/wheel artifacts and attaching them to the GitHub Release.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**
Runs Python unit tests across Python 3.10, 3.11, 3.12, 3.13.

- [ ] **Step 2: Create `.github/workflows/release.yml`**
Builds universal AppImage and python packages, uses `softprops/action-gh-release` to upload assets to GitHub Releases.

- [ ] **Step 3: Commit**
```bash
git add .github/
git commit -m "ci: add github actions for test automation and release builds"
```

---

### Task 6: Comprehensive README.md and Documentation

**Files:**
- Create: `/home/zyqwax/Projects/my-mouse-claws/README.md`
- Create: `/home/zyqwax/Projects/my-mouse-claws/docs/hardware_protocol.md`

**Interfaces:**
- Documents:
  - Hardware model details (Claw's Nexus Air V1, PixArt PAW3325 sensor, Compx 2.4G MCU, VID `0x3554`, PID `0xF512` / `0xF5D5` / `0xF5A7`).
  - Explicit credits: Reverse engineered using **REA (Reverse Engineer Anything)** toolset and **Gemini 4 Argon Medium**.
  - Installation and usage instructions for all distros (Arch/CachyOS, Ubuntu/Debian, Fedora, AppImage).
  - Reverse-engineered EEPROM memory map and protocol specifications.

- [ ] **Step 1: Draft `docs/hardware_protocol.md`**
Document all opcodes (`0x03`, `0x04`, `0x07`, `0x08`, `0x0E`, `0x0F`, `0x12`), EEPROM address map (`0x00..0xBA`), and separate `0xA0`/`0xA7` write requirements.

- [ ] **Step 2: Write complete `README.md`**
Include feature list, screenshots/CLI preview, supported hardware, installation guides, AppImage usage, and the required REA + Gemini 4 Argon Medium acknowledgment.

- [ ] **Step 3: Commit**
```bash
git add README.md docs/
git commit -m "docs: add comprehensive readme with hardware details, credits, and protocol spec"
```
