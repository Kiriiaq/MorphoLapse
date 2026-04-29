# BASELINE_TESTS — Phase C MorphoLapse

> Branche : `audit/20260429`
> État : ✅ baseline qui passe — 33 tests actifs, 4 skipped (Phase E targets), 0 failed

---

## Vue d'ensemble

| Item | Valeur |
|---|---|
| Tests collectés | 37 |
| Tests passants | **33** ✅ |
| Tests skipped | 4 (Phase E targets) |
| Tests échouants | 0 |
| Durée | ~1.1 s |
| Couverture cœur métier | mesure différée Phase F (`pytest --cov`) |
| GUI smoke launch | ✅ EXIT=124 (timeout 8s, pas de crash, stderr vide) |

**Critère bloquant Phase D :** `pytest tests/ -q` retourne `0 failed`. ✅ rempli.

---

## C.1 — Smoke tests (15 tests, `tests/test_smoke.py`)

Filet de sécurité sur les workflows principaux. Naming `test_<action>_<condition>` quand pertinent, descriptif sinon.

| Test | But | Couverture |
|---|---|---|
| `test_all_src_modules_import_without_crash` | 17 imports ; UI mainloop exclu | Tous les modules `src/` (sauf `main_window`, qui crée un CTk root) |
| `test_config_manager_set_get_roundtrip` | set→save→reload→get | `ConfigManager.{set,save,load,get}` |
| `test_config_manager_reset_to_defaults` | reset retourne defaults | `ConfigManager.reset_to_defaults` |
| `test_config_manager_get_unknown_key_returns_default` | get robuste | `ConfigManager.get` |
| `test_logger_basic_levels_log_without_crash` | 5 niveaux loguent | `Logger.{info,warning,error,success,debug}` |
| `test_logger_callback_receives_entries` | callback fire | `Logger.add_callback` |
| `test_workflow_manager_step_lifecycle` | add + enable/disable | `WorkflowManager.{add_step,enable_step,get_step}` |
| `test_workflow_manager_runs_simple_step` | run() exécute fonction étape | `WorkflowManager.run` (avec `create_run_directory` stub) |
| `test_file_utils_get_image_files_lists_only_images` | filtre extensions | `FileUtils.get_image_files` |
| `test_file_utils_pad_numbers_in_filename` | padding numérique | `FileUtils.pad_numbers_in_filename` |
| `test_image_utils_load_image_returns_none_on_missing` | None sur fichier absent | `ImageUtils.load_image` |
| `test_image_utils_save_load_roundtrip` | save→load preserve shape | `ImageUtils.{save_image,load_image}` |
| `test_validate_image_file_accepts_valid_png` | PNG valide accepté | `validate_image_file` (step_import) |
| `test_validate_image_file_rejects_missing_file` | NOT_FOUND raised | idem |
| `test_validate_image_file_rejects_too_small` | TOO_SMALL raised | idem |

**Fixtures partagées (`tests/conftest.py`) :**
- `_reset_logger_singleton` (autouse) — reset `Logger._instance` entre tests, indispensable car `Logger` est singleton process-wide
- `synthetic_image` — `np.zeros((100,100,3), uint8)` avec carré gris central
- `temp_image_dir` — 3 PNG synthétiques `000.png`/`001.png`/`002.png`
- `temp_config_path` — chemin `tmp_path / config.json`

---

## C.2 — Golden master (12 tests, `tests/test_golden.py`)

**Verrouillent le comportement actuel** (incluant les bugs identifiés en Phase B) pour détecter toute régression accidentelle pendant Phase E. Suffixe `_BUG` sur les tests qui locktent un bug confirmé : ils devront être supprimés ou inversés au commit de fix Phase E.

### Easing function mapping

| Test | État | Note |
|---|---|---|
| `test_easing_unknown_string_falls_back_to_linear` | ✅ pass | Fallback safe |
| `test_easing_french_ui_label_falls_back_to_linear_BUG` | ✅ pass (lock le bug) | UI dropdown FR (`Lineaire`/`Ease In/Out`/...) ne mappe pas → toujours `LINEAR` |
| `test_easing_english_keys_map_correctly` | ✅ pass | Clés EN du backend OK |
| `test_phase_e_easing_french_maps_correctly` | ⏸️ skip | Cible Phase E — à dé-skipper après fix |

### Blend mode mapping

| Test | État | Note |
|---|---|---|
| `test_blend_mode_unknown_string_falls_back_to_alpha` | ✅ pass | Fallback safe |
| `test_blend_mode_ui_labels_fall_back_to_alpha_BUG` | ✅ pass (lock le bug) | UI `Normal`/`Cross-dissolve`/`Additive` → toujours `ALPHA` |
| `test_blend_mode_english_keys_map_correctly` | ✅ pass | Clés EN OK |
| `test_phase_e_blend_mode_ui_labels_map_correctly` | ⏸️ skip | Cible Phase E |

### Quality preset mapping (step_morph.py:202-204)

| Test | État | Note |
|---|---|---|
| `test_quality_preset_mapping_lowercase_works` | ✅ pass | Map `{low/medium/high/ultra}` → preset ffmpeg correcte |
| `test_quality_preset_mapping_french_returns_none_BUG` | ✅ pass (lock le bug) | UI envoie `Basse/Moyenne/...` → `quality_map.get()` retourne None → fallback `medium` |

### Phase E targets (skipped)

