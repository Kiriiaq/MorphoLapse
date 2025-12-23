"""
Face Aligner - Module d'alignement des visages
"""

import numpy as np
import cv2
from typing import Optional, Tuple, Dict
from .face_detector import FaceDetector


class FaceAligner:
    """Aligne les visages sur une image de référence via transformation Procrustes"""

    def __init__(self, detector: FaceDetector = None, logger=None):
        """
        Initialise l'aligneur de visages.

        Args:
            detector: Instance de FaceDetector (créé automatiquement si None)
            logger: Instance du logger
        """
        self.detector = detector
        self.logger = logger
        self._cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

    def set_detector(self, detector: FaceDetector):
        """Définit le détecteur de visages"""
        self.detector = detector

    def align_to_reference(self, source_image: np.ndarray,
                           reference_image: np.ndarray,
                           source_landmarks: np.ndarray = None,
                           reference_landmarks: np.ndarray = None,
                           border: int = 0,
                           overlay_mode: bool = False,
                           previous_result: np.ndarray = None) -> Optional[np.ndarray]:
        """
        Aligne une image source sur une image de référence.

        Args:
            source_image: Image à aligner
            reference_image: Image de référence
            source_landmarks: Landmarks de l'image source (détection auto si None)
            reference_landmarks: Landmarks de la référence (détection auto si None)
            border: Taille de bordure blanche à ajouter
            overlay_mode: Superposer sur le résultat précédent
            previous_result: Résultat précédent pour overlay

        Returns:
            Image alignée ou None en cas d'erreur
        """
        if self.detector is None:
            self._log_error("Aucun détecteur configuré")
            return None

        # Obtenir les landmarks si non fournis
        if source_landmarks is None:
            source_landmarks = self.detector.get_landmarks(source_image, add_boundary=False)
            if source_landmarks is None:
                self._log_error("Impossible de détecter le visage source")
                return None

        if reference_landmarks is None:
            reference_landmarks = self.detector.get_landmarks(reference_image, add_boundary=False)
            if reference_landmarks is None:
                self._log_error("Impossible de détecter le visage de référence")
                return None

        # Calculer la transformation
        align_points = FaceDetector.ALIGN_POINTS
        transformation = self._compute_transformation(
            reference_landmarks[align_points],
            source_landmarks[align_points]
        )

        # Inverser la transformation
        M = cv2.invertAffineTransform(transformation[:2])

        # Ajouter bordure si demandé
        image_to_warp = source_image.copy()
        if border > 0:
            image_to_warp = cv2.copyMakeBorder(
                image_to_warp, border, border, border, border,
                borderType=cv2.BORDER_CONSTANT,
                value=(255, 255, 255)
            )

        # Appliquer la transformation
        aligned = self._warp_image(
            image_to_warp, M, reference_image.shape,
            previous=previous_result if overlay_mode else None
        )

        return aligned

    def align_batch(self, images: list, reference_image: np.ndarray,
                    border: int = 0, overlay: bool = False,
                    progress_callback=None) -> list:
        """
        Aligne un lot d'images sur une référence.

        Args:
            images: Liste de tuples (chemin, image) ou d'images
            reference_image: Image de référence
            border: Taille de bordure
            overlay: Mode superposition
            progress_callback: Callback(index, total, message)

        Returns:
            Liste d'images alignées
        """
        results = []
        total = len(images)
        previous = None

        for idx, item in enumerate(images):
            if progress_callback:
                progress_callback(idx, total, f"Alignement {idx + 1}/{total}")

            # Gérer les différents formats d'entrée
            if isinstance(item, tuple):
                path, image = item
            else:
                image = item
                path = f"image_{idx}"

            aligned = self.align_to_reference(
                image, reference_image,
                border=border,
                overlay_mode=overlay,
                previous_result=previous
            )

            if aligned is not None:
                results.append(aligned)
                if overlay:
                    previous = aligned
            else:
                self._log_error(f"Échec alignement: {path}")

        return results

    def _compute_transformation(self, points1: np.ndarray,
                                 points2: np.ndarray) -> np.ndarray:
        """
        Calcule la transformation affine optimale (Procrustes orthogonal).

        Args:
            points1: Points de destination
            points2: Points source

        Returns:
            Matrice de transformation 3x3
        """
        points1 = points1.astype(np.float64)
        points2 = points2.astype(np.float64)

        # Centrer les points
        c1 = np.mean(points1, axis=0)
        c2 = np.mean(points2, axis=0)
        points1 = points1 - c1
        points2 = points2 - c2

        # Normaliser par l'écart-type
        s1 = np.std(points1)
        s2 = np.std(points2)
        points1 = points1 / s1
        points2 = points2 / s2

        # SVD pour trouver la rotation optimale
        U, S, Vt = np.linalg.svd(np.dot(points1.T, points2))
        R = np.dot(U, Vt).T

        # Construire la matrice de transformation complète
        scale = s2 / s1
        translation = c2.T - scale * np.dot(R, c1.T)

        # Assurer que c'est un array 1D
        if hasattr(c2, 'A1'):  # Si c'est une matrice numpy
            c2_flat = c2.A1
            c1_flat = c1.A1
        else:
            c2_flat = np.asarray(c2).flatten()
            c1_flat = np.asarray(c1).flatten()

        translation = c2_flat - scale * np.dot(R, c1_flat)

        # Matrice 3x3
        M = np.zeros((3, 3))
        M[:2, :2] = scale * R
        M[:2, 2] = translation
        M[2, 2] = 1.0

        return M

    def _warp_image(self, image: np.ndarray, M: np.ndarray,
                    target_shape: Tuple[int, ...],
                    previous: np.ndarray = None) -> np.ndarray:
        """
        Applique une transformation affine à une image.

        Args:
            image: Image à transformer
            M: Matrice de transformation 2x3
            target_shape: Shape de l'image de sortie
            previous: Image précédente pour overlay

        Returns:
            Image transformée
        """
        border_mode = cv2.BORDER_REFLECT_101 if previous is not None else cv2.BORDER_CONSTANT

        warped = cv2.warpAffine(
            image, M, (target_shape[1], target_shape[0]),
            flags=cv2.INTER_CUBIC,
            borderMode=border_mode
        )

        if previous is not None:
            # Créer un masque pour l'overlay
            mask = cv2.warpAffine(
                np.ones_like(image, dtype=np.float32),
                M, (target_shape[1], target_shape[0]),
                flags=cv2.INTER_CUBIC
            )
            warped = (mask * warped + (1 - mask) * previous).astype(np.uint8)

        return warped

    def clear_cache(self):
        """Vide le cache des landmarks"""
        self._cache.clear()

    def _log_info(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str):
        if self.logger:
            self.logger.error(message)
