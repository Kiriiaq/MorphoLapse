"""
Logger - Système de journalisation en temps réel
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Callable, List
from enum import Enum
from queue import Queue
from threading import Lock


class LogLevel(Enum):
    """Niveaux de log"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogEntry:
    """Entrée de log structurée"""

    def __init__(self, level: LogLevel, message: str, timestamp: datetime = None,
                 source: str = None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self.source = source or ""

    def __str__(self):
        time_str = self.timestamp.strftime("%H:%M:%S")
        level_str = self.level.name.ljust(8)
        source_str = f"[{self.source}] " if self.source else ""
        return f"{time_str} | {level_str} | {source_str}{self.message}"

    def to_dict(self):
        return {
            'level': self.level.name,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source
        }


class Logger:
    """Système de logging avec support temps réel et callbacks"""

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, name: str = "MorphoLapse", log_dir: str = None,
                 console_output: bool = True, file_output: bool = True):
        if self._initialized:
            return

        self.name = name
        self.log_dir = log_dir or os.path.join(os.getcwd(), "logs")
        self.console_output = console_output
        self.file_output = file_output

        self._level = LogLevel.INFO
        self._callbacks: List[Callable[[LogEntry], None]] = []
        self._history: List[LogEntry] = []
        self._max_history = 10000
        self._file_handler = None
        self._current_log_file = None
        self._queue = Queue()

        self._setup_logging()
        self._initialized = True

    def _setup_logging(self):
        """Configure le système de logging"""
        # Créer le dossier de logs si nécessaire
        if self.file_output and not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

        # Configurer le logger Python standard
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()

        # Format
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )

        # Handler console
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

        # Handler fichier
        if self.file_output:
            self._setup_file_handler()

    def _setup_file_handler(self):
        """Configure le handler de fichier de log"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = f"{self.name}_{timestamp}.log"
        self._current_log_file = os.path.join(self.log_dir, log_filename)

        file_handler = logging.FileHandler(
            self._current_log_file,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self._logger.addHandler(file_handler)
        self._file_handler = file_handler

    def set_level(self, level: LogLevel):
        """Définit le niveau de log minimum"""
        self._level = level
        self._logger.setLevel(level.value)

    def add_callback(self, callback: Callable[[LogEntry], None]):
        """Ajoute un callback appelé à chaque log"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[LogEntry], None]):
        """Retire un callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _log(self, level: LogLevel, message: str, source: str = None):
        """Méthode interne de logging"""
        if level.value < self._level.value:
            return

        entry = LogEntry(level, message, source=source)

        # Ajouter à l'historique
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Logger via le système standard
        self._logger.log(level.value, message)

        # Appeler les callbacks
        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception:
                pass

    def debug(self, message: str, source: str = None):
        """Log niveau DEBUG"""
        self._log(LogLevel.DEBUG, message, source)

    def info(self, message: str, source: str = None):
        """Log niveau INFO"""
        self._log(LogLevel.INFO, message, source)

    def warning(self, message: str, source: str = None):
        """Log niveau WARNING"""
        self._log(LogLevel.WARNING, message, source)

    def error(self, message: str, source: str = None):
        """Log niveau ERROR"""
        self._log(LogLevel.ERROR, message, source)

    def critical(self, message: str, source: str = None):
        """Log niveau CRITICAL"""
        self._log(LogLevel.CRITICAL, message, source)

    def success(self, message: str, source: str = None):
        """Log de succès (niveau INFO avec préfixe)"""
        self._log(LogLevel.INFO, f"[OK] {message}", source)

    def step(self, step_name: str, status: str = "START"):
        """Log une étape du workflow"""
        self._log(LogLevel.INFO, f"[STEP] {step_name}: {status}")

    def progress(self, current: int, total: int, message: str = ""):
        """Log de progression"""
        percent = (current / total * 100) if total > 0 else 0
        self._log(LogLevel.INFO, f"[{percent:.1f}%] {message} ({current}/{total})")

    def get_history(self, level: LogLevel = None, limit: int = None) -> List[LogEntry]:
        """
        Récupère l'historique des logs.

        Args:
            level: Filtrer par niveau minimum
            limit: Nombre maximum d'entrées

        Returns:
            Liste des entrées de log
        """
        history = self._history

        if level:
            history = [e for e in history if e.level.value >= level.value]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self):
        """Vide l'historique"""
        self._history.clear()

    def export_log(self, filepath: str) -> bool:
        """
        Exporte l'historique dans un fichier.

        Args:
            filepath: Chemin du fichier

        Returns:
            True si l'export a réussi
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self._history:
                    f.write(str(entry) + '\n')
            return True
        except Exception as e:
            self.error(f"Erreur d'export: {e}")
            return False

    @property
    def current_log_file(self) -> Optional[str]:
        """Retourne le chemin du fichier de log actuel"""
        return self._current_log_file

    def start_run_log(self, run_dir: str):
        """
        Démarre un nouveau fichier de log pour un run spécifique.

        Args:
            run_dir: Répertoire du run
        """
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)

        log_file = os.path.join(run_dir, "run.log")
        self._current_log_file = log_file

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self._logger.addHandler(file_handler)
        self._file_handler = file_handler


def get_logger(name: str = "MorphoLapse") -> Logger:
    """
    Factory pour obtenir l'instance du logger.

    Args:
        name: Nom du logger

    Returns:
        Instance du Logger singleton
    """
    return Logger(name)
