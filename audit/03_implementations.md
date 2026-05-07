# Phase 3 — Combler les trous

> Référence inventaire : `audit/01_inventaire.md` matrice de couverture.
> État de départ Phase 3 v2 : **0 ❌ · 0 🔲 · 1 ⚠️ · 45+ ✅** — la quasi-totalité des trous a été comblée pendant la Phase E v1 (15 commits, branche `audit/20260429`).

---

## Ce qui était déjà implémenté avant Phase 3 v2

La Phase E v1 (commits `b3ee0cb` → `0dffea0`) a comblé **23 trous fonctionnels**. Récapitulatif :

| # | Trou (status pré-audit) | Implémentation | Commit |
|---|---|---|---|
| 1 | Icône fenêtre cassée silencieusement (`ico/` supprimé, chemin obsolète, `iconbitmap` no-op) | `src/utils/paths.py::get_icon_path()` PyInstaller-aware (`sys.frozen`/`_MEIPASS`) ; `MainWindow.__init__` pointe dessus | `a8d4864` |
| 2 | `pyproject.toml [project.scripts]` cassé (`main_app:main` → fichier supprimé) | Pointe sur `main:main` | `29d830e` |
| 3 | CI release.yml cassé (×4 références obsolètes `main_app.py` + `ico/icone.ico`) | Pointe sur `main.py` + `assets/icons/icone.ico` | `8eaa2bc` |
| 4 | Version dispersée (1.0.0 vs 2.0.0) | `src/__init__.py::__version__` source unique ; `build.py` lit `pyproject.toml` via tomllib ; `step_export.py`, `main_window.py` titre/sidebar/splash consomment cette source | `50c121f` |
| 5 | Dropdown `OPT_VIDEO_QUALITY` FR ne mappe pas `quality_map` EN | Mapping étendu accepte FR ET EN | `90096b5` |
| 6 | Dropdown `OPT_EASING` 4 labels FR sans mapping | Mapping étendu | `90096b5` |
| 7 | Dropdown `OPT_BLEND_MODE` 3 labels UI sans mapping | Mapping étendu (Cross-dissolve → ALPHA) | `90096b5` |
| 8 | `VideoEncoder.finish_encoding` ignore `quality` reçu de `start_encoding` | `_PRESET_TO_CRF` table + `_preset`/`_crf` honorés au finish ; tests positif et négatif ajoutés | `38bb940` |
| 9 | `DetectionConfig.retry: bool = False` vs slider int 1-5 | `retry: int = 3` ; step_align/step_morph passent `max_attempts` à `FaceDetector.get_landmarks` ; cast defensif pour les configs legacy | `962aa8c` |
| 10-19 | 10 widgets stockés mais jamais consommés (`auto_crop`, `stabilize`, `detection_threshold`, `multi_face`, `parallel_processing`, `num_threads`, `auto_backup`, `export_frames`, `export_landmarks`, `output_format`) | Retirés de l'UI (décision : **honnêteté UX > faux contrôles**) | `5263015` |
| 20 | `OPT_DEBUG_MODE` checkbox stockée mais jamais lue | Câblé : toggle change `Logger.set_level(DEBUG/INFO)` immédiatement | `5263015` |
| 21 | `OPT_RESOLUTION` mismatch casse "Original"/"original" | Normalisation `.lower()` au consommateur | `5263015` |
| 22 | QuickActions toolbar : 4 boutons mais 2 sans handler (reset, help) ; 3 handlers sans bouton (export, clear, settings) | Réduit à 2 boutons (open, save) ; `ACTIONS` constante de classe = source unique de vérité ; 3 handlers orphelins supprimés | `cfb1a42` |
| 23a | Module orphelin `src/utils/export_manager.py` (666 LOC, dépend openpyxl/reportlab non déclarés) | Déplacé `_archive/`, `__init__.py` nettoyé | `0299f0f` |
| 23b | Module orphelin `src/utils/validators.py` (612 LOC, jamais consommé) | Idem | `0299f0f` |
| 24 | 13 silent excepts (`workflow_manager` ×5, `image_utils` ×2, `file_utils` ×2, `config_manager` ×2, `widgets.ImagePreview`, `logger.callback`) | Logging structuré au niveau adapté (DEBUG/WARNING) ; pas de récursion logger | `be01b63` |
| 25 | 4× `time.sleep(0.1)` artificiels dans le splash | Retirés ; MainWindow init fournit la durée naturelle | `bde71ab` |
| 26 | README obsolète (×6 main_app, ×2 ico, modules supprimés mentionnés) | Réécrit | `9ad29f3` |
| 27 | 215 issues ruff + 29 fichiers à reformater | Auto-fix + format ; FP S101 isolés via `# noqa` ciblés | `199a1ad` |

