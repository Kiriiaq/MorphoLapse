# RAPPORT_PHASE_B — Cartographie MorphoLapse

> Branche : `audit/20260429` · État : working tree dirty (transition main_app→main)
> Périmètre : tous fichiers `src/`, `main.py`, `build.py`, `pyproject.toml`, `.github/workflows/`
> Note : `INVENTAIRE.xlsx` du prompt fourni en CSV (`INVENTAIRE.csv`) — la génération `.xlsx` est différée à Phase E (nécessite `openpyxl` à valider en runtime).

---

## B.1 — Statique

### Stack identifiée

| Item | Valeur |
|---|---|
| Langage | Python ≥ 3.10 (pyproject) ; CI tourne en 3.11 |
| OS cible | Windows 10/11 (pyproject classifier ; `iconbitmap` Windows-only ; `os.startfile` utilisé) |
| Encodage fichiers | UTF-8 (avec warning git LF/CRLF sur 4 fichiers) |
| Framework UI | customtkinter (≥5.2) + tkinter/ttk (splash) — singleton tkinter app |
| Dépendances runtime | customtkinter, opencv-python, numpy, scipy, Pillow, dlib (6 paquets) |
| Dépendance externe | FFmpeg (binaire, vérifié runtime via `subprocess`) |
| Modèle externe | `shape_predictor_68_face_landmarks.dat` (~99 MB, hors git, recherché à 3 emplacements) |

### Arborescence annotée

```
.
├── main.py                       # ⚠️ entry-point (untracked — remplace main_app.py supprimé)
├── build.py                      # ⚠️ modifié — VERSION="1.0.0" obsolète, icône "assets/icons/icone.ico"
├── pyproject.toml                # ⚠️ modifié — entry-point pointe encore main_app:main (cassé)
├── requirements.txt              # OK (mais redondant avec pyproject [project] deps)
├── README.md                     # ⚠️ doc obsolète (main_app.py + ico/ + help_system + keyboard_manager)
├── RELEASE_1.0.0.md              # untracked, version 1.0.0 (incohérent)
├── LICENSE                       # OK (MIT)
├── .gitignore                    # OK (couvre venv, *.exe, *.dat, .env, *.pem, *.key, .claude)
├── .github/
│   ├── FUNDING.yml
│   └── workflows/
│       ├── ci.yml                # ⚠️ pip install -e ".[dev]" → fail (entry-point cassé)
│       └── release.yml           # ⚠️ référence main_app.py + ico/icone.ico (cassé ×4)
├── config/
│   └── config.json               # untracked — état d'options 2.0.0
├── assets/
│   ├── icons/icone.ico           # untracked (déplacé depuis ico/ supprimé)
│   └── shape_predictor_68_face_landmarks.dat   # 95 MB, gitignored, runtime
├── ico/                          # SUPPRIMÉ (déplacé vers assets/icons/)
├── logs/                         # 4 fichiers de log historiques (gitignored)
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── face_detector.py      # 286 LOC — dlib wrapper, init lazy, robuste
│   │   ├── face_aligner.py       # 240 LOC — Procrustes alignment
│   │   ├── face_morpher.py       # 607 LOC — Delaunay + cross-dissolve, bibliothèque pure
│   │   └── video_encoder.py      # 197 LOC — FFmpeg via subprocess (frames sur disque)
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── workflow_manager.py   # 365 LOC — orchestration steps, 5× except:pass muets
│   │   ├── step_import.py        # ⚠️ modifié — validation magic-bytes images
│   │   ├── step_align.py         # 151 LOC — utilise FaceDetector + FaceAligner
│   │   ├── step_morph.py         # 420 LOC — boucle morph+encode, ⚠️ quality_map non câblé
│   │   └── step_export.py        # 151 LOC — copie vidéo + summary JSON, version hardcodée "2.0.0"
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py        # ⚠️ modifié — 712 LOC, charge ico/icone.ico (cassé), 22 options
│   │   ├── widgets.py            # 666 LOC — ToolTip/CollapsibleSection/StepIndicator/LogViewer/OptionsPanel/ImagePreview/QuickActions
│   │   ├── help_system.py        # SUPPRIMÉ (jamais importé — orphelin retiré)
│   │   └── keyboard_manager.py   # SUPPRIMÉ (jamais importé — orphelin retiré)
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # 278 LOC — singleton, callbacks UI thread-safe
│       ├── config_manager.py     # 319 LOC — dataclass-based, dot-notation get/set, JSON persist
│       ├── validators.py         # ⚠️ modifié — 612 LOC, ValidationLevel + WorkflowValidator + read_file_with_encoding_fallback
│       ├── export_manager.py     # 👻 ORPHELIN — 666 LOC, dépend openpyxl/reportlab (NON déclarés)
│       ├── file_utils.py         # 291 LOC — listing, EXIF rename, padding numérique
│       ├── image_utils.py        # 320 LOC — load/save/resize/blend (cv2 + PIL)
│       └── splash_screen.py      # untracked — 176 LOC, splash tkinter avec progress
└── tests/
    ├── __init__.py
    └── test_core.py              # 127 LOC — unittest, 4 classes, ~10 tests imports + boundary
```

