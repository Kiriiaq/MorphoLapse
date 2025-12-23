"""
Widgets - Composants UI personnalises avec options avancees
"""

import customtkinter as ctk
from typing import Callable, Optional, List, Dict, Any
from PIL import Image, ImageTk
import os


class ToolTip:
    """Infobulle pour les widgets"""

    def __init__(self, widget, text: str, delay: int = 400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.scheduled_id = None

        self.widget.bind("<Enter>", self._schedule_show)
        self.widget.bind("<Leave>", self._hide)

    def _schedule_show(self, event=None):
        self._cancel_scheduled()
        self.scheduled_id = self.widget.after(self.delay, self._show)

    def _cancel_scheduled(self):
        if self.scheduled_id:
            self.widget.after_cancel(self.scheduled_id)
            self.scheduled_id = None

    def _show(self, event=None):
        if self.tooltip_window:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2

        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)

        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            corner_radius=4,
            fg_color=("#2d2d2d", "#2d2d2d"),
            text_color=("#ffffff", "#ffffff"),
            font=ctk.CTkFont(size=11),
            padx=8,
            pady=4
        )
        label.pack()

    def _hide(self, event=None):
        self._cancel_scheduled()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def update_text(self, new_text: str):
        self.text = new_text


class CollapsibleSection(ctk.CTkFrame):
    """Section repliable avec indicateur visuel"""

    def __init__(self, master, title: str, icon: str = "", expanded: bool = True,
                 highlight: bool = False, **kwargs):
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
            self.header,
            text="▼" if self._expanded else "▶",
            font=ctk.CTkFont(size=10),
            width=16
        )
        self.expand_label.pack(side="left", padx=(8, 2))

        # Titre avec icone
        title_text = f"{self.icon} {self.title}" if self.icon else self.title
        self.title_label = ctk.CTkLabel(
            self.header,
            text=title_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
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
                height=16
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

    def get_content_frame(self) -> ctk.CTkFrame:
        return self.content


class StepIndicator(ctk.CTkFrame):
    """Indicateur d'etat compact d'une etape du workflow"""

    ICONS = {
        'pending': '○',
        'running': '◉',
        'completed': '✓',
        'error': '✗',
        'skipped': '⊘',
        'disabled': '⊗'
    }

    COLORS = {
        'pending': ('#6b7280', '#6b7280'),
        'running': ('#3b82f6', '#3b82f6'),
        'completed': ('#22c55e', '#22c55e'),
        'error': ('#ef4444', '#ef4444'),
        'skipped': ('#9ca3af', '#9ca3af'),
        'disabled': ('#4b5563', '#4b5563')
    }

    def __init__(self, master, step_name: str, step_description: str,
                 enabled: bool = True, on_toggle: Callable = None, **kwargs):
        super().__init__(master, **kwargs)

        self.step_name = step_name
        self.step_description = step_description
        self._status = 'pending'
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
            self.main_frame, text="", width=20, height=20,
            checkbox_width=16, checkbox_height=16,
            command=self._toggle
        )
        self.checkbox.pack(side="left", padx=(6, 4))
        if self._enabled:
            self.checkbox.select()

        # Icone de statut
        self.icon_label = ctk.CTkLabel(
            self.main_frame,
            text=self.ICONS['pending'],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS['pending'],
            width=20
        )
        self.icon_label.pack(side="left", padx=2)

        # Nom de l'etape
        self.name_label = ctk.CTkLabel(
            self.main_frame,
            text=self.step_name,
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.name_label.pack(side="left", fill="x", expand=True, padx=4)

        # Barre de progression compacte
        self.progress_bar = ctk.CTkProgressBar(
            self.main_frame, width=60, height=6
        )
        self.progress_bar.pack(side="right", padx=6)
        self.progress_bar.set(0)

        ToolTip(self.main_frame, self.step_description)

    def _toggle(self):
        self._enabled = self.checkbox.get()
        self.set_status('pending' if self._enabled else 'disabled')
        if self._on_toggle:
            self._on_toggle(self.step_name, self._enabled)

    def set_status(self, status: str):
        self._status = status
        self.icon_label.configure(
            text=self.ICONS.get(status, '?'),
            text_color=self.COLORS.get(status, self.COLORS['pending'])
        )
        border = 2 if status == 'running' else 0
        self.main_frame.configure(border_width=border, border_color=self.COLORS.get(status))

    def set_progress(self, progress: float):
        self._progress = progress / 100.0
        self.progress_bar.set(self._progress)

    @property
    def enabled(self) -> bool:
        return self._enabled


class LogViewer(ctk.CTkFrame):
    """Visualiseur de logs compact"""

    def __init__(self, master, max_lines: int = 500, **kwargs):
        super().__init__(master, **kwargs)
        self.max_lines = max_lines
        self._line_count = 0
        self._setup_ui()

    def _setup_ui(self):
        # Toolbar compacte
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=28)
        toolbar.pack(fill="x", padx=4, pady=2)
        toolbar.pack_propagate(False)

        ctk.CTkLabel(
            toolbar, text="Logs",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(side="left", padx=4)

        # Boutons compacts
        ctk.CTkButton(
            toolbar, text="Effacer", width=50, height=22,
            font=ctk.CTkFont(size=10), command=self.clear
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            toolbar, text="Export", width=50, height=22,
            font=ctk.CTkFont(size=10), command=self._export_logs
        ).pack(side="right", padx=2)

        self.level_var = ctk.StringVar(value="INFO")
        ctk.CTkOptionMenu(
            toolbar, values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self.level_var, width=70, height=22,
            font=ctk.CTkFont(size=10)
        ).pack(side="right", padx=4)

        # Zone de texte avec scrollbar integree
        self.textbox = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word", state="disabled"
        )
        self.textbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Tags de couleur
        self.textbox._textbox.tag_configure("DEBUG", foreground="#9ca3af")
        self.textbox._textbox.tag_configure("INFO", foreground="#e5e7eb")
        self.textbox._textbox.tag_configure("WARNING", foreground="#f59e0b")
        self.textbox._textbox.tag_configure("ERROR", foreground="#ef4444")
        self.textbox._textbox.tag_configure("SUCCESS", foreground="#22c55e")

    def log(self, message: str, level: str = "INFO"):
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        current_level = self.level_var.get()
        if level in levels and levels.index(level) < levels.index(current_level):
            return

        self.textbox.configure(state="normal")
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.textbox.insert("end", f"[{timestamp}] {message}\n", level)
        self._line_count += 1

        if self._line_count > self.max_lines:
            self.textbox.delete("1.0", "2.0")
            self._line_count -= 1

        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self._line_count = 0
        self.textbox.configure(state="disabled")

    def _export_logs(self):
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.textbox.get("1.0", "end"))


