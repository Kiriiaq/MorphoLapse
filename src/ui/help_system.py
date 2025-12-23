"""
Help System - Système d'aide intégré
Documentation contextuelle et tooltips améliorés
"""

import customtkinter as ctk
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class HelpTopic:
    """Un sujet d'aide"""
    id: str
    title: str
    content: str
    category: str
    keywords: list


# Base de connaissances de l'aide
HELP_TOPICS: Dict[str, HelpTopic] = {
    # === Paramètres Vidéo ===
    "fps": HelpTopic(
        id="fps",
        title="Images par seconde (FPS)",
        content="""
**FPS (Frames Per Second)**

Définit le nombre d'images affichées par seconde dans la vidéo finale.

**Valeurs recommandées:**
- 24 fps : Standard cinéma, aspect plus "filmique"
- 25 fps : Standard PAL (Europe)
- 30 fps : Standard NTSC (Amérique du Nord)
- 60 fps : Ultra-fluide, idéal pour le web

**Impact:**
- Plus de FPS = vidéo plus fluide mais fichier plus gros
- Moins de FPS = transitions moins lisses mais fichier plus petit

**Conseil:** Pour un rendu naturel, utilisez 25-30 fps.
        """,
        category="Vidéo",
        keywords=["fps", "framerate", "images", "seconde", "fluide"]
    ),

    "video_quality": HelpTopic(
        id="video_quality",
        title="Qualité vidéo",
        content="""
**Qualité de la vidéo**

Contrôle le niveau de compression de la vidéo finale.

**Options:**
- **Low (Basse)** : Fichier petit, qualité réduite (CRF 28)
- **Medium (Moyenne)** : Bon compromis taille/qualité (CRF 23)
- **High (Haute)** : Qualité élevée, fichier plus gros (CRF 18) ⭐ Recommandé
- **Ultra** : Qualité maximale, gros fichier (CRF 15)

**Conseil:** "High" est idéal pour la plupart des usages.
        """,
        category="Vidéo",
        keywords=["qualité", "quality", "compression", "crf"]
    ),

    "output_format": HelpTopic(
        id="output_format",
        title="Format de sortie",
        content="""
**Format vidéo**

Le format du fichier vidéo final.

**Options:**
- **MP4** : Format universel, compatible partout ⭐ Recommandé
- **AVI** : Ancien format, moins compressé
- **WebM** : Idéal pour le web, open source

**Conseil:** Utilisez MP4 pour une compatibilité maximale.
        """,
        category="Vidéo",
        keywords=["format", "mp4", "avi", "webm", "codec"]
    ),

    "resolution": HelpTopic(
        id="resolution",
        title="Résolution",
        content="""
**Résolution de sortie**

La taille de la vidéo finale en pixels.

**Options:**
- **Original** : Garde la résolution des images sources
- **1080p** : Full HD (1920×1080) ⭐ Recommandé
- **720p** : HD (1280×720), bon pour le web
- **480p** : SD, petits fichiers

**Conseil:** 1080p offre un bon équilibre qualité/taille.
        """,
        category="Vidéo",
        keywords=["résolution", "resolution", "1080p", "720p", "hd"]
    ),

    # === Paramètres Morphing ===
    "transition_duration": HelpTopic(
        id="transition_duration",
        title="Durée de transition",
        content="""
**Durée de la transition (secondes)**

Temps pour passer d'une image à l'autre.

**Valeurs suggérées:**
- 1-2s : Transitions rapides, effet dynamique
- 3-4s : Rythme naturel ⭐ Recommandé
- 5-10s : Transitions lentes, effet contemplatif

**Impact:**
Durée × FPS = nombre de frames de morphing
Ex: 3s × 25fps = 75 frames de morphing par transition
        """,
        category="Morphing",
        keywords=["durée", "transition", "duration", "secondes"]
    ),

    "easing": HelpTopic(
        id="easing",
        title="Fonction d'easing",
        content="""
**Easing (courbe d'animation)**

Contrôle la vitesse de la transition au cours du temps.

**Options:**
- **Linear** : Vitesse constante
- **Ease In** : Démarre lentement, accélère
- **Ease Out** : Démarre vite, ralentit ⭐ Recommandé
- **Ease In-Out** : Lent → rapide → lent
- **Bounce** : Effet de rebond

**Conseil:** "Ease Out" donne un effet naturel et agréable.
        """,
        category="Morphing",
        keywords=["easing", "courbe", "animation", "vitesse"]
    ),

    "blend_mode": HelpTopic(
        id="blend_mode",
        title="Mode de fusion",
        content="""
**Mode de fusion des images**

Comment les deux images sont combinées pendant le morphing.

**Options:**
- **Alpha** : Mélange classique par transparence ⭐ Standard
- **Additive** : Addition (plus lumineux)
- **Multiply** : Multiplication (plus sombre)
- **Screen** : Inverse de multiply

**Conseil:** Utilisez "Alpha" pour un morphing naturel.
        """,
        category="Morphing",
        keywords=["blend", "fusion", "mode", "alpha"]
    ),

    # === Paramètres Détection ===
    "detection_threshold": HelpTopic(
        id="detection_threshold",
        title="Seuil de détection",
        content="""
**Seuil de confiance pour la détection**

Sensibilité de la détection de visages.

**Valeurs:**
- 0.3 : Très sensible, détecte plus de visages
- 0.5 : Équilibré ⭐ Recommandé
- 0.8 : Strict, moins de faux positifs

**Conseil:** Augmentez si trop de fausses détections,
diminuez si des visages ne sont pas détectés.
        """,
        category="Détection",
        keywords=["seuil", "threshold", "confiance", "détection"]
    ),

    "multi_face": HelpTopic(
        id="multi_face",
        title="Détection multi-visages",
        content="""
**Mode multi-visages**

Gère les images contenant plusieurs personnes.

**Comportement:**
- **Désactivé** : Utilise uniquement le visage principal
- **Activé** : Détecte et traite tous les visages

**Conseil:** Désactivez pour des portraits individuels,
activez pour des photos de groupe.
        """,
        category="Détection",
        keywords=["multi", "plusieurs", "visages", "groupe"]
    ),

    # === Paramètres Export ===
    "create_gif": HelpTopic(
        id="create_gif",
        title="Création de GIF",
        content="""
**Export GIF animé**

Crée un GIF animé en plus de la vidéo.

**Caractéristiques:**
- Résolution réduite (480px de large)
- FPS limité à 15 pour la taille
- Idéal pour le partage sur les réseaux sociaux

**Note:** Le GIF sera plus volumineux que la vidéo MP4
pour une qualité moindre (limite du format).
        """,
        category="Export",
        keywords=["gif", "animé", "animation", "partage"]
    ),

    "export_landmarks": HelpTopic(
        id="export_landmarks",
        title="Export des landmarks",
        content="""
**Export des points faciaux (landmarks)**

Sauvegarde les 68 points de repère du visage en JSON.

**Contenu:**
- Coordonnées X, Y de chaque point
- Contour du visage, sourcils, yeux, nez, bouche
- Pour chaque image traitée

**Usage:**
- Analyse ultérieure
- Utilisation dans d'autres applications
- Debug et vérification de la détection
        """,
        category="Export",
        keywords=["landmarks", "points", "json", "export"]
    )
}


