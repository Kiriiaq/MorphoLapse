# RAPPORT_PHASE_A — Pré-audit MorphoLapse

> Branche : `audit/20260429` · Tag rollback : `pre-audit-20260429` (= `a4fdb7e`)
> Date : 2026-04-29
> Statut : ✅ validé par l'utilisateur

---

## Adaptation du plan (contexte ≠ template)

Le prompt template suppose un outil Excel/Word/PDF. MorphoLapse est une **app desktop image/vidéo** (face morphing dlib + OpenCV + FFmpeg, IHM customtkinter). Adaptations actées :

| Section | Statut | Justification |
|---|---|---|
| D.1 edge cases PDF/Word/Excel | Remplacés | Edge cases image (formats, EXIF, transparence, taille), dlib (no-face/multi-faces), FFmpeg (binaire absent, codec), Windows long paths, modèle .dat 99 MB |
| Phase E dépendances Excel | Sans objet | Stack image-vidéo : opencv-python, numpy, scipy, Pillow, dlib, customtkinter |
| Outils COM Office | Sans objet | Pas d'intégration Office |
| Phase G hidden imports typiques | Adapté | `customtkinter`, `darkdetect`, `cv2`, `numpy`, `scipy.spatial`, `dlib`, `PIL._tkinter_finder` |

---

## Variables actées

| Variable | Valeur |
|---|---|
| `PROJECT_NAME` | MorphoLapse |
| `PROJECT_VERSION` | 2.0.0 (canonique : pyproject + git tag + IHM ; build.py 1.0.0 sera aligné) |
| `PROJECT_TAGLINE` | Face Morphing & Time-Lapse Generator |
| `REPO_PATH` | `D:\#Bureau\Face Movie` |
| `ENTRY_POINT_HINT` | `main.py` |
| `UI_FRAMEWORK` | customtkinter (+ ttk pour splash) |
| `DOMAIN` | image / vidéo (face morphing time-lapse) |
| `ICON_PATH` | `assets/icons/icone.ico` |
| `ICON_FOLDER` | `assets/icons` |
| `EXTRA_DATA_FOLDERS` | `assets`, `src`, `config` |
| `APP_USER_MODEL_ID` | `morpholapse.facemorphing.app.2.0` |
| `ICON_SETUP_HOOK` | `main.py:25-30` (AppUserModelID) + `src/ui/main_window.py:40-42` (iconbitmap, à corriger : pointe vers `ico/` supprimé) |
| `LANGUAGE_UI` | fr (tutoiement) |
| `TEST_COMMANDS` | `pytest tests/ -q` ; `python main.py` (smoke launch GUI 8s) |
| `SIZE_TARGET_MB` | 180 (à valider après build initial) |
| `MAX_ITERATIONS` | 5 |
| `PERIMETER_OUT` | `assets/shape_predictor_68_face_landmarks.dat`, `logs/`, `runs/` |
| `ALLOW_DELETE` | **non** (déplacement vers `_archive/`) |
| `ALLOW_RENAME` | **non** (préserver API publique sauf rupture nécessaire documentée) |
| `ALLOW_UI_REFACTOR` | **non** (corrections fonctionnelles uniquement, structure IHM préservée) |

---

## A.1 — Sécurisation git

| Item | État |
|---|---|
| Repo git initialisé | ✅ |
| Branche `audit/20260429` | ✅ créée |
| Tag `pre-audit-20260429` (= `a4fdb7e`) | ✅ créé |
| Working tree | ⚠️ **dirty** — 15 fichiers (transition `main_app.py`→`main.py`, suppression `ico/` et docs, ajout `assets/`+`config/`) |

Décision (Q2) : la branche `audit/20260429` part de l'état dirty actuel. **Aucun commit automatique** ; un snapshot `chore: snapshot pre-audit working tree` sera proposé au démarrage de Phase E (avant toute modification destructive).

---

## A.2 — Détection secrets

✅ **Aucun secret hardcodé.** Scans :
- `api_key|secret|password|token|bearer|aws_|private_key|BEGIN RSA|sk_live|sk_test` (insensitive)
- Patterns AWS/Stripe/GitHub PAT (`ghp_`, `ghs_`)/Google API (`AIza`)/Slack (`xox`)/entropy ≥40 chars