| Test | Cible |
|---|---|
| `test_phase_e_easing_french_maps_correctly` | Mapping FR↔EN easing |
| `test_phase_e_blend_mode_ui_labels_map_correctly` | Mapping FR↔EN blend |
| `test_phase_e_video_encoder_honors_quality_preset` | `VideoEncoder.finish_encoding` doit utiliser preset transmis (actuellement hardcode `fast`) |
| `test_phase_e_quickactions_reset_and_help_have_handlers` | Branches `reset`/`help` dans `_on_quick_action` |

---

## C.3 — Snapshot UI

`tests/snapshots/before/` créé. **Capture automatisée non concluante** dans cette session car le desktop interactif n'est pas accessible (écran de verrouillage Windows visible lors de la tentative de capture). Le process `python main.py` démarre cependant correctement et affiche le GUI (preuve : EXIT=124 = timeout 8s sans crash, stdout fonctionnel, stderr vide).

**Action manuelle recommandée pour l'utilisateur :**
```bash
python main.py
# Une fois la fenêtre principale visible, prendre Win+Shift+S ou Print Screen
# Sauver dans tests/snapshots/before/main_window_initial.png
# Idem pour les sections d'OptionsPanel dépliées (6 sections)
```

Snapshots manuels recommandés (référence visuelle pour vérifier qu'aucune régression UI Phase E) :
1. `main_window_initial.png` — fenêtre principale, état au démarrage
2. `main_window_with_inputs.png` — après sélection d'un dossier source (avec aperçus images)
3. `options_video_expanded.png` — section Video dépliée
4. `options_morphing_expanded.png` — section Morphing dépliée
5. `options_detection_expanded.png` — section Detection (avec badge NEW)
6. `running_workflow.png` — pendant un run (StepIndicator running, ProgressBar)

---

## GUI smoke launch (preuve)

```bash
$ timeout 8 python main.py
EXIT=124  # timeout fired = process alive 8s without crash

stdout (extrait, encoding cp1252 sur console Windows mais fonctionnel) :
  09:47:08 | INFO     | Étape ajoutée: Import des images
  09:47:08 | INFO     | Étape ajoutée: Alignement des visages
  09:47:08 | INFO     | Étape ajoutée: Morphing facial
  09:47:08 | INFO     | Étape ajoutée: Export des résultats
  09:47:08 | INFO     | MorphoLapse démarré
  09:47:08 | INFO     | Configuration chargée: D:\#Bureau\Face Movie\config\config.json

stderr : (vide)
```

**Confirmé runtime :**
- ✅ Splash screen + main window construits sans exception
- ✅ Logger initialisé, fichier `logs/MorphoLapse_YYYY-MM-DD_HH-MM-SS.log` créé
- ✅ ConfigManager charge `config/config.json` existant
- ✅ Les 4 WorkflowSteps enregistrés
- ⚠️ Icône fenêtre **silencieusement absente** (`ico/icone.ico` cherché, n'existe plus — `if os.path.exists(): self.iconbitmap()` no-op silencieux ; trace dans `iconbitmap` non observée)
- ⚠️ AppUserModelID posé (`morpholapse.facemorphing.app.2.0`) mais l'icône barre des tâches utilisera l'icône Python par défaut tant que `iconbitmap` n'est pas réussi

---

## Structure tests/

```
tests/
├── __init__.py
├── conftest.py                         # ✅ nouveau — fixtures partagées
├── test_core.py                        # existant — 10 tests (FaceDetector, FaceMorpher, VideoEncoder, FaceAligner)
├── test_smoke.py                       # ✅ nouveau — 15 tests
├── test_golden.py                      # ✅ nouveau — 12 tests (8 actifs + 4 skipped Phase E)
├── fixtures/
│   └── golden/                         # ⏸️ vide — fixtures images golden ajoutées Phase E si besoin
├── snapshots/
│   └── before/                         # ⏸️ vide — capture manuelle recommandée (cf. C.3)
└── runs/                               # ⏸️ vide — sera peuplé par Phase F (rapports pytest+coverage horodatés)
```

---

## Lancer baseline

```bash
python -m pytest tests/ -q                    # 33 passed, 4 skipped en ~1.1s
python -m pytest tests/ -q --tb=short -v      # verbose
python -m pytest tests/ -q --cov=src --cov-report=html   # coverage HTML (Phase F)
```

---

## Décisions verrouillées par les tests `_BUG`

Ces tests passent **maintenant** mais devront être inversés / supprimés en Phase E lors des fix. Le commit de fix doit donc TOUCHER ces tests pour montrer l'intention :

| Bug locké | Action Phase E |
|---|---|
| `test_easing_french_ui_label_falls_back_to_linear_BUG` | Inverser : assertion devient `EASE_IN_OUT` etc. ; dé-skip `test_phase_e_easing_french_maps_correctly` |
| `test_blend_mode_ui_labels_fall_back_to_alpha_BUG` | Idem pour blend |
| `test_quality_preset_mapping_french_returns_none_BUG` | Le mapping doit accepter FR ; supprimer ce test (devient sans objet) |

Cela donne une **traçabilité bidirectionnelle** : un commit qui modifie `step_morph.py:get_easing_function` SANS toucher ces tests doit lever un drapeau au reviewer.

---

## Validation attendue

Réponds **`OK phase C → continue`** pour passer à Phase D (diagnostic exigeant ligne par ligne de la matrice B.3 — chaque widget ⚠️/❌ examiné en détail, décision retenir/retirer/câbler documentée).
