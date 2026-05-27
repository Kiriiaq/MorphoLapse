"""
Widgets - Composants UI personnalises avec options avancees
"""

import logging
import os
from collections.abc import Callable

import customtkinter as ctk
from PIL import Image, ImageTk

_log = logging.getLogger(__name__)


class CollapsibleSection(ctk.CTkFrame):
    """Section repliable avec indicateur visuel"""

    def __init__(self, master, title: str, icon: str = "", expanded: bool = True, highlight: bool = False, **kwargs):
        super().__init__(master, **kwargs)

        self.title = title
        self.icon = icon
        self._expanded = expanded
        self._highlight = highlight

        self.configure(fg_color="transparent")
        self._setup_ui()

    def _setup_ui(self):
        # Header cliquable
        header_color = ("#1f6aa5", "#1f6aa5") if self._highlight else ("gray25", "gray25")

        self.header = ctk.CTkFrame(self, fg_color=header_color, corner_radius=6, height=28)
        self.header.pack(fill="x", pady=(0, 2))
        self.header.pack_propagate(False)

        # Icone expand/collapse
        self.expand_label = ctk.CTkLabel(
            self.header, text="▼" if self._expanded else "▶", font=ctk.CTkFont(size=10), width=16
        )
        self.expand_label.pack(side="left", padx=(8, 2))

        # Titre avec icone
        title_text = f"{self.icon} {self.title}" if self.icon else self.title
        self.title_label = ctk.CTkLabel(
            self.header, text=title_text, font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        # Badge NEW si highlight
        if self._highlight:
            badge = ctk.CTkLabel(
                self.header,
                text="NEW",
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color="#e74c3c",
                corner_radius=4,
                width=32,
                height=16,
            )
            badge.pack(side="right", padx=8)

        # Contenu
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        if self._expanded:
            self.content.pack(fill="x", padx=4, pady=(0, 5))

        # Bind click
        self.header.bind("<Button-1>", self._toggle)
        self.expand_label.bind("<Button-1>", self._toggle)
        self.title_label.bind("<Button-1>", self._toggle)

    def _toggle(self, event=None):
        self._expanded = not self._expanded
        self.expand_label.configure(text="▼" if self._expanded else "▶")

        if self._expanded:
            self.content.pack(fill="x", padx=4, pady=(0, 5))
        else:
            self.content.pack_forget()

    def toggle(self):
        """Bascule l'état déplié/replié. Exposé pour les raccourcis clavier."""
        self._toggle()

    @property
    def expanded(self) -> bool:
        return self._expanded

    def get_content_frame(self) -> ctk.CTkFrame:
        return self.content


class StepIndicator(ctk.CTkFrame):
    """Indicateur d'etat compact d'une etape du workflow"""

    ICONS = {
        "pending": "○",
        "running": "◉",
        "completed": "✓",
        "error": "✗",
        "skipped": "⊘",
        "disabled": "⊗",
        "cancelled": "⏹",
    }

    COLORS = {
        "pending": ("#6b7280", "#6b7280"),
        "running": ("#3b82f6", "#3b82f6"),
        "completed": ("#22c55e", "#22c55e"),
        "error": ("#ef4444", "#ef4444"),
        "skipped": ("#9ca3af", "#9ca3af"),
        "disabled": ("#4b5563", "#4b5563"),
        "cancelled": ("#f59e0b", "#f59e0b"),
    }

    def __init__(
        self, master, step_name: str, step_description: str, enabled: bool = True, on_toggle: Callable = None, **kwargs
    ):
        super().__init__(master, **kwargs)

        self.step_name = step_name
        self.step_description = step_description
        self._status = "pending"
        self._enabled = enabled
        self._on_toggle = on_toggle
        self._progress = 0

        self._setup_ui()

    def _setup_ui(self):
        self.configure(fg_color="transparent")

        # Frame principale compacte
        self.main_frame = ctk.CTkFrame(self, corner_radius=6, height=36)
        self.main_frame.pack(fill="x", pady=1)
        self.main_frame.pack_propagate(False)

        # Checkbox compact
        self.checkbox = ctk.CTkCheckBox(
            self.main_frame, text="", width=20, height=20, checkbox_width=16, checkbox_height=16, command=self._toggle
        )
        self.checkbox.pack(side="left", padx=(6, 4))
        if self._enabled:
            self.checkbox.select()

        # Icone de statut
        self.icon_label = ctk.CTkLabel(
            self.main_frame,
            text=self.ICONS["pending"],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS["pending"],
            width=20,
        )
        self.icon_label.pack(side="left", padx=2)

        # Nom de l'etape
        self.name_label = ctk.CTkLabel(self.main_frame, text=self.step_name, font=ctk.CTkFont(size=11), anchor="w")
        self.name_label.pack(side="left", fill="x", expand=True, padx=4)

        # Barre de progression compacte
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, width=60, height=6)
        self.progress_bar.pack(side="right", padx=6)
        self.progress_bar.set(0)


    def _toggle(self):
        self._enabled = self.checkbox.get()
        self.set_status("pending" if self._enabled else "disabled")
        if self._on_toggle:
            self._on_toggle(self.step_name, self._enabled)

    def set_status(self, status: str):
        self._status = status
        self.icon_label.configure(
            text=self.ICONS.get(status, "?"), text_color=self.COLORS.get(status, self.COLORS["pending"])
        )
        border = 2 if status == "running" else 0
        self.main_frame.configure(border_width=border, border_color=self.COLORS.get(status))

    def set_progress(self, progress: float):
        self._progress = progress / 100.0
        self.progress_bar.set(self._progress)

    @property
    def enabled(self) -> bool:
        return self._enabled


