"""
Validators - Module de validation des entrées
Gestion robuste des erreurs et validation des données
"""

import os
import re
import shutil
from typing import Optional, List, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ValidationLevel(Enum):
    """Niveau de sévérité de la validation"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Résultat d'une validation"""
    valid: bool
    level: ValidationLevel
    message: str
    field: str = ""
    suggestion: str = ""

    def __bool__(self):
        return self.valid


class ValidationError(Exception):
    """Exception levée lors d'une erreur de validation critique"""

    def __init__(self, message: str, results: Optional[List[ValidationResult]] = None):
        super().__init__(message)
        self.results = results or []


class InputValidator:
    """
    Validateur d'entrées pour MorphoLapse.

    Valide:
    - Chemins de fichiers et dossiers
    - Paramètres numériques
    - Formats de fichiers
    - Configuration
    """

    # Extensions d'images supportées
    SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

    # Extensions vidéo supportées
    SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.webm', '.mov', '.mkv'}

    # Limites des paramètres
    PARAM_LIMITS = {
        'fps': (1, 120),
        'transition_duration': (0.1, 60.0),
        'pause_duration': (0.0, 60.0),
        'border_size': (0, 500),
        'detection_threshold': (0.0, 1.0),
    }

    @classmethod
    def validate_directory(
        cls,
        path: str,
        must_exist: bool = True,
        must_be_writable: bool = False,
        min_files: int = 0,
        file_extensions: Optional[set] = None
    ) -> ValidationResult:
        """
        Valide un chemin de dossier.

        Args:
            path: Chemin à valider
            must_exist: Le dossier doit exister
            must_be_writable: Le dossier doit être accessible en écriture
            min_files: Nombre minimum de fichiers attendus
            file_extensions: Extensions de fichiers à compter

        Returns:
            ValidationResult
        """
        if not path or not path.strip():
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message="Chemin non spécifié",
                field="directory",
                suggestion="Veuillez sélectionner un dossier"
            )

        path = os.path.abspath(path.strip())

        # Vérifier l'existence
        if must_exist and not os.path.exists(path):
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"Le dossier n'existe pas: {path}",
                field="directory",
                suggestion="Vérifiez le chemin ou créez le dossier"
            )

        if must_exist and not os.path.isdir(path):
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"Le chemin n'est pas un dossier: {path}",
                field="directory"
            )

        # Vérifier les droits d'écriture
        if must_be_writable:
            if os.path.exists(path) and not os.access(path, os.W_OK):
                return ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Pas de droits d'écriture sur: {path}",
                    field="directory",
                    suggestion="Choisissez un autre dossier ou modifiez les permissions"
                )

        # Compter les fichiers
        if min_files > 0 and os.path.exists(path):
            extensions = file_extensions or cls.SUPPORTED_IMAGE_EXTENSIONS
            files = [
                f for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f))
                and os.path.splitext(f)[1].lower() in extensions
            ]
            if len(files) < min_files:
                return ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Pas assez de fichiers: {len(files)}/{min_files}",
                    field="directory",
                    suggestion=f"Le dossier doit contenir au moins {min_files} images"
                )

        return ValidationResult(
            valid=True,
            level=ValidationLevel.INFO,
            message="Dossier valide",
            field="directory"
        )

    @classmethod
    def validate_file(
        cls,
        path: str,
        must_exist: bool = True,
        allowed_extensions: Optional[set] = None,
        max_size_mb: Optional[float] = None
    ) -> ValidationResult:
        """
        Valide un chemin de fichier.

        Args:
            path: Chemin du fichier
            must_exist: Le fichier doit exister
            allowed_extensions: Extensions autorisées
            max_size_mb: Taille maximale en Mo

        Returns:
            ValidationResult
        """
        if not path or not path.strip():
            return ValidationResult(
                valid=True,  # Fichier optionnel
                level=ValidationLevel.INFO,
                message="Fichier non spécifié (optionnel)",
                field="file"
            )

        path = os.path.abspath(path.strip())

        # Vérifier l'existence
        if must_exist and not os.path.exists(path):
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"Fichier non trouvé: {path}",
                field="file"
            )

        if must_exist and not os.path.isfile(path):
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"N'est pas un fichier: {path}",
                field="file"
            )

        # Vérifier l'extension
        if allowed_extensions:
            ext = os.path.splitext(path)[1].lower()
            if ext not in allowed_extensions:
                return ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Extension non supportée: {ext}",
                    field="file",
                    suggestion=f"Extensions valides: {', '.join(allowed_extensions)}"
                )

        # Vérifier la taille
        if max_size_mb and os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > max_size_mb:
                return ValidationResult(
                    valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Fichier trop volumineux: {size_mb:.1f} Mo > {max_size_mb} Mo",
                    field="file"
                )

        return ValidationResult(
            valid=True,
            level=ValidationLevel.INFO,
            message="Fichier valide",
            field="file"
        )

    @classmethod
    def validate_numeric(
        cls,
        value: Any,
        param_name: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        allow_float: bool = True
    ) -> ValidationResult:
        """
        Valide une valeur numérique.

        Args:
            value: Valeur à valider
            param_name: Nom du paramètre
            min_val: Valeur minimale
            max_val: Valeur maximale
            allow_float: Autoriser les décimales

        Returns:
            ValidationResult
        """
        # Utiliser les limites par défaut si disponibles
        if param_name in cls.PARAM_LIMITS:
            default_min, default_max = cls.PARAM_LIMITS[param_name]
            min_val = min_val if min_val is not None else default_min
            max_val = max_val if max_val is not None else default_max

        try:
            if allow_float:
                num_value = float(value)
            else:
                num_value = int(value)
        except (ValueError, TypeError):
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"Valeur non numérique pour {param_name}: {value}",
                field=param_name,
                suggestion="Entrez une valeur numérique valide"
            )

        if min_val is not None and num_value < min_val:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"{param_name} trop petit: {num_value} < {min_val}",
                field=param_name,
                suggestion=f"Valeur minimale: {min_val}"
            )

        if max_val is not None and num_value > max_val:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"{param_name} trop grand: {num_value} > {max_val}",
                field=param_name,
                suggestion=f"Valeur maximale: {max_val}"
            )

        return ValidationResult(
            valid=True,
            level=ValidationLevel.INFO,
            message=f"{param_name} valide: {num_value}",
            field=param_name
        )

    @classmethod
    def validate_disk_space(
        cls,
        path: str,
        required_mb: float
    ) -> ValidationResult:
        """
        Vérifie l'espace disque disponible.

        Args:
            path: Chemin du dossier
            required_mb: Espace requis en Mo

        Returns:
            ValidationResult
        """
        try:
            # Trouver le point de montage
            if os.path.exists(path):
                check_path = path
            else:
                check_path = os.path.dirname(path)
                while not os.path.exists(check_path) and check_path:
                    check_path = os.path.dirname(check_path)

            if not check_path:
                check_path = os.getcwd()

            total, used, free = shutil.disk_usage(check_path)
            free_mb = free / (1024 * 1024)

            if free_mb < required_mb:
                return ValidationResult(
                    valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Espace disque insuffisant: {free_mb:.0f} Mo < {required_mb:.0f} Mo requis",
                    field="disk_space",
                    suggestion="Libérez de l'espace ou choisissez un autre emplacement"
                )

            return ValidationResult(
                valid=True,
                level=ValidationLevel.INFO,
                message=f"Espace disque OK: {free_mb:.0f} Mo disponibles",
                field="disk_space"
            )

        except Exception as e:
            return ValidationResult(
                valid=True,  # Ne pas bloquer en cas d'erreur
                level=ValidationLevel.WARNING,
                message=f"Impossible de vérifier l'espace disque: {e}",
                field="disk_space"
            )

    @classmethod
    def validate_ffmpeg(cls) -> ValidationResult:
        """
        Vérifie que FFmpeg est disponible.

        Returns:
            ValidationResult
        """
        import subprocess

        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extraire la version
                output = result.stdout.decode('utf-8', errors='ignore')
                version_match = re.search(r'ffmpeg version (\S+)', output)
                version = version_match.group(1) if version_match else "inconnue"

                return ValidationResult(
                    valid=True,
                    level=ValidationLevel.INFO,
                    message=f"FFmpeg trouvé (version {version})",
                    field="ffmpeg"
                )

        except FileNotFoundError:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.CRITICAL,
                message="FFmpeg n'est pas installé",
                field="ffmpeg",
                suggestion="Installez FFmpeg: https://ffmpeg.org/download.html"
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.WARNING,
                message="FFmpeg ne répond pas",
                field="ffmpeg"
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"Erreur FFmpeg: {e}",
                field="ffmpeg"
            )

        return ValidationResult(
            valid=False,
            level=ValidationLevel.ERROR,
            message="FFmpeg non fonctionnel",
            field="ffmpeg"
        )

    @classmethod
    def validate_model_file(cls, path: str) -> ValidationResult:
        """
        Valide le fichier de modèle dlib.

        Args:
            path: Chemin vers le fichier .dat

        Returns:
            ValidationResult
        """
        expected_name = "shape_predictor_68_face_landmarks.dat"

        if not path:
            # Chercher dans les emplacements standards
            search_paths = [
                f"./{expected_name}",
                f"./assets/{expected_name}",
                f"../assets/{expected_name}",
            ]
            for sp in search_paths:
                if os.path.exists(sp):
                    return ValidationResult(
                        valid=True,
                        level=ValidationLevel.INFO,
                        message=f"Modèle trouvé: {sp}",
                        field="model"
                    )

            return ValidationResult(
                valid=False,
                level=ValidationLevel.CRITICAL,
                message=f"Modèle non trouvé: {expected_name}",
                field="model",
                suggestion="Téléchargez le modèle depuis dlib.net"
            )

        if not os.path.exists(path):
            return ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                message=f"Fichier modèle non trouvé: {path}",
                field="model"
            )

        # Vérifier la taille (environ 99 Mo)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb < 90 or size_mb > 110:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.WARNING,
                message=f"Taille du modèle suspecte: {size_mb:.1f} Mo (attendu ~99 Mo)",
                field="model",
                suggestion="Le fichier est peut-être corrompu"
            )

        return ValidationResult(
            valid=True,
            level=ValidationLevel.INFO,
            message="Modèle valide",
            field="model"
        )


