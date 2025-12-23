"""
File Utils - Utilitaires de gestion des fichiers
"""

import os
import re
import shutil
from datetime import datetime
from typing import List, Tuple, Optional
from PIL import Image
from PIL.ExifTags import TAGS


class FileUtils:
    """Utilitaires pour la gestion des fichiers et dossiers"""

    VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif'}
    VALID_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

    @staticmethod
    def get_image_files(directory: str, sort: bool = True) -> List[str]:
        """
        Liste les fichiers images d'un répertoire.

        Args:
            directory: Chemin du répertoire
            sort: Trier les fichiers

        Returns:
            Liste des chemins complets
        """
        if not os.path.isdir(directory):
            return []

        files = []
        for filename in os.listdir(directory):
            ext = os.path.splitext(filename)[1].lower()
            if ext in FileUtils.VALID_IMAGE_EXTENSIONS:
                files.append(os.path.join(directory, filename))

        if sort:
            files.sort(key=lambda x: os.path.basename(x).lower())

        return files

    @staticmethod
    def create_run_directory(base_dir: str = "./runs") -> str:
        """
        Crée un répertoire de run horodaté.

        Args:
            base_dir: Répertoire parent

        Returns:
            Chemin du nouveau répertoire
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(base_dir, timestamp)

        os.makedirs(run_dir, exist_ok=True)

        # Créer les sous-dossiers standard
        subdirs = ['01_import', '02_align', '03_morph', '04_export']
        for subdir in subdirs:
            os.makedirs(os.path.join(run_dir, subdir), exist_ok=True)

        return run_dir

    @staticmethod
    def pad_numbers_in_filename(filename: str, width: int = 6) -> str:
        """
        Pad les nombres dans un nom de fichier pour le tri lexicographique.

        Args:
            filename: Nom du fichier
            width: Largeur du padding

        Returns:
            Nom de fichier avec nombres paddés
        """
        parts = re.split(r'(\d+)', filename)
        for i, part in enumerate(parts):
            if part.isdigit():
                parts[i] = part.zfill(width)
        return ''.join(parts)

    @staticmethod
    def rename_files_for_sorting(directory: str, dry_run: bool = False) -> List[Tuple[str, str]]:
        """
        Renomme les fichiers pour un tri lexicographique correct.

        Args:
            directory: Répertoire à traiter
            dry_run: Simuler sans renommer

        Returns:
            Liste de tuples (ancien_nom, nouveau_nom)
        """
        changes = []
        files = FileUtils.get_image_files(directory, sort=False)

        for filepath in files:
            dirname = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)

            new_name = FileUtils.pad_numbers_in_filename(name) + ext
            new_path = os.path.join(dirname, new_name)

            if new_name != filename:
                changes.append((filepath, new_path))
                if not dry_run:
                    os.rename(filepath, new_path)

        return changes

    @staticmethod
    def get_exif_date(filepath: str) -> Optional[str]:
        """
        Extrait la date de prise de vue des métadonnées EXIF.

        Args:
            filepath: Chemin de l'image

        Returns:
            Date au format YYYY_MM_DD ou None
        """
        try:
            image = Image.open(filepath)
            exif_data = image._getexif()

            if exif_data:
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag)
                    if tag_name == "DateTimeOriginal":
                        return value.split(" ")[0].replace(":", "_")
        except Exception:
            pass

        return None

    @staticmethod
    def rename_with_exif_date(directory: str, dry_run: bool = False) -> List[Tuple[str, str]]:
        """
        Renomme les fichiers en ajoutant la date EXIF.

        Args:
            directory: Répertoire à traiter
            dry_run: Simuler sans renommer

        Returns:
            Liste de tuples (ancien_nom, nouveau_nom)
        """
        changes = []
        files = FileUtils.get_image_files(directory, sort=False)

        for filepath in files:
            date = FileUtils.get_exif_date(filepath)
            if date:
                dirname = os.path.dirname(filepath)
                filename = os.path.basename(filepath)

                new_name = f"{date}_{filename}"
                new_path = os.path.join(dirname, new_name)

                if not os.path.exists(new_path):
                    changes.append((filepath, new_path))
                    if not dry_run:
                        os.rename(filepath, new_path)

        return changes

    @staticmethod
    def copy_files(files: List[str], destination: str,
                   progress_callback=None) -> List[str]:
        """
        Copie une liste de fichiers vers un répertoire.

        Args:
            files: Liste des fichiers à copier
            destination: Répertoire destination
            progress_callback: Callback(index, total)

        Returns:
            Liste des nouveaux chemins
        """
        os.makedirs(destination, exist_ok=True)
        copied = []

        for idx, filepath in enumerate(files):
            if os.path.isfile(filepath):
                filename = os.path.basename(filepath)
                dest_path = os.path.join(destination, filename)
                shutil.copy2(filepath, dest_path)
                copied.append(dest_path)

            if progress_callback:
                progress_callback(idx + 1, len(files))

        return copied

    @staticmethod
    def clean_directory(directory: str, keep_subdirs: bool = False):
        """
        Nettoie un répertoire.

        Args:
            directory: Répertoire à nettoyer
            keep_subdirs: Conserver les sous-dossiers
        """
        if not os.path.isdir(directory):
            return

        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)

            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path) and not keep_subdirs:
                shutil.rmtree(item_path)

    @staticmethod
    def get_file_info(filepath: str) -> dict:
        """
        Récupère les informations d'un fichier.

        Args:
            filepath: Chemin du fichier

        Returns:
            Dictionnaire d'informations
        """
        if not os.path.exists(filepath):
            return {}

        stat = os.stat(filepath)
        info = {
            'name': os.path.basename(filepath),
            'path': filepath,
            'size': stat.st_size,
            'size_human': FileUtils._human_readable_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'extension': os.path.splitext(filepath)[1].lower()
        }

        # Informations supplémentaires pour les images
        if info['extension'] in FileUtils.VALID_IMAGE_EXTENSIONS:
            try:
                with Image.open(filepath) as img:
                    info['width'] = img.width
                    info['height'] = img.height
                    info['format'] = img.format
                    info['mode'] = img.mode
            except Exception:
                pass

        return info

    @staticmethod
    def _human_readable_size(size: int) -> str:
        """Convertit une taille en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @staticmethod
    def ensure_unique_filename(filepath: str) -> str:
        """
        Assure qu'un nom de fichier est unique.

        Args:
            filepath: Chemin proposé

        Returns:
            Chemin unique (avec suffixe si nécessaire)
        """
        if not os.path.exists(filepath):
            return filepath

        dirname = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)

        counter = 1
        while True:
            new_path = os.path.join(dirname, f"{name}_{counter}{ext}")
            if not os.path.exists(new_path):
                return new_path
            counter += 1
