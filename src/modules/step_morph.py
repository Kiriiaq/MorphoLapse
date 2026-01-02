"""
Morph Step - Étape de morphing facial
Version optimisée avec gestion mémoire efficace et générateurs
"""

import os
import gc
import cv2
from typing import Callable, Generator, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from ..utils.image_utils import ImageUtils
from ..core.face_detector import FaceDetector
from ..core.face_morpher import FaceMorpher, MorphConfig, EasingFunction, BlendMode
from ..core.video_encoder import VideoEncoder
from .workflow_manager import WorkflowContext


@dataclass
class ImageData:
    """Données d'une image pour le morphing (version légère)"""
    path: str
    landmarks: Optional[Any] = None
    _image: Optional[Any] = None

    def load_image(self):
        """Charge l'image à la demande"""
        if self._image is None:
            self._image = ImageUtils.load_image(self.path)
        return self._image

    def unload_image(self):
        """Libère la mémoire"""
        self._image = None

    @property
    def image(self):
        return self.load_image()


def image_pair_generator(
    image_paths: list,
    context: WorkflowContext,
    detector: FaceDetector,
    logger=None
) -> Generator[Tuple[ImageData, ImageData], None, None]:
    """
    Générateur qui charge les paires d'images à la demande.
    Économise la mémoire en ne gardant que 2 images en mémoire maximum.

    Yields:
        Tuple (image1_data, image2_data)
    """
    prev_data: Optional[ImageData] = None

    for idx, image_path in enumerate(image_paths):
        # Charger l'image actuelle
        image = ImageUtils.load_image(image_path)
        if image is None:
            if logger:
                logger.warning(f"Impossible de charger: {image_path}")
            continue

        # Récupérer les landmarks
        if context.landmarks and idx < len(context.landmarks) and context.landmarks[idx] is not None:
            landmarks = context.landmarks[idx]
        else:
            landmarks = detector.get_landmarks(image, add_boundary=True)

        current_data = ImageData(
            path=image_path,
            landmarks=landmarks,
            _image=image
        )

        # Yield la paire si on a une image précédente
        if prev_data is not None:
            yield (prev_data, current_data)
            # Libérer la mémoire de l'image précédente (sauf la première qui devient 'prev')
            if idx > 1:
                prev_data.unload_image()

        prev_data = current_data

    # Nettoyage final
    if prev_data:
        prev_data.unload_image()

    gc.collect()


def get_easing_function(easing_name: str) -> EasingFunction:
    """Convertit un nom d'easing en enum."""
    mapping = {
        "linear": EasingFunction.LINEAR,
        "ease_in": EasingFunction.EASE_IN,
        "ease_out": EasingFunction.EASE_OUT,
        "ease_in_out": EasingFunction.EASE_IN_OUT,
        "cubic": EasingFunction.CUBIC,
        "bounce": EasingFunction.BOUNCE
    }
    return mapping.get(easing_name, EasingFunction.LINEAR)


def get_blend_mode(blend_name: str) -> BlendMode:
    """Convertit un nom de blend mode en enum."""
    mapping = {
        "alpha": BlendMode.ALPHA,
        "additive": BlendMode.ADDITIVE,
        "multiply": BlendMode.MULTIPLY,
        "screen": BlendMode.SCREEN
    }
    return mapping.get(blend_name, BlendMode.ALPHA)


