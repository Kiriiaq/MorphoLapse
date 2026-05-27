"""
Main Window - Fenêtre principale de l'application
Version compacte avec options avancées
"""

import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import __version__ as MORPHOLAPSE_VERSION
from ..modules.step_align import AlignStep
from ..modules.step_export import ExportStep
from ..modules.step_import import ImportStep
from ..modules.step_morph import MorphStep
from ..modules.workflow_manager import StepStatus, WorkflowManager, WorkflowStep
from ..utils.config_manager import ConfigManager
from ..utils.logger import LogEntry, Logger, LogLevel
from ..utils.paths import get_dlib_model_path, get_icon_path
from .widgets import ImagePreview, LogViewer, OptionsPanel, QuickActions, StepIndicator


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
        self.workflow: WorkflowManager | None = None

        # Variables
        self.input_dir = ctk.StringVar(value="")
        self.reference_image = ctk.StringVar(value="")
        self.output_dir = ctk.StringVar(value="")
        # Dossier choisi par l'utilisateur pour les frames JPEG intermédiaires
        # du morphing. S'il reste vide, on garde le comportement par défaut
        # (frames dans runs/<ts>/03_morph/frames/). S'il est rempli, les
        # frames sont écrites dans <ce_dossier>/<timestamp>/ — pratique pour
        # les compiler ensuite avec n'importe quel outil externe (ffmpeg CLI,
        # Premiere, DaVinci…) sans dépendre du pipeline interne.
        self.intermediate_frames_dir = ctk.StringVar(value="")
        self._step_indicators = {}

        # État interne pour empêcher les doubles lancements (cf. _run_workflow)
        self._workflow_starting = False
        # Chemin du modèle dlib résolu lors de la validation pré-run, pour
        # le passer ensuite au WorkflowContext.config["model_path"].
        self._resolved_model_path: str = ""

        # Setup (ordre important : shortcuts en DERNIER, après que tous les
        # widgets et options soient peuplés, pour éviter qu'un raccourci
        # déclenché par hasard pendant l'initialisation n'agisse sur un état
        # incomplet — cf. DA-RES-3 du pré-rapport audit Phase 2).
        self._setup_ui()
        self._setup_workflow()
        self._setup_logger_callback()

        # Synchroniser l'état du bouton Lancer + stats + previews quand
        # l'utilisateur édite ou colle un chemin directement dans le champ.
        # Les sélecteurs (bouton "...") appelaient déjà ces helpers, mais une
        # frappe/paste libre dans le Entry ne déclenchait que la mise à jour
        # du bouton — laissant le compteur d'images à 0 (cf. DA-4 audit).
        self.input_dir.trace_add("write", self._on_input_dir_changed)
        self.reference_image.trace_add("write", self._on_reference_changed)
        self.output_dir.trace_add("write", self._on_output_dir_changed)
        self.intermediate_frames_dir.trace_add("write", self._on_intermediate_changed)

        self._load_last_settings()
        self._update_run_button_state()
        self._refresh_path_displays()

        # Enregistrer les raccourcis seulement maintenant que l'IHM est prête
        self._setup_shortcuts()

        # Logging initial
        self.logger.info("MorphoLapse démarré")
        self.logger.info(f"Configuration chargée: {self.config_manager.config_path}")

    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        # Frame principale avec grille
        # row 0 : contenu (sidebar / centre / options) — expand
        # row 1 : pied de page (footer) avec infos système + CPU + FFmpeg
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === Sidebar gauche ===
        self._create_sidebar()

        # === Zone centrale ===
        self._create_main_area()

        # === Sidebar droite (options) ===
        self._create_options_panel()

        # === Pied de page ===
        self._create_footer()

    def _create_sidebar(self):
        """Crée la sidebar gauche avec les étapes - VERSION COMPACTE"""
        sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Logo / Titre - COMPACT
        title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(title_frame, text="🎬 MorphoLapse", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text=f"v{MORPHOLAPSE_VERSION} - Face Morphing Time-lapse",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w")

        # Séparateur
        ctk.CTkFrame(sidebar, height=1, fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=5)

        # Section Dossiers - COMPACT
        folders_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        folders_frame.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(folders_frame, text="📁 Dossiers", font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", pady=(0, 5)
        )

        # Input directory
        self._create_folder_selector(
            folders_frame,
            "Dossier source:",
            self.input_dir,
            self._select_input_dir,
            "Dossier contenant les images sources",
        )

        # Reference image
        self._create_folder_selector(
            folders_frame,
            "Image de référence:",
            self.reference_image,
            self._select_reference,
            "Image pour l'alignement (optionnel)",
        )

        # Output directory
        self._create_folder_selector(
            folders_frame, "Dossier de sortie:", self.output_dir, self._select_output_dir, "Dossier pour les résultats"
        )

        # Intermediate frames directory — optionnel. Si rempli, les frames
        # du morphing y sont copiées dans un sous-dossier horodaté, ce qui
        # permet ensuite de les compiler avec n'importe quel outil externe.
        self._create_folder_selector(
            folders_frame,
            "Dossier frames (intermédiaire) :",
            self.intermediate_frames_dir,
            self._select_intermediate_frames_dir,
            "Optionnel — dossier où sauvegarder les frames JPEG du morphing "
            "pour les recompiler ensuite avec un autre outil",
        )

        # Bloc « Chemins sélectionnés » : récap en lecture-seule des 3 chemins
        # avec wrap multi-ligne. Permet de voir le chemin COMPLET (et pas
        # juste les premiers caractères comme dans l'Entry à scroll horizontal),
        # même quand l'utilisateur n'a pas le focus dessus.
        paths_summary = ctk.CTkFrame(folders_frame, fg_color=("gray90", "gray18"), corner_radius=4)
        paths_summary.pack(fill="x", pady=(6, 0))

        self._path_display_source = ctk.CTkLabel(
            paths_summary,
            text="📁 (aucun dossier source sélectionné)",
            font=ctk.CTkFont(size=9),
            text_color=("gray25", "gray75"),
            wraplength=230,
            justify="left",
            anchor="w",
        )
        self._path_display_source.pack(fill="x", padx=6, pady=(4, 1))

        self._path_display_ref = ctk.CTkLabel(
            paths_summary,
            text="🖼️ (auto — 1re image utilisée)",
            font=ctk.CTkFont(size=9),
            text_color=("gray25", "gray75"),
            wraplength=230,
            justify="left",
            anchor="w",
        )
        self._path_display_ref.pack(fill="x", padx=6, pady=1)

        self._path_display_output = ctk.CTkLabel(
            paths_summary,
            text="📂 (sortie dans runs/<timestamp>/)",
            font=ctk.CTkFont(size=9),
            text_color=("gray25", "gray75"),
            wraplength=230,
            justify="left",
            anchor="w",
        )
        self._path_display_output.pack(fill="x", padx=6, pady=1)

        self._path_display_frames = ctk.CTkLabel(
            paths_summary,
            text="🎞️ (frames dans runs/<ts>/03_morph/frames/)",
            font=ctk.CTkFont(size=9),
            text_color=("gray25", "gray75"),
            wraplength=230,
            justify="left",
            anchor="w",
        )
        self._path_display_frames.pack(fill="x", padx=6, pady=(1, 4))

        # Séparateur
        ctk.CTkFrame(sidebar, height=1, fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=5)

        # Section Workflow - COMPACT
        workflow_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        workflow_frame.pack(fill="both", expand=True, padx=10, pady=3)

        ctk.CTkLabel(workflow_frame, text="📋 Workflow", font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", pady=(0, 5)
        )

        # Container scrollable pour les étapes
        self.steps_container = ctk.CTkScrollableFrame(workflow_frame, fg_color="transparent")
        self.steps_container.pack(fill="both", expand=True)

        # Boutons d'action - COMPACT
        actions_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions_frame.pack(fill="x", padx=10, pady=8)

        # Sélecteur CPU placé AU-DESSUS du bouton Lancer : choix fait juste
        # avant de lancer le pipeline, pour exploiter (ou bridé volontairement)
        # tous les cœurs disponibles. Le réglage est appliqué par
        # _apply_cpu_setting() au moment du run (cv2.setNumThreads + env BLAS).
        cpu_count = max(1, os.cpu_count() or 4)
        cpu_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        cpu_frame.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            cpu_frame, text="CPU :", font=ctk.CTkFont(size=10), width=34, anchor="w"
        ).pack(side="left")

        cpu_values = ["Auto", "1", "2", "4", "8", f"Max ({cpu_count})"]
        self.cpu_threads = ctk.CTkOptionMenu(
            cpu_frame,
            values=cpu_values,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color=("gray85", "gray25"),
            button_color=("gray70", "gray35"),
            button_hover_color=("gray60", "gray45"),
        )
        self.cpu_threads.set("Auto")
        self.cpu_threads.pack(side="right", fill="x", expand=True)

        self.run_button = ctk.CTkButton(
            actions_frame,
            text="▶️ Lancer",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35,
            command=self._run_workflow,
            state="disabled",  # désactivé tant que input_dir vide (cf. _update_run_button_state)
        )
        self.run_button.pack(fill="x", pady=(0, 3))

        # Bouton Annuler/Stop : rouge quand actif, gris quand désactivé pour bonne visibilité
        self.stop_button = ctk.CTkButton(
            actions_frame,
            text="⏹️ Annuler",
            height=28,
            fg_color=("#c0392b", "#c0392b"),
            hover_color=("#a93226", "#a93226"),
            text_color=("#ffffff", "#ffffff"),
            command=self._stop_workflow,
            state="disabled",
        )
        self.stop_button.pack(fill="x")

    def _create_folder_selector(self, parent, label: str, variable: ctk.StringVar, command, tooltip: str):
        """Crée un sélecteur de dossier/fichier avec synchro manuelle Variable↔Entry.

        On NE PASSE PAS `textvariable=variable` à CTkEntry : sur certaines
        versions de customtkinter, ce binding ne propage pas .set() au
        rendu visuel (variable mise à jour, mais Entry vide à l'écran).
        À la place, on installe nos propres traces dans les deux sens :

        - StringVar → Entry  : trace_add("write") qui appelle delete + insert
                               puis xview_moveto(1.0) pour montrer la fin
                               du chemin (la partie informative quand long).
        - Entry → StringVar : <KeyRelease> + <FocusOut> qui propagent la
                               saisie utilisateur dans la variable.

        Le garde `if entry.get() != new` empêche toute boucle infinie.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w")

        entry_frame = ctk.CTkFrame(frame, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(1, 0))

        # Volontairement SANS textvariable : on synchronise manuellement.
        entry = ctk.CTkEntry(
            entry_frame,
            height=28,
            font=ctk.CTkFont(size=11),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 3))

        btn = ctk.CTkButton(entry_frame, text="...", width=30, height=28, command=command)
        btn.pack(side="right")

        # Variable → Entry
        def _var_to_entry(*_args):
            new = variable.get()
            if entry.get() != new:
                entry.delete(0, "end")
                entry.insert(0, new)
            try:
                entry.xview_moveto(1.0)
            except Exception:
                pass
        variable.trace_add("write", _var_to_entry)

        # Entry → Variable (saisie / paste manuels)
        def _entry_to_var(_event=None):
            new = entry.get()
            if variable.get() != new:
                variable.set(new)
        entry.bind("<KeyRelease>", _entry_to_var, add="+")
        entry.bind("<FocusOut>", _entry_to_var, add="+")

        # Application initiale (cas d'une variable pré-remplie via _load_last_settings)
        _var_to_entry()

        return entry

    def _create_main_area(self):
        """Crée la zone centrale - VERSION COMPACTE"""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        # Barre d'actions rapides
        self.quick_actions = QuickActions(main_frame, on_action=self._on_quick_action)
        self.quick_actions.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Zone d'aperçu - COMPACT
        preview_frame = ctk.CTkFrame(main_frame)
        preview_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        # Header avec titre et stats sur la même ligne
        header_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=8, pady=(5, 3))

        ctk.CTkLabel(header_frame, text="🖼️ Aperçu", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

        self.stats_label = ctk.CTkLabel(
            header_frame,
            text="0 images | Réf: Auto | Sortie: -",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
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

        # Barre de progression globale — visible et contrastée à l'état initial
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))

        progress_inner = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_inner.pack(fill="x", padx=10, pady=8)

        self.global_progress_label = ctk.CTkLabel(
            progress_inner,
            text="Prêt",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
            width=200,
        )
        self.global_progress_label.pack(side="left", padx=(0, 8))

        # Pourcentage visible à droite, mis à jour en parallèle de la barre
        self.global_progress_percent = ctk.CTkLabel(
            progress_inner,
            text="0 %",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=48,
            anchor="e",
        )
        self.global_progress_percent.pack(side="right", padx=(8, 0))

        self.global_progress_bar = ctk.CTkProgressBar(
            progress_inner,
            height=20,
            border_width=1,
            border_color=("gray55", "gray45"),
            progress_color=("#3b82f6", "#3b82f6"),
            # Track de fond contrasté pour que la barre soit identifiable
            # même à 0 % (le bord seul ne suffit pas sur certains thèmes ;
            # cf. DA-6 audit, plainte T-036 « aucune visibilité »).
            fg_color=("gray80", "gray25"),
            corner_radius=4,
        )
        self.global_progress_bar.pack(side="right", fill="x", expand=True, padx=4)
        self.global_progress_bar.set(0)

    def _create_options_panel(self):
        """Crée le panneau d'options à droite - COMPACT avec scrollbar intégrée.

        La cellule (0,2) contient un container vertical qui empile l'OptionsPanel
        (scrollable, prend toute la hauteur) et les boutons Sauver/Reset (ancrés
        en bas, hors de la zone scrollable). Cette structure évite la
        superposition observée pré-audit (cf. RAPPORT pré-audit, T-035).
        """
        right_container = ctk.CTkFrame(self, fg_color="transparent")
        right_container.grid(row=0, column=2, sticky="nsew", padx=(0, 5), pady=5)
        right_container.grid_columnconfigure(0, weight=1)
        right_container.grid_rowconfigure(0, weight=1)

        self.options_panel = OptionsPanel(right_container, width=230)
        self.options_panel.grid(row=0, column=0, sticky="nsew")

        # Boutons de sauvegarde/reset, ancrés en bas du container (pas dans le scroll)
        btns_frame = ctk.CTkFrame(right_container, fg_color="transparent")
        btns_frame.grid(row=1, column=0, sticky="ew", pady=(6, 4))

        save_btn = ctk.CTkButton(
            btns_frame,
            text="💾 Sauver",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._save_settings,
        )
        save_btn.pack(side="left", padx=4)

        reset_btn = ctk.CTkButton(
            btns_frame,
            text="↺ Reset",
            width=70,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray45"),
            border_width=1,
            border_color=("gray45", "gray55"),
            command=self._reset_settings,
        )
        reset_btn.pack(side="left", padx=4)

    def _create_footer(self):
        """Pied de page de l'app : statut FFmpeg + rappel CPU + version.

        Toujours visible (sticky en bas, ne défile pas) — informe l'utilisateur
        en permanence de l'état des deux dépendances critiques (FFmpeg pour
        l'encodage, sélecteur CPU pour la vitesse) sans qu'il ait à fouiller
        dans les paramètres.
        """
        footer = ctk.CTkFrame(self, height=26, corner_radius=0, fg_color=("gray85", "gray18"))
        footer.grid(row=1, column=0, columnspan=3, sticky="ew")
        footer.grid_propagate(False)

        # Gauche : version + identité
        ctk.CTkLabel(
            footer,
            text=f"MorphoLapse v{MORPHOLAPSE_VERSION}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray70"),
        ).pack(side="left", padx=(10, 6))

        # Séparateur visuel
        ctk.CTkLabel(
            footer, text="•", font=ctk.CTkFont(size=10), text_color=("gray60", "gray45")
        ).pack(side="left")

        # Centre : rappel CPU live (mis à jour via _refresh_footer_cpu)
        self._footer_cpu_label = ctk.CTkLabel(
            footer,
            text="CPU : …",
            font=ctk.CTkFont(size=10),
            text_color=("gray20", "gray85"),
        )
        self._footer_cpu_label.pack(side="left", padx=6)

        # Droite : statut FFmpeg (✓ vert ou ✗ rouge)
        ffmpeg_ok = self._probe_ffmpeg_available()
        self._footer_ffmpeg_label = ctk.CTkLabel(
            footer,
            text=f"FFmpeg : {'✓ détecté' if ffmpeg_ok else '✗ introuvable (encodage indisponible)'}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#16a34a", "#22c55e") if ffmpeg_ok else ("#b91c1c", "#ef4444"),
        )
        self._footer_ffmpeg_label.pack(side="right", padx=10)

        # Câbler le sélecteur CPU pour mettre à jour le footer en live
        # (configure(command=) accepte un callback appelé à chaque sélection).
        try:
            self.cpu_threads.configure(command=self._refresh_footer_cpu)
        except Exception:
            pass
        # Initialisation
        self._refresh_footer_cpu()

    def _probe_ffmpeg_available(self) -> bool:
        """Vérification ponctuelle de la présence de FFmpeg pour le footer.

        Utilise VideoEncoder.check_ffmpeg (qui mémoïze la réponse), donc
        cet appel coûte au plus un subprocess.run('ffmpeg -version') une
        fois par démarrage de l'app.
        """
        try:
            from ..core.video_encoder import VideoEncoder
            return VideoEncoder(logger=None).check_ffmpeg()
        except Exception:
            return False

    def _refresh_footer_cpu(self, _value=None):
        """Met à jour le label CPU du footer (appelé sur changement du dropdown)."""
        if not hasattr(self, "_footer_cpu_label"):
            return
        cpu_count = max(1, os.cpu_count() or 4)
        value = self.cpu_threads.get()
        if value == "Auto":
            resolved = f"Auto (système, max {cpu_count})"
        elif value.startswith("Max"):
            resolved = f"tous les {cpu_count} cœurs (max puissance)"
        else:
            try:
                n = int(value)
                resolved = f"{n} cœur{'s' if n > 1 else ''} max"
            except ValueError:
                resolved = value
        self._footer_cpu_label.configure(
            text=f"CPU : {cpu_count} cœurs détectés · sélection : {resolved}"
        )

    def _setup_workflow(self):
        """Configure le workflow avec les étapes"""
        self.workflow = WorkflowManager(logger=self.logger, config_manager=self.config_manager)

        # Ajouter les étapes
        steps = [ImportStep.create_step(), AlignStep.create_step(), MorphStep.create_step(), ExportStep.create_step()]

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
            self.steps_container, step.name, step.description, enabled=step.enabled, on_toggle=self._on_step_toggle
        )
        indicator.pack(fill="x", pady=2)
        self._step_indicators[step.id] = indicator

    def _setup_logger_callback(self):
        """Configure le callback pour afficher les logs dans l'UI"""

        def log_callback(entry: LogEntry):
            self.after(0, lambda: self.log_viewer.log(entry.message, entry.level.name))

        self.logger.add_callback(log_callback)

    def _update_progress_label(self, fraction: float, status_text: str | None = None):
        """Met à jour la barre de progression globale + le label de pourcentage.

        fraction : valeur entre 0.0 et 1.0
        status_text : texte du label de gauche (laissé inchangé si None)
        """
        fraction = max(0.0, min(1.0, fraction))
        self.global_progress_bar.set(fraction)
        self.global_progress_percent.configure(text=f"{int(fraction * 100)} %")
        if status_text is not None:
            self.global_progress_label.configure(text=status_text)

    def _update_run_button_state(self, *_args):
        """Active/désactive le bouton Lancer selon la cohérence de l'état UI."""
        # Pendant un run, le bouton reste désactivé (géré dans _run_workflow / _on_workflow_complete)
        if self._workflow_starting or (self.workflow is not None and self.workflow.is_running):
            return
        has_input = bool(self.input_dir.get().strip())
        self.run_button.configure(state="normal" if has_input else "disabled")

    def _on_input_dir_changed(self, *_args):
        """Trace callback sur input_dir : bouton + stats + previews + bloc chemins."""
        self._update_run_button_state()
        self._update_previews()
        self._refresh_stats()
        self._refresh_path_displays()

    def _on_reference_changed(self, *_args):
        """Trace callback sur reference_image : stats + bloc chemins."""
        self._refresh_stats()
        self._refresh_path_displays()

    def _on_output_dir_changed(self, *_args):
        """Trace callback sur output_dir : stats + bloc chemins."""
        self._refresh_stats()
        self._refresh_path_displays()

    def _on_intermediate_changed(self, *_args):
        """Trace callback sur intermediate_frames_dir : juste le bloc chemins."""
        self._refresh_path_displays()

    def _refresh_path_displays(self):
        """Met à jour le bloc « Chemins sélectionnés » sous les sélecteurs.

        Affiche le chemin COMPLET en wrap multi-ligne. Quand un chemin est
        vide, affiche un placeholder explicatif (« auto », « par défaut »…)
        pour que l'utilisateur sache ce qui sera utilisé à la place.
        """
        src = self.input_dir.get().strip()
        self._path_display_source.configure(
            text=f"📁 {src}" if src else "📁 (aucun dossier source sélectionné)"
        )
        ref = self.reference_image.get().strip()
        self._path_display_ref.configure(
            text=f"🖼️ {ref}" if ref else "🖼️ (auto — 1re image utilisée)"
        )
        out = self.output_dir.get().strip()
        self._path_display_output.configure(
            text=f"📂 {out}" if out else "📂 (sortie dans runs/<timestamp>/)"
        )
        inter = self.intermediate_frames_dir.get().strip()
        self._path_display_frames.configure(
            text=f"🎞️ {inter}" if inter else "🎞️ (frames dans runs/<ts>/03_morph/frames/)"
        )

    def _apply_cpu_setting(self) -> int:
        """Configure le nombre de threads OpenCV + BLAS + FFmpeg avant un run.

        Le pipeline délègue le gros du calcul à OpenCV (warpAffine, resize,
        blend, encode JPEG), NumPy/SciPy (BLAS/LAPACK), et FFmpeg (encodage
        H.264). Trois leviers à piloter de façon cohérente :
          - cv2.setNumThreads(n)              → boucles de morphing
          - OMP_/OPENBLAS_/MKL_NUM_THREADS    → numpy / scipy
          - -threads N côté FFmpeg            → encodage x264 (le plus lourd)

        Cette méthode applique les deux premiers immédiatement et retourne
        la valeur N à passer ensuite à FFmpeg via context.config.
        Retourne `n` (0 = auto/illimité, >0 = nombre fixe).
        """
        import cv2

        value = self.cpu_threads.get()
        max_cores = os.cpu_count() or 4
        if value == "Auto":
            # 0 dans OpenCV = « tous les cœurs disponibles » (comportement
            # par défaut). On laisse aussi les BLAS choisir librement.
            n = 0
        elif value.startswith("Max"):
            n = max_cores
        else:
            try:
                n = int(value)
            except ValueError:
                n = 0
            n = max(1, min(n, max_cores))

        try:
            cv2.setNumThreads(n)
        except Exception as e:
            self.logger.warning(f"cv2.setNumThreads({n}) a échoué : {e}")

        # Limiter les BLAS uniquement quand l'utilisateur a choisi une valeur
        # explicite ; en mode Auto on ne touche pas à l'env (pour respecter
        # une éventuelle configuration système).
        if n > 0:
            for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
                os.environ[var] = str(n)

        self.logger.info(
            f"CPU threads : {value} (cv2={n if n > 0 else 'all'}, ffmpeg -threads={n})"
        )
        return n

    def _setup_shortcuts(self):
        """Configure les raccourcis clavier globaux.

        Ctrl+1..5 → toggle des 5 premières sections de l'OptionsPanel
        Escape    → annule le workflow si un run est en cours
        F1        → affiche la liste des raccourcis
        """
        section_keys = OptionsPanel.SECTION_KEYS  # ("video","morphing","alignment","detection","workflow", ...)

        # Alias émis par le pavé numérique quand Num Lock est OFF : sur
        # Windows, KP_1 devient KP_End, KP_2 → KP_Down, etc. Sans ces
        # bindings supplémentaires, Ctrl+1..5 depuis le pavé numérique
        # serait silencieusement ignoré (cf. DA-2 audit).
        numpad_off_aliases = ("KP_End", "KP_Down", "KP_Next", "KP_Left", "KP_Begin")

        # Alias AZERTY (clavier français) : la rangée du haut produit, SANS
        # Shift, les caractères & é " ' ( au lieu de 1 2 3 4 5. Sans ces
        # bindings, Ctrl+1..5 ne déclenche rien sur clavier français — c'est
        # exactement le NOK rapporté sur V-012..V-018.
        azerty_aliases = ("ampersand", "eacute", "quotedbl", "apostrophe", "parenleft")

        for idx in range(5):
            key = section_keys[idx]
            # QWERTY (rangée du haut, layout US/UK/DE/etc.)
            self.bind_all(f"<Control-Key-{idx + 1}>", lambda _e, k=key: self._on_section_shortcut(k))
            # AZERTY (rangée du haut sans Shift, layout FR/BE)
            self.bind_all(
                f"<Control-Key-{azerty_aliases[idx]}>",
                lambda _e, k=key: self._on_section_shortcut(k),
            )
            # Pavé numérique avec Num Lock ON
            self.bind_all(f"<Control-KP_{idx + 1}>", lambda _e, k=key: self._on_section_shortcut(k))
            # Pavé numérique avec Num Lock OFF
            self.bind_all(
                f"<Control-{numpad_off_aliases[idx]}>",
                lambda _e, k=key: self._on_section_shortcut(k),
            )

        self.bind_all("<Escape>", self._on_escape_pressed)
        self.bind_all("<F1>", self._on_help_shortcut)

    def _on_section_shortcut(self, section_key: str):
        """Bascule une section de l'OptionsPanel. Ignore si focus dans un champ texte.

        focus_get() retourne le widget tkinter interne (tk.Entry / tk.Text)
        et non l'enveloppe CTk (CTkEntry / CTkTextbox), donc le test
        isinstance() précédent ne matchait jamais. On filtre via winfo_class()
        qui couvre uniformément les deux familles (cf. DA-1 audit).
        """
        focused = self.focus_get()
        if focused is not None:
            try:
                widget_class = focused.winfo_class()
            except Exception:
                widget_class = ""
            if widget_class in {"Entry", "Text", "TEntry", "Spinbox"}:
                return
        if self.options_panel.toggle_section(section_key):
            self.logger.debug(f"Section togglée via raccourci: {section_key}")

    def _on_escape_pressed(self, _event=None):
        """Demande l'annulation du workflow si un run est en cours."""
        if self.workflow is not None and self.workflow.is_running:
            self._stop_workflow()

    def _on_help_shortcut(self, _event=None):
        """Affiche un mémo des raccourcis clavier."""
        messagebox.showinfo(
            "Raccourcis clavier",
            "Ctrl+1 — Section Vidéo\n"
            "Ctrl+2 — Section Morphing\n"
            "Ctrl+3 — Section Alignement\n"
            "Ctrl+4 — Section Détection\n"
            "Ctrl+5 — Section Workflow\n"
            "Échap   — Annuler le traitement en cours\n"
            "F1      — Afficher cette aide",
        )

    def _load_last_settings(self):
        """Charge les derniers paramètres utilisés - avec nouvelles options"""
        self.input_dir.set(self.config_manager.get("paths.last_input_dir", ""))
        self.output_dir.set(self.config_manager.get("paths.last_output_dir", ""))
        self.reference_image.set(self.config_manager.get("paths.last_reference_image", ""))
        self.intermediate_frames_dir.set(self.config_manager.get("paths.intermediate_frames_dir", ""))

        # Réglage CPU : restauré tel quel s'il fait partie des valeurs
        # actuellement proposées par le dropdown (le libellé "Max (N)" dépend
        # du nombre de cœurs détectés, qui peut varier d'un PC à l'autre).
        saved_cpu = self.config_manager.get("workflow.cpu_threads", "Auto")
        valid_values = list(self.cpu_threads.cget("values"))
        self.cpu_threads.set(saved_cpu if saved_cpu in valid_values else "Auto")

        # Rafraîchir l'affichage des stats + aperçus avec les valeurs restaurées
        self._update_previews()
        self._refresh_stats()

        # Only options exposed in the UI are loaded here. Removed inert keys
        # in commit 9 (auto_crop, stabilize, detection_threshold, multi_face,
        # parallel_processing, num_threads, auto_backup, export_frames,
        # export_landmarks, output_format) — see CHANGELOG.md (2.0.0 audit).
        options = {
            # Video
            "fps": self.config_manager.get("morphing.fps", 25),
            "video_quality": self.config_manager.get("video.quality", "high"),
            "resolution": self.config_manager.get("video.resolution", "original"),
            # Morphing
            "transition_duration": self.config_manager.get("morphing.transition_duration", 3.0),
            "pause_duration": self.config_manager.get("morphing.pause_duration", 0.0),
            "easing": self.config_manager.get("morphing.easing", "linear"),
            "blend_mode": self.config_manager.get("morphing.blend_mode", "alpha"),
            # Alignment
            "border_size": self.config_manager.get("alignment.border_size", 0),
            "overlay_mode": self.config_manager.get("alignment.overlay_mode", False),
            # Detection
            "retry_detection": self.config_manager.get("detection.retry", 3),
            # Workflow
            "continue_on_error": self.config_manager.get("workflow.continue_on_error", False),
            "debug_mode": self.config_manager.get("workflow.debug_mode", False),
            # Export
            "create_gif": self.config_manager.get("export.gif", False),
            "thumbnail": self.config_manager.get("export.thumbnail", True),
        }
        self.options_panel.set_options(options)

        # Appliquer immédiatement debug_mode au logger : sinon les logs DEBUG
        # restent invisibles au boot tant que l'utilisateur n'a pas re-sauvé
        # les paramètres (cf. DA-7 audit).
        self.logger.set_level(LogLevel.DEBUG if bool(options.get("debug_mode", False)) else LogLevel.INFO)

    def _save_settings(self):
        """Sauvegarde les paramètres exposés dans l'UI."""
        # Sauvegarder les chemins
        self.config_manager.set("paths.last_input_dir", self.input_dir.get(), auto_save=False)
        self.config_manager.set("paths.last_output_dir", self.output_dir.get(), auto_save=False)
        self.config_manager.set("paths.last_reference_image", self.reference_image.get(), auto_save=False)
        self.config_manager.set("paths.intermediate_frames_dir", self.intermediate_frames_dir.get(), auto_save=False)

        # Sauvegarder les options exposées
        options = self.options_panel.get_options()

        # Video
        self.config_manager.set("morphing.fps", int(options.get("fps", 25)), auto_save=False)
        self.config_manager.set("video.quality", options.get("video_quality", "high"), auto_save=False)
        self.config_manager.set("video.resolution", options.get("resolution", "original"), auto_save=False)

        # Morphing
        self.config_manager.set(
            "morphing.transition_duration", options.get("transition_duration", 3.0), auto_save=False
        )
        self.config_manager.set("morphing.pause_duration", options.get("pause_duration", 0.0), auto_save=False)
        self.config_manager.set("morphing.easing", options.get("easing", "linear"), auto_save=False)
        self.config_manager.set("morphing.blend_mode", options.get("blend_mode", "alpha"), auto_save=False)

        # Alignment
        self.config_manager.set("alignment.border_size", int(options.get("border_size", 0)), auto_save=False)
        self.config_manager.set("alignment.overlay_mode", options.get("overlay_mode", False), auto_save=False)

        # Detection
        self.config_manager.set("detection.retry", int(options.get("retry_detection", 3)), auto_save=False)

        # Workflow
        debug_mode = bool(options.get("debug_mode", False))
        self.config_manager.set("workflow.continue_on_error", options.get("continue_on_error", False), auto_save=False)
        self.config_manager.set("workflow.debug_mode", debug_mode, auto_save=False)
        self.config_manager.set("workflow.cpu_threads", self.cpu_threads.get(), auto_save=False)

        # Export
        self.config_manager.set("export.gif", options.get("create_gif", False), auto_save=False)
        self.config_manager.set("export.thumbnail", options.get("thumbnail", True), auto_save=False)

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
            self._refresh_stats()
            self.logger.info(f"Dossier source: {path}")

    def _select_reference(self):
        """Sélectionne l'image de référence"""
        path = filedialog.askopenfilename(
            title="Sélectionner l'image de référence",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
        )
        if path:
            self.reference_image.set(path)
            self._refresh_stats()
            self.logger.info(f"Image de référence: {path}")

    def _select_output_dir(self):
        """Sélectionne le dossier de sortie"""
        path = filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if path:
            self.output_dir.set(path)
            self._refresh_stats()
            self.logger.info(f"Dossier de sortie: {path}")

    def _select_intermediate_frames_dir(self):
        """Sélectionne le dossier où sauvegarder les frames JPEG intermédiaires.

        Optionnel : si vide, les frames vont dans le run par défaut.
        Si rempli, un sous-dossier horodaté est créé dans ce chemin à
        chaque run, contenant les frames + un viewer HTML.
        """
        path = filedialog.askdirectory(
            title="Sélectionner le dossier des frames intermédiaires (optionnel)"
        )
        if path:
            self.intermediate_frames_dir.set(path)
            self.logger.info(f"Dossier frames intermédiaires : {path}")

    def _count_images(self) -> int:
        """Compte les images dans le dossier source courant (0 si dossier invalide)."""
        from ..utils.file_utils import FileUtils

        input_dir = self.input_dir.get()
        if not input_dir or not os.path.isdir(input_dir):
            return 0
        return len(FileUtils.get_image_files(input_dir))

    def _refresh_stats(self):
        """Met à jour le label de stats à partir des trois variables (input/réf/sortie).

        Toujours visible, même si l'utilisateur n'a pas encore choisi le dossier
        source. Utilisé après chaque sélection et au chargement des préférences.
        """
        count = self._count_images()
        ref_path = self.reference_image.get()
        if ref_path:
            ref_name = os.path.basename(ref_path)
            ref = ref_name[:15] + "…" if len(ref_name) > 16 else ref_name
        else:
            ref = "Auto"
        output = "✓" if self.output_dir.get() else "-"
        self.stats_label.configure(text=f"{count} images | Réf: {ref} | Sortie: {output}")

    def _update_previews(self):
        """Met à jour les aperçus d'images (première/dernière du dossier source).

        Le chargement effectif (PIL.Image.thumbnail) est délégué à un thread
        daemon pour éviter de figer le main loop sur des gros dossiers
        (cf. DA-RES-5 du pré-rapport Phase 2). Les `set_image()` sont
        replanifiés dans le main loop via `after(0, ...)`.
        """
        from ..utils.file_utils import FileUtils

        input_dir = self.input_dir.get()
        if not (input_dir and os.path.isdir(input_dir)):
            return

        def _worker():
            images = FileUtils.get_image_files(input_dir)
            if not images:
                return
            first, last = images[0], images[-1]
            self.after(0, lambda: self.preview_first.set_image(first))
            self.after(0, lambda: self.preview_last.set_image(last))

        threading.Thread(target=_worker, daemon=True).start()

    def _update_previews_sync(self):
        """Version synchrone (legacy) conservée pour compatibilité future."""
        from ..utils.file_utils import FileUtils

        input_dir = self.input_dir.get()
        if input_dir and os.path.isdir(input_dir):
            images = FileUtils.get_image_files(input_dir)
            if images:
                self.preview_first.set_image(images[0])
                self.preview_last.set_image(images[-1])

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
        if self.workflow is None:
            return
        for step in self.workflow.steps:
            if step.name == step_name:
                self.workflow.enable_step(step.id, enabled)
                break

    def _run_workflow(self):
        """Lance le workflow"""
        # Garde anti-double exécution (souris + raccourci clavier)
        if self._workflow_starting:
            return
        if self.workflow is not None and self.workflow.is_running:
            return

        # Validation : dossier source
        input_dir = self.input_dir.get()
        if not input_dir:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source")
            return
        if not os.path.isdir(input_dir):
            messagebox.showerror("Erreur", f"Le dossier source est introuvable :\n{input_dir}")
            return

        # Validation : présence d'images dans le dossier source
        if self._count_images() == 0:
            messagebox.showerror(
                "Erreur",
                "Aucune image trouvée dans le dossier source.\n\n"
                f"Dossier exploré :\n{input_dir}\n\n"
                "Formats supportés : .jpg, .jpeg, .png, .bmp, .tiff, .webp",
            )
            return

        # Validation : modèle dlib disponible.
        # On cherche dans cet ordre : (1) chemin custom de la config, (2) bundle
        # PyInstaller via paths.get_dlib_model_path() (gère sys._MEIPASS pour
        # les EXE frozen onedir/onefile), (3) racine projet, (4) assets/.
        configured = self.config_manager.get("paths.model_path", "")
        bundled = str(get_dlib_model_path())
        candidate_paths = [
            configured,
            bundled,
            "./shape_predictor_68_face_landmarks.dat",
            "assets/shape_predictor_68_face_landmarks.dat",
        ]
        resolved_model = next((p for p in candidate_paths if p and os.path.exists(p)), None)
        if resolved_model is None:
            messagebox.showerror(
                "Erreur",
                "Modèle de détection faciale introuvable.\n\n"
                "Téléchargez `shape_predictor_68_face_landmarks.dat` et placez-le\n"
                "à la racine du projet ou dans `assets/`.\n\n"
                f"Chemins testés :\n• {configured or '(non configuré)'}\n• {bundled}\n"
                "• ./shape_predictor_68_face_landmarks.dat\n"
                "• assets/shape_predictor_68_face_landmarks.dat",
            )
            return
        # Stocker le chemin résolu pour le passer au contexte du workflow
        self._resolved_model_path = resolved_model

        # Verrouiller immédiatement pour éviter double-clic
        self._workflow_starting = True
        self.run_button.configure(state="disabled")

        # Récapitulatif des chemins effectivement utilisés pour ce run.
        # Permet au testeur de tracer dans les logs exactement quelles
        # entrées/sorties le workflow voit (utile en cas d'anomalie).
        ref_display = self.reference_image.get() or "(auto — 1re image)"
        out_display = self.output_dir.get() or "(non défini — exports dans runs/<timestamp>/)"
        self.logger.info("=== Chemins du run ===")
        self.logger.info(f"  📁 Dossier source     : {input_dir}")
        self.logger.info(f"  🖼️  Image de référence : {ref_display}")
        self.logger.info(f"  📂 Dossier de sortie  : {out_display}")
        self.logger.info(f"  🧠 Modèle dlib         : {self._resolved_model_path}")
        self.logger.info(f"  ⚙️  CPU                : {self.cpu_threads.get()}")

        # Appliquer le réglage CPU AVANT toute init du pipeline : ainsi le
        # FaceDetector et FaceMorpher hériteront du bon pool de threads dès
        # leur première opération. La valeur résolue est aussi passée à
        # FFmpeg via context.config["ffmpeg_threads"] pour piloter l'encodage.
        ffmpeg_threads = self._apply_cpu_setting()

        # Configurer le contexte avec toutes les options
        options = self.options_panel.get_options()

        self.workflow.set_context(
            input_dir=self.input_dir.get(),
            reference_image=self.reference_image.get(),
            output_dir=self.output_dir.get(),
            config={
                # Paths : chemin du modèle dlib résolu par la validation
                # ci-dessus (gère bundle PyInstaller, racine projet, etc.).
                "model_path": self._resolved_model_path,
                # Video
                "fps": int(options.get("fps", 25)),
                "video_quality": options.get("video_quality", "high"),
                "resolution": options.get("resolution", "original"),
                # Morphing
                "transition_duration": options.get("transition_duration", 3.0),
                "pause_duration": options.get("pause_duration", 0.0),
                "easing": options.get("easing", "linear"),
                "blend_mode": options.get("blend_mode", "alpha"),
                # Alignment
                "border_size": int(options.get("border_size", 0)),
                "overlay_mode": options.get("overlay_mode", False),
                # Detection
                "retry_detection": int(options.get("retry_detection", 3)),
                # Workflow
                "debug_mode": bool(options.get("debug_mode", False)),
                # Export
                "create_gif": options.get("create_gif", False),
                "thumbnail": options.get("thumbnail", True),
                # Dossier frames intermédiaire (vide = défaut). Passé au
                # step_morph qui le transmettra au VideoEncoder.
                "intermediate_frames_dir": self.intermediate_frames_dir.get().strip(),
                # Nombre de threads FFmpeg : routé vers `-threads N` côté
                # x264. 0 = libx264 auto, N > 0 = limite stricte.
                "ffmpeg_threads": ffmpeg_threads,
            },
        )

        # UI
        self.stop_button.configure(state="normal")
        self.global_progress_bar.set(0)
        self._update_progress_label(0.0, "En attente...")

        # Reset des indicateurs
        for indicator in self._step_indicators.values():
            indicator.set_status("pending")
            indicator.set_progress(0)

        # Lancer dans un thread
        continue_on_error = options.get("continue_on_error", False)

        def run_thread():
            try:
                self.workflow.run(continue_on_error=continue_on_error)
            finally:
                # Le flag est levé même si workflow.run() lève une exception
                self._workflow_starting = False

        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()

    def _stop_workflow(self):
        """Arrête le workflow et donne un feedback visuel immédiat.

        L'annulation est coopérative : selon l'étape, la frame en cours peut
        prendre 0.1–1 s à se libérer. On désactive donc Annuler tout de suite
        (anti double-clic) et on bascule le label en « Annulation en cours… »
        pour éviter que l'utilisateur croie la commande ignorée (cf. DA-3).
        """
        if self.workflow:
            self.workflow.stop()
            self.logger.warning("Arrêt du workflow demandé...")
            self.stop_button.configure(state="disabled")
            self.global_progress_label.configure(text="Annulation en cours...")

    def _on_step_start(self, step: WorkflowStep):
        """Callback au démarrage d'une étape"""

        def update():
            if step.id in self._step_indicators:
                self._step_indicators[step.id].set_status("running")
            self.global_progress_label.configure(text=f"En cours: {step.name}")

        self.after(0, update)

    def _on_step_complete(self, step: WorkflowStep):
        """Callback à la fin d'une étape (succès OU annulation propre).

        Le statut CANCELLED est routé ici et non vers _on_step_error car
        l'annulation n'est pas une erreur applicative.
        """

        def update():
            if step.id not in self._step_indicators:
                return
            status = "cancelled" if step.status == StepStatus.CANCELLED else "completed"
            self._step_indicators[step.id].set_status(status)
            if status == "completed":
                self._step_indicators[step.id].set_progress(100)

        self.after(0, update)

    def _on_step_error(self, step: WorkflowStep, error: Exception):
        """Callback en cas d'erreur"""

        def update():
            if step.id in self._step_indicators:
                self._step_indicators[step.id].set_status("error")

        self.after(0, update)

    def _on_progress(self, step: WorkflowStep, progress: float, message: str):
        """Callback de progression — basé sur les étapes ACTIVÉES uniquement."""

        def update():
            if step.id in self._step_indicators:
                self._step_indicators[step.id].set_progress(progress)

            # Calculer la progression globale en filtrant les étapes désactivées
            enabled_steps = [s for s in self.workflow.steps if s.enabled]
            total = len(enabled_steps) or 1
            try:
                current_index = next(i for i, s in enumerate(enabled_steps) if s.id == step.id)
            except StopIteration:
                current_index = 0
            global_progress = (current_index + progress / 100.0) / total
            self._update_progress_label(global_progress)

        self.after(0, update)

    def _on_workflow_complete(self, success: bool, context):
        """Callback à la fin du workflow (succès, échec ou annulation)."""

        def update():
            self.stop_button.configure(state="disabled")
            # Réactiver le bouton Lancer selon l'état courant des champs
            self._update_run_button_state()

            # Détecter une annulation : au moins une étape avec statut CANCELLED
            cancelled = any(s.status == StepStatus.CANCELLED for s in self.workflow.steps)

            if cancelled:
                self._update_progress_label(0.0, "Workflow annulé")
                messagebox.showinfo("Annulé", "Le traitement a été annulé.")
            elif success:
                self._update_progress_label(1.0, "Workflow terminé avec succès")
                messagebox.showinfo("Succès", f"Workflow terminé!\n\nRésultats dans:\n{context.run_dir}")
            else:
                self._update_progress_label(self.global_progress_bar.get(), "Workflow terminé avec des erreurs")

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
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erreur", f"Échec du démarrage: {e}")
        root.destroy()
