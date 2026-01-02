"""
Video Encoder - Module d'encodage vidéo via FFmpeg
Version simplifiée et robuste - encode depuis un dossier d'images
"""

import subprocess
import os
from typing import List, Tuple, Optional, Callable
import numpy as np
import cv2


class VideoEncoder:
    """Encodeur vidéo utilisant FFmpeg - mode fichiers (plus robuste)"""

    def __init__(self, logger=None):
        self.logger = logger
        self._ffmpeg_available = None
        self._frames_dir = None
        self._frame_count = 0
        self._output_path = None
        self._fps = 25
        self._size = None

    def check_ffmpeg(self) -> bool:
        """Vérifie que FFmpeg est disponible."""
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available

        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._ffmpeg_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._ffmpeg_available = False

        if not self._ffmpeg_available:
            self._log_error("FFmpeg n'est pas installé ou accessible")

        return self._ffmpeg_available

    def start_encoding(self, output_path: str, fps: int = 25,
                       size: Tuple[int, int] = None,
                       codec: str = 'libx264',
                       quality: str = 'medium') -> bool:
        """
        Prépare l'encodage - crée un dossier temporaire pour les frames.
        """
        if not self.check_ffmpeg():
            return False

        self._output_path = output_path
        self._fps = fps
        self._size = size
        self._frame_count = 0

        # Créer dossier temporaire pour les frames
        output_dir = os.path.dirname(output_path)
        self._frames_dir = os.path.join(output_dir, "_frames_temp")
        os.makedirs(self._frames_dir, exist_ok=True)

        self._log_info(f"Préparation encodage: {output_path}")
        return True

    def write_frame(self, frame: np.ndarray):
        """Sauvegarde une frame en JPEG."""
        if self._frames_dir is None:
            self._log_error("Encodage non démarré")
            return

        try:
            # Redimensionner si nécessaire
            if self._size:
                w, h = self._size
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = cv2.resize(frame, (w, h))

            # Sauvegarder avec numérotation
            frame_path = os.path.join(self._frames_dir, f"frame_{self._frame_count:06d}.jpg")
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            self._frame_count += 1
        except Exception as e:
            self._log_error(f"Erreur écriture frame: {e}")

    def finish_encoding(self) -> bool:
        """Encode toutes les frames sauvegardées en vidéo avec FFmpeg."""
        if self._frames_dir is None or self._frame_count == 0:
            self._log_error("Aucune frame à encoder")
            return False

        self._log_info(f"Encodage de {self._frame_count} frames...")

        try:
            # Commande FFmpeg pour encoder depuis les images
            pattern = os.path.join(self._frames_dir, "frame_%06d.jpg")

            command = [
                'ffmpeg', '-y',
                '-framerate', str(self._fps),
                '-i', pattern,
                '-c:v', 'libx264',
                '-preset', 'fast',  # Fast pour éviter les timeouts
                '-crf', '23',       # Qualité correcte
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',  # Optimisé pour le web
                self._output_path
            ]

            self._log_info("Lancement FFmpeg...")

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3600  # 1 heure max
            )

            success = result.returncode == 0

            if success:
                self._log_info("Encodage terminé avec succès")
                # Nettoyer les frames temporaires
                self._cleanup_frames()
            else:
                self._log_error(f"Erreur FFmpeg: {result.stderr[:500]}")

            return success

        except subprocess.TimeoutExpired:
            self._log_error("Timeout FFmpeg (1 heure)")
            return False
        except Exception as e:
            self._log_error(f"Erreur encodage: {e}")
            return False

    def _cleanup_frames(self):
        """Supprime les frames temporaires."""
        if self._frames_dir and os.path.exists(self._frames_dir):
            try:
                import shutil
                shutil.rmtree(self._frames_dir)
                self._log_info("Frames temporaires supprimées")
            except Exception as e:
                self._log_error(f"Erreur nettoyage: {e}")

    def write_frames(self, frames: List[np.ndarray],
                     progress_callback: Callable[[int, int], None] = None):
        """Écrit plusieurs frames."""
        total = len(frames)
        for idx, frame in enumerate(frames):
            self.write_frame(frame)
            if progress_callback:
                progress_callback(idx + 1, total)

    def write_pause_frames(self, frame: np.ndarray, count: int):
        """Écrit plusieurs copies d'une frame."""
        for _ in range(count):
            self.write_frame(frame)

    def encode_frames_to_video(self, frames: List[np.ndarray],
                               output_path: str,
                               fps: int = 25,
                               progress_callback: Callable[[int, int], None] = None) -> bool:
        """Encode une liste de frames en vidéo."""
        if len(frames) == 0:
            self._log_error("Aucune frame à encoder")
            return False

        h, w = frames[0].shape[:2]

        if not self.start_encoding(output_path, fps, (w, h)):
            return False

        self.write_frames(frames, progress_callback)
        return self.finish_encoding()

    @property
    def is_encoding(self) -> bool:
        """Vérifie si un encodage est en préparation."""
        return self._frames_dir is not None

    @property
    def frame_count(self) -> int:
        """Nombre de frames écrites."""
        return self._frame_count

    def _log_info(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str):
        if self.logger:
            self.logger.error(message)