### Volumétrie LOC top 20

```
712  src/ui/main_window.py
666  src/ui/widgets.py
666  src/utils/export_manager.py     ← orphelin
612  src/utils/validators.py
607  src/core/face_morpher.py
420  src/modules/step_morph.py
365  src/modules/workflow_manager.py
319  src/utils/config_manager.py
320  src/utils/image_utils.py
291  src/utils/file_utils.py
286  src/core/face_detector.py
278  src/utils/logger.py
251  main.py
243  src/modules/step_import.py
240  src/core/face_aligner.py
197  src/core/video_encoder.py
176  src/utils/splash_screen.py
151  src/modules/step_align.py
151  src/modules/step_export.py
133  build.py
```

### Graphe de dépendances internes (texte)

```
main.py
 ├─→ src.ui.main_window.run_app
 │    └─→ src.ui.main_window.MainWindow (CTk)
 │         ├─→ src.ui.widgets.{ToolTip, StepIndicator, LogViewer, OptionsPanel, ImagePreview, QuickActions, CollapsibleSection}
 │         ├─→ src.utils.logger.{Logger, LogLevel, LogEntry}
 │         ├─→ src.utils.config_manager.ConfigManager
 │         ├─→ src.utils.file_utils.FileUtils  (via _update_previews)
 │         ├─→ src.utils.splash_screen.SplashScreen
 │         └─→ src.modules.workflow_manager.{WorkflowManager, WorkflowStep, StepStatus}
 │              ├─→ src.modules.step_import.ImportStep
 │              │    └─→ src.utils.{file_utils.FileUtils, image_utils.ImageUtils}
 │              ├─→ src.modules.step_align.AlignStep
 │              │    └─→ src.core.{face_detector.FaceDetector, face_aligner.FaceAligner}, src.utils.{file_utils, image_utils}
 │              ├─→ src.modules.step_morph.MorphStep
 │              │    └─→ src.core.{face_detector, face_morpher.{FaceMorpher,MorphConfig,EasingFunction,BlendMode}, video_encoder.VideoEncoder}
 │              │         + image_utils
 │              └─→ src.modules.step_export.ExportStep
 │                   └─→ src.utils.file_utils
 └─→ (CLI) imports identiques sans src.ui.*

ORPHELINS (importés par personne) :
 - src.utils.export_manager (666 LOC) — auto-référencé seulement
 - src.utils.validators.{InputValidator, WorkflowValidator, read_file_with_encoding_fallback} (612 LOC) — IMPORT NUL : aucun fichier ne les importe (à confirmer dynamiquement)
```

**Hubs trop centraux :** `workflow_manager.py` (orchestrateur, attendu) ; `image_utils.py` (utilisé par 4 modules, attendu) ; `config_manager.py` (lu par main_window mais aussi indirectement via context.config dans tous les steps).

