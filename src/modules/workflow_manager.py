"""
Workflow Manager - Gestionnaire des étapes de traitement
"""

import os
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import traceback


class StepStatus(Enum):
    """États possibles d'une étape"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"
    DISABLED = "disabled"


@dataclass
class WorkflowStep:
    """Définition d'une étape du workflow"""
    id: str
    name: str
    description: str
    function: Callable
    enabled: bool = True
    status: StepStatus = StepStatus.PENDING
    progress: float = 0.0
    error_message: str = ""
    result: Any = None
    duration: float = 0.0


@dataclass
class WorkflowContext:
    """Contexte partagé entre les étapes"""
    run_dir: str = ""
    input_dir: str = ""
    output_dir: str = ""
    reference_image: str = ""
    images: List[str] = field(default_factory=list)
    landmarks: List[Any] = field(default_factory=list)
    aligned_images: List[str] = field(default_factory=list)
    output_video: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


class WorkflowManager:
    """Gestionnaire du workflow de traitement"""

    def __init__(self, logger=None, config_manager=None):
        """
        Initialise le gestionnaire de workflow.

        Args:
            logger: Instance du logger
            config_manager: Instance du ConfigManager
        """
        self.logger = logger
        self.config = config_manager
        self._steps: List[WorkflowStep] = []
        self._context = WorkflowContext()
        self._is_running = False
        self._should_stop = False
        self._current_step_index = -1

        # Callbacks
        self._on_step_start: List[Callable] = []
        self._on_step_complete: List[Callable] = []
        self._on_step_error: List[Callable] = []
        self._on_progress: List[Callable] = []
        self._on_workflow_complete: List[Callable] = []

    def add_step(self, step: WorkflowStep):
        """
        Ajoute une étape au workflow.

        Args:
            step: Étape à ajouter
        """
        self._steps.append(step)
        self._log_info(f"Étape ajoutée: {step.name}")

    def remove_step(self, step_id: str):
        """
        Retire une étape du workflow.

        Args:
            step_id: ID de l'étape
        """
        self._steps = [s for s in self._steps if s.id != step_id]

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """
        Récupère une étape par son ID.

        Args:
            step_id: ID de l'étape

        Returns:
            WorkflowStep ou None
        """
        for step in self._steps:
            if step.id == step_id:
                return step
        return None

    def enable_step(self, step_id: str, enabled: bool = True):
        """
        Active ou désactive une étape.

        Args:
            step_id: ID de l'étape
            enabled: État souhaité
        """
        step = self.get_step(step_id)
        if step:
            step.enabled = enabled
            step.status = StepStatus.PENDING if enabled else StepStatus.DISABLED

    def set_context(self, **kwargs):
        """
        Met à jour le contexte du workflow.

        Args:
            **kwargs: Attributs du contexte à mettre à jour
        """
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)
            else:
                self._context.extra[key] = value

    def create_run_directory(self) -> str:
        """
        Crée le répertoire du run actuel.

        Returns:
            Chemin du répertoire créé
        """
        base_dir = "./runs"
        if self.config:
            base_dir = self.config.get("paths.runs_dir", base_dir)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(base_dir, timestamp)

        os.makedirs(run_dir, exist_ok=True)

        # Créer les sous-dossiers
        for step in self._steps:
            step_dir = os.path.join(run_dir, f"{step.id}")
            os.makedirs(step_dir, exist_ok=True)

        self._context.run_dir = run_dir
        self._log_info(f"Run directory créé: {run_dir}")

        return run_dir

    def run(self, continue_on_error: bool = False) -> bool:
        """
        Exécute le workflow complet.

        Args:
            continue_on_error: Continuer malgré les erreurs

        Returns:
            True si le workflow s'est terminé avec succès
        """
        if self._is_running:
            self._log_error("Un workflow est déjà en cours")
            return False

        self._is_running = True
        self._should_stop = False
        self._reset_steps()

        # Créer le répertoire du run
        self.create_run_directory()

        success = True
        start_time = datetime.now()

        self._log_info("=== Démarrage du workflow ===")

        for idx, step in enumerate(self._steps):
            if self._should_stop:
                self._log_info("Workflow interrompu par l'utilisateur")
                break

            self._current_step_index = idx

            if not step.enabled:
                step.status = StepStatus.SKIPPED
                self._log_info(f"Étape ignorée (désactivée): {step.name}")
                continue

            # Exécuter l'étape
            step_success = self._run_step(step)

            if not step_success:
                success = False
                if not continue_on_error:
                    self._log_error(f"Workflow arrêté suite à l'erreur: {step.name}")
                    break

        total_duration = (datetime.now() - start_time).total_seconds()
        self._log_info(f"=== Workflow terminé en {total_duration:.1f}s ===")

        self._is_running = False
        self._current_step_index = -1

        # Notifier la fin
        for callback in self._on_workflow_complete:
            try:
                callback(success, self._context)
            except Exception:
                pass

        return success

    def _run_step(self, step: WorkflowStep) -> bool:
        """
        Exécute une étape unique.

        Args:
            step: Étape à exécuter

        Returns:
            True si l'étape a réussi
        """
        step.status = StepStatus.RUNNING
        step.progress = 0.0
        step.error_message = ""

        self._log_info(f"[STEP] Démarrage: {step.name}")
        self._notify_step_start(step)

        start_time = datetime.now()

        try:
            # Créer une fonction de progression
            def progress_callback(current, total, message=""):
                step.progress = (current / total * 100) if total > 0 else 0
                self._notify_progress(step, step.progress, message)

            # Exécuter la fonction de l'étape
            result = step.function(self._context, progress_callback, self.logger)
            step.result = result
            step.status = StepStatus.COMPLETED
            step.progress = 100.0

            step.duration = (datetime.now() - start_time).total_seconds()
            self._log_info(f"[STEP] Terminé: {step.name} ({step.duration:.1f}s)")
            self._notify_step_complete(step)

            return True

        except Exception as e:
            step.status = StepStatus.ERROR
            step.error_message = str(e)
            step.duration = (datetime.now() - start_time).total_seconds()

            self._log_error(f"[STEP] Erreur: {step.name} - {e}")
            self._log_error(traceback.format_exc())
            self._notify_step_error(step, e)

            return False

    def stop(self):
        """Demande l'arrêt du workflow"""
        self._should_stop = True
        self._log_info("Arrêt du workflow demandé...")

    def _reset_steps(self):
        """Réinitialise l'état de toutes les étapes"""
        for step in self._steps:
            step.status = StepStatus.PENDING if step.enabled else StepStatus.DISABLED
            step.progress = 0.0
            step.error_message = ""
            step.result = None
            step.duration = 0.0

    # === Callbacks ===

    def on_step_start(self, callback: Callable):
        """Enregistre un callback pour le démarrage d'étape"""
        self._on_step_start.append(callback)

    def on_step_complete(self, callback: Callable):
        """Enregistre un callback pour la fin d'étape"""
        self._on_step_complete.append(callback)

    def on_step_error(self, callback: Callable):
        """Enregistre un callback pour les erreurs d'étape"""
        self._on_step_error.append(callback)

    def on_progress(self, callback: Callable):
        """Enregistre un callback pour la progression"""
        self._on_progress.append(callback)

    def on_workflow_complete(self, callback: Callable):
        """Enregistre un callback pour la fin du workflow"""
        self._on_workflow_complete.append(callback)

    def _notify_step_start(self, step: WorkflowStep):
        for callback in self._on_step_start:
            try:
                callback(step)
            except Exception:
                pass

    def _notify_step_complete(self, step: WorkflowStep):
        for callback in self._on_step_complete:
            try:
                callback(step)
            except Exception:
                pass

    def _notify_step_error(self, step: WorkflowStep, error: Exception):
        for callback in self._on_step_error:
            try:
                callback(step, error)
            except Exception:
                pass

    def _notify_progress(self, step: WorkflowStep, progress: float, message: str):
        for callback in self._on_progress:
            try:
                callback(step, progress, message)
            except Exception:
                pass

    # === Propriétés ===

    @property
    def steps(self) -> List[WorkflowStep]:
        return self._steps

    @property
    def context(self) -> WorkflowContext:
        return self._context

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def current_step(self) -> Optional[WorkflowStep]:
        if 0 <= self._current_step_index < len(self._steps):
            return self._steps[self._current_step_index]
        return None

    def _log_info(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str):
        if self.logger:
            self.logger.error(message)