class OptionsPanel(ctk.CTkScrollableFrame):
    """Panneau d'options avancees avec sections repliables et nouvelles options"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._options = {}
        self._setup_ui()

    def _setup_ui(self):
        # === SECTION VIDEO ===
        video_section = CollapsibleSection(self, "Video", icon="🎬", expanded=True)
        video_section.pack(fill="x", pady=2)
        video_content = video_section.get_content_frame()

        self._options['fps'] = self._create_slider(
            video_content, "FPS", 10, 60, 25,
            "Images par seconde (24=cinema, 30=standard, 60=fluide)"
        )

        self._options['video_quality'] = self._create_dropdown(
            video_content, "Qualite", ["Basse", "Moyenne", "Haute", "Maximum"],
            "Moyenne", "Qualite d'encodage (affecte la taille du fichier)"
        )

        self._options['output_format'] = self._create_dropdown(
            video_content, "Format", ["MP4 (H.264)", "WebM (VP9)", "AVI", "GIF"],
            "MP4 (H.264)", "Format de sortie video"
        )

        self._options['resolution'] = self._create_dropdown(
            video_content, "Resolution", ["Original", "1080p", "720p", "480p"],
            "Original", "Resolution de sortie"
        )

        # === SECTION MORPHING ===
        morph_section = CollapsibleSection(self, "Morphing", icon="🔀", expanded=True)
        morph_section.pack(fill="x", pady=2)
        morph_content = morph_section.get_content_frame()

        self._options['transition_duration'] = self._create_slider(
            morph_content, "Transition (s)", 0.5, 10, 3,
            "Duree du morphing entre deux images"
        )

        self._options['pause_duration'] = self._create_slider(
            morph_content, "Pause (s)", 0, 5, 0,
            "Pause sur chaque image avant transition"
        )

        self._options['easing'] = self._create_dropdown(
            morph_content, "Courbe", ["Lineaire", "Ease In/Out", "Ease In", "Ease Out"],
            "Lineaire", "Type d'acceleration de la transition"
        )

        self._options['blend_mode'] = self._create_dropdown(
            morph_content, "Fusion", ["Normal", "Cross-dissolve", "Additive"],
            "Normal", "Mode de fusion des images"
        )

        # === SECTION ALIGNEMENT ===
        align_section = CollapsibleSection(self, "Alignement", icon="📐", expanded=False)
        align_section.pack(fill="x", pady=2)
        align_content = align_section.get_content_frame()

        self._options['border_size'] = self._create_slider(
            align_content, "Bordure (px)", 0, 100, 0,
            "Bordure blanche autour des images"
        )

        self._options['overlay_mode'] = self._create_checkbox(
            align_content, "Superposition",
            "Superposer les images alignees"
        )

        self._options['auto_crop'] = self._create_checkbox(
            align_content, "Recadrage auto",
            "Recadrer automatiquement sur le visage"
        )

        self._options['stabilize'] = self._create_checkbox(
            align_content, "Stabilisation",
            "Stabiliser les micro-mouvements"
        )

        # === SECTION DETECTION (NEW) ===
        detect_section = CollapsibleSection(
            self, "Detection", icon="👁", expanded=False, highlight=True
        )
        detect_section.pack(fill="x", pady=2)
        detect_content = detect_section.get_content_frame()

        self._options['detection_threshold'] = self._create_slider(
            detect_content, "Sensibilite", 0.1, 1.0, 0.5,
            "Seuil de detection des visages"
        )

        self._options['multi_face'] = self._create_dropdown(
            detect_content, "Multi-visages", ["Premier", "Plus grand", "Manuel"],
            "Premier", "Selection quand plusieurs visages detectes"
        )

        self._options['retry_detection'] = self._create_slider(
            detect_content, "Tentatives", 1, 5, 3,
            "Nombre de tentatives de detection"
        )

        # === SECTION WORKFLOW ===
        workflow_section = CollapsibleSection(self, "Workflow", icon="⚡", expanded=False)
        workflow_section.pack(fill="x", pady=2)
        workflow_content = workflow_section.get_content_frame()

        self._options['continue_on_error'] = self._create_checkbox(
            workflow_content, "Continuer si erreur",
            "Continue meme en cas d'erreur sur une image"
        )

        self._options['debug_mode'] = self._create_checkbox(
            workflow_content, "Mode debug",
            "Affiche des informations detaillees"
        )

        self._options['parallel_processing'] = self._create_checkbox(
            workflow_content, "Traitement parallele",
            "Utilise plusieurs coeurs CPU"
        )

        self._options['auto_backup'] = self._create_checkbox(
            workflow_content, "Sauvegarde auto",
            "Sauvegarde les etapes intermediaires"
        )

        # === SECTION EXPORT (NEW) ===
        export_section = CollapsibleSection(
            self, "Export", icon="📤", expanded=False, highlight=True
        )
        export_section.pack(fill="x", pady=2)
        export_content = export_section.get_content_frame()

        self._options['export_frames'] = self._create_checkbox(
            export_content, "Exporter frames",
            "Sauvegarder toutes les frames en images"
        )

        self._options['export_landmarks'] = self._create_checkbox(
            export_content, "Exporter landmarks",
            "Sauvegarder les points de repere en JSON"
        )

        self._options['create_gif'] = self._create_checkbox(
            export_content, "Creer GIF",
            "Generer aussi un GIF anime"
        )

        self._options['thumbnail'] = self._create_checkbox(
            export_content, "Miniature",
            "Generer une miniature de la video"
        )

    def _create_slider(self, parent, label: str, min_val: float, max_val: float,
                       default: float, tooltip: str) -> ctk.CTkSlider:
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=40)
        frame.pack(fill="x", pady=2)
        frame.pack_propagate(False)

        lbl = ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11), width=90, anchor="w")
        lbl.pack(side="left", padx=(0, 4))

        value_label = ctk.CTkLabel(frame, text=f"{default:.1f}", width=35,
                                   font=ctk.CTkFont(size=10))
        value_label.pack(side="right", padx=2)

        slider = ctk.CTkSlider(
            frame, from_=min_val, to=max_val, height=14,
            number_of_steps=int((max_val - min_val) * 10)
        )
        slider.set(default)
        slider.pack(side="right", fill="x", expand=True, padx=2)

        def update_value(val):
            value_label.configure(text=f"{val:.1f}")
        slider.configure(command=update_value)

        ToolTip(frame, tooltip)
        return slider

    def _create_checkbox(self, parent, label: str, tooltip: str) -> ctk.CTkCheckBox:
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=28)
        frame.pack(fill="x", pady=1)
        frame.pack_propagate(False)

        checkbox = ctk.CTkCheckBox(
            frame, text=label, font=ctk.CTkFont(size=11),
            checkbox_width=18, checkbox_height=18, height=24
        )
        checkbox.pack(side="left", padx=0)

        ToolTip(checkbox, tooltip)
        return checkbox

    def _create_dropdown(self, parent, label: str, values: List[str],
                         default: str, tooltip: str) -> ctk.CTkOptionMenu:
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=32)
        frame.pack(fill="x", pady=2)
        frame.pack_propagate(False)

        lbl = ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11), width=90, anchor="w")
        lbl.pack(side="left", padx=(0, 4))

        dropdown = ctk.CTkOptionMenu(
            frame, values=values, width=110, height=24,
            font=ctk.CTkFont(size=10)
        )
        dropdown.set(default)
        dropdown.pack(side="right", padx=2)

        ToolTip(frame, tooltip)
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

        self.image_label = ctk.CTkLabel(
            self, text="", width=self.size[0], height=self.size[1]
        )
        self.image_label.pack(padx=4, pady=4)

        self.info_label = ctk.CTkLabel(
            self, text="Aucune image",
            font=ctk.CTkFont(size=9),
            text_color=("gray50", "gray60")
        )
        self.info_label.pack(pady=(0, 4))

    def set_image(self, image_path: str):
        try:
            img = Image.open(image_path)
            img.thumbnail(self.size, Image.Resampling.LANCZOS)

            photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.image_label.configure(image=photo)
            self._current_image = photo

            name = os.path.basename(image_path)
            self.info_label.configure(text=name[:20] + "..." if len(name) > 20 else name)
        except Exception as e:
            self.info_label.configure(text="Erreur")

    def clear(self):
        self.image_label.configure(image=None)
        self.info_label.configure(text="Aucune image")
        self._current_image = None


class QuickActions(ctk.CTkFrame):
    """Barre d'actions rapides"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        self._callbacks = {}
        self._setup_ui()

    def _setup_ui(self):
        actions = [
            ("📂", "open", "Ouvrir dossier"),
            ("💾", "save", "Sauvegarder"),
            ("🔄", "reset", "Reinitialiser"),
            ("❓", "help", "Aide"),
        ]

        for icon, action_id, tooltip in actions:
            btn = ctk.CTkButton(
                self, text=icon, width=32, height=28,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                hover_color=("gray70", "gray30"),
                command=lambda a=action_id: self._trigger(a)
            )
            btn.pack(side="left", padx=1)
            ToolTip(btn, tooltip)

    def _trigger(self, action_id: str):
        if action_id in self._callbacks:
            self._callbacks[action_id]()

    def set_callback(self, action_id: str, callback: Callable):
        self._callbacks[action_id] = callback
