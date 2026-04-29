#!/usr/bin/env python3
"""Build MorphoLapse executable with PyInstaller.

Usage:
    python build.py             # release (default) — windowed, no console
    python build.py debug       # debug — console + --debug=imports
    python build.py release     # release explicit
    python build.py all         # debug then release
    python build.py clean       # remove build/, dist/, *.spec
"""

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
with open(PROJECT_ROOT / "pyproject.toml", "rb") as _f:
    _PYPROJECT = tomllib.load(_f)

APP_NAME = "MorphoLapse"
VERSION = _PYPROJECT["project"]["version"]
ICON = "assets/icons/icone.ico"

HIDDEN_IMPORTS = [
    "customtkinter",
    "darkdetect",
    "cv2",
    "numpy",
    "scipy",
    "scipy.spatial",
    "scipy.spatial._qhull",     # Delaunay C extension
    "dlib",
    "PIL",
    "PIL._tkinter_finder",      # tkinter image bridge for ctk.CTkImage
]

# Packages with C extensions / binary deps that pyinstaller's analysis often
# misses. --collect-submodules walks the package tree, --collect-binaries
# pulls in .pyd / .dll files (essential for scipy.spatial.Delaunay et al).
COLLECT_SUBMODULES = ["scipy"]
COLLECT_BINARIES = ["scipy", "dlib", "cv2"]

EXCLUDE_MODULES = [
    # Heavy libs not used by MorphoLapse
    "pandas", "moviepy", "whisper",
    "oletools", "openpyxl", "reportlab",
    "fitz", "pymupdf", "docx", "pptx", "PyPDF2",
    "matplotlib", "seaborn", "win32com",
    # Dev / interactive
    "pytest", "ruff", "ipython", "jupyter", "notebook",
    # Heavy ML frameworks
    "tensorflow", "torch",
]

GLOBAL_EXCLUDES = [
    "unittest", "test", "tests", "pydoc", "doctest",
    "lib2to3", "ensurepip", "venv", "distutils",
    "setuptools", "pkg_resources", "pip",
    "tkinter.test", "idlelib",
    "matplotlib.tests", "numpy.tests", "pandas.tests", "scipy.tests",
    "PIL.tests",
]


def _common_args(name: str, dist_dir: Path, build_dir: Path) -> list[str]:
    """Build the pyinstaller flag list common to debug and release."""
    cmd: list[str] = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", name,
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(PROJECT_ROOT),
        "--noconfirm",
        "--noupx",                  # avoid AV false positives
    ]
    icon_path = PROJECT_ROOT / ICON
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
    else:
        print(f"WARN: icon not found at {icon_path}", file=sys.stderr)

    for hi in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", hi])
    for pkg in COLLECT_SUBMODULES:
        cmd.extend(["--collect-submodules", pkg])
    for pkg in COLLECT_BINARIES:
        cmd.extend(["--collect-binaries", pkg])
    for mod in EXCLUDE_MODULES + GLOBAL_EXCLUDES:
        cmd.extend(["--exclude-module", mod])
    for data_dir in ["assets", "src", "config"]:
        src_path = PROJECT_ROOT / data_dir
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{os.pathsep}{data_dir}"])
    return cmd


def build(profile: str) -> Path:
    """Build for given profile: 'debug' or 'release'. Returns exe path."""
    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"

    # Clean stale .spec only (keep build/ for incremental cache)
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
    dist_dir.mkdir(exist_ok=True)

    if profile == "debug":
        name = f"{APP_NAME}-debug"
        mode_args = ["--console", "--debug=imports"]
    elif profile == "release":
        name = APP_NAME
        mode_args = ["--windowed"]
    else:
        raise ValueError(f"Unknown profile: {profile!r}")

    cmd = _common_args(name, dist_dir, build_dir)
    cmd.extend(mode_args)
    cmd.append(str(PROJECT_ROOT / "main.py"))

    print(f"=== Building {name}.exe (profile={profile}, version={VERSION}) ===")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    # Cleanup .spec; keep build/ across calls for incremental rebuild speed
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()

    exe = dist_dir / f"{name}.exe"
    if result.returncode == 0 and exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"OK: {exe.name} ({size_mb:.1f} MB) -> {exe}")
        return exe
    else:
        print(f"BUILD FAILED for profile={profile} (returncode={result.returncode})", file=sys.stderr)
        sys.exit(1)


def clean() -> None:
    """Remove build/, dist/, *.spec."""
    for d in [PROJECT_ROOT / "build", PROJECT_ROOT / "dist"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"Removed: {d.name}/")
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
        print(f"Removed: {spec.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Build {APP_NAME} v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "profile",
        nargs="?",
        default="release",
        choices=["debug", "release", "all", "clean"],
        help="Build profile (default: release)",
    )
    args = parser.parse_args()

    if args.profile == "clean":
        clean()
    elif args.profile == "all":
        build("debug")
        build("release")
    else:
        build(args.profile)


if __name__ == "__main__":
    main()
