# Changelog

Toutes les modifications notables de MorphoLapse sont consignées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ;
versionnage [SemVer](https://semver.org/lang/fr/).

## [2.2.0] — 2026-05-27

Améliorations apportées après la 2.0.0 (la 2.1.0 historique sur le tag
`v2.1.0` est restée sur `chore: industrialize repo`, sans le polish UI
ni les correctifs FFmpeg). Regroupées par lots.

### Lot J — Synchronisation IHM ↔ modèle
- Les Entry des 3 (puis 4) sélecteurs de dossier rafraîchissent désormais le compteur d'images et les previews quand l'utilisateur tape ou colle un chemin (et plus seulement via le bouton `…`).

### Lot K — Robustesse des raccourcis
- Filtre de focus refait via `winfo_class()` (les `CTkEntry` composites étaient mal détectés).
- AZERTY : ajout des bindings `<Control-Key-ampersand>`, `<Control-Key-eacute>`, `<Control-Key-quotedbl>`, `<Control-Key-apostrophe>`, `<Control-Key-parenleft>` pour que `Ctrl+1..5` fonctionne sur claviers français sans Shift.
- Pavé numérique : `<Control-KP_End/Down/Next/Left/Begin>` ajoutés pour Num Lock OFF.

### Lot L — Feedback annulation et barre de progression
- Bouton Annuler désactivé immédiatement après clic ; label passe à « Annulation en cours… ».
- Track gris contrasté + `corner_radius=4` sur la barre globale (visible dès 0 %).

### Lot M — Contraste OptionsPanel
- Checkboxes : `border_width=2`, bordure explicite.
- Dropdowns : `fg_color`/`button_color` explicites pour ne pas se confondre avec le fond.

### Lot N — `debug_mode` appliqué au boot
- `_load_last_settings` appelle désormais `logger.set_level(...)` cohérent avec la valeur persistée. Les logs `DEBUG` apparaissent dès le démarrage sans nécessiter une re-sauvegarde.

### Défauts additionnels (DA-1..9 du pré-rapport d'audit Phase 1)
- DA-1 : filtre de focus → résolu par Lot K.
- DA-2 : Num Lock OFF → résolu par Lot K.
- DA-3 : feedback annulation → résolu par Lot L.
- DA-4 : paste manuel dans Entry → résolu par Lot J.
- DA-5 : contraste OptionsPanel → résolu par Lot M.
- DA-6 : barre invisible à 0 % → résolu par Lot L.
- DA-7 : `debug_mode` non appliqué au boot → résolu par Lot N.
- DA-8 : `_workflow_starting` non remis à False si thread tué brutalement — laissé volontairement (coût > bénéfice, scénario théorique).
- DA-9 : EXE `dist/` antérieur aux Lots A-N peut fausser une campagne — section G.6 de procédure rebuild ajoutée à la doc.

### Nouvelles fonctionnalités

- **Sélecteur CPU** au-dessus du bouton Lancer (`Auto` / `1..8` / `Max (N)`). Pilote `cv2.setNumThreads`, les variables `OMP_/OPENBLAS_/MKL_NUM_THREADS` et `ffmpeg -threads N`. Persisté dans `config.json` (`workflow.cpu_threads`).
- **Dossier frames intermédiaire** : 4ᵉ sélecteur dans la sidebar, optionnel. Permet d'écrire les frames JPEG dans `<dossier_choisi>/<timestamp>/` pour recompiler avec un outil externe.
- **Viewer HTML `preview.html`** auto-généré dans le dossier des frames : scrub avec slider, play/pause, flèches, vitesse variable, et lecteur `<video>` pour la MP4 finale après encodage.
- **Footer applicatif** : version + sélection CPU (live) + statut FFmpeg (✓ / ✗) toujours visible en bas.
- **Bloc « Chemins sélectionnés »** sous les Entry : affiche les 4 chemins courants en wrap multi-ligne, même quand l'Entry défile.
- **Validation rapide HTML** (`qa/validation_rapide.html`) : 60 tests focalisés sur les correctifs récents, OK/NOK/N/A par clic ou raccourcis O/N/A, export JSON et Markdown, persistance `localStorage`.

### Correctifs robustesse FFmpeg

- `CREATE_NO_WINDOW` ajouté à toutes les `subprocess.Popen` et `subprocess.run` sous Windows : plus de console FFmpeg parasite que l'utilisateur pouvait fermer par mégarde.
- Drainage de stderr dans un thread daemon : corrige le deadlock de pipe à ~64 KB qui figait FFmpeg autour de 98 % d'encodage.
- Timeout 1h absolu remplacé par un timeout d'inactivité (10 min sans nouvelle frame) : les longs encodages legitimes ne sont plus tués à tort.
- Snapshots de progression dans `logs/MorphoLapse_*.log` toutes les 30 s pendant l'encodage.
- `-progress pipe:1` parsé en temps réel pour afficher frame courante / total / fps / ETA dans la barre de progression UI et dans le label.
- `ffmpeg -threads N` enfin câblé au sélecteur CPU (avant, seul OpenCV/NumPy étaient pilotés).
- Frames JPEG conservées par défaut (`keep_frames=True`) après encodage réussi — permet la récupération manuelle si besoin.
- Récupération manuelle assistée : si l'encodage échoue, le log indique la commande FFmpeg exacte à relancer sur les frames intermédiaires.

### Correctifs imagerie / E/S

- `ImageUtils.load_image` / `save_image` réécrites avec `np.fromfile` + `cv2.imdecode` (et `imencode` + `tofile`) : `cv2.imread` perdait silencieusement les fichiers avec accents, esperluettes, parenthèses ou espaces combinés sous Windows. Plus de « Impossible de charger » sur des fichiers parfaitement valides.
- `ImagePreview.set_image` bypassé `CTkImage` au profit de `ImageTk.PhotoImage` avec `master` explicite : corrige le `RuntimeError: Too early to create image` quand `tkinter._default_root` pointait vers le splash détruit.

### Modèle dlib et chemins

- `get_dlib_model_path()` (déjà présent dans `src/utils/paths.py`) explicitement utilisé dans `_run_workflow` : la résolution `sys._MEIPASS / "assets" / shape_predictor_*.dat` fonctionne en EXE.

### LogViewer enrichi

- Historique interne complet (indépendant du filtre) : on peut passer de `INFO` à `WARNING` à `ERROR` en cours de session sans perdre les anciennes lignes.
- Compteur live `(N)` à côté du titre Logs.
- Export `.txt` ou `.csv` (séparateur `;`, ouvrable directement dans Excel pour tri par niveau).
- Popup de confirmation après export.

### Tooltips

- Tentatives multiples (ToolTip composite-aware avec pointer-bounds check) puis **suppression complète** des infobulles (retours utilisateur : implémentation peu fiable). Les descriptions de section (texte italique gris) restent dans l'OptionsPanel.

### Build / packaging

- 3 profils PyInstaller maintenus parallèlement : debug onedir, release onedir, release onefile.
- Modèle dlib bundlé dans `_internal/assets/` via `--add-data` et résolu via `paths.get_dlib_model_path()`.

### Réorganisation du dépôt (cette PR)

- Dossier `test/` renommé en `qa/` pour lever l'ambiguïté avec `tests/` (suite pytest).
- 15 fichiers `.md` historiques (rapports d'audit Phase A-G + v2) fusionnés dans ce `CHANGELOG.md` et la nouvelle structure de `README.md` (7 sections).
- Dossier `audit/` supprimé après absorption de son contenu.
- Nettoyage : `logs/*.log`, `tests/runs/coverage_v2/`, `tests/runs/20260429/coverage/`, `INVENTAIRE.csv`, `.coverage`, `__pycache__/` à la racine.

## [2.0.0] — 2026-04-29

Audit complet du produit (branche `audit/20260429`, 22 commits, tag rollback `pre-audit-20260429`).

### Bugs corrigés (35 numérotés)

- Icône fenêtre cassée silencieusement (`ico/icone.ico` supprimé, `iconbitmap` no-op) — helper `paths.get_icon_path()` PyInstaller-aware.
- `pyproject.toml [project.scripts]` cassé (`main_app:main` → `main:main`).
- CI `release.yml` référençait `main_app.py` + 4× `ico/icone.ico`.
- Version dispersée (1.0.0 vs 2.0.0 dans 6 endroits) → centralisée dans `src/__init__.__version__`.
- Dropdown `OPT_VIDEO_QUALITY` français (`Basse/Moyenne/Haute/Maximum`) ne mappait pas le backend → preset par défaut systématique. Idem pour `OPT_EASING` (4 labels) et `OPT_BLEND_MODE` (3 labels).
- `VideoEncoder.finish_encoding` ignorait le `quality` reçu en init.
- `DetectionConfig.retry: bool = False` vs slider int 1-5.
- 10 widgets stockés sans effet sur le backend (`auto_crop`, `stabilize`, `detection_threshold`, `multi_face`, `parallel_processing`, `num_threads`, `auto_backup`, `export_frames`, `export_landmarks`, `output_format`) — supprimés.
- `OPT_DEBUG_MODE` checkbox stockée sans effet → câblée à `Logger.set_level(DEBUG)`.
- `OPT_RESOLUTION` mismatch « Original/original » → unifié.
- QuickActions toolbar : 4 boutons / 5 handlers (orphelins des deux côtés) → `QuickActions.ACTIONS` source unique.
- `src/utils/export_manager.py` (666 LOC) + `validators.py` (612 LOC) orphelins avec dépendances non déclarées → archivés sous `_archive/` (dossier supprimé en 2.2.0).
- 13 `except Exception: pass` muets (workflow_manager ×5, image_utils ×2, file_utils ×2, config_manager ×2, widgets, logger) → tous remplacés par du logging structuré.
- 4× `time.sleep(0.1)` artificiels dans le splash → supprimés (-600 ms démarrage perçu).
- 215 erreurs `ruff` (E/F/W/B/S) + 29 fichiers à reformater → 0.
- `ImageValidationError.message` accédé mais jamais stocké.
- `MainWindow._on_step_toggle` accédait `self.workflow=None`.
- `start_encoding(codec=)` et `_create_folder_selector(is_file=)` paramètres morts.
- `face_aligner.align_to_reference` arguments `np.ndarray = None` non-Optional (mypy clean).
- `step_align.landmarks_list` sans annotation.
- `main.py` AppUserModelID try/except: pass silencieux → logging.debug.
- `LogViewer._export_logs` swallowait `OSError` → messagebox visible.

### Ajouts

- Helper `paths.get_icon_path()` et `get_dlib_model_path()` PyInstaller-aware (résolution dynamique `sys._MEIPASS` en frozen, racine projet en source).
- Mapping FR↔EN exhaustif des dropdowns dans `step_morph.py`.
- `_PRESET_TO_CRF` table + preset/CRF honorés par `VideoEncoder`.
- `retry_detection` int passé à `dlib.get_landmarks(max_attempts=)`.
- 117 tests pytest (smoke + functional + perf + stress + volume).
- Suite tests golden via `tests/fixtures/golden/`.

### Build et distribution

- 2 EXE PyInstaller à 197 MB générés et passant le smoke test (PE subsystems vérifiés : WINDOWS_GUI release, WINDOWS_CUI debug).
- `--collect-all scipy/dlib/cv2/customtkinter` pour résoudre les imports lazy.
- 17 paquets exclus (pandas, matplotlib, torch, tensorflow, etc.) → -30 % vs naïf.

### Métriques

| Métrique | Avant | Après | Delta |
|---|---|---|---|
| LOC actives `src/` | ~7 280 | ~5 200 | **-29 %** |
| Bugs ❌ utilisateur | 6 + 5 ⚠️ | 0 | **-100 %** |
| Tests | 10 | 117 | ×11.7 |
| Couverture pytest | ~36 % | 43 % | +7 pts |
| Erreurs ruff | 233 | 0 | -100 % |
| `except: pass` muets | 13 | 0 | -100 % |
| Modules orphelins | 4 | 0 | -100 % |
| Versions dispersées | 5 endroits | 1 | source unique |

## [1.0.0] — Initial

Version initiale de MorphoLapse, dérivée du projet [face-movie](https://github.com/andrewdcampbell/face-movie) d'Andrew Campbell. Interface CustomTkinter, pipeline import → align → morph → export, support FFmpeg H.264.