def morph_faces(context: WorkflowContext, progress_callback: Callable, logger=None) -> dict:
    """
    Étape de morphing des visages avec gestion mémoire optimisée.

    Utilise des générateurs pour ne charger que 2 images à la fois,
    évitant les problèmes de mémoire avec de nombreuses images.

    Args:
        context: Contexte du workflow
        progress_callback: Callback(current, total, message)
        logger: Logger instance

    Returns:
        Dictionnaire des résultats
    """
    if logger:
        logger.info("Démarrage du morphing facial (mode optimisé)")

    # Vérifier les prérequis
    images = context.aligned_images if context.aligned_images else context.images
    if not images:
        raise ValueError("Aucune image pour le morphing")

    if len(images) < 2:
        raise ValueError("Au moins 2 images sont nécessaires pour le morphing")

    # Créer le dossier de morphing
    morph_dir = os.path.join(context.run_dir, "03_morph")
    os.makedirs(morph_dir, exist_ok=True)

    # Récupérer les paramètres
    config = context.config
    fps = config.get('fps', 25)
    transition_duration = config.get('transition_duration', 3.0)
    pause_duration = config.get('pause_duration', 0.0)
    easing_name = config.get('easing', 'linear')
    blend_mode_name = config.get('blend_mode', 'alpha')

    frames_per_transition = int(fps * transition_duration)
    pause_frames = int(fps * pause_duration)

    # Configurer le morphing
    morph_config = MorphConfig(
        easing=get_easing_function(easing_name),
        blend_mode=get_blend_mode(blend_mode_name)
    )

    # Initialiser les composants
    model_path = config.get('model_path', './shape_predictor_68_face_landmarks.dat')
    detector = FaceDetector(logger=logger)
    if not detector.initialize(model_path):
        raise RuntimeError("Impossible d'initialiser le détecteur")

    morpher = FaceMorpher(logger=logger, config=morph_config)
    encoder = VideoEncoder(logger=logger)

    if not encoder.check_ffmpeg():
        raise RuntimeError("FFmpeg n'est pas disponible")

    # Calculer les dimensions à partir de la première image
    first_image = ImageUtils.load_image(images[0])
    if first_image is None:
        raise ValueError("Impossible de charger la première image")

    h, w = first_image.shape[:2]
    original_ratio = w / h

    # Appliquer la résolution configurée (en gardant le ratio d'aspect)
    resolution = config.get('resolution', 'original')
    if resolution != 'original' and resolution != 'Original':
        # Hauteurs cibles pour chaque résolution
        height_map = {
            '1080p': 1080,
            '720p': 720,
            '480p': 480
        }
        if resolution in height_map:
            target_h = height_map[resolution]
            target_w = int(target_h * original_ratio)
            # Assurer dimensions paires (requis par H.264)
            target_w = target_w + (target_w % 2)
            target_h = target_h + (target_h % 2)
            w, h = target_w, target_h

    output_path = os.path.join(morph_dir, "morph_video.mp4")

    # Qualité vidéo (preset FFmpeg)
    quality = config.get('video_quality', 'high')
    quality_map = {'low': 'ultrafast', 'medium': 'medium', 'high': 'slow', 'ultra': 'slower'}
    preset = quality_map.get(quality, 'medium')

    if not encoder.start_encoding(output_path, fps=fps, size=(w, h), quality=preset):
        raise RuntimeError("Impossible de démarrer l'encodage")

    frame_count = 0
    total_pairs = len(images) - 1
    total_frames_estimate = pause_frames + total_pairs * (frames_per_transition + pause_frames)

    if logger:
        logger.info(f"Estimation: {total_frames_estimate} frames pour {total_pairs} transitions")

    # Écrire les frames de pause initiale
    if pause_frames > 0:
        # Redimensionner si nécessaire
        if first_image.shape[1] != w or first_image.shape[0] != h:
            first_image = cv2.resize(first_image, (w, h))

        for _ in range(pause_frames):
            encoder.write_frame(first_image)
            frame_count += 1

    del first_image
    gc.collect()

    # Traiter les paires d'images avec le générateur
    pair_idx = 0
    for data1, data2 in image_pair_generator(images, context, detector, logger):
        progress_callback(
            pair_idx + 1, total_pairs,
            f"Morphing: {os.path.basename(data1.path)} -> {os.path.basename(data2.path)}"
        )

        if logger:
            logger.info(f"Morphing paire {pair_idx + 1}/{total_pairs}")

        im1 = data1.image
        im2 = data2.image

        # Redimensionner si nécessaire
        if im1.shape[1] != w or im1.shape[0] != h:
            im1 = cv2.resize(im1, (w, h))
        if im2.shape[1] != w or im2.shape[0] != h:
            im2 = cv2.resize(im2, (w, h))

        landmarks1 = data1.landmarks
        landmarks2 = data2.landmarks

        # Vérifier si on peut faire un morphing ou une dissolution
        if landmarks1 is None or landmarks2 is None:
            if logger:
                logger.warning("Visage non détecté, utilisation de dissolution croisée")
            # Utiliser le générateur pour économiser la mémoire
            for frame in morpher.stream_cross_dissolve(im1, im2, frames_per_transition):
                encoder.write_frame(frame)
                frame_count += 1
        else:
            # Utiliser le générateur de morphing
            for frame in morpher.stream_morph_frames(
                im1, im2, landmarks1, landmarks2,
                frames_per_transition
            ):
                encoder.write_frame(frame)
                frame_count += 1

        # Frames de pause entre les transitions
        if pause_frames > 0:
            for _ in range(pause_frames):
                encoder.write_frame(im2)
                frame_count += 1

        pair_idx += 1

        # Forcer le garbage collection après chaque paire
        gc.collect()

    # Finaliser l'encodage
    if not encoder.finish_encoding():
        raise RuntimeError("Erreur lors de la finalisation de l'encodage")

    # Mettre à jour le contexte
    context.output_video = output_path

    # Gérer les exports supplémentaires
    extra_exports = {}

    # Export GIF si demandé
    if config.get('create_gif', False):
        gif_path = create_gif_from_video(output_path, morph_dir, fps, logger)
        if gif_path:
            extra_exports['gif'] = gif_path

    # Export thumbnail si demandé
    if config.get('thumbnail', True):
        thumbnail_path = create_thumbnail(output_path, morph_dir, logger)
        if thumbnail_path:
            extra_exports['thumbnail'] = thumbnail_path

    if logger:
        logger.success(f"Vidéo créée: {output_path} ({frame_count} frames)")
        if extra_exports:
            logger.info(f"Exports additionnels: {list(extra_exports.keys())}")

    return {
        'output_video': output_path,
        'total_frames': frame_count,
        'duration': frame_count / fps,
        'resolution': (w, h),
        'extra_exports': extra_exports
    }