**Modules orphelins confirmés statiquement :**
1. `src/utils/export_manager.py` — 666 LOC. Aucun import. Dépend de `openpyxl` et `reportlab` non déclarés runtime. **À archiver Phase E.**
2. `src/utils/validators.py` — 612 LOC, classes `InputValidator`, `WorkflowValidator`, fonction `read_file_with_encoding_fallback`. **Aucun import dans le reste du code** — confirmé par grep. La validation est en réalité refaite ad-hoc dans `step_import.validate_image_file` et `_run_workflow` (juste `if not self.input_dir.get()`). **Module entier orphelin malgré sa qualité.**

---

## B.2 — Dynamique (analyse statique-substitut)

> Note : trace runtime via `python main.py` non exécutée car (a) le GUI tkinter ne termine pas, (b) le bug ico/ silencieux ne se manifeste pas comme crash. Trace dérivée du graphe statique + test suite ; sera complétée par smoke launch en Phase C.

**Imports chargés au démarrage GUI (chaîne `main → main_window.run_app → MainWindow.__init__`) :**
- stdlib : `sys`, `os`, `argparse`, `ctypes`, `threading`, `time`, `logging`, `json`, `re`, `shutil`, `subprocess`, `pathlib`, `enum`, `dataclasses`, `datetime`, `typing`, `queue`
- 3rd party : `customtkinter`, `tkinter` (filedialog, messagebox, ttk), `PIL` (Image, ImageTk, ExifTags)
- 1st party : tous les modules `src/` SAUF `core/face_*`, `core/video_encoder`, `step_*` (chargés lazy à `_run_workflow`)

**Imports sur action utilisateur "Lancer" :**
- `cv2`, `numpy`, `scipy.spatial`, `dlib`, gc
- `src.core.face_detector`, `src.core.face_aligner`, `src.core.face_morpher`, `src.core.video_encoder`
- `src.modules.step_import.validate_image_file` (et magic bytes)

**Modules JAMAIS chargés (orphelins runtime) :**
- `src.utils.export_manager` — 0 import path
- `src.utils.validators` — 0 import path (sauf si tests le couvrent — non, test_core.py teste les modules core uniquement)
- `src.ui.help_system`, `src.ui.keyboard_manager` — supprimés (déjà retirés du disque)

**Profil démarrage estimé :** initialisation lourde via splash (4× `time.sleep(0.1)` = 400 ms artificiels) + import customtkinter (~150-300 ms). FaceDetector NON initialisé au démarrage (bien — initialisation déférée à `_run_workflow`).

**Warnings runtime attendus :**
- `iconbitmap` silencieusement no-op à cause du chemin `ico/` cassé → icône fenêtre absente
- `LF will be replaced by CRLF` git warnings (ne concerne pas runtime)

---

## B.3 — Matrice UI → Backend

> Légende : ✅ OK · ⚠️ PARTIEL (option stockée mais non consommée par backend) · ❌ CASSÉ (mismatch valeurs FR/EN, type, ou crash) · 🔲 ABSENT (widget sans handler) · 👻 ORPHELIN (logique sans widget appelant)

### Matrice complète (50+ widgets)

