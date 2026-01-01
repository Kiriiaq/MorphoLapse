"""
Align Step - Étape d'alignement des visages avec support multithreading
"""

import os
import cv2
from typing import Callable, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from ..utils.file_utils import FileUtils
from ..utils.image_utils import ImageUtils
from ..core.face_detector import FaceDetector
from ..core.face_aligner import FaceAligner
from .workflow_manager import WorkflowContext


class AlignmentWorker:
    """Worker thread-safe pour l'alignement d'images"""

    def __init__(self, model_path: str, ref_image, ref_landmarks, border: int,
                 overlay: bool, align_dir: str, logger=None):
        self.model_path = model_path
        self.ref_image = ref_image
        self.ref_landmarks = ref_landmarks
        self.border = border
        self.overlay = overlay
        self.align_dir = align_dir
        self.logger = logger
        self._lock = Lock()

        # Chaque thread aura son propre détecteur (dlib n'est pas thread-safe)
        self._local_detectors = {}

    def _get_detector(self, thread_id: int) -> FaceDetector:
        """Obtient ou crée un détecteur pour ce thread"""
        if thread_id not in self._local_detectors:
            detector = FaceDetector(logger=None)  # Pas de log pour éviter le spam
            detector.initialize(self.model_path)
            self._local_detectors[thread_id] = detector
        return self._local_detectors[thread_id]

    def process_image(self, args: Tuple[int, str, int]) -> Tuple[int, Optional[str], Optional[any], str]:
        """
        Traite une image (appelé par les threads)

        Args:
            args: (index, image_path, thread_id)

        Returns:
            (index, output_path ou None, landmarks ou None, filename)
        """
        idx, image_path, thread_id = args
        filename = os.path.basename(image_path)

        try:
            # Charger l'image
            image = ImageUtils.load_image(image_path)
            if image is None:
                return (idx, None, None, filename)

            # Obtenir le détecteur pour ce thread
            detector = self._get_detector(thread_id)
            aligner = FaceAligner(detector=detector, logger=None)

            # Détecter les landmarks
            landmarks = detector.get_landmarks(image, add_boundary=False)
            if landmarks is None:
                # Copier l'image sans alignement
                output_path = os.path.join(self.align_dir, f"{os.path.splitext(filename)[0]}.jpg")
                ImageUtils.save_image(image, output_path)
                return (idx, output_path, None, filename)

            # Aligner l'image
            aligned = aligner.align_to_reference(
                image, self.ref_image,
                source_landmarks=landmarks,
                reference_landmarks=self.ref_landmarks,
                border=self.border,
                overlay_mode=False,  # Overlay désactivé en mode parallèle
                previous_result=None
            )

            if aligned is not None:
                output_path = os.path.join(self.align_dir, f"{os.path.splitext(filename)[0]}.jpg")
                ImageUtils.save_image(aligned, output_path)

                # Recalculer les landmarks sur l'image alignée
                aligned_landmarks = detector.get_landmarks(aligned, add_boundary=True)
                return (idx, output_path, aligned_landmarks, filename)
            else:
                return (idx, None, None, filename)

        except Exception as e:
            if self.logger:
                with self._lock:
                    self.logger.warning(f"Erreur alignement {filename}: {e}")
            return (idx, None, None, filename)


