"""
Face Detector - Module de détection faciale et extraction des landmarks
"""

import os
import numpy as np
import cv2
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class FaceData:
    """Structure de données pour un visage détecté"""
    landmarks: np.ndarray
    bounding_box: Tuple[int, int, int, int]
    confidence: float = 1.0


class FaceDetector:
    """Détecteur de visages avec extraction des 68 landmarks faciaux"""

    # Constantes pour les groupes de landmarks
    JAW_POINTS = list(range(0, 17))
    RIGHT_BROW_POINTS = list(range(17, 22))
    LEFT_BROW_POINTS = list(range(22, 27))
    NOSE_POINTS = list(range(27, 35))
    RIGHT_EYE_POINTS = list(range(36, 42))
    LEFT_EYE_POINTS = list(range(42, 48))
    MOUTH_POINTS = list(range(48, 61))
    INNER_MOUTH_POINTS = list(range(61, 68))

    FACE_POINTS = list(range(17, 68))
    ALIGN_POINTS = (LEFT_BROW_POINTS + RIGHT_EYE_POINTS + LEFT_EYE_POINTS +
                    RIGHT_BROW_POINTS + NOSE_POINTS + MOUTH_POINTS)

    def __init__(self, predictor_path: str = None, logger=None):
        """
        Initialise le détecteur de visages.

        Args:
            predictor_path: Chemin vers le modèle shape_predictor_68_face_landmarks.dat
            logger: Instance du logger (optionnel)
        """
        self.logger = logger
        self._detector = None
        self._predictor = None
        self._predictor_path = predictor_path
        self._initialized = False

    def initialize(self, predictor_path: str = None) -> bool:
        """
        Initialise dlib avec le modèle de prédiction.

        Args:
            predictor_path: Chemin vers le fichier .dat du modèle

        Returns:
            True si l'initialisation a réussi
        """
        try:
            import dlib

            if predictor_path:
                self._predictor_path = predictor_path

            if not self._predictor_path:
                # Chercher le modèle dans les emplacements courants
                possible_paths = [
                    "./shape_predictor_68_face_landmarks.dat",
                    "../shape_predictor_68_face_landmarks.dat",
                    "assets/shape_predictor_68_face_landmarks.dat",
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        self._predictor_path = path
                        break

            if not self._predictor_path or not os.path.exists(self._predictor_path):
                self._log_error(f"Modèle non trouvé: {self._predictor_path}")
                return False

            self._detector = dlib.get_frontal_face_detector()
            self._predictor = dlib.shape_predictor(self._predictor_path)
            self._initialized = True
            self._log_info(f"Détecteur initialisé avec: {self._predictor_path}")
            return True

        except ImportError:
            self._log_error("dlib n'est pas installé. Installez-le avec: pip install dlib")
            return False
        except Exception as e:
            self._log_error(f"Erreur d'initialisation: {e}")
            return False

    def detect_faces(self, image: np.ndarray, upsample: int = 1) -> List[Tuple[int, int, int, int]]:
        """
        Détecte les visages dans une image.

        Args:
            image: Image BGR (numpy array)
            upsample: Niveau de suréchantillonnage (1 = normal, 0 = rapide)

        Returns:
            Liste des bounding boxes (x1, y1, x2, y2)
        """
        if not self._initialized:
            self._log_error("Détecteur non initialisé")
            return []

        rects = self._detector(image, upsample)

        # Fallback si aucune détection
        if len(rects) == 0 and upsample > 0:
            rects = self._detector(image, 0)

        return [(r.left(), r.top(), r.right(), r.bottom()) for r in rects]

    def get_landmarks(self, image: np.ndarray,
                      face_rect: Tuple[int, int, int, int] = None,
                      add_boundary: bool = True,
                      max_attempts: int = 3) -> Optional[np.ndarray]:
        """
        Extrait les 68 landmarks faciaux.

        Args:
            image: Image BGR
            face_rect: Bounding box du visage (optionnel, détection auto sinon)
            add_boundary: Ajouter 8 points aux bordures de l'image
            max_attempts: Nombre de tentatives de détection

        Returns:
            Array numpy des landmarks (68 ou 76 points) ou None
        """
        if not self._initialized:
            self._log_error("Détecteur non initialisé")
            return None

        import dlib

        # Si pas de bounding box fournie, détecter automatiquement
        if face_rect is None:
            for attempt in range(max_attempts):
                rects = self._detector(image, 1)
                if len(rects) == 0:
                    rects = self._detector(image, 0)
                if len(rects) > 0:
                    break
                self._log_info(f"Tentative {attempt + 1}/{max_attempts}: Aucun visage détecté")

            if len(rects) == 0:
                self._log_error("Aucun visage détecté après toutes les tentatives")
                return None

            rect = rects[0]
        else:
            x1, y1, x2, y2 = face_rect
            rect = dlib.rectangle(x1, y1, x2, y2)

        # Extraire les landmarks
        shape = self._predictor(image, rect)
        landmarks = np.array([(p.x, p.y) for p in shape.parts()])

        # Ajouter les points de bordure si demandé
        if add_boundary:
            boundary = self._get_boundary_points(image.shape)
            landmarks = np.vstack([landmarks, boundary])

        return landmarks

    def get_all_faces_landmarks(self, image: np.ndarray,
                                add_boundary: bool = True) -> List[FaceData]:
        """
        Extrait les landmarks de tous les visages détectés.

        Args:
            image: Image BGR
            add_boundary: Ajouter les points de bordure

        Returns:
            Liste de FaceData pour chaque visage
        """
        if not self._initialized:
            return []

        import dlib

        rects = self._detector(image, 1)
        if len(rects) == 0:
            rects = self._detector(image, 0)

        faces = []
        for rect in rects:
            shape = self._predictor(image, rect)
            landmarks = np.array([(p.x, p.y) for p in shape.parts()])

            if add_boundary:
                boundary = self._get_boundary_points(image.shape)
                landmarks = np.vstack([landmarks, boundary])

            face_data = FaceData(
                landmarks=landmarks,
                bounding_box=(rect.left(), rect.top(), rect.right(), rect.bottom())
            )
            faces.append(face_data)

        return faces

    def _get_boundary_points(self, shape: Tuple[int, ...]) -> np.ndarray:
        """
        Génère 8 points aux bordures de l'image.

        Args:
            shape: Shape de l'image (h, w, ...)

        Returns:
            Array de 8 points de bordure
        """
        h, w = shape[:2]
        return np.array([
            (1, 1), (w - 1, 1), (1, h - 1), (w - 1, h - 1),
            ((w - 1) // 2, 1), (1, (h - 1) // 2),
            ((w - 1) // 2, h - 1), (w - 1, (h - 1) // 2)
        ])

    def annotate_image(self, image: np.ndarray, landmarks: np.ndarray,
                       show_numbers: bool = False) -> np.ndarray:
        """
        Annote une image avec les landmarks détectés.

        Args:
            image: Image BGR
            landmarks: Array des landmarks
            show_numbers: Afficher les numéros des points

        Returns:
            Image annotée
        """
        annotated = image.copy()

        for idx, point in enumerate(landmarks):
            pos = (int(point[0]), int(point[1]))
            cv2.circle(annotated, pos, 3, (0, 255, 0), -1)

            if show_numbers:
                cv2.putText(annotated, str(idx), pos,
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        return annotated

    def draw_face_boxes(self, image: np.ndarray,
                        faces: List[Tuple[int, int, int, int]]) -> np.ndarray:
        """
        Dessine les bounding boxes des visages détectés.

        Args:
            image: Image BGR
            faces: Liste des bounding boxes

        Returns:
            Image avec les boxes dessinées
        """
        annotated = image.copy()

        for idx, (x1, y1, x2, y2) in enumerate(faces):
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(annotated, str(idx), (x1 + 5, y1 + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        return annotated

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _log_info(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str):
        if self.logger:
            self.logger.error(message)
