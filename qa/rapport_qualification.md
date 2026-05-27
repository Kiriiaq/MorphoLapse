# Rapport de qualification — MorphoLapse v2.0.0

> Squelette à remplir au fil de la campagne. Compléter chaque section après exécution
> des tests. Le HTML interactif (`validation_ihm.html`) peut générer automatiquement
> un bloc Markdown pour les sections 3 et 4 via le bouton « Résumé Markdown ».

---

## 1. Identification

| Champ | Valeur |
|---|---|
| **Outil** | MorphoLapse |
| **Version** | 2.0.0 (post-corrections Lots A+B+C+D du 2026-05-15) |
| **Branche / commit Git** | `main` (HEAD = à renseigner après commit) |
| **Build testé** | (onefile release / onefile debug / onedir / source `python main.py`) |
| **Testeur** | (Nom Prénom) |
| **Date** | (AAAA-MM-JJ) |
| **Environnement OS** | Windows 11 Home 10.0.26200 |
| **Environnement Python** | Python 3.11.9 |
| **Dépendances critiques** | customtkinter, opencv-python, dlib, numpy, scipy, Pillow, ffmpeg |
| **Modèle dlib** | `shape_predictor_68_face_landmarks.dat` présent : (oui/non) |
| **FFmpeg PATH** | `ffmpeg -version` retourne version : (à renseigner) |

---

## 2. Périmètre testé

- **118 tests** répartis sur **8 catégories** (cf. `matrice_tests.xlsx`)
- **20 exigences** (REQ-001..REQ-020) tracées par la colonne `Exigence liée`
- **10 jeux d'inputs** sous `inputs/` (cf. `scripts/generate_inputs.py` pour régénération)
- **Hors scope** :
  - Tests fonctionnels vidéo réels (T-063..T-082 sur photos) nécessitent que l'utilisateur dépose 3-5 photos dans `inputs/input_reel/`
  - Interruption du subprocess FFmpeg pendant `finish_encoding` (limitation connue, cf. pré-rapport audit)
  - Tests sur macOS / Linux (non couverts par cette campagne)

---

## 3. Synthèse chiffrée

> Cette section est régénérée automatiquement depuis `validation_ihm.html` (export Markdown)
> et depuis la feuille **Synthèse** de `matrice_tests.xlsx`.

### Par catégorie

| Catégorie | Total | OK | NOK | NA | À tester | % OK |
|---|---|---|---|---|---|---|
| IHM | 40 | — | — | — | — | — |
| Paramètres | 22 | — | — | — | — | — |
| Entrées | 12 | — | — | — | — | — |
| Sorties | 8 | — | — | — | — | — |
| Cas limites | 12 | — | — | — | — | — |
| Performance | 5 | — | — | — | — | — |
| Robustesse | 8 | — | — | — | — | — |
| Régression | 11 | — | — | — | — | — |
| **Total** | **118** | — | — | — | — | — |

### Par sévérité

| Sévérité | Total | OK | NOK | % OK |
|---|---|---|---|---|
| Bloquant | (à calculer) | — | — | — |
| Majeur | (à calculer) | — | — | — |
| Mineur | (à calculer) | — | — | — |

---

## 4. Anomalies détectées

| ID Test | Sévérité | Description | Reproductibilité | Contournement | État |
|---|---|---|---|---|---|
| (à compléter) | | | | | |

---

## 5. Couverture fonctionnelle (matrice exigences × tests)

| Exigence | Description | Tests liés | Statut |
|---|---|---|---|
| REQ-001 | Sélecteur dossier source obligatoire | T-002, T-063, T-064, T-074 | — |
| REQ-002 | Compteur d'images + état des sélections | T-003, T-004, T-027..T-029, T-113 | — |
| REQ-003 | Bouton Lancer désactivé si input vide ou run actif | T-017..T-020, T-114 | — |
| REQ-004 | Bouton Annuler actif uniquement pendant run | T-021..T-024 | — |
| REQ-005 | Annulation effective sous 1 s | T-013, T-076, T-100..T-102, T-116 | — |
| REQ-006 | Raccourcis Ctrl+1..5 togglent les sections | T-024, T-070..T-075, T-104, T-105, T-108..T-112 | — |
| REQ-007 | Barre de progression visible dès l'état initial | T-036..T-038, T-115 | — |
| REQ-008 | Workflow 4 étapes configurables | T-005..T-016, T-063, T-088..T-091 | — |
| REQ-009 | Détection faciale dlib avec retry configurable | T-010, T-057, T-058, T-073 | — |
| REQ-010 | Encodage H.264 + preset qualité honoré | T-075..T-078 | — |
| REQ-011 | Persistance config JSON | T-026, T-106 | — |
| REQ-012 | Logs temps réel avec filtre | T-032..T-035 | — |
| REQ-013 | Previews première/dernière image | T-002, T-030, T-031 | — |
| REQ-014 | Mapping FR↔EN cohérent (easing/blend/quality) | T-039..T-056, T-117 | — |
| REQ-015 | Annulation distincte d'une erreur | T-013, T-076 | — |
| REQ-016 | Double-lancement bloqué | T-020, T-103 | — |
| REQ-017 | Pré-validation pré-run | T-064, T-072, T-083, T-093 | — |
| REQ-018 | Restauration au démarrage | T-118 | — |
| REQ-019 | Compatibilité Windows path spéciaux | T-068, T-069, T-085 | — |
| REQ-020 | Mode CLI fonctionnel | (test ad hoc) | — |