def align_faces(context: WorkflowContext, progress_callback: Callable, logger=None) -> dict:
    """
    Étape d'alignement des visages sur une référence avec support multithreading.

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
        reference = context.images[0]
        if logger:
            logger.warning(f"Pas de référence définie, utilisation de: {os.path.basename(reference)}")

    # Créer le dossier d'alignement
    align_dir = os.path.join(context.run_dir, "02_align")
    os.makedirs(align_dir, exist_ok=True)

    # Initialiser le détecteur principal
    model_path = context.config.get('model_path', './shape_predictor_68_face_landmarks.dat')
    detector = FaceDetector(logger=logger)

    if not detector.initialize(model_path):
        raise RuntimeError("Impossible d'initialiser le détecteur de visages. Vérifiez le modèle.")

    # Charger l'image de référence
    ref_image = ImageUtils.load_image(reference)
    if ref_image is None:
        raise ValueError(f"Impossible de charger l'image de référence: {reference}")

    ref_landmarks = detector.get_landmarks(ref_image, add_boundary=False)
    if ref_landmarks is None:
        raise ValueError("Impossible de détecter le visage dans l'image de référence")

    # Paramètres
    border = context.config.get('border_size', 0)
    overlay = context.config.get('overlay_mode', False)
    parallel = context.config.get('parallel', True)
    num_threads = context.config.get('num_threads', 0)

    # Déterminer le nombre de threads
    if num_threads <= 0:
        import multiprocessing
        num_threads = max(1, multiprocessing.cpu_count() - 1)

    total = len(context.images)

    # Mode parallèle ou séquentiel
    if parallel and total > 4 and not overlay:
        if logger:
            logger.info(f"Mode parallèle activé ({num_threads} threads)")
        return _align_parallel(
            context, progress_callback, logger,
            model_path, ref_image, ref_landmarks,
            border, overlay, align_dir, num_threads
        )
    else:
        if overlay and parallel:
            if logger:
                logger.info("Mode overlay incompatible avec le parallélisme, passage en séquentiel")
        return _align_sequential(
            context, progress_callback, logger,
            detector, ref_image, ref_landmarks,
            border, overlay, align_dir
        )


def _align_parallel(context: WorkflowContext, progress_callback: Callable, logger,
                    model_path: str, ref_image, ref_landmarks,
                    border: int, overlay: bool, align_dir: str,
                    num_threads: int) -> dict:
    """Alignement en parallèle avec ThreadPoolExecutor"""

    worker = AlignmentWorker(
        model_path, ref_image, ref_landmarks,
        border, overlay, align_dir, logger
    )

    total = len(context.images)
    results = [None] * total
    completed = 0
    lock = Lock()

    # Préparer les tâches avec assignation de thread
    tasks = [(idx, path, idx % num_threads) for idx, path in enumerate(context.images)]

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(worker.process_image, task): task[0] for task in tasks}

        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                results[result[0]] = result

                with lock:
                    completed += 1
                    progress_callback(completed, total, f"Alignement: {result[3]}")

            except Exception as e:
                if logger:
                    logger.warning(f"Erreur thread {idx}: {e}")

    # Extraire les résultats dans l'ordre
    aligned_files = []
    landmarks_list = []
    failed = 0

    for result in results:
        if result is None:
            failed += 1
            landmarks_list.append(None)
            continue

        idx, output_path, landmarks, filename = result
        if output_path:
            aligned_files.append(output_path)
            landmarks_list.append(landmarks)
        else:
            failed += 1
            if logger:
                logger.warning(f"Échec: {filename}")

    # Mettre à jour le contexte
    context.aligned_images = aligned_files
    context.landmarks = landmarks_list

    if logger:
        logger.success(f"{len(aligned_files)} images alignées avec succès")
        if failed > 0:
            logger.warning(f"{failed} images ont échoué")

    return {
        'aligned_count': len(aligned_files),
        'failed_count': failed,
        'align_dir': align_dir,
        'files': aligned_files,
        'mode': 'parallel',
        'threads': num_threads
    }


def _align_sequential(context: WorkflowContext, progress_callback: Callable, logger,
                      detector: FaceDetector, ref_image, ref_landmarks,
                      border: int, overlay: bool, align_dir: str) -> dict:
    """Alignement séquentiel (mode original)"""

    aligner = FaceAligner(detector=detector, logger=logger)

    aligned_files = []
    landmarks_list = []
    total = len(context.images)
    previous = None

    for idx, image_path in enumerate(context.images):
        filename = os.path.basename(image_path)
        progress_callback(idx + 1, total, f"Alignement: {filename}")

        image = ImageUtils.load_image(image_path)
        if image is None:
            if logger:
                logger.warning(f"Impossible de charger: {filename}")
            continue

        landmarks = detector.get_landmarks(image, add_boundary=False)
        if landmarks is None:
            if logger:
                logger.warning(f"Aucun visage détecté: {filename}")
            output_path = os.path.join(align_dir, f"{os.path.splitext(filename)[0]}.jpg")
            ImageUtils.save_image(image, output_path)
            aligned_files.append(output_path)
            landmarks_list.append(None)
            continue

        aligned = aligner.align_to_reference(
            image, ref_image,
            source_landmarks=landmarks,
            reference_landmarks=ref_landmarks,
            border=border,
            overlay_mode=overlay,
            previous_result=previous
        )

        if aligned is not None:
            output_path = os.path.join(align_dir, f"{os.path.splitext(filename)[0]}.jpg")
            ImageUtils.save_image(aligned, output_path)
            aligned_files.append(output_path)

            aligned_landmarks = detector.get_landmarks(aligned, add_boundary=True)
            landmarks_list.append(aligned_landmarks)

            if overlay:
                previous = aligned
        else:
            if logger:
                logger.warning(f"Échec alignement: {filename}")
            landmarks_list.append(None)

    context.aligned_images = aligned_files
    context.landmarks = landmarks_list

    if logger:
        logger.success(f"{len(aligned_files)} images alignées avec succès")

    return {
        'aligned_count': len(aligned_files),
        'align_dir': align_dir,
        'files': aligned_files,
        'mode': 'sequential'
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