class HelpSystem:
    """
    Système d'aide centralisé pour MorphoLapse.

    Fournit:
    - Aide contextuelle
    - Recherche dans l'aide
    - Fenêtre d'aide complète
    """

    def __init__(self, topics: Optional[Dict[str, HelpTopic]] = None):
        self.topics = topics or HELP_TOPICS

    def get_topic(self, topic_id: str) -> Optional[HelpTopic]:
        """Récupère un sujet d'aide par son ID"""
        return self.topics.get(topic_id)

    def search(self, query: str) -> list:
        """Recherche dans les sujets d'aide"""
        query = query.lower()
        results = []

        for topic in self.topics.values():
            score = 0

            # Recherche dans le titre
            if query in topic.title.lower():
                score += 10

            # Recherche dans les mots-clés
            for keyword in topic.keywords:
                if query in keyword.lower():
                    score += 5

            # Recherche dans le contenu
            if query in topic.content.lower():
                score += 2

            if score > 0:
                results.append((topic, score))

        # Trier par score décroissant
        results.sort(key=lambda x: x[1], reverse=True)
        return [topic for topic, score in results]

    def get_topics_by_category(self) -> Dict[str, list]:
        """Retourne les sujets groupés par catégorie"""
        result = {}
        for topic in self.topics.values():
            if topic.category not in result:
                result[topic.category] = []
            result[topic.category].append(topic)
        return result


class EnhancedToolTip:
    """
    Tooltip amélioré avec support du markdown simplifié
    et lien vers l'aide détaillée.
    """

    def __init__(
        self,
        widget: ctk.CTkBaseClass,
        text: str,
        help_topic_id: Optional[str] = None,
        help_system: Optional[HelpSystem] = None,
        delay: int = 500
    ):
        self.widget = widget
        self.text = text
        self.help_topic_id = help_topic_id
        self.help_system = help_system
        self.delay = delay
        self.tooltip_window: Optional[ctk.CTkToplevel] = None
        self._id = None

        self.widget.bind("<Enter>", self._schedule_show)
        self.widget.bind("<Leave>", self._hide)
        self.widget.bind("<Button-1>", self._hide)

    def _schedule_show(self, event=None):
        """Programme l'affichage du tooltip"""
        self._cancel_scheduled()
        self._id = self.widget.after(self.delay, self._show)

    def _cancel_scheduled(self):
        """Annule l'affichage programmé"""
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None

    def _show(self, event=None):
        """Affiche le tooltip"""
        if self.tooltip_window:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Frame principale
        frame = ctk.CTkFrame(
            self.tooltip_window,
            corner_radius=6,
            fg_color=("gray90", "gray20"),
            border_width=1,
            border_color=("gray70", "gray40")
        )
        frame.pack(fill="both", expand=True)

        # Texte principal
        label = ctk.CTkLabel(
            frame,
            text=self.text,
            font=ctk.CTkFont(size=11),
            wraplength=250,
            justify="left"
        )
        label.pack(padx=10, pady=8)

        # Lien vers l'aide si disponible
        if self.help_topic_id and self.help_system:
            topic = self.help_system.get_topic(self.help_topic_id)
            if topic:
                help_link = ctk.CTkLabel(
                    frame,
                    text="ℹ️ Plus d'infos (F1)",
                    font=ctk.CTkFont(size=10),
                    text_color=("blue", "lightblue"),
                    cursor="hand2"
                )
                help_link.pack(padx=10, pady=(0, 5))
                help_link.bind("<Button-1>", lambda e: self._show_help())

    def _hide(self, event=None):
        """Cache le tooltip"""
        self._cancel_scheduled()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def _show_help(self):
        """Affiche l'aide détaillée"""
        if self.help_topic_id and self.help_system:
            HelpDialog.show_topic(
                self.widget.winfo_toplevel(),
                self.help_system,
                self.help_topic_id
            )