| ID UI | Fichier:ligne UI | Label / Type | Callback | Fonction backend | Fichier:ligne backend | Statut | Note |
|---|---|---|---|---|---|---|---|
| **WINDOW_INIT** | main_window.py:29 | Title `"MorphoLapse 2.0"` | — | — | — | ⚠️ | manque `PROJECT_VERSION`+`TAGLINE` (`MorphoLapse 2.0.0 - Face Morphing & Time-Lapse Generator`) |
| **WINDOW_ICON** | main_window.py:40 | iconbitmap `ico/icone.ico` | os.path.join | (chemin obsolète) | (file deleted) | ❌ | Pointe vers `ico/` supprimé. `iconbitmap` no-op silencieux. À pointer `assets/icons/icone.ico` |
| **APP_USER_MODEL_ID** | main.py:27 | `morpholapse.facemorphing.app.2.0` | ctypes shell32 | — | — | ✅ | Bien posé pour l'icône barre des tâches (mais l'icône fenêtre cassée annule l'effet visuel) |
| **ENTRY_INPUT_DIR** | main_window.py:122 | textvariable `input_dir` (StringVar) | _select_input_dir | filedialog.askdirectory + _update_previews | main_window.py:467 | ✅ | OK |
| **BTN_INPUT_DIR** | main_window.py:207 | bouton `"..."` | _select_input_dir | idem | main_window.py:467 | ✅ | OK |
| **ENTRY_REFERENCE** | main_window.py:128 | textvariable `reference_image` | _select_reference | filedialog.askopenfilename | main_window.py:475 | ✅ | OK |
| **BTN_REFERENCE** | main_window.py:207 | bouton `"..."` | _select_reference | idem | main_window.py:475 | ✅ | OK |
| **ENTRY_OUTPUT_DIR** | main_window.py:134 | textvariable `output_dir` | _select_output_dir | filedialog.askdirectory | main_window.py:485 | ✅ | OK |
| **BTN_OUTPUT_DIR** | main_window.py:207 | bouton `"..."` | _select_output_dir | idem | main_window.py:485 | ✅ | OK |
| **BTN_RUN** | main_window.py:163 | `"▶️ Lancer"` | _run_workflow | WorkflowManager.run dans thread | main_window.py:539, workflow_manager.py:165 | ✅ | OK (threading propre, callbacks via `after`) |
| **BTN_STOP** | main_window.py:173 | `"⏹️ Stop"` | _stop_workflow | WorkflowManager.stop | main_window.py:606, workflow_manager.py:275 | ✅ | OK |
| **BTN_SAVE** | main_window.py:307 | `"💾 Sauver"` | _save_settings | ConfigManager.set ×24 + save | main_window.py:410 | ✅ | OK |
| **BTN_RESET** | main_window.py:315 | `"↺ Reset"` | _reset_settings | ConfigManager.reset_to_defaults + _load_last_settings | main_window.py:458 | ✅ | OK (avec confirmation messagebox) |
| **STEP_IND_01_import** | main_window.py:351 | StepIndicator + checkbox | _on_step_toggle | WorkflowManager.enable_step | main_window.py:532, workflow_manager.py:113 | ✅ | OK |
| **STEP_IND_02_align** | main_window.py:351 | StepIndicator + checkbox | _on_step_toggle | idem | idem | ✅ | OK |
| **STEP_IND_03_morph** | main_window.py:351 | StepIndicator + checkbox | _on_step_toggle | idem | idem | ✅ | OK |
| **STEP_IND_04_export** | main_window.py:351 | StepIndicator + checkbox | _on_step_toggle | idem | idem | ✅ | OK |
| **QA_OPEN** | widgets.py:642 (`📂 open`) | bouton toolbar | _on_quick_action("open") | _select_input_dir | main_window.py:514 | ✅ | OK |
| **QA_SAVE** | widgets.py:643 (`💾 save`) | bouton toolbar | _on_quick_action("save") | _save_settings | main_window.py:516 | ✅ | OK |
| **QA_RESET** | widgets.py:644 (`🔄 reset`) | bouton toolbar | _on_quick_action("reset") | — | (aucun handler) | ❌ | Action `"reset"` émise mais `_on_quick_action` ne la traite pas → bouton inerte |
| **QA_HELP** | widgets.py:645 (`❓ help`) | bouton toolbar | _on_quick_action("help") | — | (aucun handler) | ❌ | Idem `help` non traité → bouton inerte (correspondait probablement à `help_system.py` supprimé) |
| **QA_EXPORT** | (jamais émis) | — | — | _on_quick_action("export") branche | main_window.py:518 | 👻 | handler `"export"` orphelin (renvoie à `_run_workflow`) |
| **QA_CLEAR** | (jamais émis) | — | — | _on_quick_action("clear") branche | main_window.py:520 | 👻 | handler `"clear"` orphelin (renvoie à `log_viewer.clear`) |
| **QA_SETTINGS** | (jamais émis) | — | — | _on_quick_action("settings") branche | main_window.py:522 | 👻 | handler `"settings"` orphelin (`os.startfile`) |
| **OPT_FPS** | widgets.py:351 | slider 10–60, default 25 | (slider command update_value uniquement) | morphing.fps lu dans `_run_workflow` config dict | main_window.py:557, step_morph.py:147 | ✅ | OK |
| **OPT_VIDEO_QUALITY** | widgets.py:356 | dropdown FR `["Basse","Moyenne","Haute","Maximum"]`, default `"Moyenne"` | get_options retourne FR | step_morph.py:202 `quality_map` attend `"low"/"medium"/"high"/"ultra"` | step_morph.py:202-204 | ❌ | **MISMATCH FR/EN** : la valeur FR n'est jamais dans `quality_map` → fallback `"medium"` toujours. **Bug bloquant fonctionnellement** |
| **OPT_OUTPUT_FORMAT** | widgets.py:361 | dropdown `["MP4 (H.264)","WebM (VP9)","AVI","GIF"]`, default `"MP4 (H.264)"` | get_options | aucun lecteur — `VideoEncoder.finish_encoding` hardcode `libx264` | video_encoder.py:104 | ❌ | **Format toujours MP4/H264** quel que soit le choix UI. WebM/AVI/GIF ne marchent pas. |
| **OPT_RESOLUTION** | widgets.py:366 | dropdown `["Original","1080p","720p","480p"]` | get_options | step_morph.py:184 lit `"original"`/`"Original"` (les deux casses) ; `"1080p"/"720p"/"480p"` map ✓ | step_morph.py:184-198 | ⚠️ | OK pour les 4 valeurs UI réelles, mais incohérence casse (pyproject + UI = `"Original"`, code teste les deux). Robuste mais confus |
| **OPT_TRANSITION_DURATION** | widgets.py:376 | slider 0.5–10 default 3 | — | morphing.transition_duration | step_morph.py:148 | ✅ | OK |
| **OPT_PAUSE_DURATION** | widgets.py:381 | slider 0–5 default 0 | — | morphing.pause_duration | step_morph.py:149 | ✅ | OK |
| **OPT_EASING** | widgets.py:386 | dropdown FR `["Lineaire","Ease In/Out","Ease In","Ease Out"]`, default `"Lineaire"` | get_options | step_morph.py:91 `get_easing_function` attend `"linear"/"ease_in"/"ease_out"/"ease_in_out"/"cubic"/"bounce"` | step_morph.py:91-101 | ❌ | **MISMATCH FR/EN** : retombe toujours sur `EasingFunction.LINEAR`. Les 6 courbes annoncées (README) inaccessibles via UI |
| **OPT_BLEND_MODE** | widgets.py:391 | dropdown `["Normal","Cross-dissolve","Additive"]`, default `"Normal"` | get_options | step_morph.py:104 attend `"alpha"/"additive"/"multiply"/"screen"` | step_morph.py:104-112 | ❌ | **MISMATCH** + valeurs UI ≠ valeurs documentées README. Toujours fallback `BlendMode.ALPHA` |
| **OPT_BORDER_SIZE** | widgets.py:401 | slider 0–100 | — | alignment.border_size | step_align.py:63 | ✅ | OK |
| **OPT_OVERLAY_MODE** | widgets.py:406 | checkbox | — | alignment.overlay_mode | step_align.py:64 | ✅ | OK |
| **OPT_AUTO_CROP** | widgets.py:411 | checkbox `"Recadrage auto"` | — | aucun lecteur (`alignment.auto_crop` jamais lu) | — | ⚠️ | Stocké, ignoré |
| **OPT_STABILIZE** | widgets.py:416 | checkbox `"Stabilisation"` | — | aucun lecteur | — | ⚠️ | Stocké, ignoré |
| **OPT_DETECTION_THRESHOLD** | widgets.py:428 | slider 0.1–1.0 | — | aucun lecteur (`detection.threshold` non utilisé par FaceDetector) | — | ⚠️ | Stocké, ignoré |
| **OPT_MULTI_FACE** | widgets.py:433 | dropdown `["Premier","Plus grand","Manuel"]` | — | DetectionConfig.multi_face : **bool** (ConfigManager L:74), step_morph passe `options.get('multi_face', False)` | config_manager.py:74, main_window.py:573 | ❌ | **TYPE MISMATCH** : UI string, config bool. Stockage cassé |
| **OPT_RETRY_DETECTION** | widgets.py:438 | slider 1–5 (int) | — | DetectionConfig.retry : **bool** | config_manager.py:75 | ❌ | **TYPE MISMATCH** : UI int, config bool. Stockage cassé |
| **OPT_CONTINUE_ON_ERROR** | widgets.py:448 | checkbox | — | workflow.continue_on_error → run_thread | main_window.py:601 | ✅ | OK |
| **OPT_DEBUG_MODE** | widgets.py:453 | checkbox | — | workflow.debug_mode (stocké, non consommé runtime ; main.py:158 lit ENV var `MORPHOLAPSE_DEBUG`, pas la config) | — | ⚠️ | Decouplé : ENV vs config |
| **OPT_PARALLEL_PROCESSING** | widgets.py:458 | checkbox | — | aucun parallélisme effectif dans `morph_faces` (séquentiel sur paires) | — | ⚠️ | Stocké, ignoré (pas de threadpool) |
| **OPT_NUM_THREADS** | widgets.py:463 | slider 0–16 | — | aucun lecteur | — | ⚠️ | Stocké, ignoré |
| **OPT_AUTO_BACKUP** | widgets.py:468 | checkbox | — | aucun lecteur | — | ⚠️ | Stocké, ignoré |
| **OPT_EXPORT_FRAMES** | widgets.py:480 | checkbox | — | step_export.py ne lit pas `export_frames` (n'exporte que vidéo + JSON + 2 images-clés + metadata) | step_export.py | ⚠️ | Stocké, ignoré |
| **OPT_EXPORT_LANDMARKS** | widgets.py:485 | checkbox | — | aucun lecteur | — | ⚠️ | Stocké, ignoré |
| **OPT_CREATE_GIF** | widgets.py:490 | checkbox | — | step_morph.create_gif_from_video | step_morph.py:316 | ✅ | OK |
| **OPT_THUMBNAIL** | widgets.py:495 | checkbox default true | — | step_morph.create_thumbnail | step_morph.py:363 | ✅ | OK |
| **LOG_LEVEL_FILTER** | widgets.py:280 | OptionMenu `["DEBUG","INFO","WARNING","ERROR"]` | (filtre dans `log()`) | LogViewer.log filtrage par level | widgets.py:301 | ✅ | OK |
| **LOG_BTN_CLEAR** | widgets.py:270 | bouton `"Effacer"` | LogViewer.clear | textbox.delete | widgets.py:320 | ✅ | OK |
| **LOG_BTN_EXPORT** | widgets.py:275 | bouton `"Export"` | LogViewer._export_logs | filedialog.asksaveasfilename + open(..., 'w') | widgets.py:326 | ⚠️ | OK fonctionnel mais aucune validation chemin/erreur écriture (silencieux si fail) |
| **PREVIEW_FIRST** | main_window.py:262 | ImagePreview | _update_previews | FileUtils.get_image_files + Image.open | main_window.py:492, widgets.py:610 | ✅ | OK (avec `try/except Exception` silencieux mineur) |
| **PREVIEW_LAST** | main_window.py:270 | ImagePreview | idem | idem | idem | ✅ | OK |
| **STATS_LABEL** | main_window.py:246 | CTkLabel `"X images \| Réf: ... \| Sortie: ..."` | _update_previews | calcul direct | main_window.py:506 | ✅ | OK |
| **GLOBAL_PROGRESS_BAR** | main_window.py:292 | CTkProgressBar | callbacks workflow | _on_progress | main_window.py:638 | ✅ | OK (mis à jour via `after()`) |
| **GLOBAL_PROGRESS_LABEL** | main_window.py:285 | CTkLabel "Prêt"/"En cours: X" | callbacks | idem | main_window.py:617 | ✅ | OK |
| **OPTIONS_PANEL_SECTIONS** | widgets.py:347 | 6× CollapsibleSection (Video, Morphing, Alignement, Detection, Workflow, Export) | _toggle | toggle pack/forget | widgets.py:132 | ✅ | OK ; mais clic sur badge "NEW" ne toggle pas (mineur) |

### Synthèse statuts (50 lignes principales)

| Statut | Nombre | % |
|---|---|---|
| ✅ OK | 28 | 56 % |
| ⚠️ PARTIEL (stocké, non consommé) | 11 | 22 % |
| ❌ CASSÉ (mismatch FR/EN ou type) | 6 | 12 % |
| 🔲 ABSENT | 0 | 0 % |
| 👻 ORPHELIN (handler sans bouton) | 3 | 6 % |
| Anomalies cosmétiques (titre fenêtre, casse `Original`) | 2 | 4 % |

**6 widgets ❌ cassés (priorité bloquante Phase E) :**
1. `OPT_VIDEO_QUALITY` — dropdown FR ne mappe pas `quality_map` EN
2. `OPT_OUTPUT_FORMAT` — choix UI ignoré, hardcode H264
3. `OPT_EASING` — dropdown FR ne mappe pas (6 courbes annoncées indispo)
4. `OPT_BLEND_MODE` — dropdown UI ne mappe pas valeurs backend (4 modes annoncés indispo)
5. `OPT_MULTI_FACE` — dropdown string vs config bool
6. `OPT_RETRY_DETECTION` — slider int vs config bool
+ `WINDOW_ICON` (chemin cassé) et `QA_RESET`/`QA_HELP` (boutons inertes).

**11 widgets ⚠️ partiels :** options stockées dans `config.json` au save mais jamais utilisées par le code métier. Doit être **supprimées de l'UI** OU **câblées correctement**. Décision Phase D.

**3 handlers 👻 orphelins** (`export/clear/settings`) → branches mortes dans `_on_quick_action`.

---

## Anomalies transverses (hors matrice)

### A. Code mort confirmé
- `src/utils/export_manager.py` — 666 LOC, dépend `openpyxl`/`reportlab` non déclarés. Aucun import. **À archiver Phase E.**
- `src/utils/validators.py::InputValidator` — 612 LOC, classes complètes jamais importées. La validation est refaite ad-hoc dans `step_import.py`. **À archiver OU à intégrer Phase E.**
- 5 handlers `_on_quick_action("export"/"clear"/"settings"/"reset"/"help")` orphelins (3 sans émetteur, 2 émetteurs sans handler)

### B. Mismatchs version
- pyproject.toml = 2.0.0 ✓
- main.py header = 2.0.0 ✓
- main_window.py title = "MorphoLapse 2.0" (manque .0)
- config_manager AppConfig.version = "2.0.0" ✓
- step_export.py:97 metadata = `"version": "2.0.0"` (hardcodé)
- **build.py:18 VERSION = "1.0.0"** ❌
- **RELEASE_1.0.0.md** ❌
- git tag = `v2.0.0` ✓

### C. Mismatchs entry-point (main_app.py)
- pyproject.toml `[project.scripts] morpholapse = "main_app:main"` ❌
- pyproject.toml `[tool.setuptools] py-modules = ["main_app"]` ❌
- .github/workflows/release.yml:44, 67 ❌
- main.py docstring + epilog (cosmétique mais incohérent)
- README.md ×6

### D. Mismatchs icône (ico/icone.ico)
- src/ui/main_window.py:40 ❌ (chargement runtime no-op silencieux)
- .github/workflows/release.yml:29, 52 ❌
- README.md:244, 248 ❌
- build.py:18 → utilise `assets/icons/icone.ico` ✓

### E. Patterns d'erreur silencieuse
- `workflow_manager.py:222, 316, 322, 328, 334` — 5× `except Exception: pass` dans wrappers callbacks. Une erreur dans un callback UI ne sera ni loguée ni propagée → bugs invisibles
- `face_detector.py:91-98` — `except ImportError` retourne False, mais `except Exception` log+False masque les vraies causes
- `widgets.py:621-623 ImagePreview.set_image` — `except Exception` → "Erreur" générique sans log
- `image_utils.py:34, 59` — `try/except Exception: return None/False` muet
- `file_utils.py:137-138 get_exif_date` — `except: pass` muet

### F. Bug fonctionnel : qualité vidéo non transmise
`VideoEncoder.start_encoding(quality='medium')` reçoit le preset, mais `finish_encoding` hardcode :
```python
'-preset', 'fast', '-crf', '23'
```
→ Le paramètre `quality` est complètement ignoré. **Bug livré dans la version actuelle.**

### G. Bugs mineurs UI
- Splash : `time.sleep(0.1)` ×4 en main thread = 400 ms artificiels (UX dégradée pour rien)
- LogViewer : pas de scroll-lock (auto-scroll permanent — gênant si l'utilisateur veut lire)
- ImagePreview.set_image : `Image.open` non contextualisé (fichier non fermé sur retour normal — léger leak)
- OptionsPanel : labels FR mais les clés internes (`'fps'`, `'video_quality'`, ...) sont en anglais → inconsistance mais pas un bug

### H. Sécurité / stabilité
- ✅ Aucun secret hardcodé
- ✅ Pas d'eval/exec dynamique
- ⚠️ `subprocess.run(['ffmpeg', ...])` sans `shell=True` (bien) mais sans validation des chemins de sortie — chemin attaquant possible si `output_path` contient des caractères malicieux. Faible risque (input vient du UI utilisateur, pas réseau)
- ⚠️ `os.startfile(...)` (main_window.py:526) sur dossier de config — Windows-only, pas de fallback

---

## Décisions de Phase D anticipées

Pour chaque widget ⚠️/❌ : décision implicite à confirmer en D :
- **OPT_AUTO_CROP, STABILIZE, DETECTION_THRESHOLD, NUM_THREADS, AUTO_BACKUP, PARALLEL_PROCESSING, EXPORT_FRAMES, EXPORT_LANDMARKS, DEBUG_MODE** : **retirer de l'UI** (ALLOW_UI_REFACTOR=NO mais "supprimer un widget visible mais inerte" est un fix bloquant, pas un refactor — à arbitrer)
- **OPT_VIDEO_QUALITY, OUTPUT_FORMAT, EASING, BLEND_MODE** : **corriger le mapping FR↔EN** (mapping table dans widgets ou normalisation au moment du `get_options`)
- **OPT_MULTI_FACE, RETRY_DETECTION** : **aligner le type** (config bool ↔ UI cohérent)
- **VideoEncoder.finish_encoding** : **honorer le preset transmis** par `start_encoding`

---

## Livrables Phase B

| Livrable | Format | Statut |
|---|---|---|
| `RAPPORT_PHASE_B.md` | Markdown | ✅ ce fichier |
| `INVENTAIRE.csv` | CSV (lisible Excel, séparateur `;`) | ✅ généré |
| `INVENTAIRE.xlsx` | Excel | ⏸️ différé Phase E (nécessite openpyxl, à valider) |
| `dependency_graph.svg` | SVG | ⏸️ différé Phase E (nécessite pydeps + graphviz) |
| `runtime_trace.json` | JSON | ⏸️ différé Phase C (smoke launch + coverage trace) |

---

## Validation attendue

Réponds avec **`OK phase B → continue`** pour passer à la Phase C (mise en place tests baseline + golden master + snapshots UI).

Ou bien indique :
- Désaccords sur le statut d'un widget (ex: si `OPT_AUTO_CROP` doit être implémenté plutôt que retiré)
- Décisions à anticiper pour Phase D/E (ex: pour les 11 widgets ⚠️ : retirer ou implémenter ?)
- Si tu veux que je tente le run dynamique (`python main.py` 8s timeout) maintenant pour confirmer la trace
