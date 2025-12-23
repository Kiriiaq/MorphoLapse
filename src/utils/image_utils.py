"""
Image Utils - Utilitaires de traitement d'images
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
from PIL import Image


class ImageUtils:
    """Utilitaires pour le traitement d'images"""

    @staticmethod
    def load_image(filepath: str, color_mode: str = 'BGR') -> Optional[np.ndarray]:
        """
        Charge une image depuis un fichier.

        Args:
            filepath: Chemin de l'image
            color_mode: 'BGR', 'RGB' ou 'GRAY'

        Returns:
            Image numpy ou None
        """
        try:
            if color_mode == 'GRAY':
                return cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            else:
                img = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if img is not None and color_mode == 'RGB':
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                return img
        except Exception:
            return None

    @staticmethod
    def save_image(image: np.ndarray, filepath: str, quality: int = 95) -> bool:
        """
        Sauvegarde une image.

        Args:
            image: Image numpy (BGR)
            filepath: Chemin de destination
            quality: Qualité JPEG (0-100)

        Returns:
            True si la sauvegarde a réussi
        """
        try:
            ext = filepath.lower().split('.')[-1]
            if ext in ['jpg', 'jpeg']:
                cv2.imwrite(filepath, image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            elif ext == 'png':
                cv2.imwrite(filepath, image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            else:
                cv2.imwrite(filepath, image)
            return True
        except Exception:
            return False

    @staticmethod
    def resize_image(image: np.ndarray, target_size: Tuple[int, int],
                     keep_aspect: bool = True,
                     fill_color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
        """
        Redimensionne une image.

        Args:
            image: Image source
            target_size: Taille cible (width, height)
            keep_aspect: Conserver le ratio d'aspect
            fill_color: Couleur de remplissage BGR

        Returns:
            Image redimensionnée
        """
        h, w = image.shape[:2]
        target_w, target_h = target_size

        if not keep_aspect:
            return cv2.resize(image, (target_w, target_h))

        # Calculer le ratio de redimensionnement
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Redimensionner
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Créer l'image de fond
        if len(image.shape) == 3:
            result = np.full((target_h, target_w, 3), fill_color, dtype=np.uint8)
        else:
            result = np.full((target_h, target_w), fill_color[0], dtype=np.uint8)

        # Centrer l'image redimensionnée
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        result[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return result

    @staticmethod
    def crop_to_face(image: np.ndarray, face_rect: Tuple[int, int, int, int],
                     margin: float = 0.3) -> np.ndarray:
        """
        Recadre une image sur un visage.

        Args:
            image: Image source
            face_rect: Rectangle du visage (x1, y1, x2, y2)
            margin: Marge relative autour du visage

        Returns:
            Image recadrée
        """
        x1, y1, x2, y2 = face_rect
        h, w = image.shape[:2]

        # Calculer les marges
        face_w = x2 - x1
        face_h = y2 - y1
        margin_x = int(face_w * margin)
        margin_y = int(face_h * margin)

        # Appliquer les marges avec limites
        new_x1 = max(0, x1 - margin_x)
        new_y1 = max(0, y1 - margin_y)
        new_x2 = min(w, x2 + margin_x)
        new_y2 = min(h, y2 + margin_y)

        return image[new_y1:new_y2, new_x1:new_x2].copy()

    @staticmethod
    def normalize_image(image: np.ndarray) -> np.ndarray:
        """
        Normalise une image (0-1).

        Args:
            image: Image source

        Returns:
            Image normalisée (float32)
        """
        return image.astype(np.float32) / 255.0

    @staticmethod
    def denormalize_image(image: np.ndarray) -> np.ndarray:
        """
        Dénormalise une image (0-255).

        Args:
            image: Image normalisée

        Returns:
            Image uint8
        """
        return (np.clip(image, 0, 1) * 255).astype(np.uint8)

    @staticmethod
    def blend_images(image1: np.ndarray, image2: np.ndarray,
                     alpha: float) -> np.ndarray:
        """
        Mélange deux images.

        Args:
            image1: Première image
            image2: Deuxième image
            alpha: Coefficient (0=image1, 1=image2)

        Returns:
            Image mélangée
        """
        return cv2.addWeighted(image1, 1 - alpha, image2, alpha, 0)

    @staticmethod
    def add_border(image: np.ndarray, size: int,
                   color: Tuple[int, int, int] = (255, 255, 255)) -> np.ndarray:
        """
        Ajoute une bordure à une image.

        Args:
            image: Image source
            size: Taille de la bordure en pixels
            color: Couleur BGR

        Returns:
            Image avec bordure
        """
        return cv2.copyMakeBorder(
            image, size, size, size, size,
            borderType=cv2.BORDER_CONSTANT,
            value=color
        )

    @staticmethod
    def adjust_brightness_contrast(image: np.ndarray,
                                   brightness: float = 0,
                                   contrast: float = 1) -> np.ndarray:
        """
        Ajuste la luminosité et le contraste.

        Args:
            image: Image source
            brightness: Ajustement luminosité (-100 à 100)
            contrast: Facteur de contraste (0.5 à 2.0)

        Returns:
            Image ajustée
        """
        adjusted = image.astype(np.float32)
        adjusted = adjusted * contrast + brightness
        return np.clip(adjusted, 0, 255).astype(np.uint8)

    @staticmethod
    def create_thumbnail(image: np.ndarray, size: int = 128) -> np.ndarray:
        """
        Crée une vignette carrée.

        Args:
            image: Image source
            size: Taille de la vignette

        Returns:
            Vignette carrée
        """
        h, w = image.shape[:2]

        # Recadrer au carré
        if w > h:
            offset = (w - h) // 2
            cropped = image[:, offset:offset + h]
        else:
            offset = (h - w) // 2
            cropped = image[offset:offset + w, :]

        # Redimensionner
        return cv2.resize(cropped, (size, size), interpolation=cv2.INTER_AREA)

    @staticmethod
    def stack_images(images: List[np.ndarray], direction: str = 'horizontal',
                     gap: int = 0) -> Optional[np.ndarray]:
        """
        Empile plusieurs images.

        Args:
            images: Liste d'images
            direction: 'horizontal' ou 'vertical'
            gap: Espace entre les images

        Returns:
            Image empilée ou None
        """
        if not images:
            return None

        # Uniformiser les tailles
        if direction == 'horizontal':
            target_h = max(img.shape[0] for img in images)
            resized = []
            for img in images:
                if img.shape[0] != target_h:
                    scale = target_h / img.shape[0]
                    new_w = int(img.shape[1] * scale)
                    img = cv2.resize(img, (new_w, target_h))
                resized.append(img)

            if gap > 0:
                gap_img = np.zeros((target_h, gap, 3), dtype=np.uint8)
                result = []
                for i, img in enumerate(resized):
                    result.append(img)
                    if i < len(resized) - 1:
                        result.append(gap_img)
                return np.hstack(result)
            return np.hstack(resized)

        else:  # vertical
            target_w = max(img.shape[1] for img in images)
            resized = []
            for img in images:
                if img.shape[1] != target_w:
                    scale = target_w / img.shape[1]
                    new_h = int(img.shape[0] * scale)
                    img = cv2.resize(img, (target_w, new_h))
                resized.append(img)

            if gap > 0:
                gap_img = np.zeros((gap, target_w, 3), dtype=np.uint8)
                result = []
                for i, img in enumerate(resized):
                    result.append(img)
                    if i < len(resized) - 1:
                        result.append(gap_img)
                return np.vstack(result)
            return np.vstack(resized)

    @staticmethod
    def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
        """Convertit BGR vers RGB"""
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    @staticmethod
    def rgb_to_bgr(image: np.ndarray) -> np.ndarray:
        """Convertit RGB vers BGR"""
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    @staticmethod
    def numpy_to_pil(image: np.ndarray) -> Image.Image:
        """Convertit numpy array BGR vers PIL Image"""
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    @staticmethod
    def pil_to_numpy(image: Image.Image) -> np.ndarray:
        """Convertit PIL Image vers numpy array BGR"""
        rgb = np.array(image)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
