"""
Config Manager - Gestion de la configuration JSON
"""

import json
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class MorphingConfig:
    """Configuration du morphing"""
    transition_duration: float = 3.0
    pause_duration: float = 0.0
    fps: int = 25
    codec: str = "libx264"
    quality: str = "medium"


@dataclass
class AlignmentConfig:
    """Configuration de l'alignement"""
    border_size: int = 0
    overlay_mode: bool = False
    max_detection_attempts: int = 3


@dataclass
class UIConfig:
    """Configuration de l'interface"""
    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    log_level: str = "INFO"
    show_tooltips: bool = True
    language: str = "fr"


@dataclass
class PathsConfig:
    """Configuration des chemins"""
    model_path: str = "./shape_predictor_68_face_landmarks.dat"
    last_input_dir: str = ""
    last_output_dir: str = ""
    runs_dir: str = "./runs"


@dataclass
class WorkflowConfig:
    """Configuration du workflow"""
    continue_on_error: bool = False
    auto_cleanup: bool = True
    create_run_folders: bool = True
    debug_mode: bool = False
    parallel: bool = True
    num_threads: int = 0  # 0 = auto (nombre de CPU)
    auto_backup: bool = False


@dataclass
class VideoConfig:
    """Configuration vidéo"""
    quality: str = "high"
    format: str = "mp4"
    resolution: str = "original"


@dataclass
class DetectionConfig:
    """Configuration de la détection faciale"""
    threshold: float = 0.5
    multi_face: bool = False
    retry: bool = False


@dataclass
class ExportConfig:
    """Configuration de l'export"""
    frames: bool = False
    landmarks: bool = False
    gif: bool = False
    thumbnail: bool = True


@dataclass
class AppConfig:
    """Configuration complète de l'application"""
    morphing: MorphingConfig = field(default_factory=MorphingConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    version: str = "2.0.0"


class ConfigManager:
    """Gestionnaire de configuration avec persistance JSON"""

    DEFAULT_CONFIG_NAME = "config.json"
    DEFAULT_CONFIG_DIR = "config"

    def __init__(self, config_path: str = None):
        """
        Initialise le gestionnaire de configuration.

        Args:
            config_path: Chemin du fichier de configuration
        """
        self._config_path = config_path or self._get_default_config_path()
        self._config: AppConfig = AppConfig()
        self._default_config: AppConfig = AppConfig()
        self._callbacks = []

    def _get_default_config_path(self) -> str:
        """Retourne le chemin par défaut du fichier de config"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_dir = os.path.join(base_dir, self.DEFAULT_CONFIG_DIR)
        return os.path.join(config_dir, self.DEFAULT_CONFIG_NAME)

    def load(self) -> bool:
        """
        Charge la configuration depuis le fichier.

        Returns:
            True si le chargement a réussi
        """
        if not os.path.exists(self._config_path):
            # Créer une configuration par défaut
            self.save()
            return True

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruire la configuration
            self._config = self._dict_to_config(data)
            self._notify_change()
            return True

        except json.JSONDecodeError as e:
            print(f"Erreur de parsing JSON: {e}")
            return False
        except Exception as e:
            print(f"Erreur de chargement: {e}")
            return False

    def save(self) -> bool:
        """
        Sauvegarde la configuration dans le fichier.

        Returns:
            True si la sauvegarde a réussi
        """
        try:
            # Créer le dossier si nécessaire
            config_dir = os.path.dirname(self._config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            # Convertir en dict et sauvegarder
            data = self._config_to_dict(self._config)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Erreur de sauvegarde: {e}")
            return False

    def reset_to_defaults(self):
        """Réinitialise la configuration aux valeurs par défaut"""
        self._config = AppConfig()
        self.save()
        self._notify_change()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration.

        Args:
            key: Clé de configuration (ex: "morphing.fps")
            default: Valeur par défaut

        Returns:
            Valeur de configuration
        """
        parts = key.split('.')
        obj = self._config

        try:
            for part in parts:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return default
            return obj
        except Exception:
            return default

    def set(self, key: str, value: Any, auto_save: bool = True):
        """
        Définit une valeur de configuration.

        Args:
            key: Clé de configuration
            value: Nouvelle valeur
            auto_save: Sauvegarder automatiquement
        """
        parts = key.split('.')
        obj = self._config

        try:
            # Naviguer jusqu'au parent
            for part in parts[:-1]:
                obj = getattr(obj, part)

            # Définir la valeur
            setattr(obj, parts[-1], value)

            if auto_save:
                self.save()

            self._notify_change()

        except Exception as e:
            print(f"Erreur de configuration: {e}")

    def add_change_callback(self, callback):
        """Ajoute un callback appelé lors des changements"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_change_callback(self, callback):
        """Retire un callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_change(self):
        """Notifie tous les callbacks d'un changement"""
        for callback in self._callbacks:
            try:
                callback(self._config)
            except Exception:
                pass

    def _config_to_dict(self, config: AppConfig) -> dict:
        """Convertit la configuration en dictionnaire"""
        return {
            'morphing': asdict(config.morphing),
            'alignment': asdict(config.alignment),
            'ui': asdict(config.ui),
            'paths': asdict(config.paths),
            'workflow': asdict(config.workflow),
            'video': asdict(config.video),
            'detection': asdict(config.detection),
            'export': asdict(config.export),
            'version': config.version
        }

    def _dict_to_config(self, data: dict) -> AppConfig:
        """Convertit un dictionnaire en configuration"""
        config = AppConfig()

        if 'morphing' in data:
            config.morphing = MorphingConfig(**data['morphing'])
        if 'alignment' in data:
            config.alignment = AlignmentConfig(**data['alignment'])
        if 'ui' in data:
            config.ui = UIConfig(**data['ui'])
        if 'paths' in data:
            config.paths = PathsConfig(**data['paths'])
        if 'workflow' in data:
            config.workflow = WorkflowConfig(**data['workflow'])
        if 'video' in data:
            config.video = VideoConfig(**data['video'])
        if 'detection' in data:
            config.detection = DetectionConfig(**data['detection'])
        if 'export' in data:
            config.export = ExportConfig(**data['export'])
        if 'version' in data:
            config.version = data['version']

        return config

    @property
    def config(self) -> AppConfig:
        """Accès direct à la configuration"""
        return self._config

    @property
    def morphing(self) -> MorphingConfig:
        return self._config.morphing

    @property
    def alignment(self) -> AlignmentConfig:
        return self._config.alignment

    @property
    def ui(self) -> UIConfig:
        return self._config.ui

    @property
    def paths(self) -> PathsConfig:
        return self._config.paths

    @property
    def workflow(self) -> WorkflowConfig:
        return self._config.workflow

    @property
    def config_path(self) -> str:
        return self._config_path
