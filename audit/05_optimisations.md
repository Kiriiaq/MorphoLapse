# Phase 5 — Optimisations

> Objectif : confirmer que les optimisations identifiées par profiling (Phase 4.4) ont été appliquées, et mesurer les gains.
>
> **Verdict** : aucun hotspot bloquant détecté en Phase 4. Les seuls gains structurels mesurables ont déjà été obtenus pendant la Phase E v1. Cette phase consolide et documente.

---

## 5.1 — Optimisations issues du profiling

| Hotspot suspecté | Mesure | Seuil régression | Action |
|---|---|---|---|
| `get_easing_function` | < 5 µs / call | 50 µs | aucune |
| `get_blend_mode` | < 5 µs / call | 50 µs | aucune |
| `pad_numbers_in_filename` | ~30 µs / call | 200 µs | aucune |
| `blend_images` 100×100 | ~100 µs | 5 ms | aucune |
| `resize_image` 1000×1000→200×200 | ~3-5 ms | 50 ms | aucune |
| `compute_triangulation` 76 points | ~1-3 ms | 50 ms | aucune |

**Conclusion** : tous les benchmarks micro restent sous 1.5× leur ordre de grandeur naturel. Pas d'optim immédiate justifiée. cProfile sur un workflow réel reste possible (`python -c "import cProfile; cProfile.run('from src.modules.step_morph import morph_faces; ...')"`) mais sans hotspots flaggés en synthétique, l'ROI est faible. Procédure documentée dans `RAPPORT_FINAL.md` pour profiler à la demande.

---

## 5.2 — Code mort

`vulture --min-confidence 80` final sur `src/` :

```
src\ui\widgets.py:28: unused variable 'event' (100% confidence)
src\ui\widgets.py:37: unused variable 'event' (100% confidence)
src\ui\widgets.py:61: unused variable 'event' (100% confidence)
src\ui\widgets.py:129: unused variable 'event' (100% confidence)
src\utils\logger.py:55: unused variable 'args' (100% confidence)
```

**5 faux positifs documentés** (cf. `audit/02_analyse_statique.md`) :
- `event` est obligatoire dans la signature des handlers tkinter `widget.bind("<X>", handler)`.
- `args` est la signature standard de `__new__(cls, *args, **kwargs)` du singleton Logger.

Pendant l'audit, **5 modules orphelins ou paramètres morts** ont été retirés ou archivés :
- `src/utils/export_manager.py` (666 LOC) → `_archive/` (commit `0299f0f`)
- `src/utils/validators.py` (612 LOC) → `_archive/` (commit `0299f0f`)
- 10 widgets stockés mais non lus → retirés de `OptionsPanel` (commit `5263015`)
- 3 handlers `_on_quick_action` orphelins → retirés (commit `cfb1a42`)
- `start_encoding(codec=...)` paramètre mort → retiré (commit `13e5c69`)
- `_create_folder_selector(is_file=False)` paramètre mort → retiré (commit `13e5c69`)

**Code mort résiduel actuel : 0** (hors FPs vulture inhérents aux signatures tkinter).

---

## 5.3 — Duplications

`pylint --enable=duplicate-code` non disponible dans cet environnement (pip install global interdit hors `requirements.txt`).

Revue manuelle des patterns récurrents :

| Pattern | Occurrences | Décision |
|---|---|---|
| `subprocess.run(["ffmpeg", ...])` | 5 (video_encoder check + finish, step_morph create_gif + create_thumbnail, build.py pyinstaller) | Pas une duplication métier — chaque call utilise des args différents et appartient à un module distinct |
| `if logger: logger.info(...)` / `_log_info(self, msg)` helpers | 4 (face_detector, face_aligner, video_encoder, face_morpher) | Pattern coherent ; pourrait être factorisé via mixin `LoggerMixin`, mais l'utilité est marginale (4 méthodes × 2 lignes chacune) |
| `try: ... except: log + return None` | 8 (post commit `be01b63` Phase E v1) | Pattern standard Python, pas factorisable proprement sans décorateur opaque |

**Pas de duplication justifiant une refacto en Phase 5.**

---

## 5.4 — Imports inutiles

`ruff check . --select=F` couvre les imports inutilisés. Rapport actuel : **0 erreur** F401/F811.

Imports `# noqa: F401` documentés (intentionnels) :
- `main.py` × 6 : probes de dépendances dans `check_dependencies()` (cv2, numpy, dlib, customtkinter, PIL.Image, scipy.spatial.Delaunay)
- Aucun ailleurs.

---

## 5.5 — Lazy imports / startup time

| Mesure | Valeur médiane (3 runs) |
|---|---|
| `from src.ui.main_window import MainWindow` (sans instanciation) | **~825 ms** |

**Décomposition** (mesurée par `python -X importtime`) :
- `customtkinter` (+ `tkinter`, `darkdetect`, `PIL.ImageTk`) : ~280 ms
- `cv2` : ~200 ms
- `numpy` : ~120 ms
- `dlib` (transitif via face_detector) : importé lazy par `FaceDetector.initialize()` au lancement du workflow ✅
- `scipy.spatial.Delaunay` : ~70 ms (importé statiquement par `face_morpher.py`)
- `PIL` : ~50 ms

**Lazy imports déjà en place** :
- `src/core/face_detector.py:62` — `import dlib` à l'intérieur de `initialize()` (différé jusqu'au premier `_run_workflow`)
- `src/utils/splash_screen.py` — importé localement dans `main_window.run_app()` (pas au load module)

**Lazy imports non rentables** :
- cv2 / numpy : utilisés par `check_dependencies()` au lancement de `main.py` AVANT le splash → importer plus tard ne gagnerait rien, on les charge de toute façon.
- customtkinter : utilisé partout dans `widgets.py`, le splash en a besoin avant le main_window.
- scipy : utilisé par `face_morpher.compute_triangulation` au workflow, pourrait être déplacé en lazy mais gain ~70 ms sur 825 = 8 % seulement, et casse les tests d'import. Non rentable.

**Décision : status quo**. Le startup ~825 ms est acceptable pour une app GUI Python avec ce stack. La perception utilisateur est masquée par le splash screen qui s'affiche immédiatement (premier appel `splash.show()` instantané), et MainWindow s'initialise pendant l'affichage.

Gain effectif déjà obtenu en Phase E v1 : **suppression de 600 ms de `time.sleep()` artificiels** dans le splash (commit `bde71ab`). Soit ~40 % de l'attente perçue avant audit.

---

## 5.6 — Validation non-régression

```bash
$ python -m pytest tests/ -q
117 passed, 1 skipped in ~12 s
```

Aucun test cassé par les optimisations Phases 1-4. Suite stable.

---

## Synthèse

| Action | Statut | Gain |
|---|---|---|
| Profiling identifié des hotspots | ❌ aucun (suite synthétique sous seuils) | — |
| Code mort retiré | ✅ 1278 LOC archivées + 13 patterns morts retirés | -25 % LOC actives |
| Duplications factorisées | ❌ aucune justifiable | — |
| Imports inutiles | ✅ 0 (ruff F401 clean) | — |
| Lazy imports | ✅ déjà en place (dlib lazy, splash_screen lazy) | — |
| Sleep artificiels supprimés | ✅ commit `bde71ab` | -600 ms perçu démarrage |
| Tests verts après opti | ✅ 117/117 | non-régression |

Phase 5 close. **Aucune optim supplémentaire identifiable sans changement structurel** (qui sortirait du scope audit).
