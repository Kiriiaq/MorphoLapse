#!/usr/bin/env python3
"""
Script de build pour MorphoLapse
Genere les executables Production et Debug via PyInstaller
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

# Configuration
APP_NAME = "MorphoLapse"
VERSION = "2.0.0"


def get_platform_name():
    """Retourne le nom de la plateforme"""
    system = platform.system().lower()
    if system == "windows":
        return "win64"
    elif system == "darwin":
        return "macos"
    else:
        return "linux"


def clean_build():
    """Nettoie les dossiers de build precedents"""
    items_to_clean = [
        "build",
        "dist",
        "__pycache__",
        "src/__pycache__",
        "src/core/__pycache__",
        "src/ui/__pycache__",
        "src/utils/__pycache__",
        "src/modules/__pycache__",
        "tests/__pycache__",
    ]

    for item in items_to_clean:
        path = Path(item)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
                print(f"[OK] Supprime: {item}")
            else:
                path.unlink()
                print(f"[OK] Supprime: {item}")


def build_production():
    """Construit l'executable de production (sans console)"""
    print("\n" + "=" * 60)
    print("BUILD PRODUCTION - MorphoLapse.exe")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "MorphoLapse.spec"
    ]

    print(f"Commande: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        print("\n[OK] Build PRODUCTION termine avec succes!")
        print(f"     -> dist/MorphoLapse/MorphoLapse.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERREUR] Build production echoue: {e}")
        return False


def build_debug():
    """Construit l'executable de debug (avec console)"""
    print("\n" + "=" * 60)
    print("BUILD DEBUG - MorphoLapse_debug.exe")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "MorphoLapse_debug.spec"
    ]

    print(f"Commande: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        print("\n[OK] Build DEBUG termine avec succes!")
        print(f"     -> dist/MorphoLapse_debug/MorphoLapse_debug.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERREUR] Build debug echoue: {e}")
        return False


def create_release_archives():
    """Cree les archives de distribution"""
    platform_name = get_platform_name()
    releases_dir = Path("releases")
    releases_dir.mkdir(exist_ok=True)

    archives_created = []

    # Archive Production
    prod_dist = Path("dist/MorphoLapse")
    if prod_dist.exists():
        archive_name = f"{APP_NAME}-v{VERSION}-{platform_name}"
        if platform_name == "win64":
            archive_path = releases_dir / f"{archive_name}.zip"
            shutil.make_archive(str(releases_dir / archive_name), "zip", "dist", "MorphoLapse")
        else:
            archive_path = releases_dir / f"{archive_name}.tar.gz"
            shutil.make_archive(str(releases_dir / archive_name), "gztar", "dist", "MorphoLapse")

        size_mb = archive_path.stat().st_size / 1024 / 1024
        print(f"[OK] Archive Production: {archive_path} ({size_mb:.1f} MB)")
        archives_created.append(archive_path)

    # Archive Debug
    debug_dist = Path("dist/MorphoLapse_debug")
    if debug_dist.exists():
        archive_name = f"{APP_NAME}_debug-v{VERSION}-{platform_name}"
        if platform_name == "win64":
            archive_path = releases_dir / f"{archive_name}.zip"
            shutil.make_archive(str(releases_dir / archive_name), "zip", "dist", "MorphoLapse_debug")
        else:
            archive_path = releases_dir / f"{archive_name}.tar.gz"
            shutil.make_archive(str(releases_dir / archive_name), "gztar", "dist", "MorphoLapse_debug")

        size_mb = archive_path.stat().st_size / 1024 / 1024
        print(f"[OK] Archive Debug: {archive_path} ({size_mb:.1f} MB)")
        archives_created.append(archive_path)

    return archives_created


def check_dependencies():
    """Verifie que PyInstaller est installe"""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("[ERREUR] PyInstaller n'est pas installe.")
        print("         Installez-le avec: pip install pyinstaller")
        return False


def check_spec_files():
    """Verifie que les fichiers .spec existent"""
    specs = ["MorphoLapse.spec", "MorphoLapse_debug.spec"]
    missing = [s for s in specs if not Path(s).exists()]

    if missing:
        print(f"[ERREUR] Fichiers .spec manquants: {missing}")
        return False

    print("[OK] Fichiers .spec trouves")
    return True


def check_icon():
    """Verifie que l'icone existe"""
    icon_path = Path("ico/icone.ico")
    if icon_path.exists():
        print(f"[OK] Icone trouvee: {icon_path}")
        return True
    else:
        print(f"[ATTENTION] Icone non trouvee: {icon_path}")
        return False


def main():
    """Point d'entree principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build MorphoLapse - Generateur d'executables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python build.py --all          # Build complet (production + debug + archives)
  python build.py --production   # Build production uniquement
  python build.py --debug        # Build debug uniquement
  python build.py --clean        # Nettoyer les fichiers de build
        """
    )

    parser.add_argument("--clean", action="store_true",
                        help="Nettoyer les fichiers de build")
    parser.add_argument("--production", action="store_true",
                        help="Construire l'executable de production")
    parser.add_argument("--debug", action="store_true",
                        help="Construire l'executable de debug")
    parser.add_argument("--archive", action="store_true",
                        help="Creer les archives de distribution")
    parser.add_argument("--all", action="store_true",
                        help="Executer toutes les etapes")

    args = parser.parse_args()

    # Si aucun argument, afficher l'aide
    if not any([args.clean, args.production, args.debug, args.archive, args.all]):
        parser.print_help()
        return

    print("\n" + "=" * 60)
    print(f"  MorphoLapse Build System v{VERSION}")
    print("=" * 60)

    # Verifications
    if not check_dependencies():
        sys.exit(1)

    if (args.production or args.debug or args.all) and not check_spec_files():
        sys.exit(1)

    check_icon()

    # Executer les etapes
    if args.clean or args.all:
        print("\n--- Nettoyage ---")
        clean_build()

    if args.production or args.all:
        if not build_production():
            sys.exit(1)

    if args.debug or args.all:
        if not build_debug():
            sys.exit(1)

    if args.archive or args.all:
        print("\n--- Creation des archives ---")
        create_release_archives()

    print("\n" + "=" * 60)
    print("  BUILD TERMINE AVEC SUCCES!")
    print("=" * 60)


if __name__ == "__main__":
    main()
