# DIAGNOSTIC — Phase D MorphoLapse

> Branche : `audit/20260429`
> Source : matrice B.3 (`RAPPORT_PHASE_B.md` + `INVENTAIRE.csv`) + checks D.1–D.7 supplémentaires
> Format : 1 ligne par anomalie · `[criticité] ID — observation → correction`

**Critères de criticité :**
- **🔴 BLOQUANT** : casse une fonctionnalité visible par l'utilisateur OU le build/CI OU l'installation
- **🟠 MAJEUR** : casse une promesse documentée OU induit l'utilisateur en erreur (option qui ne fait rien)
- **🟡 MINEUR** : code mort, hardcoded, log silencieux, propreté

---

## Vérifications transverses (D.1–D.7)

| Axe | Statut | Note |
|---|---|---|
| **D.1 backend fonctionnalité** (edge cases image/dlib/ffmpeg) | ⚠️ partiel | Edge cases couverts pour fichier-absent / corrompu / trop-petit. Non couvert : EXIF orientation (cv2.imread ignore), 16-bit / alpha (cv2 force 8-bit BGR), Windows long paths, fichier verrouillé par autre process |
| **D.2 backend robustesse** (excepts, validation) | ⚠️ | 13 `except Exception: pass`/`return None` muets identifiés (cf. tableau §C ci-dessous) |
| **D.3 frontend implémentation** (commands, Vars lus) | ⚠️ | 11 widgets ⚠️ stockés non lus + 2 boutons sans handler + 3 handlers sans bouton (cf. matrice B.3) |
| **D.4 frontend UX** (threading, états boutons, erreurs visibles) | ✅ | `Thread(daemon=True)` + `after(0, ...)` partout. `run_button` + `stop_button` togglés correctement. Erreurs via `messagebox` (pas de traceback exposé). |
| **D.5 accessibilité** (clavier, raccourcis, focus, DPI) | ⚠️ minimaliste | 0 raccourcis (F1/Ctrl-O/Ctrl-S absents). 0 bind Enter/Escape sur dialogues. Tab natif customtkinter par défaut. DPI géré par CTk. Décision : **scope-out** Phase E (hors scope correctif minimal) |
| **D.6 intégration** (séparation backend/UI) | ✅ excellente | `src/core/*` n'importe ni `tkinter` ni `customtkinter`. UI ne fait pas de parsing métier. |
| **D.7 langue / messages** | ⚠️ | Mix tutoiement neutre dans backend ("Veuillez sélectionner") et "Aucun fichier trouvé" sans suggestion d'action systématique. Tracebacks `_log_error(traceback.format_exc())` dans `_run_step` → si pas filtrés, exposition technique dans le LogViewer. À réviser au cas par cas, scope-out global. |

---

## A. Anomalies BLOQUANTES (Phase E priorité 1) — 11 items

