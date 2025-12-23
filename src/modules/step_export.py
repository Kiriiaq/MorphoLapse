"""
Export Step - Étape d'export et de finalisation
"""

import os
import shutil
import json
from datetime import datetime
from typing import Callable
from ..utils.file_utils import FileUtils
from .workflow_manager import WorkflowContext


def export_results(context: WorkflowContext, progress_callback: Callable, logger=None) -> dict:
    """
    Étape d'export des résultats finaux.

    Args:
        context: Contexte du workflow
        progress_callback: Callback(current, total, message)
        logger: Logger instance

    Returns:
        Dictionnaire des résultats
    """
    if logger:
        logger.info("Démarrage de l'export des résultats")

    # Créer le dossier d'export
    export_dir = os.path.join(context.run_dir, "04_export")
    os.makedirs(export_dir, exist_ok=True)

    exported_files = []
    total_steps = 4
    current_step = 0

    # 1. Copier la vidéo finale si elle existe
    current_step += 1
    progress_callback(current_step, total_steps, "Export de la vidéo...")

    if context.output_video and os.path.exists(context.output_video):
        video_name = os.path.basename(context.output_video)
        final_video = os.path.join(export_dir, f"final_{video_name}")
        shutil.copy2(context.output_video, final_video)
        exported_files.append(final_video)
        if logger:
            logger.info(f"Vidéo exportée: {final_video}")

    # 2. Créer un résumé JSON
    current_step += 1
    progress_callback(current_step, total_steps, "Génération du résumé...")

    summary = {
        'timestamp': datetime.now().isoformat(),
        'run_dir': context.run_dir,
        'input': {
            'source_dir': context.input_dir,
            'image_count': len(context.images),
            'reference': context.reference_image
        },
        'output': {
            'video': context.output_video,
            'aligned_count': len(context.aligned_images) if context.aligned_images else 0
        },
        'config': context.config,
        'files': {
            'imported': [os.path.basename(f) for f in context.images],
            'aligned': [os.path.basename(f) for f in context.aligned_images] if context.aligned_images else []
        }
    }

    summary_path = os.path.join(export_dir, "run_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    exported_files.append(summary_path)

    # 3. Copier la première et dernière image alignée
    current_step += 1
    progress_callback(current_step, total_steps, "Export des images clés...")

    if context.aligned_images:
        first_img = context.aligned_images[0]
        last_img = context.aligned_images[-1]

        first_export = os.path.join(export_dir, "first_frame.jpg")
        last_export = os.path.join(export_dir, "last_frame.jpg")

        shutil.copy2(first_img, first_export)
        shutil.copy2(last_img, last_export)
        exported_files.extend([first_export, last_export])

    # 4. Générer un fichier de métadonnées
    current_step += 1
    progress_callback(current_step, total_steps, "Génération des métadonnées...")

    metadata = {
        'project': 'MorphoLapse',
        'version': '2.0.0',
        'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'source_images': len(context.images),
        'fps': context.config.get('fps', 25),
        'transition_duration': context.config.get('transition_duration', 3.0),
        'output_format': 'MP4 (H.264)'
    }

    metadata_path = os.path.join(export_dir, "metadata.txt")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write("=" * 50 + "\n")
        f.write("MORPHOLAPSE - RUN REPORT\n")
        f.write("=" * 50 + "\n\n")
        for key, value in metadata.items():
            f.write(f"{key}: {value}\n")
        f.write("\n" + "=" * 50 + "\n")
    exported_files.append(metadata_path)

    # Copier le contenu final vers output_dir si défini
    if context.output_dir and context.output_dir != export_dir:
        os.makedirs(context.output_dir, exist_ok=True)
        for file_path in exported_files:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                dest = os.path.join(context.output_dir, filename)
                shutil.copy2(file_path, dest)

    if logger:
        logger.success(f"Export terminé: {len(exported_files)} fichiers")

    return {
        'export_dir': export_dir,
        'exported_files': exported_files,
        'summary_path': summary_path
    }


class ExportStep:
    """Classe wrapper pour l'étape d'export"""

    ID = "04_export"
    NAME = "Export des résultats"
    DESCRIPTION = "Exporte la vidéo finale et génère les rapports"

    @staticmethod
    def create_step():
        """Crée l'instance WorkflowStep"""
        from .workflow_manager import WorkflowStep
        return WorkflowStep(
            id=ExportStep.ID,
            name=ExportStep.NAME,
            description=ExportStep.DESCRIPTION,
            function=export_results
        )