class WorkflowValidator:
    """Validateur complet pour le workflow"""

    def __init__(self, context):
        self.context = context
        self.errors: List[ValidationResult] = []
        self.warnings: List[ValidationResult] = []

    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        """
        Valide toutes les entrées du workflow.

        Returns:
            Tuple (is_valid, list_of_results)
        """
        results = []

        # Dossier source
        result = InputValidator.validate_directory(
            self.context.input_dir,
            must_exist=True,
            min_files=2,
            file_extensions=InputValidator.SUPPORTED_IMAGE_EXTENSIONS
        )
        results.append(result)

        # Dossier de sortie
        if self.context.output_dir:
            result = InputValidator.validate_directory(
                self.context.output_dir,
                must_exist=False,
                must_be_writable=True
            )
            results.append(result)

        # Image de référence (optionnel)
        if self.context.reference_image:
            result = InputValidator.validate_file(
                self.context.reference_image,
                must_exist=True,
                allowed_extensions=InputValidator.SUPPORTED_IMAGE_EXTENSIONS
            )
            results.append(result)

        # Modèle dlib
        model_path = self.context.config.get('model_path', '')
        result = InputValidator.validate_model_file(model_path)
        results.append(result)

        # FFmpeg
        result = InputValidator.validate_ffmpeg()
        results.append(result)

        # Paramètres numériques
        for param in ['fps', 'transition_duration', 'pause_duration', 'border_size']:
            if param in self.context.config:
                result = InputValidator.validate_numeric(
                    self.context.config[param],
                    param
                )
                results.append(result)

        # Espace disque (estimation: 50 Mo par image)
        if self.context.input_dir and os.path.exists(self.context.input_dir):
            num_images = len([
                f for f in os.listdir(self.context.input_dir)
                if os.path.splitext(f)[1].lower() in InputValidator.SUPPORTED_IMAGE_EXTENSIONS
            ])
            required_space = num_images * 50  # 50 Mo par image en moyenne

            output_path = self.context.output_dir or self.context.run_dir
            if output_path:
                result = InputValidator.validate_disk_space(output_path, required_space)
                results.append(result)

        # Séparer erreurs et warnings
        self.errors = [r for r in results if not r.valid and r.level in (ValidationLevel.ERROR, ValidationLevel.CRITICAL)]
        self.warnings = [r for r in results if not r.valid and r.level == ValidationLevel.WARNING]

        is_valid = len(self.errors) == 0
        return is_valid, results

    def get_error_summary(self) -> str:
        """Retourne un résumé des erreurs"""
        if not self.errors:
            return "Aucune erreur"

        lines = ["Erreurs de validation:"]
        for error in self.errors:
            lines.append(f"  • {error.message}")
            if error.suggestion:
                lines.append(f"    → {error.suggestion}")

        return "\n".join(lines)
