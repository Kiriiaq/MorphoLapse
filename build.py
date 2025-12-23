#!/usr/bin/env python3
"""
Script de build pour MorphoLapse
Genere l'executable portable unique via PyInstaller
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
        "releases",
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


def build_executable():
    """Construit l'executable unique portable (onefile, sans console)"""
    print("\n" + "=" * 60)
    print("BUILD EXECUTABLE UNIQUE - MorphoLapse.exe")
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

        # Verifier que l'executable existe
        exe_path = Path("dist/MorphoLapse.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1024 / 1024
            print(f"\n[OK] Build termine avec succes!")
            print(f"     -> dist/MorphoLapse.exe ({size_mb:.1f} MB)")
            return True
        else:
            print("[ERREUR] Executable non trouve apres le build")
            return False
    except subprocess.CalledProcessError as e:
        print(f"[ERREUR] Build echoue: {e}")
        return False


def create_release_zip():
    """Cree l'archive ZIP pour la release"""
    platform_name = get_platform_name()
    releases_dir = Path("releases")
    releases_dir.mkdir(exist_ok=True)

    exe_path = Path("dist/MorphoLapse.exe")
    if not exe_path.exists():
        print("[ERREUR] Executable non trouve")
        return None

    archive_name = f"{APP_NAME}-v{VERSION}-{platform_name}"
    archive_path = releases_dir / f"{archive_name}.zip"

    # Creer un ZIP contenant juste l'executable
    import zipfile
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, "MorphoLapse.exe")

    size_mb = archive_path.stat().st_size / 1024 / 1024
    print(f"[OK] Archive: {archive_path} ({size_mb:.1f} MB)")
    return archive_path


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


def check_spec_file():
    """Verifie que le fichier .spec existe"""
    spec_path = Path("MorphoLapse.spec")
    if not spec_path.exists():
        print("[ERREUR] Fichier MorphoLapse.spec manquant")
        return False

    print("[OK] Fichier MorphoLapse.spec trouve")
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
        description="Build MorphoLapse - Executable portable unique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python build.py --all       # Build complet (nettoyage + build + archive)
  python build.py --build     # Build executable uniquement
  python build.py --clean     # Nettoyer les fichiers de build
  python build.py --archive   # Creer l'archive ZIP
        """
    )

    parser.add_argument("--clean", action="store_true",
                        help="Nettoyer les fichiers de build")
    parser.add_argument("--build", action="store_true",
                        help="Construire l'executable portable")
    parser.add_argument("--archive", action="store_true",
                        help="Creer l'archive ZIP de distribution")
    parser.add_argument("--all", action="store_true",
                        help="Executer toutes les etapes")

    args = parser.parse_args()

    # Si aucun argument, afficher l'aide
    if not any([args.clean, args.build, args.archive, args.all]):
        parser.print_help()
        return

    print("\n" + "=" * 60)
    print(f"  MorphoLapse Build System v{VERSION}")
    print("=" * 60)

    # Verifications
    if not check_dependencies():
        sys.exit(1)

    if (args.build or args.all) and not check_spec_file():
        sys.exit(1)

    check_icon()

    # Executer les etapes
    if args.clean or args.all:
        print("\n--- Nettoyage ---")
        clean_build()

    if args.build or args.all:
        if not build_executable():
            sys.exit(1)

    if args.archive or args.all:
        print("\n--- Creation de l'archive ---")
        create_release_zip()

    print("\n" + "=" * 60)
    print("  BUILD TERMINE AVEC SUCCES!")
    print("=" * 60)


if __name__ == "__main__":
    main()
