#!/usr/bin/env python3
"""Build MorphoLapse executable with PyInstaller.

Usage:
    python build.py                       # release onefile (default)
    python build.py debug                 # debug onefile (console + --debug=imports)
    python build.py release               # release onefile explicit
    python build.py debug   --onedir      # debug onedir (FAST startup, folder output)
    python build.py release --onedir      # release onedir
    python build.py all                   # debug + release, both onefile
    python build.py all     --onedir      # both onedir
    python build.py clean                 # purge build/, dist/, *.spec

Modes:
    onefile  : single .exe, extracts to %TEMP% on launch (~1.5-2s cold, 197 MB)
    onedir   : folder dist/<name>/ with EXE + DLLs (~300-500ms cold, ~390 MB total
               but only ~12 MB for the EXE itself; rest is DLL/.pyd in _internal/)
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

# --collect-all = submodules + binaries + datas (atomic). Required for scipy
# in --onedir mode, where separate --collect-submodules + --collect-binaries
# can miss inter-package .pyd resolution. Also safer for dlib / cv2 / customtkinter.
COLLECT_ALL = ["scipy", "dlib", "cv2", "customtkinter"]

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
    # PIL plugins we never use (we read JPEG/PNG/BMP/GIF/WEBP/TIFF only — gain ~1 MB)
    "PIL.ImageQt", "PIL.PdfImagePlugin", "PIL.PsdImagePlugin",
    "PIL.IcnsImagePlugin", "PIL.WmfImagePlugin",
]

GLOBAL_EXCLUDES = [
    "lib2to3", "ensurepip", "venv",
    "setuptools", "pkg_resources", "pip",
    "tkinter.test", "idlelib",
    "matplotlib.tests", "numpy.tests", "pandas.tests", "scipy.tests",
    "PIL.tests",
]

# Excludes safe to apply ONLY in --onefile mode. PyInstaller in --onefile
# bundles the entire pyc archive into the exe even when transitive imports
# pull in these modules; the runtime archive contains them anyway. In
# --onedir mode the same excludes physically remove the .pyd files, which
# breaks numpy.testing -> unittest -> scipy._lib chain at runtime. Tested.
ONEFILE_ONLY_EXCLUDES = [
    "unittest", "doctest", "pydoc", "distutils",
]


def _common_args(name: str, dist_dir: Path, build_dir: Path, onedir: bool) -> list[str]:
    """Build the pyinstaller flag list common to debug and release."""
    cmd: list[str] = [
        sys.executable, "-m", "PyInstaller",
        "--onedir" if onedir else "--onefile",
        "--name", name,
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(PROJECT_ROOT),
        "--noconfirm",
        "--noupx",                  # AV false positives; --upx not used
        "--optimize", "2",          # python -O equivalent (drop assertions, __debug__)
    ]
    icon_path = PROJECT_ROOT / ICON
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
    else:
        print(f"WARN: icon not found at {icon_path}", file=sys.stderr)

    for hi in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", hi])
    for pkg in COLLECT_ALL:
        cmd.extend(["--collect-all", pkg])
    excludes = EXCLUDE_MODULES + GLOBAL_EXCLUDES
    if not onedir:
        excludes = excludes + ONEFILE_ONLY_EXCLUDES
    for mod in excludes:
        cmd.extend(["--exclude-module", mod])
    for data_dir in ["assets", "src", "config"]:
        src_path = PROJECT_ROOT / data_dir
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{os.pathsep}{data_dir}"])
    return cmd


def _measure_size(path: Path) -> str:
    """Return human-readable size for an EXE (onefile) or a folder (onedir)."""
    if path.is_file():
        return f"{path.stat().st_size / (1024 * 1024):.1f} MB"
    total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    n = sum(1 for p in path.rglob("*") if p.is_file())
    return f"{total / (1024 * 1024):.1f} MB across {n} files"


def build(profile: str, onedir: bool = False) -> Path:
    """Build for given profile. Returns the EXE path (or the onedir folder root)."""
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

    cmd = _common_args(name, dist_dir, build_dir, onedir)
    cmd.extend(mode_args)
    cmd.append(str(PROJECT_ROOT / "main.py"))

    layout = "onedir" if onedir else "onefile"
    print(f"=== Building {name} ({profile}, {layout}, version={VERSION}) ===")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))  # noqa: S603

    # Cleanup .spec; keep build/ across calls for incremental rebuild speed
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()

    if onedir:
        target = dist_dir / name
        exe = target / f"{name}.exe"
    else:
        target = dist_dir / f"{name}.exe"
        exe = target

    if result.returncode == 0 and exe.exists():
        print(f"OK: {target.name} ({_measure_size(target)}) -> {target}")
        return target
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
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="--onedir layout (folder, faster cold start) instead of --onefile",
    )
    args = parser.parse_args()

    if args.profile == "clean":
        clean()
    elif args.profile == "all":
        build("debug", onedir=args.onedir)
        build("release", onedir=args.onedir)
    else:
        build(args.profile, onedir=args.onedir)


if __name__ == "__main__":
    main()
