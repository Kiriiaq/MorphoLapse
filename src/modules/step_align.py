"""
Align Step - Étape d'alignement des visages
"""

import os
import cv2
from typing import Callable
from ..utils.file_utils import FileUtils
from ..utils.image_utils import ImageUtils
from ..core.face_detector import FaceDetector
from ..core.face_aligner import FaceAligner
from .workflow_manager import WorkflowContext


def align_faces(context: WorkflowContext, progress_callback: Callable, logger=None) -> dict:
    """
    Étape d'alignement des visages sur une référence.

    Args:
        context: Contexte du workflow
        progress_callback: Callback(current, total, message)
        logger: Logger instance

    Returns:
        Dictionnaire des résultats
    """
    if logger:
        logger.info("Démarrage de l'alignement des visages")

    # Vérifier les prérequis
    if not context.images:
        raise ValueError("Aucune image à aligner. Exécutez d'abord l'étape d'import.")

    reference = context.reference_image
    if not reference or not os.path.exists(reference):
        # Utiliser la première image comme référence
        reference = context.images[0]
        if logger:
            logger.warning(f"Pas de référence définie, utilisation de: {os.path.basename(reference)}")

    # Créer le dossier d'alignement
    align_dir = os.path.join(context.run_dir, "02_align")
    os.makedirs(align_dir, exist_ok=True)

    # Initialiser le détecteur et l'aligneur
    model_path = context.config.get('model_path', './shape_predictor_68_face_landmarks.dat')
    detector = FaceDetector(logger=logger)

    if not detector.initialize(model_path):
        raise RuntimeError("Impossible d'initialiser le détecteur de visages. Vérifiez le modèle.")

    aligner = FaceAligner(detector=detector, logger=logger)

    # Charger l'image de référence
    ref_image = ImageUtils.load_image(reference)
    if ref_image is None:
        raise ValueError(f"Impossible de charger l'image de référence: {reference}")

    ref_landmarks = detector.get_landmarks(ref_image, add_boundary=False)
    if ref_landmarks is None:
        raise ValueError("Impossible de détecter le visage dans l'image de référence")

    # Paramètres d'alignement
    border = context.config.get('border_size', 0)
    overlay = context.config.get('overlay_mode', False)

    aligned_files = []
    landmarks_list = []
    total = len(context.images)
    previous = None

    for idx, image_path in enumerate(context.images):
        filename = os.path.basename(image_path)
        progress_callback(idx + 1, total, f"Alignement: {filename}")

        # Charger l'image
        image = ImageUtils.load_image(image_path)
        if image is None:
            if logger:
                logger.warning(f"Impossible de charger: {filename}")
            continue

        # Détecter les landmarks
        landmarks = detector.get_landmarks(image, add_boundary=False)
        if landmarks is None:
            if logger:
                logger.warning(f"Aucun visage détecté: {filename}")
            # Copier l'image sans alignement
            output_path = os.path.join(align_dir, f"{os.path.splitext(filename)[0]}.jpg")
            ImageUtils.save_image(image, output_path)
            aligned_files.append(output_path)
            landmarks_list.append(None)
            continue

        # Aligner l'image
        aligned = aligner.align_to_reference(
            image, ref_image,
            source_landmarks=landmarks,
            reference_landmarks=ref_landmarks,
            border=border,
            overlay_mode=overlay,
            previous_result=previous
        )

        if aligned is not None:
            # Sauvegarder
            output_path = os.path.join(align_dir, f"{os.path.splitext(filename)[0]}.jpg")
            ImageUtils.save_image(aligned, output_path)
            aligned_files.append(output_path)

            # Recalculer les landmarks sur l'image alignée
            aligned_landmarks = detector.get_landmarks(aligned, add_boundary=True)
            landmarks_list.append(aligned_landmarks)

            if overlay:
                previous = aligned
        else:
            if logger:
                logger.warning(f"Échec alignement: {filename}")
            landmarks_list.append(None)

    # Mettre à jour le contexte
    context.aligned_images = aligned_files
    context.landmarks = landmarks_list

    if logger:
        logger.success(f"{len(aligned_files)} images alignées avec succès")

    return {
        'aligned_count': len(aligned_files),
        'align_dir': align_dir,
        'files': aligned_files
    }


class AlignStep:
    """Classe wrapper pour l'étape d'alignement"""

    ID = "02_align"
    NAME = "Alignement des visages"
    DESCRIPTION = "Aligne tous les visages sur une image de référence"

    @staticmethod
    def create_step():
        """Crée l'instance WorkflowStep"""
        from .workflow_manager import WorkflowStep
        return WorkflowStep(
            id=AlignStep.ID,
            name=AlignStep.NAME,
            description=AlignStep.DESCRIPTION,
            function=align_faces
        )
