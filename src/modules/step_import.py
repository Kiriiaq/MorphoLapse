"""
Import Step - Étape d'importation des images
"""

import os
import shutil
from collections.abc import Callable
from pathlib import Path

from ..utils.file_utils import FileUtils
from .workflow_manager import WorkflowContext

# Image validation constants
MIN_IMAGE_SIZE = 100  # Minimum 100 bytes
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # Maximum 50 MB
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"\xff\xd8\xff": "JPEG",
    b"GIF87a": "GIF",
    b"GIF89a": "GIF",
    b"BM": "BMP",
    b"RIFF": "WEBP",
}


class ImageValidationError(Exception):
    """Exception for image validation failures."""

    def __init__(self, message: str, file_path: str, error_type: str):
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.error_type = error_type


def validate_image_file(file_path: str) -> tuple:
    """
    Validate a single image file.

    Args:
        file_path: Path to image file

    Returns:
        (is_valid, error_message, warnings)

    Raises:
        ImageValidationError: If image is invalid
    """
    path = Path(file_path)
    warnings = []

    # Check existence
    if not path.exists():
        raise ImageValidationError(f"File not found: {file_path}", file_path, "NOT_FOUND")

    # Check read permission
    if not os.access(path, os.R_OK):
        raise ImageValidationError(f"Permission denied: {file_path}", file_path, "PERMISSION_DENIED")

    # Check file size
    try:
        size = path.stat().st_size
    except Exception as e:
        raise ImageValidationError(f"Cannot read file: {e}", file_path, "READ_ERROR") from e

    if size < MIN_IMAGE_SIZE:
        raise ImageValidationError(f"Image too small ({size} bytes): {file_path}", file_path, "TOO_SMALL")

    if size > MAX_IMAGE_SIZE:
        warnings.append(f"Large image ({size / 1024 / 1024:.1f} MB): {path.name}")

    # Check extension
    ext = path.suffix.lower()
    if ext not in VALID_EXTENSIONS:
        warnings.append(f"Unusual extension: {ext}")

    # Check magic bytes (signature)
    try:
        with open(path, "rb") as f:
            header = f.read(16)

        valid_signature = any(header.startswith(sig) for sig in IMAGE_SIGNATURES)

        if not valid_signature and ext in VALID_EXTENSIONS:
            raise ImageValidationError(
                f"Invalid image format (corrupted or not an image): {file_path}", file_path, "CORRUPTED"
            )
    except ImageValidationError:
        raise
    except Exception as e:
        raise ImageValidationError(f"Cannot validate image: {e}", file_path, "VALIDATION_ERROR") from e

    # Try to open with PIL for final validation
    try:
        from PIL import Image

        with Image.open(file_path) as img:
            if img.width == 0 or img.height == 0:
                raise ImageValidationError(f"Image has zero dimensions: {file_path}", file_path, "ZERO_DIMENSIONS")
    except ImageValidationError:
        raise
    except Exception as e:
        raise ImageValidationError(f"Cannot open image (corrupted): {file_path} - {e}", file_path, "CORRUPTED") from e

    return True, None, warnings


def import_images(context: WorkflowContext, progress_callback: Callable, logger=None) -> dict:
    """
    Étape d'importation des images sources.

    Args:
        context: Contexte du workflow
        progress_callback: Callback(current, total, message)
        logger: Logger instance

    Returns:
        Dictionnaire des résultats
    """
    if logger:
        logger.info("Demarrage de l'importation des images")

    input_dir = context.input_dir
    if not input_dir or not os.path.isdir(input_dir):
        raise ValueError(f"Repertoire d'entree invalide: {input_dir}")

    # Check read permission on input directory
    if not os.access(input_dir, os.R_OK):
        raise PermissionError(f"Permission denied (read): {input_dir}")

    # Créer le dossier d'import dans le run
    import_dir = os.path.join(context.run_dir, "01_import")
    os.makedirs(import_dir, exist_ok=True)

    # Lister les images
    image_files = FileUtils.get_image_files(input_dir)
    if not image_files:
        raise ValueError(f"Aucune image trouvee dans: {input_dir}")

    # Validate all images first
    if logger:
        logger.info(f"Validation de {len(image_files)} images...")

    validated_files = []
    skipped_files = []
    all_warnings = []

    for img_path in image_files:
        try:
            is_valid, error, warnings = validate_image_file(img_path)
            validated_files.append(img_path)
            all_warnings.extend(warnings)
        except ImageValidationError as e:
            if logger:
                logger.warning(f"Image ignoree: {e.message}")
            skipped_files.append((img_path, str(e)))

    if not validated_files:
        raise ValueError(f"Aucune image valide trouvee dans: {input_dir}")

    if skipped_files and logger:
        logger.warning(f"{len(skipped_files)} image(s) ignoree(s) (invalides)")

    for warning in all_warnings[:5]:  # Show first 5 warnings only
        if logger:
            logger.warning(warning)

    if logger:
        logger.info(f"Importation de {len(validated_files)} images valides...")

    # Copier et traiter les images
    imported = []
    total = len(validated_files)

    for idx, src_path in enumerate(validated_files):
        filename = os.path.basename(src_path)

        # Renommer pour tri lexicographique si nécessaire
        name, ext = os.path.splitext(filename)
        new_name = FileUtils.pad_numbers_in_filename(name) + ext
        dst_path = os.path.join(import_dir, new_name)

        # Copier le fichier
        shutil.copy2(src_path, dst_path)
        imported.append(dst_path)

        progress_callback(idx + 1, total, f"Import: {filename}")

    # Mettre à jour le contexte
    context.images = sorted(imported)

    if logger:
        logger.success(f"{len(imported)} images importées avec succès")

    return {"imported_count": len(imported), "import_dir": import_dir, "files": imported}


class ImportStep:
    """Classe wrapper pour l'étape d'import"""

    ID = "01_import"
    NAME = "Import des images"
    DESCRIPTION = "Importe et prépare les images sources pour le traitement"

    @staticmethod
    def create_step():
        """Crée l'instance WorkflowStep"""
        from .workflow_manager import WorkflowStep

        return WorkflowStep(
            id=ImportStep.ID, name=ImportStep.NAME, description=ImportStep.DESCRIPTION, function=import_images
        )
