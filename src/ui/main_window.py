"""
Main Window - Fenêtre principale de l'application
Version compacte avec options avancées
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
from typing import Optional

from .widgets import StepIndicator, LogViewer, OptionsPanel, ImagePreview, ToolTip, QuickActions
from ..utils.logger import Logger, LogLevel, LogEntry
from ..utils.config_manager import ConfigManager
from ..modules.workflow_manager import WorkflowManager, WorkflowStep, StepStatus
from ..modules.step_import import ImportStep
from ..modules.step_align import AlignStep
from ..modules.step_morph import MorphStep
from ..modules.step_export import ExportStep


class MainWindow(ctk.CTk):
    """Fenêtre principale de MorphoLapse - Version compacte"""

    def __init__(self):
        super().__init__()

        # Configuration de la fenêtre - TAILLE RÉDUITE
        self.title("MorphoLapse 2.0")
        self.geometry("1100x700")
        self.minsize(900, 600)

        # Thème
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Composants
        self.logger = Logger("MorphoLapse")
        self.config_manager = ConfigManager()
        self.config_manager.load()
        self.workflow: Optional[WorkflowManager] = None

        # Variables
        self.input_dir = ctk.StringVar(value="")
        self.reference_image = ctk.StringVar(value="")
        self.output_dir = ctk.StringVar(value="")
        self._step_indicators = {}

        # Setup
        self._setup_ui()
        self._setup_workflow()
        self._setup_logger_callback()
        self._load_last_settings()

        # Logging initial
        self.logger.info("MorphoLapse démarré")
        self.logger.info(f"Configuration chargée: {self.config_manager.config_path}")

    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        # Frame principale avec grille
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === Sidebar gauche ===
        self._create_sidebar()

        # === Zone centrale ===
        self._create_main_area()

        # === Sidebar droite (options) ===
        self._create_options_panel()

    def _create_sidebar(self):
        """Crée la sidebar gauche avec les étapes - VERSION COMPACTE"""
        sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Logo / Titre - COMPACT
        title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(
            title_frame,
            text="🎬 MorphoLapse",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="v2.0 - Face Morphing Time-lapse",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60")
        ).pack(anchor="w")

        # Séparateur
        ctk.CTkFrame(sidebar, height=1, fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=5)

        # Section Dossiers - COMPACT
        folders_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        folders_frame.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(
            folders_frame,
            text="📁 Dossiers",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", pady=(0, 5))

        # Input directory
        self._create_folder_selector(
            folders_frame, "Dossier source:", self.input_dir,
            self._select_input_dir, "Dossier contenant les images sources"
        )

        # Reference image
        self._create_folder_selector(
            folders_frame, "Image de référence:", self.reference_image,
            self._select_reference, "Image pour l'alignement (optionnel)", is_file=True
        )

        # Output directory
        self._create_folder_selector(
            folders_frame, "Dossier de sortie:", self.output_dir,
            self._select_output_dir, "Dossier pour les résultats"
        )

        # Séparateur
        ctk.CTkFrame(sidebar, height=1, fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=5)

        # Section Workflow - COMPACT
        workflow_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        workflow_frame.pack(fill="both", expand=True, padx=10, pady=3)

        ctk.CTkLabel(
            workflow_frame,
            text="📋 Workflow",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", pady=(0, 5))

        # Container scrollable pour les étapes
        self.steps_container = ctk.CTkScrollableFrame(
            workflow_frame,
            fg_color="transparent"
        )
        self.steps_container.pack(fill="both", expand=True)

        # Boutons d'action - COMPACT
        actions_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions_frame.pack(fill="x", padx=10, pady=8)

        self.run_button = ctk.CTkButton(
            actions_frame,
            text="▶️ Lancer",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35,
            command=self._run_workflow
        )
        self.run_button.pack(fill="x", pady=(0, 3))
        ToolTip(self.run_button, "Exécute toutes les étapes activées")

        self.stop_button = ctk.CTkButton(
            actions_frame,
            text="⏹️ Stop",
            height=28,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._stop_workflow,
            state="disabled"
        )
        self.stop_button.pack(fill="x")

    def _create_folder_selector(self, parent, label: str, variable: ctk.StringVar,
                                 command, tooltip: str, is_file: bool = False):
        """Crée un sélecteur de dossier/fichier - COMPACT"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=10)
        ).pack(anchor="w")

        entry_frame = ctk.CTkFrame(frame, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(1, 0))

        entry = ctk.CTkEntry(
            entry_frame,
            textvariable=variable,
            height=24,
            font=ctk.CTkFont(size=10)
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 3))

        btn = ctk.CTkButton(
            entry_frame,
            text="...",
            width=28,
            height=24,
            command=command
        )
        btn.pack(side="right")

        ToolTip(frame, tooltip)

    def _create_main_area(self):
        """Crée la zone centrale - VERSION COMPACTE"""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        # Barre d'actions rapides
        self.quick_actions = QuickActions(
            main_frame,
            on_action=self._on_quick_action
        )
        self.quick_actions.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Zone d'aperçu - COMPACT
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        # Header avec titre et stats sur la même ligne
        header_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=8, pady=(5, 3))

        ctk.CTkLabel(
            header_frame,
            text="🖼️ Aperçu",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

        self.stats_label = ctk.CTkLabel(
            header_frame,
            text="0 images | Réf: Auto | Sortie: -",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60")
        )
        self.stats_label.pack(side="right")

        # Aperçus en ligne - TAILLE RÉDUITE
        previews_container = ctk.CTkFrame(preview_frame, fg_color="transparent")
        previews_container.pack(fill="x", padx=8, pady=(0, 5))

        # Première image
        first_frame = ctk.CTkFrame(previews_container, fg_color="transparent")
        first_frame.pack(side="left", padx=(0, 10))

        self.preview_first = ImagePreview(first_frame, size=(100, 100))
        self.preview_first.pack()
        ctk.CTkLabel(first_frame, text="Début", font=ctk.CTkFont(size=9)).pack()

        # Dernière image
        last_frame = ctk.CTkFrame(previews_container, fg_color="transparent")
        last_frame.pack(side="left", padx=(0, 10))

        self.preview_last = ImagePreview(last_frame, size=(100, 100))
        self.preview_last.pack()
        ctk.CTkLabel(last_frame, text="Fin", font=ctk.CTkFont(size=9)).pack()

        # Zone de logs - prend plus de place
        self.log_viewer = LogViewer(main_frame, height=150)
        self.log_viewer.grid(row=2, column=0, sticky="nsew")

        # Barre de progression globale - COMPACT
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))

        progress_inner = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_inner.pack(fill="x", padx=8, pady=4)

        self.global_progress_label = ctk.CTkLabel(
            progress_inner,
            text="Prêt",
            font=ctk.CTkFont(size=10)
        )
        self.global_progress_label.pack(side="left")

        self.global_progress_bar = ctk.CTkProgressBar(progress_inner, height=10, width=200)
        self.global_progress_bar.pack(side="right")
        self.global_progress_bar.set(0)

    def _create_options_panel(self):
        """Crée le panneau d'options à droite - COMPACT avec scrollbar intégrée"""
        # Le panneau est maintenant un CTkScrollableFrame dans widgets.py
        self.options_panel = OptionsPanel(self, width=230)
        self.options_panel.grid(row=0, column=2, sticky="nsew", padx=(0, 5), pady=5)

        # Boutons de sauvegarde/reset - COMPACT en bas
        btns_frame = ctk.CTkFrame(self, fg_color="transparent")
        btns_frame.grid(row=0, column=2, sticky="s", padx=5, pady=(0, 10))

        ctk.CTkButton(
            btns_frame,
            text="💾 Sauver",
            width=70,
            height=26,
            font=ctk.CTkFont(size=10),
            command=self._save_settings
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btns_frame,
            text="↺ Reset",
            width=60,
            height=26,
            font=ctk.CTkFont(size=10),
            fg_color=("gray70", "gray30"),
            command=self._reset_settings
        ).pack(side="left", padx=2)

    def _setup_workflow(self):
        """Configure le workflow avec les étapes"""
        self.workflow = WorkflowManager(
            logger=self.logger,
            config_manager=self.config_manager
        )

        # Ajouter les étapes
        steps = [
            ImportStep.create_step(),
            AlignStep.create_step(),
            MorphStep.create_step(),
            ExportStep.create_step()
        ]

        for step in steps:
            self.workflow.add_step(step)
            self._add_step_indicator(step)

        # Callbacks
        self.workflow.on_step_start(self._on_step_start)
        self.workflow.on_step_complete(self._on_step_complete)
        self.workflow.on_step_error(self._on_step_error)
        self.workflow.on_progress(self._on_progress)
        self.workflow.on_workflow_complete(self._on_workflow_complete)

    def _add_step_indicator(self, step: WorkflowStep):
        """Ajoute un indicateur d'étape dans la sidebar"""
        indicator = StepIndicator(
            self.steps_container,
            step.name,
            step.description,
            enabled=step.enabled,
            on_toggle=self._on_step_toggle
        )
        indicator.pack(fill="x", pady=2)
        self._step_indicators[step.id] = indicator

    def _setup_logger_callback(self):
        """Configure le callback pour afficher les logs dans l'UI"""
        def log_callback(entry: LogEntry):
            self.after(0, lambda: self.log_viewer.log(entry.message, entry.level.name))

        self.logger.add_callback(log_callback)

    def _load_last_settings(self):
        """Charge les derniers paramètres utilisés - avec nouvelles options"""
        self.input_dir.set(self.config_manager.get("paths.last_input_dir", ""))
        self.output_dir.set(self.config_manager.get("paths.last_output_dir", ""))

        # Charger les options (incluant les nouvelles)
        options = {
            # Video
            'fps': self.config_manager.get("morphing.fps", 25),
            'video_quality': self.config_manager.get("video.quality", "high"),
            'output_format': self.config_manager.get("video.format", "mp4"),
            'resolution': self.config_manager.get("video.resolution", "original"),
            # Morphing
            'transition_duration': self.config_manager.get("morphing.transition_duration", 3.0),
            'pause_duration': self.config_manager.get("morphing.pause_duration", 0.0),
            'easing': self.config_manager.get("morphing.easing", "linear"),
            'blend_mode': self.config_manager.get("morphing.blend_mode", "alpha"),
            # Alignment
            'border_size': self.config_manager.get("alignment.border_size", 0),
            'overlay_mode': self.config_manager.get("alignment.overlay_mode", False),
            'auto_crop': self.config_manager.get("alignment.auto_crop", False),
            'stabilize': self.config_manager.get("alignment.stabilize", False),
            # Detection (NEW)
            'detection_threshold': self.config_manager.get("detection.threshold", 0.5),
            'multi_face': self.config_manager.get("detection.multi_face", False),
            'retry_detection': self.config_manager.get("detection.retry", False),
            # Workflow
            'continue_on_error': self.config_manager.get("workflow.continue_on_error", False),
            'debug_mode': self.config_manager.get("workflow.debug_mode", False),
            'parallel_processing': self.config_manager.get("workflow.parallel", False),
            'auto_backup': self.config_manager.get("workflow.auto_backup", False),
            # Export (NEW)
            'export_frames': self.config_manager.get("export.frames", False),
            'export_landmarks': self.config_manager.get("export.landmarks", False),
            'create_gif': self.config_manager.get("export.gif", False),
            'thumbnail': self.config_manager.get("export.thumbnail", True)
        }
        self.options_panel.set_options(options)

    def _save_settings(self):
        """Sauvegarde les paramètres - toutes les nouvelles options incluses"""
        # Sauvegarder les chemins
        self.config_manager.set("paths.last_input_dir", self.input_dir.get(), auto_save=False)
        self.config_manager.set("paths.last_output_dir", self.output_dir.get(), auto_save=False)

        # Sauvegarder toutes les options
        options = self.options_panel.get_options()

        # Video
        self.config_manager.set("morphing.fps", int(options.get('fps', 25)), auto_save=False)
        self.config_manager.set("video.quality", options.get('video_quality', 'high'), auto_save=False)
        self.config_manager.set("video.format", options.get('output_format', 'mp4'), auto_save=False)
        self.config_manager.set("video.resolution", options.get('resolution', 'original'), auto_save=False)

        # Morphing
        self.config_manager.set("morphing.transition_duration", options.get('transition_duration', 3.0), auto_save=False)
        self.config_manager.set("morphing.pause_duration", options.get('pause_duration', 0.0), auto_save=False)
        self.config_manager.set("morphing.easing", options.get('easing', 'linear'), auto_save=False)
        self.config_manager.set("morphing.blend_mode", options.get('blend_mode', 'alpha'), auto_save=False)

        # Alignment
        self.config_manager.set("alignment.border_size", int(options.get('border_size', 0)), auto_save=False)
        self.config_manager.set("alignment.overlay_mode", options.get('overlay_mode', False), auto_save=False)
        self.config_manager.set("alignment.auto_crop", options.get('auto_crop', False), auto_save=False)
        self.config_manager.set("alignment.stabilize", options.get('stabilize', False), auto_save=False)

        # Detection (NEW)
        self.config_manager.set("detection.threshold", options.get('detection_threshold', 0.5), auto_save=False)
        self.config_manager.set("detection.multi_face", options.get('multi_face', False), auto_save=False)
        self.config_manager.set("detection.retry", options.get('retry_detection', False), auto_save=False)

        # Workflow
        self.config_manager.set("workflow.continue_on_error", options.get('continue_on_error', False), auto_save=False)
        self.config_manager.set("workflow.debug_mode", options.get('debug_mode', False), auto_save=False)
        self.config_manager.set("workflow.parallel", options.get('parallel_processing', False), auto_save=False)
        self.config_manager.set("workflow.auto_backup", options.get('auto_backup', False), auto_save=False)

        # Export (NEW)
        self.config_manager.set("export.frames", options.get('export_frames', False), auto_save=False)
        self.config_manager.set("export.landmarks", options.get('export_landmarks', False), auto_save=False)
        self.config_manager.set("export.gif", options.get('create_gif', False), auto_save=False)
        self.config_manager.set("export.thumbnail", options.get('thumbnail', True), auto_save=False)

        self.config_manager.save()
        self.logger.success("Paramètres sauvegardés")

    def _reset_settings(self):
        """Réinitialise les paramètres"""
        if messagebox.askyesno("Confirmation", "Réinitialiser tous les paramètres aux valeurs par défaut ?"):
            self.config_manager.reset_to_defaults()
            self._load_last_settings()
            self.logger.info("Paramètres réinitialisés")

    # === Sélection de dossiers ===

    def _select_input_dir(self):
        """Sélectionne le dossier d'entrée"""
        path = filedialog.askdirectory(title="Sélectionner le dossier source")
        if path:
            self.input_dir.set(path)
            self._update_previews()
            self.logger.info(f"Dossier source: {path}")

    def _select_reference(self):
        """Sélectionne l'image de référence"""
        path = filedialog.askopenfilename(
            title="Sélectionner l'image de référence",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")]
        )
        if path:
            self.reference_image.set(path)
            self.logger.info(f"Image de référence: {path}")

    def _select_output_dir(self):
        """Sélectionne le dossier de sortie"""
        path = filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if path:
            self.output_dir.set(path)
            self.logger.info(f"Dossier de sortie: {path}")

    def _update_previews(self):
        """Met à jour les aperçus"""
        from ..utils.file_utils import FileUtils

        input_dir = self.input_dir.get()
        if input_dir and os.path.isdir(input_dir):
            images = FileUtils.get_image_files(input_dir)
            if images:
                self.preview_first.set_image(images[0])
                self.preview_last.set_image(images[-1])

                ref = os.path.basename(self.reference_image.get())[:10] if self.reference_image.get() else "Auto"
                output = "✓" if self.output_dir.get() else "-"

                self.stats_label.configure(
                    text=f"{len(images)} images | Réf: {ref} | Sortie: {output}"
                )

    # === Actions rapides ===

    def _on_quick_action(self, action: str):
        """Gère les actions rapides depuis la toolbar"""
        if action == "open":
            self._select_input_dir()
        elif action == "save":
            self._save_settings()
        elif action == "export":
            self._run_workflow()
        elif action == "clear":
            self.log_viewer.clear()
        elif action == "settings":
            # Ouvrir le dossier de configuration
            config_path = self.config_manager.config_path
            if os.path.exists(config_path):
                os.startfile(os.path.dirname(config_path))
            else:
                self.logger.info("Aucun fichier de configuration trouvé")

    # === Workflow ===

    def _on_step_toggle(self, step_name: str, enabled: bool):
        """Callback quand une étape est activée/désactivée"""
        for step in self.workflow.steps:
            if step.name == step_name:
                self.workflow.enable_step(step.id, enabled)
                break

    def _run_workflow(self):
        """Lance le workflow"""
        # Validation
        if not self.input_dir.get():
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source")
            return

        # Configurer le contexte avec toutes les options
        options = self.options_panel.get_options()

        self.workflow.set_context(
            input_dir=self.input_dir.get(),
            reference_image=self.reference_image.get(),
            output_dir=self.output_dir.get(),
            config={
                # Paths
                'model_path': self.config_manager.get("paths.model_path", "./shape_predictor_68_face_landmarks.dat"),
                # Video
                'fps': int(options.get('fps', 25)),
                'video_quality': options.get('video_quality', 'high'),
                'output_format': options.get('output_format', 'mp4'),
                'resolution': options.get('resolution', 'original'),
                # Morphing
                'transition_duration': options.get('transition_duration', 3.0),
                'pause_duration': options.get('pause_duration', 0.0),
                'easing': options.get('easing', 'linear'),
                'blend_mode': options.get('blend_mode', 'alpha'),
                # Alignment
                'border_size': int(options.get('border_size', 0)),
                'overlay_mode': options.get('overlay_mode', False),
                'auto_crop': options.get('auto_crop', False),
                'stabilize': options.get('stabilize', False),
                # Detection
                'detection_threshold': options.get('detection_threshold', 0.5),
                'multi_face': options.get('multi_face', False),
                'retry_detection': options.get('retry_detection', False),
                # Workflow
                'parallel_processing': options.get('parallel_processing', False),
                'auto_backup': options.get('auto_backup', False),
                'debug_mode': options.get('debug_mode', False),
                # Export
                'export_frames': options.get('export_frames', False),
                'export_landmarks': options.get('export_landmarks', False),
                'create_gif': options.get('create_gif', False),
                'thumbnail': options.get('thumbnail', True)
            }
        )

        # UI
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.global_progress_bar.set(0)

        # Reset des indicateurs
        for indicator in self._step_indicators.values():
            indicator.set_status('pending')
            indicator.set_progress(0)

        # Lancer dans un thread
        continue_on_error = options.get('continue_on_error', False)

        def run_thread():
            self.workflow.run(continue_on_error=continue_on_error)

        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()

    def _stop_workflow(self):
        """Arrête le workflow"""
        if self.workflow:
            self.workflow.stop()
            self.logger.warning("Arrêt du workflow demandé...")

    def _on_step_start(self, step: WorkflowStep):
        """Callback au démarrage d'une étape"""
        def update():
            if step.id in self._step_indicators:
                self._step_indicators[step.id].set_status('running')
            self.global_progress_label.configure(text=f"En cours: {step.name}")

        self.after(0, update)

    def _on_step_complete(self, step: WorkflowStep):
        """Callback à la fin d'une étape"""
        def update():
            if step.id in self._step_indicators:
                self._step_indicators[step.id].set_status('completed')
                self._step_indicators[step.id].set_progress(100)

        self.after(0, update)

    def _on_step_error(self, step: WorkflowStep, error: Exception):
        """Callback en cas d'erreur"""
        def update():
            if step.id in self._step_indicators:
                self._step_indicators[step.id].set_status('error')

        self.after(0, update)

    def _on_progress(self, step: WorkflowStep, progress: float, message: str):
        """Callback de progression"""
        def update():
            if step.id in self._step_indicators:
                self._step_indicators[step.id].set_progress(progress)

            # Calculer la progression globale
            total_steps = len([s for s in self.workflow.steps if s.enabled])
            current_index = next(
                (i for i, s in enumerate(self.workflow.steps) if s.id == step.id),
                0
            )
            global_progress = (current_index + progress / 100) / total_steps
            self.global_progress_bar.set(global_progress)

        self.after(0, update)

    def _on_workflow_complete(self, success: bool, context):
        """Callback à la fin du workflow"""
        def update():
            self.run_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

            if success:
                self.global_progress_bar.set(1)
                self.global_progress_label.configure(text="Workflow terminé avec succès!")
                messagebox.showinfo(
                    "Succès",
                    f"Workflow terminé!\n\nRésultats dans:\n{context.run_dir}"
                )
            else:
                self.global_progress_label.configure(text="Workflow terminé avec des erreurs")

        self.after(0, update)


def run_app():
    """Point d'entrée de l'application"""
    app = MainWindow()
    app.mainloop()
