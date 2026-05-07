# Phase 1 — Inventaire & cartographie

> Branche : `audit/20260429`
> État de départ : 17 commits Phases A-G déjà livrés (cf. log git)

---

## Arborescence (sources `.py` uniquement)

```
.
├── main.py                                  # 67 LOC   point d'entrée GUI + --cli
├── build.py                                 # 156 LOC  build PyInstaller (debug/release)
├── src/
│   ├── __init__.py                          # __version__ = "2.0.0"
│   ├── core/                                # ⬇ moteurs purs (sans dépendance UI)
│   │   ├── __init__.py
│   │   ├── face_aligner.py                  # 240 LOC  Procrustes alignment
│   │   ├── face_detector.py                 # 287 LOC  dlib wrapper, init lazy
│   │   ├── face_morpher.py                  # 624 LOC  Delaunay + cross-dissolve
│   │   └── video_encoder.py                 # 230 LOC  FFmpeg subprocess + preset/CRF
│   ├── modules/                             # ⬇ orchestration workflow
│   │   ├── __init__.py
│   │   ├── step_align.py                    # 154 LOC
│   │   ├── step_export.py                   # 146 LOC
│   │   ├── step_import.py                   # 230 LOC
│   │   ├── step_morph.py                    # 392 LOC
│   │   └── workflow_manager.py              # 372 LOC
│   ├── ui/                                  # ⬇ IHM customtkinter
│   │   ├── __init__.py
│   │   ├── main_window.py                   # 681 LOC
│   │   └── widgets.py                       # 595 LOC
│   └── utils/                               # ⬇ helpers
│       ├── __init__.py
│       ├── config_manager.py                # 333 LOC  dataclass-based JSON config
│       ├── file_utils.py                    # 296 LOC
│       ├── image_utils.py                   # 311 LOC
│       ├── logger.py                        # 275 LOC  singleton + callbacks
│       ├── paths.py                         # 24 LOC   resource resolution (frozen)
│       └── splash_screen.py                 # 175 LOC
├── tests/
│   ├── __init__.py
│   ├── conftest.py                          # fixtures partagées
│   ├── test_core.py                         # 10 tests (existant pré-audit)
│   ├── test_smoke.py                        # 15 tests (Phase C)
│   └── test_golden.py                       # 11 tests (Phase C/E)
├── _archive/                                # quarantaine (orphelins)
│   ├── README.md
│   ├── export_manager.py                    # 666 LOC
│   └── validators.py                        # 612 LOC
├── assets/
│   ├── icons/icone.ico
│   └── shape_predictor_68_face_landmarks.dat (95 MB, gitignored)
├── config/config.json                       # config utilisateur runtime
├── pyproject.toml
├── requirements.txt
├── README.md
└── .github/workflows/{ci,release}.yml
```

**Total `.py` actifs (hors `_archive/`, `tests/`)** : 23 fichiers — ~5 200 LOC

---

## Point d'entrée

| Item | Valeur |
|---|---|
| Source | `main.py` |
| Console script (pip-install) | `morpholapse = main:main` (`pyproject.toml`) |
| Mode GUI | `python main.py` (default) → `src.ui.main_window.run_app()` |
| Mode CLI | `python main.py --cli <input> [-o <output>]` → exécute le workflow sans UI |
| AppUserModelID Windows | `morpholapse.facemorphing.app.2.0` posé avant toute fenêtre |

---

## Cartographie des panneaux UI

L'app a **une seule fenêtre principale** (pas de multi-onglets). Layout 3 colonnes :

| Zone | Composants | Module |
|---|---|---|
| **Sidebar gauche** | logo+version · sélecteurs dossier source / image référence / dossier sortie · workflow steps (4 × StepIndicator) · boutons Lancer / Stop | `main_window._create_sidebar` |
| **Zone centrale** | QuickActions toolbar (📂 open, 💾 save) · ImagePreview ×2 (first / last image) · stats label · ProgressBar globale · LogViewer | `main_window._create_main_area` |
| **Sidebar droite** | OptionsPanel scrollable : 5 sections repliables (Video / Morphing / Alignement / Detection / Workflow / Export) | `main_window._create_options_panel` + `widgets.OptionsPanel` |
| **Splash** | écran de chargement avec progression 5 étapes (sans sleep artificiel après commit 13) | `utils.splash_screen.SplashScreen` |

---

## Matrice de couverture (Panneau × Fonctionnalité × Statut)

> Toutes les anomalies bloquantes/cassées initiales (Phase B audit) ont été corrigées en Phase E. État au commit `0dffea0` :

### Sidebar gauche (sélecteurs + workflow + actions)

| Fonctionnalité | Module / fonction | Statut |
|---|---|---|
| Title / version sidebar | `main_window:97-105` (`f"v{MORPHOLAPSE_VERSION} ..."`) | ✅ OK |
| Sélecteur dossier source | `_select_input_dir` | ✅ OK |
| Sélecteur image référence | `_select_reference` | ✅ OK |
| Sélecteur dossier sortie | `_select_output_dir` | ✅ OK |
| Aperçu first/last image | `_update_previews` + `widgets.ImagePreview.set_image` | ✅ OK |
| Stats label (X images, ref, sortie) | `_update_previews` | ✅ OK |
| Step indicator × 4 | `widgets.StepIndicator` × {Import, Align, Morph, Export} | ✅ OK |
| Step toggle (checkbox) | `_on_step_toggle` → `WorkflowManager.enable_step` | ✅ OK |
| Bouton ▶️ Lancer | `_run_workflow` (threading.Thread daemon) | ✅ OK |
| Bouton ⏹️ Stop | `_stop_workflow` → `WorkflowManager.stop()` | ✅ OK |