class LogViewer(ctk.CTkFrame):
    """Visualiseur de logs avec filtre niveau et export TXT/CSV.

    Maintient un historique interne de TOUS les logs reçus (indépendant du
    filtre d'affichage), ce qui permet :
      - de changer le filtre niveau à n'importe quel moment et de
        ré-afficher l'historique filtré sans perdre les anciens logs ;
      - d'exporter en TXT ou en CSV (utile pour trier dans Excel par
        sévérité ou par horodatage).
    """

    LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

    def __init__(self, master, max_lines: int = 2000, **kwargs):
        super().__init__(master, **kwargs)
        self.max_lines = max_lines
        # Historique complet (level, timestamp, message) — indépendant du filtre.
        self._history: list[tuple[str, str, str]] = []
        self._setup_ui()

    def _setup_ui(self):
        # Toolbar compacte
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=28)
        toolbar.pack(fill="x", padx=4, pady=2)
        toolbar.pack_propagate(False)

        ctk.CTkLabel(toolbar, text="Logs", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=4)

        # Compteur live des logs reçus, séparé du filtre
        self.count_label = ctk.CTkLabel(
            toolbar, text="(0)", font=ctk.CTkFont(size=10),
            text_color=("gray45", "gray60"),
        )
        self.count_label.pack(side="left", padx=(2, 8))

        ctk.CTkButton(
            toolbar, text="Effacer", width=55, height=22, font=ctk.CTkFont(size=10), command=self.clear
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            toolbar, text="Export…", width=65, height=22, font=ctk.CTkFont(size=10), command=self._export_logs
        ).pack(side="right", padx=2)

        self.level_var = ctk.StringVar(value="INFO")
        ctk.CTkOptionMenu(
            toolbar,
            values=list(self.LEVELS),
            variable=self.level_var,
            command=self._on_filter_change,
            width=80,
            height=22,
            font=ctk.CTkFont(size=10),
        ).pack(side="right", padx=4)

        # Zone de texte avec scrollbar integree
        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=10), wrap="word", state="disabled")
        self.textbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Tags de couleur (re-créés à chaque rebuild si nécessaire)
        self._configure_tags()

    def _configure_tags(self):
        self.textbox._textbox.tag_configure("DEBUG", foreground="#9ca3af")
        self.textbox._textbox.tag_configure("INFO", foreground="#e5e7eb")
        self.textbox._textbox.tag_configure("WARNING", foreground="#f59e0b")
        self.textbox._textbox.tag_configure("ERROR", foreground="#ef4444")
        self.textbox._textbox.tag_configure("SUCCESS", foreground="#22c55e")

    def _level_passes(self, level: str) -> bool:
        """True si le log doit être affiché compte tenu du filtre courant."""
        current = self.level_var.get()
        if level not in self.LEVELS or current not in self.LEVELS:
            return True
        return self.LEVELS.index(level) >= self.LEVELS.index(current)

    def log(self, message: str, level: str = "INFO"):
        """Ajoute un log à l'historique ET affiche s'il passe le filtre."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._history.append((level, timestamp, message))
        # Limiter la taille de l'historique (FIFO)
        if len(self._history) > self.max_lines * 4:
            self._history = self._history[-self.max_lines * 4 :]

        self.count_label.configure(text=f"({len(self._history)})")

        if not self._level_passes(level):
            return

        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"[{timestamp}] {message}\n", level)
        # Cap le nombre de lignes affichées (pas l'historique)
        line_count = int(self.textbox.index("end-1c").split(".")[0])
        if line_count > self.max_lines:
            self.textbox.delete("1.0", "2.0")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def _on_filter_change(self, _value=None):
        """Rebuild le textbox à partir de l'historique filtré.

        Permet de passer en cours de session de INFO → WARNING ou ERROR
        pour ne voir que ce qui est important, puis revenir à INFO pour
        retrouver tout le contexte sans perdre l'historique.
        """
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        for level, ts, msg in self._history:
            if self._level_passes(level):
                self.textbox.insert("end", f"[{ts}] {msg}\n", level)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        """Vide à la fois l'affichage ET l'historique interne."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        self._history.clear()
        self.count_label.configure(text="(0)")

    def _export_logs(self):
        """Export TXT ou CSV (déterminé par l'extension choisie par l'utilisateur).

        Le format CSV permet d'ouvrir dans Excel/LibreOffice pour trier et
        filtrer par niveau, par mot-clé, par heure — utile pour le triage
        d'anomalies. Le TXT reste pratique pour un copier-coller direct.
        """
        from tkinter import filedialog, messagebox

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV (triable Excel)", "*.csv"),
                ("Texte brut", "*.txt"),
                ("Tous fichiers", "*.*"),
            ],
            initialfile="morpholapse_logs.csv",
        )
        if not filepath:
            return

        try:
            ext = filepath.lower().rsplit(".", 1)[-1] if "." in filepath else "txt"
            if ext == "csv":
                self._export_csv(filepath)
            else:
                self._export_txt(filepath)
            messagebox.showinfo(
                "Export terminé",
                f"{len(self._history)} entrées exportées dans :\n{filepath}",
            )
        except OSError as e:
            _log.warning("LogViewer export failed: %s -> %s", filepath, e)
            messagebox.showerror(
                "Export impossible",
                f"Impossible d'écrire dans :\n{filepath}\n\nErreur : {e.strerror or e}",
            )

    def _export_txt(self, filepath: str):
        """Export texte brut — ne contient que ce qui est affiché (filtré)."""
        with open(filepath, "w", encoding="utf-8") as f:
            for level, ts, msg in self._history:
                if self._level_passes(level):
                    f.write(f"[{ts}] [{level}] {msg}\n")

    def _export_csv(self, filepath: str):
        """Export CSV — TOUT l'historique avec colonnes triables (niveau, time, message)."""
        import csv
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["Niveau", "Heure", "Message"])
            for level, ts, msg in self._history:
                writer.writerow([level, ts, msg])


