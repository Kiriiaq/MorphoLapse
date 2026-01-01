"""
Video Encoder - Module d'encodage vidéo via FFmpeg
"""

import subprocess
import os
from typing import List, Tuple, Optional, Callable
from PIL import Image
import numpy as np
import cv2


class VideoEncoder:
    """Encodeur vidéo utilisant FFmpeg"""

    def __init__(self, logger=None):
        """
        Initialise l'encodeur vidéo.

        Args:
            logger: Instance du logger
        """
        self.logger = logger
        self._process = None
        self._ffmpeg_available = None

    def check_ffmpeg(self) -> bool:
        """
        Vérifie que FFmpeg est disponible.

        Returns:
            True si FFmpeg est installé
        """
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
        Démarre un processus d'encodage en streaming.

        Args:
            output_path: Chemin du fichier de sortie
            fps: Images par seconde
            size: Taille (width, height), None = auto
            codec: Codec vidéo
            quality: Préréglage de qualité (ultrafast, fast, medium, slow)

        Returns:
            True si le processus a démarré
        """
        if not self.check_ffmpeg():
            return False

        # Construire la commande FFmpeg
        command = [
            'ffmpeg',
            '-y',  # Écraser sans demander
            '-f', 'image2pipe',
            '-r', str(fps),
        ]

        if size:
            command.extend(['-s', f'{size[0]}x{size[1]}'])

        command.extend([
            '-i', '-',  # Entrée depuis stdin
            '-c:v', codec,
            '-preset', quality,
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Assure dimensions paires
            '-pix_fmt', 'yuv420p',
            output_path
        ])

        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self._log_info(f"Encodage démarré: {output_path}")
            return True
        except Exception as e:
            self._log_error(f"Erreur de démarrage: {e}")
            return False

    def write_frame(self, frame: np.ndarray):
        """
        Écrit une frame au processus d'encodage.

        Args:
            frame: Image BGR (numpy array)
        """
        if self._process is None or self._process.poll() is not None:
            self._log_error("Aucun processus d'encodage actif")
            return

        try:
            # Convertir BGR vers RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            pil_image.save(self._process.stdin, 'JPEG')
        except Exception as e:
            self._log_error(f"Erreur d'écriture frame: {e}")

    def write_frames(self, frames: List[np.ndarray],
                     progress_callback: Callable[[int, int], None] = None):
        """
        Écrit plusieurs frames au processus d'encodage.

        Args:
            frames: Liste d'images BGR
            progress_callback: Callback(frame_idx, total)
        """
        total = len(frames)
        for idx, frame in enumerate(frames):
            self.write_frame(frame)
            if progress_callback:
                progress_callback(idx + 1, total)

    def write_pause_frames(self, frame: np.ndarray, count: int):
        """
        Écrit plusieurs copies d'une frame (pour pause).

        Args:
            frame: Image à répéter
            count: Nombre de répétitions
        """
        for _ in range(count):
            self.write_frame(frame)

    def finish_encoding(self) -> bool:
        """
        Termine l'encodage et attend la fin du processus.

        Returns:
            True si l'encodage s'est terminé correctement
        """
        if self._process is None:
            return False

        try:
            self._process.stdin.close()
            self._process.wait(timeout=600)  # 10 minutes pour les longues vidéos
            success = self._process.returncode == 0

            if success:
                self._log_info("Encodage terminé avec succès")
            else:
                stderr = self._process.stderr.read().decode('utf-8', errors='ignore')
                self._log_error(f"Erreur d'encodage: {stderr}")

            self._process = None
            return success

        except subprocess.TimeoutExpired:
            self._log_error("Timeout d'encodage")
            self._process.kill()
            self._process = None
            return False
        except Exception as e:
            self._log_error(f"Erreur de finalisation: {e}")
            self._process = None
            return False

    def encode_frames_to_video(self, frames: List[np.ndarray],
                               output_path: str,
                               fps: int = 25,
                               progress_callback: Callable[[int, int], None] = None) -> bool:
        """
        Encode une liste de frames en vidéo.

        Args:
            frames: Liste d'images BGR
            output_path: Chemin de sortie
            fps: Images par seconde
            progress_callback: Callback de progression

        Returns:
            True si l'encodage a réussi
        """
        if len(frames) == 0:
            self._log_error("Aucune frame à encoder")
            return False

        # Déterminer la taille depuis la première frame
        h, w = frames[0].shape[:2]

        if not self.start_encoding(output_path, fps, (w, h)):
            return False

        self.write_frames(frames, progress_callback)
        return self.finish_encoding()

    def encode_images_folder(self, folder_path: str, output_path: str,
                             fps: int = 25, pattern: str = "*.jpg",
                             progress_callback: Callable[[int, int], None] = None) -> bool:
        """
        Encode un dossier d'images en vidéo.

        Args:
            folder_path: Dossier contenant les images
            output_path: Chemin de sortie
            fps: Images par seconde
            pattern: Pattern glob pour les images
            progress_callback: Callback de progression

        Returns:
            True si l'encodage a réussi
        """
        import glob

        # Lister et trier les images
        image_files = sorted(glob.glob(os.path.join(folder_path, pattern)))

        if not image_files:
            self._log_error(f"Aucune image trouvée dans {folder_path}")
            return False

        # Lire la première image pour obtenir les dimensions
        first_image = cv2.imread(image_files[0])
        if first_image is None:
            self._log_error(f"Impossible de lire: {image_files[0]}")
            return False

        h, w = first_image.shape[:2]

        if not self.start_encoding(output_path, fps, (w, h)):
            return False

        total = len(image_files)
        for idx, image_path in enumerate(image_files):
            frame = cv2.imread(image_path)
            if frame is not None:
                self.write_frame(frame)
            if progress_callback:
                progress_callback(idx + 1, total)

        return self.finish_encoding()

    @property
    def stdin(self):
        """Accès au stdin du processus pour compatibilité"""
        if self._process:
            return self._process.stdin
        return None

    @property
    def is_encoding(self) -> bool:
        """Vérifie si un encodage est en cours"""
        return self._process is not None and self._process.poll() is None

    def _log_info(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str):
        if self.logger:
            self.logger.error(message)