### Zone centrale (toolbar + previews + progression + logs)

| Fonctionnalité | Module / fonction | Statut |
|---|---|---|
| QuickActions 📂 (open) | `widgets.QuickActions.ACTIONS` → `_on_quick_action("open")` → `_select_input_dir` | ✅ OK |
| QuickActions 💾 (save) | idem → `_save_settings` | ✅ OK |
| ProgressBar globale | `_on_progress` via `self.after(0, ...)` thread-safe | ✅ OK |
| Status label "Prêt"/"En cours" | `_on_progress`, `_on_step_start`, `_on_step_complete` | ✅ OK |
| LogViewer (textbox + tags couleur) | `widgets.LogViewer` + Logger callback `add_callback` | ✅ OK |
| LogViewer Effacer | `LogViewer.clear` | ✅ OK |
| LogViewer Export | `LogViewer._export_logs` | ⚠️ pas de log d'erreur écriture (mineur) |
| LogViewer level dropdown | `LogViewer.log` filtre par level | ✅ OK |

### Sidebar droite (OptionsPanel)

| Section | Options exposées | Statut |
|---|---|---|
| **Video** | fps (slider 10-60) · video_quality (FR↔EN dropdown) · resolution (Original/1080p/720p/480p) | ✅ OK |
| **Morphing** | transition_duration (slider 0.5-10) · pause_duration (slider 0-5) · easing (FR↔EN) · blend_mode (UI↔backend) | ✅ OK |
| **Alignement** | border_size (slider 0-100) · overlay_mode (checkbox) | ✅ OK |
| **Detection** | retry_detection (slider 1-5, int → FaceDetector.max_attempts) | ✅ OK |
| **Workflow** | continue_on_error (checkbox) · debug_mode (checkbox → Logger.set_level DEBUG) | ✅ OK |
| **Export** | create_gif (checkbox) · thumbnail (checkbox) | ✅ OK |

**Options retirées** (commit 9, étaient stockées mais jamais lues par le backend) : `auto_crop`, `stabilize`, `detection_threshold`, `multi_face`, `parallel_processing`, `num_threads`, `auto_backup`, `export_frames`, `export_landmarks`, `output_format`. Documenté `_archive/README.md`.

### Splash screen

| Fonctionnalité | Statut |
|---|---|
| Affichage progression 5 étapes | ✅ OK |
| Disparition après MainWindow init | ✅ OK |
| Aucun sleep artificiel | ✅ OK (commit 13) |

### Workflow backend (cœur métier)

| Étape | Module | Statut |
|---|---|---|
| Import + validation magic-bytes | `step_import.validate_image_file` | ✅ OK |
| Alignment Procrustes | `step_align` + `core.face_aligner` | ✅ OK |
| Morphing Delaunay + encoding | `step_morph` + `core.face_morpher` + `core.video_encoder` | ✅ OK |
| Export final + summary JSON | `step_export` (version centralisée) | ✅ OK |

**Synthèse :** **0 ligne ❌ Cassé · 0 ligne 🔲 Manquant · 1 ligne ⚠️ Partiel** (LogViewer export sans log) · **45+ lignes ✅ OK**.

---

## Dépendances

### Runtime (`pyproject.toml [project] dependencies`)

| Paquet | Version min | Rôle |
|---|---|---|
| customtkinter | ≥ 5.2.0 | IHM principale |
| opencv-python | ≥ 4.8.0 | I/O image, redimensionnement, dessin |
| numpy | ≥ 1.24.0 | base de tous les arrays image/landmarks |
| scipy | ≥ 1.11.0 | `scipy.spatial.Delaunay` (triangulation morphing) |
| Pillow | ≥ 10.0.0 | aperçus UI (CTkImage), EXIF |
| dlib | ≥ 19.24.0 | détection visage + 68 landmarks |

**Externe non-Python :** FFmpeg (vérifié runtime via `subprocess`, pas embarqué).

### Dev (`[project.optional-dependencies] dev`)

| Paquet | Rôle |
|---|---|
| pytest | tests |
| pytest-cov | couverture |
| ruff | linting + formatage |
| build | wheel |
| pyinstaller | packaging EXE |

### Versions installées dans cet environnement

```
Python 3.11.9 · cv2 4.13.0 · numpy 2.4.4 · scipy 1.17.1 · dlib 20.0.1
customtkinter 5.2.2 · PIL 12.2.0 · pytest 9.0.3 · pyinstaller 7.1.0
mypy / vulture / bandit installés
```

---

## Reprise dans le pipeline

L'inventaire confirme que la matrice de couverture est déjà à `0 cassé / 0 manquant`. La Phase 2 (analyse statique) doit donc se concentrer sur la qualité du code (typage, dead-code, sécurité), pas sur la complétude fonctionnelle.