class OptionsPanel(ctk.CTkScrollableFrame):
    """Panneau d'options avancees avec sections repliables et nouvelles options"""

    # Clés des sections accessibles via raccourcis Ctrl+1..5 (cf. main_window._setup_shortcuts)
    SECTION_KEYS = ("video", "morphing", "alignment", "detection", "workflow", "export")

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._options = {}
        self._sections: dict[str, CollapsibleSection] = {}
        self._setup_ui()

    def toggle_section(self, key: str) -> bool:
        """Bascule l'état d'une section par sa clé. Retourne True si la section existe."""
        section = self._sections.get(key)
        if section is None:
            return False
        section.toggle()
        return True

    def get_section(self, key: str) -> "CollapsibleSection | None":
        return self._sections.get(key)

    def _setup_ui(self):
        # Only options that are actually consumed by the backend are exposed.
        # Chaque section commence par un libellé descriptif court qui résume
        # le rôle métier des paramètres en-dessous.

        # === SECTION VIDEO ===
        video_section = CollapsibleSection(self, "Video", icon="🎬", expanded=True)
        video_section.pack(fill="x", pady=2)
        self._sections["video"] = video_section
        video_content = video_section.get_content_frame()

        self._add_section_description(
            video_content,
            "Format et qualité du fichier MP4 final. Ces paramètres "
            "n'affectent pas le morphing lui-même, seulement l'encodage."
        )

        self._options["fps"] = self._create_slider(
            video_content, "FPS", 10, 60, 25,
            "Images par seconde de la vidéo finale.\n"
            "• 24 = rendu cinéma\n"
            "• 30 = standard TV/web\n"
            "• 60 = ultra-fluide (fichier ~2× plus lourd)\n"
            "Pour une transition courte (< 3 s), 25-30 suffit largement."
        )

        self._options["video_quality"] = self._create_dropdown(
            video_content,
            "Qualité",
            ["Basse", "Moyenne", "Haute", "Maximum"],
            "Moyenne",
            "Preset d'encodage H.264 (CRF + preset FFmpeg).\n"
            "• Basse : encodage ultra-rapide, fichier le plus léger\n"
            "• Moyenne : compromis vitesse / qualité\n"
            "• Haute : encodage lent, meilleur ratio qualité/taille (recommandé)\n"
            "• Maximum : encodage très lent (×3), gain visuel marginal",
        )

        self._options["resolution"] = self._create_dropdown(
            video_content,
            "Résolution",
            ["Original", "1080p", "720p", "480p"],
            "Original",
            "Résolution de sortie. Le ratio d'aspect des photos est conservé.\n"
            "• Original : taille des photos sources (recommandé)\n"
            "• 1080p / 720p / 480p : downscale, fichier plus léger\n"
            "Le upscale au-delà de la résolution source n'est jamais fait.",
        )

        # === SECTION MORPHING ===
        morph_section = CollapsibleSection(self, "Morphing", icon="🔀", expanded=True)
        morph_section.pack(fill="x", pady=2)
        self._sections["morphing"] = morph_section
        morph_content = morph_section.get_content_frame()

        self._add_section_description(
            morph_content,
            "Comportement de la transition entre deux visages : "
            "durées, courbe d'animation et mode de fusion des pixels."
        )

        self._options["transition_duration"] = self._create_slider(
            morph_content, "Transition (s)", 0.5, 10, 3,
            "Durée du morphing entre deux photos consécutives.\n"
            "Détermine le nombre de frames intermédiaires "
            "(transition × FPS = frames calculées par paire)."
        )

        self._options["pause_duration"] = self._create_slider(
            morph_content, "Pause (s)", 0, 5, 0,
            "Durée d'arrêt sur chaque photo avant la transition suivante.\n"
            "0 = transitions enchaînées sans pause (look fluide).\n"
            "0.5-1 s = chaque visage est lisible avant qu'il ne morphe."
        )

        self._options["easing"] = self._create_dropdown(
            morph_content,
            "Courbe",
            ["Lineaire", "Ease In/Out", "Ease In", "Ease Out"],
            "Lineaire",
            "Profil d'accélération de la transition (timing function).\n"
            "• Linéaire : vitesse constante du début à la fin\n"
            "• Ease In/Out : démarre lent, accélère, ralentit (le plus naturel)\n"
            "• Ease In : démarre lent puis accélère\n"
            "• Ease Out : démarre rapide puis ralentit",
        )

        self._options["blend_mode"] = self._create_dropdown(
            morph_content, "Fusion", ["Normal", "Cross-dissolve", "Additive"], "Normal",
            "Mode de mélange des pixels pendant la transition.\n"
            "• Normal : alpha blending classique (recommandé)\n"
            "• Cross-dissolve : équivalent à Normal sans morphing géométrique\n"
            "• Additive : addition lumineuse (plus clair, look surnaturel)",
        )

        # === SECTION ALIGNEMENT ===
        align_section = CollapsibleSection(self, "Alignement", icon="📐", expanded=False)
        align_section.pack(fill="x", pady=2)
        self._sections["alignment"] = align_section
        align_content = align_section.get_content_frame()

        self._add_section_description(
            align_content,
            "Recadre tous les visages sur l'image de référence avant le "
            "morphing, pour qu'ils occupent la même zone à l'écran."
        )

        # Bordure : borne ramenée à 50 px (au-dessus, l'effet sur une image
        # 800×800 dépasse 6% de la dimension utile, sans bénéfice visuel).
        self._options["border_size"] = self._create_slider(
            align_content, "Bordure (px)", 0, 50, 0,
            "Marge blanche ajoutée autour de chaque image alignée.\n"
            "0 = pas de marge (recommandé).\n"
            "Utile pour compenser un cadrage trop serré sur le visage."
        )

        self._options["overlay_mode"] = self._create_checkbox(
            align_content, "Superposition",
            "Superpose chaque image alignée avec la précédente (effet "
            "« fantôme » à 50 % d'opacité) — utile pour vérifier la qualité "
            "de l'alignement face à face. N'affecte pas la vidéo finale, "
            "seulement les images intermédiaires dans le dossier 02_align/."
        )

        # === SECTION DETECTION ===
        detect_section = CollapsibleSection(self, "Detection", icon="👁", expanded=False)
        detect_section.pack(fill="x", pady=2)
        self._sections["detection"] = detect_section
        detect_content = detect_section.get_content_frame()

        self._add_section_description(
            detect_content,
            "Détection des 68 points caractéristiques du visage avec dlib. "
            "Si le visage n'est pas détecté, le morphing bascule sur un "
            "fondu cross-dissolve pour cette image."
        )

        self._options["retry_detection"] = self._create_slider(
            detect_content, "Tentatives", 1, 5, 3,
            "Nombre de passes de détection avant de renoncer.\n"
            "À chaque tentative, dlib essaie une upscale × 2 de l'image "
            "pour repêcher les petits visages.\n"
            "• 1 : rapide mais moins robuste\n"
            "• 3 : compromis par défaut (recommandé)\n"
            "• 5 : exhaustif, plus lent sur les photos sans visage"
        )

        # === SECTION WORKFLOW ===
        workflow_section = CollapsibleSection(self, "Workflow", icon="⚡", expanded=False)
        workflow_section.pack(fill="x", pady=2)
        self._sections["workflow"] = workflow_section
        workflow_content = workflow_section.get_content_frame()

        self._add_section_description(
            workflow_content,
            "Comportement global du pipeline (Import → Alignement → "
            "Morphing → Export) face aux erreurs et au niveau de logs."
        )

        self._options["continue_on_error"] = self._create_checkbox(
            workflow_content, "Continuer si erreur",
            "Si activé : une image corrompue ou un visage non détecté n'arrête "
            "pas le workflow ; l'image est simplement sautée et listée dans "
            "le log de run.\n"
            "Si désactivé : le workflow s'arrête à la première erreur "
            "(comportement strict)."
        )

        self._options["debug_mode"] = self._create_checkbox(
            workflow_content, "Mode debug",
            "Active les logs niveau DEBUG (très verbeux).\n"
            "À utiliser quand on diagnostique un bug : chaque frame, chaque "
            "détection, chaque appel FFmpeg est tracé dans logs/MorphoLapse_*.log.\n"
            "À désactiver pour un usage normal (impact perf négligeable mais "
            "logs énormes)."
        )

        # === SECTION EXPORT ===
        export_section = CollapsibleSection(self, "Export", icon="📤", expanded=False)
        export_section.pack(fill="x", pady=2)
        self._sections["export"] = export_section
        export_content = export_section.get_content_frame()

        self._add_section_description(
            export_content,
            "Sorties additionnelles générées à côté de la vidéo MP4."
        )

        self._options["create_gif"] = self._create_checkbox(
            export_content, "Créer GIF",
            "Génère aussi un GIF animé (480p, ≤ 15 fps) à côté du MP4.\n"
            "Pratique pour partager un aperçu rapide, mais le fichier peut "
            "être lourd (5-20 Mo selon la durée). Inclus uniquement dans le "
            "dossier 04_export/."
        )

        self._options["thumbnail"] = self._create_checkbox(
            export_content, "Miniature",
            "Génère une miniature JPG (640px de large) extraite du milieu "
            "de la vidéo finale. Utile pour identifier rapidement un run "
            "dans un explorateur de fichiers."
        )

    def _add_section_description(self, content: ctk.CTkFrame, text: str):
        """Affiche un libellé descriptif sous le header d'une section.

        Le texte explique en 1-2 phrases ce que la section paramètre.
        Placé avant les widgets pour donner le contexte avant les choix.
        """
        label = ctk.CTkLabel(
            content,
            text=text,
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color=("gray35", "gray70"),
            wraplength=200,
            justify="left",
            anchor="w",
        )
        label.pack(fill="x", padx=4, pady=(2, 6))

    def _create_slider(
        self, parent, label: str, min_val: float, max_val: float, default: float, tooltip: str
    ) -> ctk.CTkSlider:
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=40)
        frame.pack(fill="x", pady=2)
        frame.pack_propagate(False)

        lbl = ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11), width=90, anchor="w")
        lbl.pack(side="left", padx=(0, 4))

        value_label = ctk.CTkLabel(frame, text=f"{default:.1f}", width=35, font=ctk.CTkFont(size=10))
        value_label.pack(side="right", padx=2)

        slider = ctk.CTkSlider(
            frame, from_=min_val, to=max_val, height=14, number_of_steps=int((max_val - min_val) * 10)
        )
        slider.set(default)
        slider.pack(side="right", fill="x", expand=True, padx=2)

        def update_value(val):
            value_label.configure(text=f"{val:.1f}")

        slider.configure(command=update_value)

        return slider

    def _create_checkbox(self, parent, label: str, tooltip: str) -> ctk.CTkCheckBox:
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=28)
        frame.pack(fill="x", pady=1)
        frame.pack_propagate(False)

        checkbox = ctk.CTkCheckBox(
            frame,
            text=label,
            font=ctk.CTkFont(size=11),
            checkbox_width=18,
            checkbox_height=18,
            height=24,
            # Bord explicite pour garantir la lisibilité sur tous les thèmes
            # système (cf. DA-5 audit).
            border_width=2,
            border_color=("gray55", "gray55"),
        )
        checkbox.pack(side="left", padx=0)

        return checkbox

    def _create_dropdown(self, parent, label: str, values: list[str], default: str, tooltip: str) -> ctk.CTkOptionMenu:
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=32)
        frame.pack(fill="x", pady=2)
        frame.pack_propagate(False)

        lbl = ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11), width=90, anchor="w")
        lbl.pack(side="left", padx=(0, 4))

        dropdown = ctk.CTkOptionMenu(
            frame,
            values=values,
            width=110,
            height=24,
            font=ctk.CTkFont(size=10),
            # Surfaces contrastées pour distinguer le dropdown du fond de
            # l'OptionsPanel sur tous les thèmes (cf. DA-5 audit).
            fg_color=("gray85", "gray25"),
            button_color=("gray70", "gray35"),
            button_hover_color=("gray60", "gray45"),
        )
        dropdown.set(default)
        dropdown.pack(side="right", padx=2)

        return dropdown

    def get_options(self) -> dict:
        result = {}
        for key, widget in self._options.items():
            if isinstance(widget, ctk.CTkSlider):
                result[key] = widget.get()
            elif isinstance(widget, ctk.CTkCheckBox):
                result[key] = bool(widget.get())
            elif isinstance(widget, ctk.CTkOptionMenu):
                result[key] = widget.get()
        return result

    def set_options(self, options: dict):
        for key, value in options.items():
            if key in self._options:
                widget = self._options[key]
                if isinstance(widget, ctk.CTkSlider):
                    widget.set(value)
                elif isinstance(widget, ctk.CTkCheckBox):
                    if value:
                        widget.select()
                    else:
                        widget.deselect()
                elif isinstance(widget, ctk.CTkOptionMenu):
                    widget.set(str(value))