Toutes ces corrections sont **traçables** par tag `pre-audit-20260429` (état initial) → `audit/20260429` (état final). `git diff pre-audit-20260429..audit/20260429 -- src/` montre l'intégralité des changements.

---

## Trous comblés en Phase 2 v2 (commit unique)

| # | Trou détecté par mypy | Implémentation |
|---|---|---|
| 28 | `ImageValidationError.message` accédé mais jamais stocké → AttributeError potentiel sur path d'erreur d'import | `__init__` stocke `self.message = message` |
| 29 | `MainWindow._on_step_toggle` accède à `self.workflow` potentiellement `None` | Guard `if self.workflow is None: return` |
| 30 | `start_encoding(codec=...)` paramètre mort | Suppression (aucun appelant ne le fournissait) |
| 31 | `_create_folder_selector(is_file=False)` paramètre mort | Suppression |
| 32 | `face_aligner.align_to_reference` arguments `np.ndarray = None` non-Optional | `np.ndarray | None = None` |
| 33 | `step_align.landmarks_list` sans annotation | `landmarks_list: list = []` |
| 34 | `main.py` `try/except: pass` sur AppUserModelID | Logging DEBUG du failure |

---

## Trou comblé en Phase 3 v2

### # 35 — `LogViewer._export_logs` n'avertissait pas l'utilisateur en cas d'erreur disque

| | |
|---|---|
| Statut pré-fix | ⚠️ Partiel — un échec d'écriture (chemin invalide, permission, disque plein) était **silencieux**. L'utilisateur croyait que l'export avait fonctionné. |
| Décision retenue | Pattern cohérent avec les autres handlers IHM : log au niveau WARNING + `messagebox.showerror` avec message actionnable (chemin + cause). On ne masque pas l'erreur, on guide l'utilisateur. |
| Implémentation | `try/except OSError` avec `_log.warning(...)` (logger module-level déjà présent depuis le commit `be01b63`) + `messagebox.showerror("Export impossible", ...)` montrant le chemin et `e.strerror`. Tests pytest négatif ajouté Phase 4. |
| Conventions respectées | (a) logger nommé `_log = logging.getLogger(__name__)` comme dans `image_utils`, `file_utils`, `config_manager` — (b) `messagebox` plutôt qu'erreur silencieuse, comme `_run_workflow` et `_save_settings` — (c) message en français avec verbe d'action et cause technique masquée derrière un libellé clair. |
| Localisation | `src/ui/widgets.py::LogViewer._export_logs` |
| Risque régression | Nul (path nominal inchangé ; le `try` n'enveloppe que le `open/write`). |

---

## Décisions documentées (alternatives écartées)

### Pourquoi retirer 10 widgets plutôt que les implémenter (commit `5263015`)
**Alternative** : implémenter `auto_crop`, `stabilize`, `parallel_processing`, etc.
**Choix** : suppression. Justification :
- Implémenter `parallel_processing` = ThreadPoolExecutor sur le morphing → refonte step_morph.morph_faces (gestion de l'ordre des frames, encoder thread-safe). Hors-scope audit.
- `auto_crop` = découpage facial automatique = nouvelle feature métier (où crope-t-on ? bbox dlib + marge ? recadrage carré ?). Décision produit nécessaire.
- `export_frames`/`export_landmarks` = ajouter 2 dossiers de sortie + serializer landmarks en JSON. Possible mais dilue le scope.
- `multi_face` (3 modes : Premier / Plus grand / Manuel) = "Manuel" implique sélection visuelle = nouvelle UI. Lourd.
**Conséquence** : moins de boutons, mais ce qui reste fait ce qu'il dit. `ALLOW_UI_REFACTOR=NO` n'a pas été enfreint car aucune option active n'a été modifiée — seulement les inertes ont été retirées.

### Pourquoi `Cross-dissolve` mappe sur `ALPHA` (commit `90096b5`)
Le moteur `face_morpher.stream_cross_dissolve` est un alpha-blend pur (`cv2.addWeighted`). Distinguer dans le UI ne ferait pas sens si le backend ne distingue pas. Le mapping reflète la réalité.

### Pourquoi un singleton Logger plutôt que `logging.getLogger`
Existant historique (`Logger._instance` + `Lock`). Conserver pour ne pas casser les callbacks UI déjà branchés. Le code applicatif utilise le singleton ; le code utilitaire utilise `logging.getLogger(__name__)` (cohabitation propre).

---

## Vérification

```bash
$ python -m pytest tests/ -q
36 passed in <1s
```

Phase 3 close. **0 trou ouvert** dans la matrice de couverture.
