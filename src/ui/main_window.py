"""
Main Window - Fenêtre principale de l'application
Version compacte avec options avancées
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
from typing import Optional

from .. import __version__ as MORPHOLAPSE_VERSION
from .widgets import StepIndicator, LogViewer, OptionsPanel, ImagePreview, ToolTip, QuickActions
from ..utils.logger import Logger, LogLevel, LogEntry
from ..utils.config_manager import ConfigManager
from ..utils.paths import get_icon_path
from ..modules.workflow_manager import WorkflowManager, WorkflowStep, StepStatus
from ..modules.step_import import ImportStep
from ..modules.step_align import AlignStep
from ..modules.step_morph import MorphStep
from ..modules.step_export import ExportStep


class MainWindow(ctk.CTk):
    """Fenêtre principale de MorphoLapse - Version compacte"""

    def __init__(self):
        super().__init__()

        # Configuration de la fenêtre - 90% de l'écran
        self.title(f"MorphoLapse {MORPHOLAPSE_VERSION} - Face Morphing & Time-Lapse Generator")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = int(screen_width * 0.9)
        height = int(screen_height * 0.9)
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(900, 600)

        # Icône de l'application (barre des tâches + fenêtre)
        icon_path = get_icon_path()
        if icon_path.exists():
            self.iconbitmap(str(icon_path))

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
            text=f"v{MORPHOLAPSE_VERSION} - Face Morphing Time-lapse",
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

        # Only options exposed in the UI are loaded here. Removed inert keys
        # in commit 9 (auto_crop, stabilize, detection_threshold, multi_face,
        # parallel_processing, num_threads, auto_backup, export_frames,
        # export_landmarks, output_format) — see DIAGNOSTIC.md.
        options = {
            # Video
            'fps': self.config_manager.get("morphing.fps", 25),
            'video_quality': self.config_manager.get("video.quality", "high"),
            'resolution': self.config_manager.get("video.resolution", "original"),
            # Morphing
            'transition_duration': self.config_manager.get("morphing.transition_duration", 3.0),
            'pause_duration': self.config_manager.get("morphing.pause_duration", 0.0),
            'easing': self.config_manager.get("morphing.easing", "linear"),
            'blend_mode': self.config_manager.get("morphing.blend_mode", "alpha"),
            # Alignment
            'border_size': self.config_manager.get("alignment.border_size", 0),
            'overlay_mode': self.config_manager.get("alignment.overlay_mode", False),
            # Detection
            'retry_detection': self.config_manager.get("detection.retry", 3),
            # Workflow
            'continue_on_error': self.config_manager.get("workflow.continue_on_error", False),
            'debug_mode': self.config_manager.get("workflow.debug_mode", False),
            # Export
            'create_gif': self.config_manager.get("export.gif", False),
            'thumbnail': self.config_manager.get("export.thumbnail", True),
        }
        self.options_panel.set_options(options)

    def _save_settings(self):
        """Sauvegarde les paramètres exposés dans l'UI."""
        # Sauvegarder les chemins
        self.config_manager.set("paths.last_input_dir", self.input_dir.get(), auto_save=False)
        self.config_manager.set("paths.last_output_dir", self.output_dir.get(), auto_save=False)

        # Sauvegarder les options exposées
        options = self.options_panel.get_options()

        # Video
        self.config_manager.set("morphing.fps", int(options.get('fps', 25)), auto_save=False)
        self.config_manager.set("video.quality", options.get('video_quality', 'high'), auto_save=False)
        self.config_manager.set("video.resolution", options.get('resolution', 'original'), auto_save=False)

        # Morphing
        self.config_manager.set("morphing.transition_duration", options.get('transition_duration', 3.0), auto_save=False)
        self.config_manager.set("morphing.pause_duration", options.get('pause_duration', 0.0), auto_save=False)
        self.config_manager.set("morphing.easing", options.get('easing', 'linear'), auto_save=False)
        self.config_manager.set("morphing.blend_mode", options.get('blend_mode', 'alpha'), auto_save=False)

        # Alignment
        self.config_manager.set("alignment.border_size", int(options.get('border_size', 0)), auto_save=False)
        self.config_manager.set("alignment.overlay_mode", options.get('overlay_mode', False), auto_save=False)

        # Detection
        self.config_manager.set("detection.retry", int(options.get('retry_detection', 3)), auto_save=False)

        # Workflow
        debug_mode = bool(options.get('debug_mode', False))
        self.config_manager.set("workflow.continue_on_error", options.get('continue_on_error', False), auto_save=False)
        self.config_manager.set("workflow.debug_mode", debug_mode, auto_save=False)

        # Export
        self.config_manager.set("export.gif", options.get('create_gif', False), auto_save=False)
        self.config_manager.set("export.thumbnail", options.get('thumbnail', True), auto_save=False)

        self.config_manager.save()

        # Apply debug_mode immediately
        self.logger.set_level(LogLevel.DEBUG if debug_mode else LogLevel.INFO)

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
        """Gère les actions rapides depuis la toolbar.

        Only handles the ids declared in QuickActions.ACTIONS (open, save).
        export/clear/settings/reset/help branches were removed in commit 10
        — they had no corresponding button.
        """
        if action == "open":
            self._select_input_dir()
        elif action == "save":
            self._save_settings()

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
                'resolution': options.get('resolution', 'original'),
                # Morphing
                'transition_duration': options.get('transition_duration', 3.0),
                'pause_duration': options.get('pause_duration', 0.0),
                'easing': options.get('easing', 'linear'),
                'blend_mode': options.get('blend_mode', 'alpha'),
                # Alignment
                'border_size': int(options.get('border_size', 0)),
                'overlay_mode': options.get('overlay_mode', False),
                # Detection
                'retry_detection': int(options.get('retry_detection', 3)),
                # Workflow
                'debug_mode': bool(options.get('debug_mode', False)),
                # Export
                'create_gif': options.get('create_gif', False),
                'thumbnail': options.get('thumbnail', True),
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
    """Point d'entrée de l'application avec splash screen"""
    from ..utils.splash_screen import SplashScreen

    # Splash screen avec progression (tout dans le main thread)
    splash = SplashScreen("MorphoLapse", MORPHOLAPSE_VERSION, width=450, height=220)
    splash.show()

    try:
        splash.update_progress(20, "Chargement de la configuration...")
        splash.update_progress(40, "Initialisation des modules...")
        splash.update_progress(60, "Création de l'interface...")
        app = MainWindow()  # heavy work; provides natural splash duration
        splash.update_progress(80, "Finalisation...")
        splash.update_progress(100, "Démarrage...")

        splash.close()
        app.mainloop()

    except Exception as e:
        splash.close()
        import traceback
        traceback.print_exc()
        from tkinter import messagebox
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erreur", f"Échec du démarrage: {e}")
        root.destroy()
