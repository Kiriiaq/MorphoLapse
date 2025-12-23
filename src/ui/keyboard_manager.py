"""
Keyboard Manager - Gestionnaire de raccourcis clavier
"""

import customtkinter as ctk
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass


@dataclass
class Shortcut:
    """Définition d'un raccourci clavier"""
    key: str
    modifiers: List[str]
    description: str
    callback: Callable
    category: str = "Général"
    enabled: bool = True

    @property
    def display_key(self) -> str:
        """Retourne la représentation affichable du raccourci"""
        parts = []
        if "Control" in self.modifiers:
            parts.append("Ctrl")
        if "Alt" in self.modifiers:
            parts.append("Alt")
        if "Shift" in self.modifiers:
            parts.append("Shift")
        parts.append(self.key.upper())
        return "+".join(parts)


class KeyboardManager:
    """
    Gestionnaire centralisé des raccourcis clavier.

    Permet de:
    - Enregistrer des raccourcis avec callbacks
    - Afficher la liste des raccourcis disponibles
    - Activer/désactiver des raccourcis
    - Personnaliser les raccourcis (future)
    """

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._shortcuts: Dict[str, Shortcut] = {}
        self._enabled = True
        self._categories = set()

    def _make_binding_key(self, key: str, modifiers: List[str]) -> str:
        """Crée la clé de binding pour tkinter"""
        parts = []
        if "Control" in modifiers:
            parts.append("Control")
        if "Alt" in modifiers:
            parts.append("Alt")
        if "Shift" in modifiers:
            parts.append("Shift")
        parts.append(key.lower())
        return f"<{'-'.join(parts)}>"

    def register(
        self,
        key: str,
        callback: Callable,
        description: str,
        modifiers: Optional[List[str]] = None,
        category: str = "Général"
    ) -> bool:
        """
        Enregistre un nouveau raccourci clavier.

        Args:
            key: Touche principale (ex: 's', 'F1', 'Return')
            callback: Fonction à appeler
            description: Description du raccourci
            modifiers: Liste des modificateurs ['Control', 'Alt', 'Shift']
            category: Catégorie pour le regroupement

        Returns:
            True si l'enregistrement a réussi
        """
        modifiers = modifiers or []
        binding_key = self._make_binding_key(key, modifiers)

        if binding_key in self._shortcuts:
            return False

        shortcut = Shortcut(
            key=key,
            modifiers=modifiers,
            description=description,
            callback=callback,
            category=category
        )

        self._shortcuts[binding_key] = shortcut
        self._categories.add(category)

        # Bind à la fenêtre root
        self.root.bind(binding_key, lambda e: self._handle_shortcut(binding_key))

        return True

    def _handle_shortcut(self, binding_key: str):
        """Gère l'exécution d'un raccourci"""
        if not self._enabled:
            return

        shortcut = self._shortcuts.get(binding_key)
        if shortcut and shortcut.enabled:
            try:
                shortcut.callback()
            except Exception as e:
                print(f"Erreur raccourci {shortcut.display_key}: {e}")

    def unregister(self, key: str, modifiers: Optional[List[str]] = None) -> bool:
        """Supprime un raccourci"""
        modifiers = modifiers or []
        binding_key = self._make_binding_key(key, modifiers)

        if binding_key in self._shortcuts:
            self.root.unbind(binding_key)
            del self._shortcuts[binding_key]
            return True
        return False

    def enable(self, enabled: bool = True):
        """Active ou désactive tous les raccourcis"""
        self._enabled = enabled

    def enable_shortcut(self, key: str, modifiers: Optional[List[str]] = None, enabled: bool = True):
        """Active ou désactive un raccourci spécifique"""
        modifiers = modifiers or []
        binding_key = self._make_binding_key(key, modifiers)
        if binding_key in self._shortcuts:
            self._shortcuts[binding_key].enabled = enabled

    def get_shortcuts_by_category(self) -> Dict[str, List[Shortcut]]:
        """Retourne les raccourcis regroupés par catégorie"""
        result = {}
        for shortcut in self._shortcuts.values():
            if shortcut.category not in result:
                result[shortcut.category] = []
            result[shortcut.category].append(shortcut)
        return result

    def get_all_shortcuts(self) -> List[Shortcut]:
        """Retourne tous les raccourcis"""
        return list(self._shortcuts.values())

    def show_shortcuts_dialog(self):
        """Affiche une fenêtre avec tous les raccourcis"""
        dialog = ShortcutsDialog(self.root, self.get_shortcuts_by_category())
        dialog.show()