| ID matrice | Observation | Correction prévue Phase E |
|---|---|---|
| 🔴 **WINDOW_ICON** | `main_window.py:40` charge `ico/icone.ico` (chemin supprimé) → `iconbitmap` no-op silencieux, icône fenêtre absente | Pointer vers `assets/icons/icone.ico` ; centraliser le chemin dans `src/utils/paths.py` (helper `get_icon_path()` qui gère `sys._MEIPASS` pour PyInstaller frozen) |
| 🔴 **OPT_VIDEO_QUALITY** | Dropdown FR `Basse/Moyenne/Haute/Maximum` ne mappe pas `quality_map` EN | Mapper FR→EN dans `OptionsPanel._create_dropdown` via dict de résolution `_FR_TO_BACKEND_VIDEO_QUALITY` ou normaliser dans `step_morph.morph_faces:202` ; tests `_BUG` à inverser |
| 🔴 **OPT_OUTPUT_FORMAT** | UI `MP4 (H.264)/WebM (VP9)/AVI/GIF` mais `VideoEncoder.finish_encoding:104` hardcode `libx264` | Décision honnête : restreindre l'UI à `MP4 (H.264)` seul (les autres ne sont pas implémentés) ; option : implémenter WebM/AVI plus tard si nécessaire (hors scope E) |
| 🔴 **OPT_EASING** | Dropdown FR ne mappe pas `get_easing_function` → toujours `LINEAR` | Mapper FR→EN dans `step_morph.get_easing_function` (élargir le dict pour accepter les libellés UI) ; documenter les 6 courbes annoncées README |
| 🔴 **OPT_BLEND_MODE** | UI `Normal/Cross-dissolve/Additive` ≠ backend `alpha/additive/multiply/screen` → toujours `ALPHA` | Mapping `Normal→ALPHA`, `Cross-dissolve→ALPHA`, `Additive→ADDITIVE` dans `get_blend_mode` ; aligner la liste UI avec les 4 modes du backend (ajouter `Multiply`, `Screen`) |
| 🔴 **OPT_MULTI_FACE** | UI string `Premier/Plus grand/Manuel` vs `DetectionConfig.multi_face: bool` → save cassé | Décision : scope-out (multi-visages non implémenté côté FaceDetector). **Retirer le widget** ; remplacer par checkbox `Détecter multi-visages` (bool) seulement si une logique multi-faces est ajoutée. Pour Phase E : retirer le widget |
| 🔴 **OPT_RETRY_DETECTION** | Slider int (1-5) vs `DetectionConfig.retry: bool` → save cassé. `FaceDetector.get_landmarks` a un paramètre `max_attempts: int = 3` (jamais relié à la config) | Aligner type config `retry: int = 3` ET câbler `step_align.py:46` pour passer ce paramètre à `detector.get_landmarks(..., max_attempts=context.config['retry_detection'])` |
| 🔴 **VIDEO_ENCODER_QUALITY** | `VideoEncoder.start_encoding(quality=...)` ignoré : `finish_encoding:104` hardcode `-preset fast -crf 23` | Stocker `quality` dans `self._preset` à `start_encoding` ; utiliser dans `finish_encoding` ; ajouter mapping CRF par preset (low=28, medium=23, high=20, ultra=18) |
| 🔴 **PYPROJECT_ENTRY_POINT** | `[project.scripts] morpholapse = "main_app:main"` + `py-modules = ["main_app"]` mais `main_app.py` supprimé | `morpholapse = "main:main"` ; `py-modules = ["main"]` |
| 🔴 **CI_RELEASE_BROKEN** | `.github/workflows/release.yml` référence `main_app.py` (×2) et `ico/icone.ico` (×2) | Remplacer par `main.py` + `assets/icons/icone.ico` ; aligner aussi les `--add-data` (`ico` n'existe plus) ; consolider sur `python build.py` plutôt que pyinstaller inline |
| 🔴 **QA_RESET_HELP_NO_HANDLER** | Boutons `🔄 reset` et `❓ help` dans `QuickActions` émettent `_on_quick_action(reset/help)` sans handler | Décision : retirer les 2 boutons (help_system.py supprimé, reset déjà disponible via bouton sidebar). Aligner `QuickActions.actions` à `[open, save]` seulement |

---

## B. Anomalies MAJEURES (Phase E priorité 2) — 8 items

| ID matrice | Observation | Correction prévue Phase E |
|---|---|---|
| 🟠 **VERSION_MISMATCH** | `build.py:18 VERSION="1.0.0"` ; `RELEASE_1.0.0.md` ; vs pyproject 2.0.0 ; main_window title `MorphoLapse 2.0` (manque `.0`) ; `step_export.py:97` hardcoded | Source unique : créer `src/__init__.py: __version__ = "2.0.0"` (single source). `build.py` lit depuis pyproject.toml via `tomllib`. `RELEASE_1.0.0.md` → renommer `RELEASE_2.0.0.md` ou supprimer (info dupliquée avec README). `main_window.title` → `f"MorphoLapse {__version__} - Face Morphing & Time-Lapse Generator"` |
| 🟠 **REQUIREMENTS_DUPLICATE** | `requirements.txt` duplique `pyproject.toml [project] dependencies` avec versions plus laxistes | Garder pyproject canonique. `requirements.txt` → soit supprimer (pip install -e . suffit), soit auto-générer via `pip-compile` |
| 🟠 **README_OBSOLETE** | README mentionne `main_app.py` ×6, `ico/icone.ico` ×2, et `src/ui/help_system.py` + `src/ui/keyboard_manager.py` (supprimés) dans l'arbo | Mise à jour intégrale. Retirer les modules supprimés de la section Architecture |
| 🟠 **BUILD_INCOHERENT** | `build.py` (script local) et `release.yml` (CI inline) ont des choix différents (icône path, hidden-imports, modes) | Phase G : unifier sur `build.py debug` / `build.py release` ; `release.yml` appelle `python build.py release` |
| 🟠 **ORPHAN_export_manager** | `src/utils/export_manager.py` (666 LOC) jamais importé en runtime ; dépend de `openpyxl`/`reportlab` non déclarés ; ré-exposé inutilement par `__init__.py` | `ALLOW_DELETE=NO` → déplacer vers `_archive/export_manager.py` ; retirer l'import depuis `src/utils/__init__.py` |
| 🟠 **ORPHAN_validators** | `src/utils/validators.py::InputValidator/WorkflowValidator` (612 LOC) jamais importés ; validation refaite ad-hoc dans `step_import.py` | Décision : déplacer vers `_archive/validators.py` (ALLOW_DELETE=NO). Conserver `read_file_with_encoding_fallback` si vraiment utilisé. La validation dans `step_import.py` reste l'autorité. Note : possible "câblage" plutôt qu'archivage si l'utilisateur préfère intégrer ces classes en E (à arbitrer) |
| 🟠 **QA_EXPORT_CLEAR_SETTINGS_ORPHAN** | Branches `_on_quick_action("export"/"clear"/"settings")` orphelines (aucun bouton émetteur après suppression du `help_system`) | Retirer les 3 branches. `_on_quick_action` ne traite plus que `open/save` (alignés aux 2 boutons restants) |
| 🟠 **GITIGNORE_LOGS_TRACKED** | `logs/` ignoré par .gitignore ; OK. Les 4 fichiers `MorphoLapse_*.log` ne sont pas trackés. | Pas d'action ; vérifier `git ls-files logs/` retourne vide |

---

## C. Anomalies MINEURES (Phase E priorité 3) — 13+ items

### C.1 Excepts silencieux (13)

| Fichier:ligne | Pattern | Correction |
|---|---|---|
| `workflow_manager.py:222` | `except Exception: pass` (callback `on_workflow_complete`) | Logger un warning structuré : `self._log_error(f"Callback error: {e}")` |
| `workflow_manager.py:315, 322, 329, 336` | Idem 4× pour `_notify_step_*` et `_notify_progress` | Idem |
| `logger.py:161` | `except Exception: pass` callback Logger | Idem (mais éviter récursion infinie : pas de re-log via `self`) → `print(f"Logger callback error: {e}", file=sys.stderr)` |
| `config_manager.py:204` | `except Exception: return default` dans `get` | Acceptable (defensive) ; logger DEBUG seulement |
| `config_manager.py:250` | `except Exception: pass` dans `_notify_change` | Logger structuré |
| `image_utils.py:34, 59` | `try/except Exception: return None/False` muets dans `load_image`/`save_image` | Logger l'exception, conserver le fallback None/False |
| `file_utils.py:137-138` | `except: pass` dans `get_exif_date` | Acceptable (EXIF optionnel) ; logger DEBUG |
| `file_utils.py:254-255` | `except Exception: pass` dans `get_file_info` | Logger DEBUG |
| `widgets.py:621-623` | `ImagePreview.set_image` `except Exception as e:` → "Erreur" générique sans log de `e` | Logger l'exception, conserver l'affichage utilisateur "Erreur" |
| `face_detector.py:96-98` | `except Exception` dans `initialize` retourne False | Logger l'exception (déjà fait via `_log_error`), OK |

### C.2 Code "stocké non lu" (11 widgets ⚠️) — décision : RETIRER de l'UI

> Décision défaut user : retirer les options qui ne servent à rien plutôt que de les implémenter (honnêteté UX). Si une option doit être conservée pour usage futur, le câblage devra suivre.

| ID matrice | Action Phase E |
|---|---|
| `OPT_AUTO_CROP` | Retirer du `OptionsPanel` (section Alignement) |
| `OPT_STABILIZE` | Retirer (section Alignement) |
| `OPT_DETECTION_THRESHOLD` | Retirer (section Detection) — ou câbler `FaceDetector.detect_faces` (probablement non, dlib n'a pas de seuil ajustable simple) |
| `OPT_PARALLEL_PROCESSING` | Retirer (section Workflow) |
| `OPT_NUM_THREADS` | Retirer (section Workflow) |
| `OPT_AUTO_BACKUP` | Retirer (section Workflow) |
| `OPT_EXPORT_FRAMES` | Retirer (section Export) — fonctionnalité non implémentée |
| `OPT_EXPORT_LANDMARKS` | Retirer (section Export) |
| `OPT_DEBUG_MODE` | Câbler à `MORPHOLAPSE_DEBUG` env var pour cohérence (au lieu de retirer) — option utile |
| `LOG_BTN_EXPORT` | Conserver mais ajouter try/except + messagebox pour l'erreur d'écriture |
| `OPT_RESOLUTION` | Normaliser casse (`Original` vs `original`) — un seul endroit d'autorité |

### C.3 Hardcoded versions / métadonnées

| Fichier:ligne | Hardcoded | Correction |
|---|---|---|
| `step_export.py:97-98` | `'project': 'MorphoLapse', 'version': '2.0.0'` | Lire depuis `src.__version__` |
| `config_manager.py:98` | `version: str = "2.0.0"` (`AppConfig`) | Idem |
| `main.py:11-12, 27, 162, 166-168` | epilog/help mentionnent `main_app.py` | Aligner sur `python main.py` |
| `splash_screen.py:144, 158` | Strings UI EN ("Initializing...", "Starting application...") | Aligner FR (cohérence avec reste UI) |

### C.4 UX mineurs

| Item | Action |
|---|---|
| `splash_screen` 4× `time.sleep(0.1)` artificiels (`main_window.py:684-697`) | Retirer ces sleep — startup plus snappy |
| `LogViewer` auto-scroll permanent (pas de scroll-lock) | Scope-out (pas un bug, juste UX) |
| `ImagePreview.set_image` ouvre `Image.open` sans `with` (leak léger sur erreur) | Wrapper en `with Image.open() as img:` |
| `CollapsibleSection` clic sur badge "NEW" ne toggle pas | Bind `<Button-1>` aussi sur badge |
| `os.startfile(...)` Windows-only dans `_on_quick_action("settings")` | Sera retiré (handler `settings` orphelin → suppression) |

---

## D. Plan d'exécution Phase E (commits proposés)

Ordre minimisant le risque de régression. Chaque commit garde `pytest tests/ -q` à 0 fail.

| # | Commit | Type | Touches | Risque | Tests impactés |
|---|---|---|---|---|---|
| 1 | `chore: snapshot pre-audit working tree` | chore | tous fichiers dirty | nul | aucun |
| 2 | `fix(ui): icon path → assets/icons/icone.ico` | fix | `main_window.py:40` (+ helper `paths.py`) | faible | aucun (chemin absent silencieux avant et après) |
| 3 | `fix(packaging): pyproject entry-point main_app→main` | fix | `pyproject.toml` ×2 | faible | aucun |
| 4 | `fix(ci): release.yml main_app→main, ico→assets/icons` | fix | `.github/workflows/release.yml` | faible | aucun |
| 5 | `chore: align version 2.0.0 (build.py, RELEASE, step_export, AppConfig, title)` | chore | `build.py`, `step_export.py`, `config_manager.py`, `main_window.py`, créer `src/__init__.py:__version__` | faible | aucun |
| 6 | `feat(ui): map FR dropdown labels to backend keys (easing, blend, quality)` | feat | `step_morph.py::get_easing_function`, `get_blend_mode`, `quality_map` ; `widgets.py` (libellés inchangés mais documentés) ; `test_golden.py` (inverse `_BUG` + dé-skip Phase E targets) | moyen | golden tests modifiés (intentionnel) |
| 7 | `fix(video): VideoEncoder honors quality preset` | fix | `video_encoder.py:46-50, 89-138` (stocker `_preset`, `_crf`) ; dé-skip `test_phase_e_video_encoder_honors_quality_preset` | moyen | nouveau test passant |
| 8 | `fix(detection): align retry_detection int with FaceDetector.max_attempts` | fix | `config_manager.py::DetectionConfig.retry: int = 3` ; `step_align.py:46` câbler ; `widgets.py` libellé slider | moyen | aucun direct |
| 9 | `feat(ui): remove 8 inert options from OptionsPanel` | feat (suppression) | `widgets.py::OptionsPanel._setup_ui` (auto_crop, stabilize, detection_threshold, parallel_processing, num_threads, auto_backup, export_frames, export_landmarks, multi_face string, output_format restreint MP4) ; `main_window.py::_load_last_settings` + `_save_settings` aligner | moyen-élevé | smoke tests (les options retirées ne doivent plus être attendues) |
| 10 | `feat(ui): trim QuickActions to {open, save} only` | feat | `widgets.py::QuickActions` ; `main_window.py::_on_quick_action` retire reset/help/export/clear/settings ; dé-skip `test_phase_e_quickactions_*` | faible | nouveau test passant |
| 11 | `chore: archive orphan modules (export_manager, validators)` | chore | déplacer vers `_archive/` ; retirer imports `src/utils/__init__.py` | faible | smoke `test_all_src_modules_import_without_crash` ajusté (retirer les 2 imports) |
| 12 | `fix: replace silent excepts with structured logging (10 occurrences)` | fix | `workflow_manager.py` ×5, `logger.py` ×1, `config_manager.py` ×2, `image_utils.py` ×2, `file_utils.py` ×2, `widgets.py` ×1 | faible | aucun |
| 13 | `chore: remove 4× artificial splash sleeps` | chore | `main_window.py:684-697` | nul | aucun |
| 14 | `docs: README — main.py, assets/icons/, drop deleted modules from architecture` | docs | `README.md` | nul | aucun |

**Critères d'acceptation par commit :**
- `pytest tests/ -q` → 0 fail
- Le commit ne touche que les fichiers listés (pas de leak hors scope)
- Message de commit conforme convention (`refactor/fix/feat/chore/docs/build/test`)
- Pour les commits qui retirent du code (orphelins, options) : note "Vu Phase B/D matrice" dans le corps

---

## E. Hors scope Phase E (différé ou décliné)

| Item | Justification |
|---|---|
| Accessibilité étendue (raccourcis F1/Ctrl-O/Ctrl-S, Enter/Escape sur dialogues, focus visible) | Effort important ; pas un bug, juste manque de feature. Différé Phase H ou versions ultérieures |
| EXIF orientation auto-rotate | Non testé sur photos terrain ; à ajouter si retours utilisateurs |
| Support 16-bit / alpha images | OpenCV impose 8-bit BGR ; conversion explicite à ajouter si demande |
| Windows long paths >260 chars | Setting système ; à documenter dans README |
| Implémenter WebM/AVI/GIF en sortie | UI restreinte à MP4 en E ; ajouter si besoin |
| Implémenter parallel/num_threads/auto_backup | Hors scope ; UI nettoyée en E10 |
| Refactoriser Logger en non-singleton | Singleton fonctionne, refacto risquée |
| pre-commit hooks + CI lint | Phase I |
| pip-audit + bandit | Phase F validation |

---

## Résumé

| Catégorie | Items |
|---|---|
| 🔴 BLOQUANT | 11 |
| 🟠 MAJEUR | 8 |
| 🟡 MINEUR | 13+ excepts + 11 widgets ⚠️ + 4 hardcoded + 5 UX |
| Plan E | 14 commits proposés |
| Différé hors scope | 9 items |

**Décisions confirmées par défauts user :**
- ALLOW_DELETE=NO → orphelins déplacés vers `_archive/` (pas supprimés)
- ALLOW_RENAME=NO → API publique préservée
- ALLOW_UI_REFACTOR=NO → mais "retirer un widget inerte" ≠ refactor (fix de cohérence UX), donc autorisé
- 11 widgets ⚠️ → **retirer** (sauf `OPT_DEBUG_MODE` câblé à env var et `OPT_RESOLUTION` normalisé)

---

## Validation attendue

Réponds **`OK phase D → continue`** pour passer à Phase E (correction directe : 14 commits selon le plan ci-dessus).

Indique si tu veux ajuster :
- L'ordre des commits
- Une décision (ex: garder `auto_crop` en stub à câbler plus tard plutôt que retirer)
- Le périmètre (ex: retirer des items du plan E pour les remettre en Phase H)