class HelpDialog:
    """Fenêtre d'aide complète"""

    _instance: Optional['HelpDialog'] = None

    @classmethod
    def show_topic(cls, parent, help_system: HelpSystem, topic_id: str):
        """Affiche l'aide pour un sujet spécifique"""
        topic = help_system.get_topic(topic_id)
        if topic:
            dialog = cls(parent, help_system)
            dialog.show()
            dialog.select_topic(topic)

    def __init__(self, parent: ctk.CTk, help_system: HelpSystem):
        self.parent = parent
        self.help_system = help_system
        self.window: Optional[ctk.CTkToplevel] = None
        self.content_text: Optional[ctk.CTkTextbox] = None

    def show(self):
        """Affiche la fenêtre d'aide"""
        if self.window is not None:
            self.window.focus()
            return

        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Aide - MorphoLapse")
        self.window.geometry("700x550")
        self.window.transient(self.parent)

        # Layout
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(1, weight=1)

        # Barre de recherche
        search_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=10)

        ctk.CTkLabel(search_frame, text="🔍").pack(side="left", padx=5)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Rechercher dans l'aide...",
            width=300
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Liste des sujets (sidebar)
        sidebar = ctk.CTkScrollableFrame(self.window, width=200)
        sidebar.grid(row=1, column=0, sticky="nsew", padx=(15, 5), pady=(0, 15))

        self.topic_buttons = {}
        for category, topics in sorted(self.help_system.get_topics_by_category().items()):
            # En-tête catégorie
            ctk.CTkLabel(
                sidebar,
                text=category,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            ).pack(fill="x", pady=(10, 5))

            for topic in topics:
                btn = ctk.CTkButton(
                    sidebar,
                    text=topic.title,
                    anchor="w",
                    height=28,
                    fg_color="transparent",
                    text_color=("gray20", "gray80"),
                    hover_color=("gray80", "gray30"),
                    command=lambda t=topic: self.select_topic(t)
                )
                btn.pack(fill="x", pady=1)
                self.topic_buttons[topic.id] = btn

        # Contenu
        content_frame = ctk.CTkFrame(self.window)
        content_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 15), pady=(0, 15))

        self.content_title = ctk.CTkLabel(
            content_frame,
            text="Bienvenue dans l'aide",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.content_title.pack(fill="x", padx=15, pady=(15, 10))

        self.content_text = ctk.CTkTextbox(
            content_frame,
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        self.content_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Message de bienvenue
        self.content_text.insert("1.0", """
Bienvenue dans l'aide de MorphoLapse !

Sélectionnez un sujet dans la liste à gauche pour afficher son contenu.

Vous pouvez également:
• Utiliser la barre de recherche pour trouver un sujet
• Appuyer sur F1 n'importe où pour ouvrir cette aide
• Survoler les options pour voir les tooltips

Bonne utilisation !
        """)
        self.content_text.configure(state="disabled")

        # Bind Escape
        self.window.bind("<Escape>", lambda e: self._close())
        self.window.protocol("WM_DELETE_WINDOW", self._close)

    def select_topic(self, topic: HelpTopic):
        """Affiche un sujet"""
        # Mettre à jour le titre
        self.content_title.configure(text=topic.title)

        # Mettre à jour le contenu
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", topic.content.strip())
        self.content_text.configure(state="disabled")

        # Highlight le bouton sélectionné
        for tid, btn in self.topic_buttons.items():
            if tid == topic.id:
                btn.configure(fg_color=("gray75", "gray35"))
            else:
                btn.configure(fg_color="transparent")

    def _on_search(self, event=None):
        """Gère la recherche"""
        query = self.search_entry.get().strip()
        if len(query) < 2:
            return

        results = self.help_system.search(query)
        if results:
            self.select_topic(results[0])

    def _close(self):
        """Ferme la fenêtre"""
        if self.window:
            self.window.destroy()
            self.window = None