class ImagePreview(ctk.CTkFrame):
    """Widget de previsualisation compact"""

    def __init__(self, master, size: tuple = (120, 120), **kwargs):
        super().__init__(master, **kwargs)
        self.size = size
        self._current_image = None
        self._setup_ui()

    def _setup_ui(self):
        self.configure(fg_color=("gray80", "gray20"), corner_radius=6)

        self.image_label = ctk.CTkLabel(self, text="", width=self.size[0], height=self.size[1])
        self.image_label.pack(padx=4, pady=4)

        self.info_label = ctk.CTkLabel(
            self, text="Aucune image", font=ctk.CTkFont(size=9), text_color=("gray50", "gray60")
        )
        self.info_label.pack(pady=(0, 4))

    def set_image(self, image_path: str):
        """Charge et affiche une vignette du fichier `image_path`.

        On bypasse `ctk.CTkImage` et on passe par `PIL.ImageTk.PhotoImage`
        avec un `master` explicite (= le label lui-même). Raison : CTkImage
        finit par appeler `ImageTk.PhotoImage(image)` SANS master, ce qui
        repose sur `tkinter._default_root`. Après la fermeture du splash
        screen (qui crée son propre Tk root en premier), `_default_root`
        pointe vers une fenêtre détruite → `RuntimeError` au prochain rendu
        d'image (cf. V-009 NOK « Erreur: RuntimeError »).

        En passant `master=self.image_label`, le PhotoImage est rattaché à
        la fenêtre principale vivante. On contourne aussi la couche CTk en
        configurant directement le tk.Label interne (`self.image_label._label`)
        car CTkLabel s'attend à recevoir un CTkImage et logue un warning sur
        un PhotoImage tk natif (sans impact fonctionnel).
        """
        try:
            with Image.open(image_path) as img:
                img.load()  # force le décodage des pixels en mémoire
                img.thumbnail(self.size, Image.Resampling.LANCZOS)
                pil_image = img.copy()  # objet indépendant du file handle
            photo = ImageTk.PhotoImage(pil_image, master=self.image_label)

            # Configurer le tk.Label interne du CTkLabel pour éviter la
            # validation CTkImage et utiliser le master déjà défini.
            try:
                self.image_label._label.configure(image=photo)
            except Exception:
                # Fallback : configure direct du CTkLabel (peut warner).
                self.image_label.configure(image=photo)
            self._current_image = photo  # référence anti-GC obligatoire

            name = os.path.basename(image_path)
            self.info_label.configure(text=name[:20] + "..." if len(name) > 20 else name)
        except Exception as e:
            _log.warning("ImagePreview.set_image(%s) failed: %s: %s", image_path, type(e).__name__, e)
            # Afficher classe + début du message pour diagnostiquer rapidement
            err_text = f"Erreur: {type(e).__name__}"
            if str(e):
                err_text += f" — {str(e)[:30]}"
            self.info_label.configure(text=err_text)
            try:
                self.image_label._label.configure(image="")
            except Exception:
                try:
                    self.image_label.configure(image=None)
                except Exception:
                    pass

    def clear(self):
        self.image_label.configure(image=None)
        self.info_label.configure(text="Aucune image")
        self._current_image = None


