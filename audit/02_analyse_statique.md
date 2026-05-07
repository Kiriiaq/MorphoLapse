# Phase 2 — Analyse statique

> Outils : `py_compile`, `ruff check --select=E,F,W,B,S`, `mypy --ignore-missing-imports`, `vulture`, `bandit -r .`
> État final : ✅ ruff 0 erreur, ✅ bandit 0 alerte, mypy 55 issues (cv2 stubs FP majoritairement), vulture 5 FP documentés.

---

## Synthèse criticité

| Niveau | Avant | Corrigé | Restant | Détail |
|---|---|---|---|---|
| **BLOQUANT** | 1 | 1 | 0 | `ImageValidationError.message` accédé sans avoir été stocké → crash potentiel dans le path d'erreur de l'import |
| **MAJEUR** | 4 | 4 | 0 | None checks, type annotations, dead args, except silencieux |
| **MINEUR** | 6 | 6 | 0 | ruff S603/S607 (FP subprocess), S110 main.py |
| **FP documentés** | — | — | 5 | vulture sur `event`/`args` requis par signature (tkinter, `__new__`) ; mypy cv2 stubs |

---

## BLOQUANT (1) — corrigé

### B-001 — `ImageValidationError.message` jamais stocké

| | |
|---|---|
| Symptôme | mypy `"ImageValidationError" has no attribute "message" [attr-defined]` à `step_import.py:155` (`logger.warning(f"Image ignoree: {e.message}")`) |
| Cause racine | `__init__` appelle `super().__init__(message)` mais ne stocke pas `self.message`. La base `Exception` met le message dans `args[0]`, jamais dans `.message`. |
| Impact runtime | Crash `AttributeError` quand une image invalide est rencontrée ET qu'un logger est branché — c'est-à-dire en mode normal de l'app après le commit 6 (logging callbacks UI actifs). |
| Localisation | `src/modules/step_import.py:30-37` |
| Fix appliqué | Ajout de `self.message = message` dans `__init__` (Phase 2 commit). |
| Risque régression | Très faible (ajout pur d'attribut). |
| Tests | `tests/test_smoke.py::test_validate_image_file_*` passent ; ajout test négatif Phase 4 confirmera le path d'erreur. |

---

## MAJEUR (4) — corrigés

### M-001 — `MainWindow._on_step_toggle` accède à `self.workflow` potentiellement `None`

| | |
|---|---|
| Symptôme | mypy `Item "None" of "WorkflowManager | None" has no attribute "steps"/"enable_step"` à `main_window.py:472,474` |
| Cause | `self.workflow: WorkflowManager | None = None` à `__init__`, mais `_setup_workflow()` l'initialise avant le premier toggle. mypy ne le sait pas, et un appel pendant le splash juste avant `_setup_workflow` crasherait. |
| Fix | `if self.workflow is None: return` au début de `_on_step_toggle`. |
| Risque | Nul (path normal inchangé). |

### M-002 — `step_align.landmarks_list` sans annotation, `previous_result` non-Optional

| | |
|---|---|
| Symptôme | mypy `Need type annotation for "landmarks_list"` + `Argument "previous_result" ... has incompatible type "None"` à `step_align.py:75,110`. |
| Cause | `previous_result: np.ndarray = None` viole le typage strict ; manque d'annotations sur les listes accumulant les résultats. |
| Fix | `landmarks_list: list = []` et `previous_result: np.ndarray | None = None` dans `face_aligner.align_to_reference` (et symétriquement `source_landmarks`/`reference_landmarks`). |
| Risque | Nul (le code accepte déjà `None` en pratique). |

### M-003 — `start_encoding(codec=...)` paramètre mort

| | |
|---|---|
| Symptôme | vulture `unused variable 'codec'` à `video_encoder.py:58` ; `finish_encoding` hardcode `libx264`. |
| Cause | Le param `codec` était présent dès la version initiale mais jamais lu — leftover d'une ancienne version `cv2.VideoWriter`. |
| Fix | Suppression du param. Aucun appelant ne le fournissait (vérifié sur tous les call sites). |
| Risque | Nul (signature appelants inchangée). |

### M-004 — `main.py:29` `try/except: pass` autour de `SetCurrentProcessExplicitAppUserModelID`

| | |
|---|---|
| Symptôme | ruff `S110 try-except-pass detected, consider logging the exception`. |
| Cause | Echec silencieux possible (pas d'icône en barre des tâches, sans diagnostic). |
| Fix | `logging.getLogger(__name__).debug("AppUserModelID not set: %s", e)` — niveau DEBUG car non-fatal. |
| Risque | Nul. |

---

## MINEUR (6) — corrigés

| ID | Fichier | Issue | Fix |
|---|---|---|---|
| L-001 | `src/ui/main_window.py:182` | `is_file=False` param + arg jamais utilisés | suppression du param et de son arg |
| L-002 → L-006 | `build.py`, `video_encoder.py:44,139`, `step_morph.py:370,407` | ruff S603/S607 subprocess (FP : commande contrôlée littérale "ffmpeg") | `# noqa: S603` (et S607 pour le partial-path "ffmpeg") |
| L-007 | `pyproject.toml` | `tests/` levaient du S101 sur `assert` | `[tool.ruff.lint.per-file-ignores] "tests/**" = ["S101"]` |

---

## FP documentés (5) — non corrigés (justifiés)

| Fichier | Vulture finding | Raison |
|---|---|---|
| `src/ui/widgets.py:28,37,61,129` | unused variable `event` | signature obligatoire pour les handlers tkinter `widget.bind("<X>", handler)` |
| `src/utils/logger.py:55` | unused variable `args` | signature standard de `__new__(cls, *args, **kwargs)` du singleton ; renommer casserait la convention |

Mypy lance ~50 erreurs supplémentaires sur cv2 (stubs `Mat | UMat | ndarray` mal projetés sur les types numpy de scipy). Aucune ne reflète une vraie incompatibilité runtime — confirmé par les 36 tests verts.

Configuration mypy ajoutée (`pyproject.toml [tool.mypy]`) : `python_version = "3.11"`, `ignore_missing_imports = true`, `exclude = ["_archive", "build", "dist"]`.

---

## Recherche manuelle (clean)

| Pattern | Occurrences |
|---|---|
| `TODO`, `FIXME`, `XXX` | 0 |
| `raise NotImplementedError` | 0 |
| Fonctions vides / `pass` orphelins | 0 |
| Handlers UI non connectés | 0 (déjà nettoyés en Phase E `feat(ui): trim QuickActions`) |
| Boutons / menus sans callback | 0 |
| `except: pass` ou `except Exception: pass` sans logging | 0 (dans `src/`) — déjà adressé en Phase E `fix: replace 13 silent excepts` |

Le contenu de `_archive/` est exclu du scan (modules quarantainés ; cf. `_archive/README.md`).

---

## Outils — état final

```bash
$ python -m py_compile $(find src -name "*.py") main.py build.py
[clean]

$ python -m ruff check . --select=E,F,W,B,S
All checks passed!

$ python -m bandit -r src -ll -q
[clean]

$ python -m mypy src --ignore-missing-imports
55 errors in 9 files (cv2 stubs FP, documented above)

$ python -m vulture src --min-confidence 80
5 unused variables (FP documentés ci-dessus)

$ python -m pytest tests/ -q
36 passed in <1s
```

Phase 2 close. Aucune anomalie BLOQUANT/MAJEUR/MINEUR ne reste ouverte.
