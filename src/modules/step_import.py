"""
Import Step - Étape d'importation des images
"""

import os
import shutil
from typing import Callable, Any
from ..utils.file_utils import FileUtils
from ..utils.image_utils import ImageUtils
from .workflow_manager import WorkflowContext


def import_images(context: WorkflowContext, progress_callback: Callable, logger=None) -> dict:
    """
    Étape d'importation des images sources.

    Args:
        context: Contexte du workflow
        progress_callback: Callback(current, total, message)
        logger: Logger instance

    Returns:
        Dictionnaire des résultats
    """
    if logger:
        logger.info("Démarrage de l'importation des images")

    input_dir = context.input_dir
    if not input_dir or not os.path.isdir(input_dir):
        raise ValueError(f"Répertoire d'entrée invalide: {input_dir}")

    # Créer le dossier d'import dans le run
    import_dir = os.path.join(context.run_dir, "01_import")
    os.makedirs(import_dir, exist_ok=True)

    # Lister les images
    image_files = FileUtils.get_image_files(input_dir)
    if not image_files:
        raise ValueError(f"Aucune image trouvée dans: {input_dir}")

    if logger:
        logger.info(f"Trouvé {len(image_files)} images à importer")

    # Copier et traiter les images
    imported = []
    total = len(image_files)

    for idx, src_path in enumerate(image_files):
        filename = os.path.basename(src_path)

        # Renommer pour tri lexicographique si nécessaire
        name, ext = os.path.splitext(filename)
        new_name = FileUtils.pad_numbers_in_filename(name) + ext
        dst_path = os.path.join(import_dir, new_name)

        # Copier le fichier
        shutil.copy2(src_path, dst_path)
        imported.append(dst_path)

        progress_callback(idx + 1, total, f"Import: {filename}")

    # Mettre à jour le contexte
    context.images = sorted(imported)

    if logger:
        logger.success(f"{len(imported)} images importées avec succès")

    return {
        'imported_count': len(imported),
        'import_dir': import_dir,
        'files': imported
    }


class ImportStep:
    """Classe wrapper pour l'étape d'import"""

    ID = "01_import"
    NAME = "Import des images"
    DESCRIPTION = "Importe et prépare les images sources pour le traitement"

    @staticmethod
    def create_step():
        """Crée l'instance WorkflowStep"""
        from .workflow_manager import WorkflowStep
        return WorkflowStep(
            id=ImportStep.ID,
            name=ImportStep.NAME,
            description=ImportStep.DESCRIPTION,
            function=import_images
        )