class QuickActions(ctk.CTkFrame):
    """Barre d'actions rapides.

    Class-level ACTIONS is the single source of truth for which buttons
    appear; main_window._on_quick_action handles exactly these ids and no
    others. The previous 'reset'/'help' icons emitted ids with no handler
    (see CHANGELOG.md, 2.0.0 audit), and are removed.
    """

    ACTIONS = (
        ("📂", "open", "Ouvrir dossier"),
        ("💾", "save", "Sauvegarder"),
    )

    def __init__(self, master, on_action: Callable = None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        self._callbacks = {}
        self._on_action = on_action
        self._setup_ui()

    def _setup_ui(self):
        for icon, action_id, _tooltip in self.ACTIONS:
            btn = ctk.CTkButton(
                self,
                text=icon,
                width=34,
                height=30,
                font=ctk.CTkFont(size=14),
                fg_color=("gray85", "gray22"),
                hover_color=("gray75", "gray30"),
                border_width=1,
                border_color=("gray60", "gray40"),
                command=lambda a=action_id: self._trigger(a),
            )
            btn.pack(side="left", padx=2)

    def _trigger(self, action_id: str):
        if self._on_action:
            self._on_action(action_id)
        elif action_id in self._callbacks:
            self._callbacks[action_id]()

    def set_callback(self, action_id: str, callback: Callable):
        self._callbacks[action_id] = callback