---

## 6. Conclusion

(à renseigner après exécution complète)

- [ ] **GO** : aucun bloquant NOK, tous les majeurs OK, mineurs NOK ≤ 3
- [ ] **GO conditionnel** : bloquants NOK ≤ 0, majeurs NOK ≤ 2 (lister les conditions)
- [ ] **NO-GO** : ≥ 1 bloquant NOK

**Conditions / réserves** : (à renseigner)

---

## 7. Annexes

| Lien | Contenu |
|---|---|
| `qa/matrice_tests.xlsx` | Matrice complète 118 tests + feuille Synthèse |
| `qa/validation_ihm.html` | Checklist interactive IHM (autonome, localStorage) |
| `qa/inputs/` | 10 jeux d'inputs synthétiques + placeholder `input_reel/` |
| `qa/outputs_reference/` | Vérités terrain (signatures ffprobe, structures JSON) |
| `qa/outputs_reels/` | Sorties de la campagne courante + `_run_summary.json` |
| `qa/scripts/run_tests.py` | Script d'exécution CLI |
| `qa/scripts/compare_outputs.py` | Script de comparaison vs références |
| `qa/scripts/generate_inputs.py` | Régénération des inputs (idempotent) |
| `qa/scripts/generate_matrix.py` | Régénération de `matrice_tests.xlsx` |
| `logs/MorphoLapse_*.log` | Logs runtime générés par l'application |
| `runs/*` | Runs MorphoLapse (1 dossier horodaté par exécution) |

---

## Annexe — Statut des tests historiques hors périmètre

Les tests **T-032 (Suppression fichier liste)** et **T-033 (Vidage liste fichiers)** du test plan
campagne historique sont marqués **« Non Applicable » (NA)** : MorphoLapse n'expose pas
de liste de fichiers explicite ajoutable/supprimable un par un. L'application fonctionne
avec un *dossier source unique* (sélecteur unique). Les T-032 et T-033 de la matrice
courante (`matrice_tests.xlsx`) ciblent d'autres fonctionnalités (LogViewer Effacer/Export)
sans rapport avec ces tests historiques.

Conséquence : la couverture fonctionnelle reste complète sur le périmètre réel du produit.
Une éventuelle implémentation d'une liste explicite de fichiers serait un chantier UI
majeur (modèle, vue, compteur, états boutons, persistance) hors scope du correctif minimal.

---

## Annexe — Décisions prises lors de l'audit (Phase 1)

Synthèse des corrections appliquées aux Lots A+B+C+D le 2026-05-15 :

| Lot | Bugs résolus | Fichiers touchés |
|---|---|---|
| **A** | Ctrl+1..5, Échap, F1 absents (T-016..T-020, T-023 historiques) | `src/ui/main_window.py`, `src/ui/widgets.py` |
| **B** | stats_label non rafraîchi sur ref/output (T-030..T-031), reference non restaurée | `src/ui/main_window.py`, `src/utils/config_manager.py` |
| **C** | Bouton Lancer enabled à vide (T-034), Annuler peu visible (T-035), conflit grille | `src/ui/main_window.py`, `src/ui/widgets.py` |
| **D** | Annulation non coopérative dans steps (T-023, T-036) | `src/modules/workflow_manager.py`, `src/modules/step_*.py`, `src/ui/main_window.py`, `src/ui/widgets.py` |

## Annexe — Phase 2 (audit complémentaire) — Lots E+F+G+H+I

| Lot | Améliorations | Fichiers touchés |
|---|---|---|
| **E** | Annulation granulaire à chaque frame morph/cross-dissolve (latence Échap < 1 frame) | `src/core/face_morpher.py`, `src/modules/step_morph.py` |
| **F** | Interruption FFmpeg via `Popen` + `terminate()` + suppression mp4 partiel | `src/core/video_encoder.py`, `src/modules/step_morph.py` |
| **G** | Ordre d'init : `_setup_shortcuts()` après `_load_last_settings()` ; smoke test non-flaky (lit aussi log files) | `src/ui/main_window.py`, `tests/smoke/test_app_launch.py` |
| **H** | Preview asynchrone (thread daemon + `after(0,...)`) ; borne slider Bordure 0-50 px | `src/ui/main_window.py`, `src/ui/widgets.py` |
| **I** | T-032/T-033 historiques marqués NA (annexe ci-dessous) | `qa/rapport_qualification.md` |

Détails complets dans le rapport pré-audit en historique de conversation et dans les fichiers modifiés.