def create_gif_from_video(video_path: str, output_dir: str, fps: int, logger=None) -> Optional[str]:
    """
    Crée un GIF animé à partir de la vidéo.

    Args:
        video_path: Chemin vers la vidéo source
        output_dir: Dossier de sortie
        fps: FPS de la vidéo source
        logger: Logger

    Returns:
        Chemin du GIF créé ou None
    """
    try:
        from PIL import Image as PILImage
        import subprocess

        gif_path = os.path.join(output_dir, "morph_preview.gif")

        # Utiliser FFmpeg pour créer le GIF (plus efficace)
        gif_fps = min(fps, 15)  # Limiter le FPS du GIF

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f'fps={gif_fps},scale=480:-1:flags=lanczos',
            '-loop', '0',
            gif_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode == 0 and os.path.exists(gif_path):
            if logger:
                logger.info(f"GIF créé: {gif_path}")
            return gif_path
        else:
            if logger:
                logger.warning("Échec de la création du GIF")
            return None

    except Exception as e:
        if logger:
            logger.warning(f"Erreur création GIF: {e}")
        return None


def create_thumbnail(video_path: str, output_dir: str, logger=None) -> Optional[str]:
    """
    Crée une miniature à partir de la vidéo.

    Args:
        video_path: Chemin vers la vidéo source
        output_dir: Dossier de sortie
        logger: Logger

    Returns:
        Chemin de la miniature ou None
    """
    try:
        import subprocess

        thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")

        # Extraire une frame au milieu de la vidéo
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', 'thumbnail,scale=640:-1',
            '-frames:v', '1',
            thumbnail_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0 and os.path.exists(thumbnail_path):
            if logger:
                logger.info(f"Miniature créée: {thumbnail_path}")
            return thumbnail_path
        else:
            return None

    except Exception as e:
        if logger:
            logger.warning(f"Erreur création miniature: {e}")
        return None


class MorphStep:
    """Classe wrapper pour l'étape de morphing"""

    ID = "03_morph"
    NAME = "Morphing facial"
    DESCRIPTION = "Crée la vidéo de morphing entre les visages (optimisé mémoire)"

    @staticmethod
    def create_step():
        """Crée l'instance WorkflowStep"""
        from .workflow_manager import WorkflowStep
        return WorkflowStep(
            id=MorphStep.ID,
            name=MorphStep.NAME,
            description=MorphStep.DESCRIPTION,
            function=morph_faces
        )
