"""
Face Morpher - Module de morphing triangulaire des visages
Version optimisée avec fonctions d'easing et modes de blend
"""

import numpy as np
import cv2
from typing import Tuple, List, Optional, Callable, Generator, Literal
from dataclasses import dataclass
from enum import Enum
from scipy.spatial import Delaunay
from PIL import Image
import io


class EasingFunction(Enum):
    """Fonctions d'easing pour les transitions"""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    CUBIC = "cubic"
    BOUNCE = "bounce"


class BlendMode(Enum):
    """Modes de mélange des images"""
    ALPHA = "alpha"         # Mélange classique
    ADDITIVE = "additive"   # Addition (plus lumineux)
    MULTIPLY = "multiply"   # Multiplication (plus sombre)
    SCREEN = "screen"       # Inverse de multiply


@dataclass
class MorphConfig:
    """Configuration du morphing"""
    easing: EasingFunction = EasingFunction.LINEAR
    blend_mode: BlendMode = BlendMode.ALPHA
    interpolation: int = cv2.INTER_LINEAR
    border_mode: int = cv2.BORDER_REFLECT_101
    quality: Literal["low", "medium", "high", "ultra"] = "high"


class FaceMorpher:
    """
    Moteur de morphing facial par triangulation de Delaunay

    Version refactorisée avec:
    - Élimination des duplications de code
    - Support des fonctions d'easing
    - Modes de blend multiples
    - Générateur pour économiser la mémoire
    - Validation des entrées
    """

    def __init__(self, logger=None, config: Optional[MorphConfig] = None):
        """
        Initialise le moteur de morphing.

        Args:
            logger: Instance du logger
            config: Configuration du morphing
        """
        self.logger = logger
        self.config = config or MorphConfig()
        self._quality_settings = {
            "low": {"supersampling": 1, "interpolation": cv2.INTER_NEAREST},
            "medium": {"supersampling": 1, "interpolation": cv2.INTER_LINEAR},
            "high": {"supersampling": 1, "interpolation": cv2.INTER_CUBIC},
            "ultra": {"supersampling": 2, "interpolation": cv2.INTER_LANCZOS4}
        }

    # ========== FONCTIONS D'EASING ==========

    def _apply_easing(self, t: float, easing: EasingFunction) -> float:
        """
        Applique une fonction d'easing à la valeur t.

        Args:
            t: Valeur entre 0 et 1
            easing: Type d'easing à appliquer

        Returns:
            Valeur transformée entre 0 et 1
        """
        if easing == EasingFunction.LINEAR:
            return t
        elif easing == EasingFunction.EASE_IN:
            return t * t
        elif easing == EasingFunction.EASE_OUT:
            return 1 - (1 - t) ** 2
        elif easing == EasingFunction.EASE_IN_OUT:
            if t < 0.5:
                return 2 * t * t
            return 1 - (-2 * t + 2) ** 2 / 2
        elif easing == EasingFunction.CUBIC:
            return t * t * t
        elif easing == EasingFunction.BOUNCE:
            if t < 1 / 2.75:
                return 7.5625 * t * t
            elif t < 2 / 2.75:
                t -= 1.5 / 2.75
                return 7.5625 * t * t + 0.75
            elif t < 2.5 / 2.75:
                t -= 2.25 / 2.75
                return 7.5625 * t * t + 0.9375
            else:
                t -= 2.625 / 2.75
                return 7.5625 * t * t + 0.984375
        return t

    # ========== MODES DE BLEND ==========

    def _blend_images(
        self,
        warped1: np.ndarray,
        warped2: np.ndarray,
        alpha: float,
        mode: BlendMode = BlendMode.ALPHA
    ) -> np.ndarray:
        """
        Mélange deux images selon le mode spécifié.

        Args:
            warped1: Première image normalisée (0-1)
            warped2: Deuxième image normalisée (0-1)
            alpha: Coefficient de mélange (0=image1, 1=image2)
            mode: Mode de mélange

        Returns:
            Image mélangée (0-255, uint8)
        """
        # S'assurer que les images ont la même forme
        if warped1.shape != warped2.shape:
            warped2 = cv2.resize(warped2, (warped1.shape[1], warped1.shape[0]))

        if mode == BlendMode.ALPHA:
            blended = (1.0 - alpha) * warped1 + alpha * warped2
        elif mode == BlendMode.ADDITIVE:
            blended = np.minimum(warped1 + alpha * warped2, 1.0)
        elif mode == BlendMode.MULTIPLY:
            base = (1.0 - alpha) * warped1 + alpha * np.ones_like(warped1)
            blended = base * warped2
        elif mode == BlendMode.SCREEN:
            inv1 = 1.0 - warped1
            inv2 = 1.0 - warped2
            blended = 1.0 - ((1.0 - alpha) * inv1 + alpha * inv2)
        else:
            blended = (1.0 - alpha) * warped1 + alpha * warped2

        return (np.clip(blended, 0, 1) * 255).astype(np.uint8)

    # ========== VALIDATION ==========

    def _validate_inputs(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray
    ) -> bool:
        """Valide les entrées avant le morphing."""
        # Vérifier les images
        if image1 is None or image2 is None:
            self._log_error("Images invalides (None)")
            return False

        if len(image1.shape) < 2 or len(image2.shape) < 2:
            self._log_error("Dimensions d'images invalides")
            return False

        # Vérifier les landmarks
        if landmarks1 is None or landmarks2 is None:
            self._log_error("Landmarks invalides (None)")
            return False

        if landmarks1.shape != landmarks2.shape:
            self._log_error(f"Forme des landmarks incompatible: {landmarks1.shape} vs {landmarks2.shape}")
            return False

        # Vérifier les NaN/Inf
        if np.any(np.isnan(landmarks1)) or np.any(np.isnan(landmarks2)):
            self._log_error("Landmarks contiennent des NaN")
            return False

        if np.any(np.isinf(landmarks1)) or np.any(np.isinf(landmarks2)):
            self._log_error("Landmarks contiennent des valeurs infinies")
            return False

        return True

    # ========== MÉTHODE PRINCIPALE DE MORPHING ==========

    def _morph_frame(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray,
        alpha: float,
        triangulation: Optional[np.ndarray] = None,
        im1_float: Optional[np.ndarray] = None,
        im2_float: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Génère une frame morphée unique.

        Méthode centrale utilisée par toutes les autres méthodes de morphing
        pour éviter la duplication de code.

        Args:
            image1: Première image
            image2: Deuxième image
            landmarks1: Landmarks de image1
            landmarks2: Landmarks de image2
            alpha: Coefficient d'interpolation (0-1)
            triangulation: Triangulation pré-calculée (optionnel)
            im1_float: Image1 en float32 (optionnel, pour performance)
            im2_float: Image2 en float32 (optionnel, pour performance)

        Returns:
            Image morphée (uint8)
        """
        # Appliquer easing si configuré
        eased_alpha = self._apply_easing(alpha, self.config.easing)

        # Interpoler les landmarks
        weighted_landmarks = (1.0 - eased_alpha) * landmarks1 + eased_alpha * landmarks2

        # Calculer la triangulation si non fournie
        if triangulation is None:
            triangulation = self.compute_triangulation(weighted_landmarks)

        # Convertir en float si nécessaire
        if im1_float is None:
            im1_float = image1.astype(np.float32)
        if im2_float is None:
            im2_float = image2.astype(np.float32)

        # Déformer les images
        warped1 = self.warp_image(im1_float, landmarks1, weighted_landmarks, triangulation)
        warped2 = self.warp_image(im2_float, landmarks2, weighted_landmarks, triangulation)

        # Normaliser (0-1)
        warped1 = warped1 / 255.0
        warped2 = warped2 / 255.0

        # Appliquer le blend
        return self._blend_images(warped1, warped2, eased_alpha, self.config.blend_mode)

    # ========== API PUBLIQUE ==========

    def compute_triangulation(self, landmarks: np.ndarray) -> np.ndarray:
        """
        Calcule la triangulation de Delaunay des landmarks.

        Args:
            landmarks: Array des points (N, 2)

        Returns:
            Array des indices des triangles (M, 3)
        """
        return Delaunay(landmarks).simplices

    def warp_image(
        self,
        image: np.ndarray,
        source_landmarks: np.ndarray,
        target_landmarks: np.ndarray,
        triangulation: np.ndarray
    ) -> np.ndarray:
        """
        Déforme une image pour mapper les landmarks source vers cible.

        Args:
            image: Image à déformer
            source_landmarks: Landmarks actuels
            target_landmarks: Landmarks cibles
            triangulation: Indices des triangles

        Returns:
            Image déformée
        """
        output = image.copy().astype(np.float32)

        for triangle_indices in triangulation:
            src_tri = source_landmarks[triangle_indices]
            dst_tri = target_landmarks[triangle_indices]
            self._morph_triangle(image.astype(np.float32), output, src_tri, dst_tri)

        return output

    def morph_pair(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray,
        alpha: float
    ) -> np.ndarray:
        """
        Crée une image intermédiaire entre deux images.

        Args:
            image1: Première image
            image2: Deuxième image
            landmarks1: Landmarks de image1
            landmarks2: Landmarks de image2
            alpha: Coefficient d'interpolation (0=image1, 1=image2)

        Returns:
            Image morphée
        """
        if not self._validate_inputs(image1, image2, landmarks1, landmarks2):
            # Fallback: retourner un blend simple
            return self._simple_blend(image1, image2, alpha)

        return self._morph_frame(image1, image2, landmarks1, landmarks2, alpha)

    def generate_morph_sequence(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray,
        num_frames: int,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[np.ndarray]:
        """
        Génère une séquence de morphing entre deux images.

        Args:
            image1: Image de départ
            image2: Image d'arrivée
            landmarks1: Landmarks de image1
            landmarks2: Landmarks de image2
            num_frames: Nombre de frames à générer
            progress_callback: Callback(frame_idx, total_frames)

        Returns:
            Liste des images de la séquence
        """
        # Utiliser le générateur et collecter les frames
        return list(self.stream_morph_frames(
            image1, image2, landmarks1, landmarks2,
            num_frames, progress_callback
        ))

    def stream_morph_frames(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray,
        num_frames: int,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Generator[np.ndarray, None, None]:
        """
        Générateur de frames morphées (économise la mémoire).

        Yields:
            Images morphées une par une
        """
        if not self._validate_inputs(image1, image2, landmarks1, landmarks2):
            # Fallback sur cross dissolve
            for frame in self.cross_dissolve(image1, image2, num_frames):
                yield frame
            return

        # Pré-calculer pour performance
        avg_landmarks = (landmarks1 + landmarks2) / 2
        triangulation = self.compute_triangulation(avg_landmarks)
        im1_float = image1.astype(np.float32)
        im2_float = image2.astype(np.float32)

        for frame_idx in range(num_frames):
            alpha = frame_idx / max(1, num_frames - 1)

            frame = self._morph_frame(
                image1, image2, landmarks1, landmarks2, alpha,
                triangulation=triangulation,
                im1_float=im1_float,
                im2_float=im2_float
            )

            yield frame

            if progress_callback:
                progress_callback(frame_idx + 1, num_frames)

            self._log_info(f"Frame {frame_idx + 1}/{num_frames} générée")

    def stream_morph_sequence(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray,
        num_frames: int,
        output_stream,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Stream une séquence de morphing directement vers un flux (ffmpeg).

        Args:
            image1: Image de départ
            image2: Image d'arrivée
            landmarks1: Landmarks de image1
            landmarks2: Landmarks de image2
            num_frames: Nombre de frames
            output_stream: Flux de sortie avec .stdin
            progress_callback: Callback de progression
        """
        for frame in self.stream_morph_frames(
            image1, image2, landmarks1, landmarks2,
            num_frames, progress_callback
        ):
            # Convertir et envoyer au stream
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            pil_image.save(output_stream.stdin, 'JPEG')

    def cross_dissolve(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        num_frames: int
    ) -> List[np.ndarray]:
        """
        Crée une transition par dissolution croisée (sans morphing géométrique).

        Args:
            image1: Image de départ
            image2: Image d'arrivée
            num_frames: Nombre de frames

        Returns:
            Liste des images de transition
        """
        return list(self.stream_cross_dissolve(image1, image2, num_frames))

    def stream_cross_dissolve(
        self,
        image1: np.ndarray,
        image2: np.ndarray,
        num_frames: int
    ) -> Generator[np.ndarray, None, None]:
        """Générateur de cross dissolve (économise la mémoire)."""
        im1 = image1.astype(np.float32) / 255.0
        im2 = image2.astype(np.float32) / 255.0

        # S'assurer des mêmes dimensions
        if im1.shape != im2.shape:
            im2 = cv2.resize(im2, (im1.shape[1], im1.shape[0]))

        for i in range(num_frames):
            alpha = i / max(1, num_frames - 1)
            eased_alpha = self._apply_easing(alpha, self.config.easing)
            blended = (1.0 - eased_alpha) * im1 + eased_alpha * im2
            yield (blended * 255).astype(np.uint8)

    def create_average_face(
        self,
        images: List[np.ndarray],
        landmarks_list: List[np.ndarray]
    ) -> Optional[np.ndarray]:
        """
        Crée un visage moyen à partir d'une liste d'images.

        Args:
            images: Liste d'images
            landmarks_list: Liste des landmarks correspondants

        Returns:
            Image du visage moyen
        """
        if len(images) != len(landmarks_list):
            self._log_error("Nombre d'images et de landmarks différent")
            return None

        if len(images) == 0:
            return None

        # Valider tous les landmarks
        valid_data = [
            (img, lm) for img, lm in zip(images, landmarks_list)
            if lm is not None and not np.any(np.isnan(lm))
        ]

        if len(valid_data) < 2:
            self._log_error("Pas assez d'images valides pour créer un visage moyen")
            return None

        images, landmarks_list = zip(*valid_data)

        # Calculer les landmarks moyens
        avg_landmarks = sum(landmarks_list) / len(landmarks_list)
        triangulation = self.compute_triangulation(avg_landmarks)

        # Déformer toutes les images vers la forme moyenne
        warped_images = []
        for img, landmarks in zip(images, landmarks_list):
            warped = self.warp_image(
                img.astype(np.float32),
                landmarks,
                avg_landmarks,
                triangulation
            )
            warped_images.append(warped)

        # Moyenner les images
        average = sum(warped_images) / len(warped_images)
        return average.astype(np.uint8)

    def _simple_blend(self, image1: np.ndarray, image2: np.ndarray, alpha: float) -> np.ndarray:
        """Blend simple sans morphing (fallback)."""
        im1 = image1.astype(np.float32)
        im2 = image2.astype(np.float32)
        if im1.shape != im2.shape:
            im2 = cv2.resize(im2, (im1.shape[1], im1.shape[0]))
        blended = (1.0 - alpha) * im1 + alpha * im2
        return blended.astype(np.uint8)

    def _morph_triangle(
        self,
        src_image: np.ndarray,
        dst_image: np.ndarray,
        src_tri: np.ndarray,
        dst_tri: np.ndarray
    ):
        """
        Morphe un triangle unique de l'image source vers destination.

        Args:
            src_image: Image source (float32)
            dst_image: Image destination (modifiée in-place)
            src_tri: Coordonnées du triangle source (3, 2)
            dst_tri: Coordonnées du triangle destination (3, 2)
        """
        # Bounding boxes
        r1 = cv2.boundingRect(np.float32([src_tri]))
        r2 = cv2.boundingRect(np.float32([dst_tri]))

        # Vérifier que les bounding boxes sont valides
        if r1[2] <= 0 or r1[3] <= 0 or r2[2] <= 0 or r2[3] <= 0:
            return

        # Points relatifs aux bounding boxes
        src_rect = [(src_tri[i][0] - r1[0], src_tri[i][1] - r1[1]) for i in range(3)]
        dst_rect = [(dst_tri[i][0] - r2[0], dst_tri[i][1] - r2[1]) for i in range(3)]

        # Masque triangulaire
        mask = np.zeros((r2[3], r2[2], 3), dtype=np.float32)
        cv2.fillConvexPoly(mask, np.int32(dst_rect), (1.0, 1.0, 1.0), 16, 0)

        # Extraction de la région source
        y1, y2 = r1[1], r1[1] + r1[3]
        x1, x2 = r1[0], r1[0] + r1[2]

        # Vérifier les limites
        h, w = src_image.shape[:2]
        y1, y2 = max(0, y1), min(h, y2)
        x1, x2 = max(0, x1), min(w, x2)

        if y2 <= y1 or x2 <= x1:
            return

        src_crop = src_image[y1:y2, x1:x2]

        # Ajuster les points source si le crop a été modifié
        if src_crop.shape[0] != r1[3] or src_crop.shape[1] != r1[2]:
            return

        # Transformation affine
        try:
            warp_mat = cv2.getAffineTransform(np.float32(src_rect), np.float32(dst_rect))
            warped = cv2.warpAffine(
                src_crop, warp_mat, (r2[2], r2[3]),
                flags=self.config.interpolation,
                borderMode=self.config.border_mode
            )
        except cv2.error:
            return

        # Vérifier les dimensions
        dy1, dy2 = r2[1], r2[1] + r2[3]
        dx1, dx2 = r2[0], r2[0] + r2[2]

        h, w = dst_image.shape[:2]
        dy1, dy2 = max(0, dy1), min(h, dy2)
        dx1, dx2 = max(0, dx1), min(w, dx2)

        region = dst_image[dy1:dy2, dx1:dx2]
        if region.shape != warped.shape:
            return

        # Appliquer le masque
        dst_image[dy1:dy2, dx1:dx2] = region * (1 - mask) + warped * mask

    def _log_info(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str):
        if self.logger:
            self.logger.error(message)