Seules occurrences : URLs publiques GitHub Kiriiaq, Ko-fi (non sensibles).

---

## A.3 — Baseline mesurable

| Métrique | Valeur |
|---|---|
| LOC Python | **7 278** sur 27 fichiers |
| Top 5 fichiers (LOC) | `main_window.py` 712 · `widgets.py` 666 · `export_manager.py` 666 · `validators.py` 612 · `face_morpher.py` 607 |
| Tests | 1 fichier (127 LOC, `unittest`, ~10 tests basiques import + boundary) |
| Taille repo (incl. `.git` 98 MB total, dont modèle dlib local 95 MB non tracké) | ~98 MB total, ~3 MB code |
| Dépendances runtime déclarées | 6 : customtkinter, opencv-python, numpy, scipy, Pillow, dlib |
| Dépendances dev | 5 : pytest, pytest-cov, ruff, build, pyinstaller |
| Bare `print()` dans `src/` | 4 |
| `except Exception: pass` dans `workflow_manager.py` | 5 (lignes 222, 316, 322, 328, 334) |
| Temps démarrage GUI | non mesuré (sera fait Phase B après run dynamique) |

Baseline détaillée → produit en `baseline/before.json` au démarrage Phase E.

---

## A.4 — Périmètre IN/OUT

**IN (audit & corrections) :** `main.py`, `build.py`, `pyproject.toml`, `requirements.txt`, `README.md`, `src/` complet, `tests/`, `.github/workflows/`, `config/config.json`.

**OUT (intouchable) :** `assets/shape_predictor_68_face_landmarks.dat` (modèle 95 MB), `LICENSE`, `logs/`, `.git/`.

---

## A.5 — Plan de rollback

| Scénario | Commande |
|---|---|
| Annuler audit, revenir au pre-audit | `git checkout pre-audit-20260429` |
| Restaurer un fichier supprimé localement | `git checkout HEAD -- <chemin>` |
| Reset complet branche audit | `git checkout main && git branch -D audit/20260429` |

---

## INCOHÉRENCES MAJEURES (préview, à corriger Phase E)

| # | Incohérence | Impact |
|---|---|---|
| 1 | `main_app.py` supprimé mais référencé dans pyproject.toml (entry-point `[project.scripts]`, `py-modules`), `.github/workflows/release.yml` (×2), `main.py` docstring (×6), `README.md` (×6) | CI cassée + entry-point pip cassé |
| 2 | `ico/icone.ico` supprimé mais référencé dans `release.yml` (×2), `README.md` (×2), **`src/ui/main_window.py:40` (chargement runtime)** | Build CI cassé + icône fenêtre absente runtime |
| 3 | Version 1.0.0 vs 2.0.0 (build.py + RELEASE_1.0.0.md vs pyproject + main.py + IHM + tag git) | Confusion publication |
| 4 | Modules `src/ui/help_system.py` et `src/ui/keyboard_manager.py` supprimés mais cités README architecture | Doc obsolète |
| 5 | 5 `except Exception: pass` muets workflow_manager (callbacks UI) | Erreurs callbacks invisibles |
| 6 | Build CI inline (release.yml) ≠ `build.py` script (icône path, modes, hidden-imports différents) | Comportement build incohérent local vs CI |

---

## Décisions actées (ouvertures Q1-Q4)

- **Q1 (version) :** 2.0.0 canonique
- **Q2 (working tree) :** branche `audit/20260429` part du dirty actuel ; snapshot commit déféré au démarrage Phase E
- **Q3 (autorisations) :** ALLOW_DELETE=NO (archive), ALLOW_RENAME=NO, ALLOW_UI_REFACTOR=NO
- **Q4 (docs supprimées) :** intent utilisateur respecté (suppressions entérinées) ; ils n'apparaîtront pas dans les artefacts post-Phase E

---

**Phase A close. Passage Phase B (cartographie statique + dynamique + matrice UI→Backend).**
