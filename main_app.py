#!/usr/bin/env python3
"""
MorphoLapse 2.0
===============

Application professionnelle de morphing facial avec interface graphique moderne.
Créez des vidéos time-lapse de morphing facial à partir de séries de photos.

Usage:
    python main_app.py              # Lance l'interface graphique
    python main_app.py --cli        # Mode ligne de commande
    python main_app.py --help       # Affiche l'aide

Auteur: MorphoLapse Team
Version: 2.0.0
Licence: MIT
"""

import sys
import os
import argparse
import ctypes

# Définir l'AppUserModelID pour Windows (icône dans la barre des tâches)
if sys.platform == 'win32':
    try:
        myappid = 'morpholapse.facemorphing.app.2.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    missing = []

    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")

    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    try:
        import dlib
    except ImportError:
        missing.append("dlib")

    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    try:
        from scipy.spatial import Delaunay
    except ImportError:
        missing.append("scipy")

    if missing:
        print("=" * 60)
        print("ERREUR: Dépendances manquantes")
        print("=" * 60)
        print("\nInstallez les dépendances avec:")
        print(f"\n    pip install {' '.join(missing)}")
        print("\nOu installez tout avec:")
        print("\n    pip install -r requirements.txt")
        print("=" * 60)
        return False

    return True


def check_model():
    """Vérifie que le modèle dlib est présent"""
    model_paths = [
        "./shape_predictor_68_face_landmarks.dat",
        "assets/shape_predictor_68_face_landmarks.dat",
        "../shape_predictor_68_face_landmarks.dat"
    ]

    for path in model_paths:
        if os.path.exists(path):
            return True

    print("=" * 60)
    print("ATTENTION: Modèle de détection faciale non trouvé")
    print("=" * 60)
    print("\nTéléchargez le modèle depuis:")
    print("http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2")
    print("\nDécompressez-le et placez-le à la racine du projet.")
    print("=" * 60)
    return False


def run_gui():
    """Lance l'interface graphique"""
    from src.ui.main_window import run_app
    run_app()


def run_cli(args):
    """Lance en mode ligne de commande"""
    from src.utils.logger import Logger
    from src.utils.config_manager import ConfigManager
    from src.modules.workflow_manager import WorkflowManager
    from src.modules.step_import import ImportStep
    from src.modules.step_align import AlignStep
    from src.modules.step_morph import MorphStep
    from src.modules.step_export import ExportStep

    logger = Logger("MorphoLapse")
    config_manager = ConfigManager()
    config_manager.load()

    # Créer le workflow
    workflow = WorkflowManager(logger=logger, config_manager=config_manager)
    workflow.add_step(ImportStep.create_step())
    workflow.add_step(AlignStep.create_step())
    workflow.add_step(MorphStep.create_step())
    workflow.add_step(ExportStep.create_step())

    # Configurer le contexte
    workflow.set_context(
        input_dir=args.input,
        reference_image=args.reference or "",
        output_dir=args.output or "",
        config={
            'model_path': args.model or './shape_predictor_68_face_landmarks.dat',
            'fps': args.fps,
            'transition_duration': args.transition,
            'pause_duration': args.pause,
            'border_size': args.border,
            'overlay_mode': args.overlay
        }
    )

    # Exécuter
    success = workflow.run(continue_on_error=args.continue_on_error)

    return 0 if success else 1


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="MorphoLapse 2.0 - Morphing facial professionnel & Time-lapse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python main_app.py                              # Interface graphique
  python main_app.py --cli -i images/ -o output/  # Mode CLI
  python main_app.py --cli -i images/ --fps 30    # CLI avec options

Pour plus d'informations: https://github.com/morpholapse
        """
    )

    parser.add_argument(
        '--cli', action='store_true',
        help='Mode ligne de commande (sans interface graphique)'
    )

    # Options CLI
    cli_group = parser.add_argument_group('Options CLI')
    cli_group.add_argument(
        '-i', '--input', type=str,
        help='Dossier contenant les images sources'
    )
    cli_group.add_argument(
        '-o', '--output', type=str,
        help='Dossier de sortie'
    )
    cli_group.add_argument(
        '-r', '--reference', type=str,
        help='Image de référence pour l\'alignement'
    )
    cli_group.add_argument(
        '-m', '--model', type=str,
        help='Chemin vers le modèle dlib'
    )

    # Paramètres de morphing
    morph_group = parser.add_argument_group('Paramètres de morphing')
    morph_group.add_argument(
        '--fps', type=int, default=25,
        help='Images par seconde (défaut: 25)'
    )
    morph_group.add_argument(
        '--transition', type=float, default=3.0,
        help='Durée de transition en secondes (défaut: 3.0)'
    )
    morph_group.add_argument(
        '--pause', type=float, default=0.0,
        help='Durée de pause entre transitions (défaut: 0.0)'
    )

    # Paramètres d'alignement
    align_group = parser.add_argument_group('Paramètres d\'alignement')
    align_group.add_argument(
        '--border', type=int, default=0,
        help='Bordure en pixels (défaut: 0)'
    )
    align_group.add_argument(
        '--overlay', action='store_true',
        help='Mode superposition'
    )

    # Options workflow
    workflow_group = parser.add_argument_group('Options workflow')
    workflow_group.add_argument(
        '--continue-on-error', action='store_true',
        help='Continuer même en cas d\'erreur'
    )

    args = parser.parse_args()

    # Vérifier les dépendances
    if not check_dependencies():
        sys.exit(1)

    # Vérifier le modèle (avertissement seulement)
    check_model()

    if args.cli:
        # Mode CLI
        if not args.input:
            parser.error("En mode CLI, --input est requis")
        sys.exit(run_cli(args))
    else:
        # Mode GUI
        run_gui()


if __name__ == "__main__":
    main()