class ShortcutsDialog:
    """Fenêtre affichant les raccourcis clavier disponibles"""

    def __init__(self, parent: ctk.CTk, shortcuts_by_category: Dict[str, List[Shortcut]]):
        self.parent = parent
        self.shortcuts = shortcuts_by_category
        self.window: Optional[ctk.CTkToplevel] = None

    def show(self):
        """Affiche la fenêtre"""
        if self.window is not None:
            self.window.focus()
            return

        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Raccourcis clavier")
        self.window.geometry("450x500")
        self.window.transient(self.parent)

        # Titre
        ctk.CTkLabel(
            self.window,
            text="⌨️ Raccourcis clavier",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(15, 10))

        # Conteneur scrollable
        scroll_frame = ctk.CTkScrollableFrame(self.window)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Afficher par catégorie
        for category, shortcuts in sorted(self.shortcuts.items()):
            # En-tête de catégorie
            cat_frame = ctk.CTkFrame(scroll_frame, fg_color=("gray85", "gray20"))
            cat_frame.pack(fill="x", pady=(10, 5))

            ctk.CTkLabel(
                cat_frame,
                text=category,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            ).pack(fill="x", padx=10, pady=5)

            # Raccourcis de cette catégorie
            for shortcut in shortcuts:
                row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)

                # Touche
                key_label = ctk.CTkLabel(
                    row,
                    text=shortcut.display_key,
                    font=ctk.CTkFont(family="Consolas", size=11),
                    fg_color=("gray80", "gray25"),
                    corner_radius=4,
                    width=100
                )
                key_label.pack(side="left", padx=(10, 10))

                # Description
                desc_label = ctk.CTkLabel(
                    row,
                    text=shortcut.description,
                    font=ctk.CTkFont(size=11),
                    anchor="w"
                )
                desc_label.pack(side="left", fill="x", expand=True)

                # Indicateur activé/désactivé
                if not shortcut.enabled:
                    status = ctk.CTkLabel(
                        row,
                        text="(désactivé)",
                        font=ctk.CTkFont(size=10),
                        text_color="gray"
                    )
                    status.pack(side="right", padx=10)

        # Bouton fermer
        ctk.CTkButton(
            self.window,
            text="Fermer",
            width=100,
            command=self._close
        ).pack(pady=15)

        # Bind Escape pour fermer
        self.window.bind("<Escape>", lambda e: self._close())

    def _close(self):
        """Ferme la fenêtre"""
        if self.window:
            self.window.destroy()
            self.window = None


def setup_default_shortcuts(keyboard: KeyboardManager, app) -> KeyboardManager:
    """
    Configure les raccourcis par défaut pour l'application.

    Args:
        keyboard: Instance du KeyboardManager
        app: Instance de l'application (MainWindow)

    Returns:
        KeyboardManager configuré
    """
    # === Fichiers ===
    keyboard.register(
        key="o", modifiers=["Control"],
        callback=app._select_input_dir,
        description="Ouvrir un dossier source",
        category="Fichiers"
    )

    keyboard.register(
        key="s", modifiers=["Control"],
        callback=app._save_settings,
        description="Sauvegarder les paramètres",
        category="Fichiers"
    )

    keyboard.register(
        key="s", modifiers=["Control", "Shift"],
        callback=lambda: app._select_output_dir(),
        description="Définir le dossier de sortie",
        category="Fichiers"
    )

    # === Workflow ===
    keyboard.register(
        key="Return", modifiers=["Control"],
        callback=app._run_workflow,
        description="Lancer le workflow",
        category="Workflow"
    )

    keyboard.register(
        key="Escape", modifiers=[],
        callback=app._stop_workflow,
        description="Arrêter le workflow",
        category="Workflow"
    )

    # === Affichage ===
    keyboard.register(
        key="l", modifiers=["Control"],
        callback=lambda: app.log_viewer.clear(),
        description="Effacer les logs",
        category="Affichage"
    )

    keyboard.register(
        key="F1", modifiers=[],
        callback=lambda: keyboard.show_shortcuts_dialog(),
        description="Afficher les raccourcis",
        category="Aide"
    )

    keyboard.register(
        key="h", modifiers=["Control"],
        callback=lambda: app._show_help() if hasattr(app, '_show_help') else None,
        description="Afficher l'aide",
        category="Aide"
    )

    # === Navigation ===
    keyboard.register(
        key="Tab", modifiers=["Control"],
        callback=lambda: app._cycle_focus(),
        description="Changer de panneau",
        category="Navigation"
    )

    return keyboard
