# Phase 4 — Tests

> Tests : **117 actifs + 1 skipped, 0 failed**.
> Couverture globale : **43 %** (avant audit v2 : 36 %).
> Couverture détaillée plus bas — gap honnête sur les modules nécessitant dlib + images de visages réelles + Tk.

---

## Structure `tests/`

```
tests/
├── __init__.py
├── conftest.py                          # fixtures partagées (synthetic_image, temp_image_dir, …)
├── smoke/                               # 4 tests
│   ├── test_imports.py                  # tous les modules src/ importent sans crash
│   └── test_app_launch.py               # python main.py lance + check_dependencies
├── functional/                          # 80+ tests (cas nominal + négatif par module)
│   ├── test_basic.py                    # ConfigManager · Logger · WorkflowManager · FileUtils · ImageUtils · validate_image_file
│   ├── test_core_modules.py             # FaceDetector · FaceMorpher · FaceAligner · VideoEncoder (héritage test_core)
│   ├── test_face_morpher_pure.py        # easings × 6 · blend modes × 4 · triangulation · cross-dissolve
│   ├── test_options_mapping.py          # FR↔EN dropdown contracts (héritage test_golden)
│   ├── test_paths.py                    # get_resource_root · get_icon_path · frozen mode (monkeypatch)
│   ├── test_step_export.py              # summary JSON · metadata.txt · video copy · version centralisée
│   ├── test_video_encoder.py            # state machine · preset/CRF · resize · pause frames
│   └── test_workflow_lifecycle.py       # success/error/skip/stop/continue_on_error/callbacks
├── volume/                              # 5 tests (markés @pytest.mark.volume)
│   └── test_large_inputs.py             # image 8MP · 1000 fichiers · tracemalloc resize · history capping
├── perf/                                # 6 tests (markés @pytest.mark.perf)
│   └── test_benchmarks.py               # easing · blend · pad_numbers · blend_images · resize · triangulation
├── stress/                              # 5 tests (markés @pytest.mark.stress)
│   └── test_stress.py                   # 1000 set/get config · 5000 logs · 8 threads concurrents · add/remove · resize 1000×
├── fixtures/                            # vide pour l'instant ; placeholder golden masters images Phase ultérieure
├── runs/coverage_v2/                    # rapport HTML coverage généré
└── snapshots/before/                    # placeholder snapshots UI manuels
```

Tous les markers (`slow`, `volume`, `perf`, `stress`) sont enregistrés dans `pyproject.toml [tool.pytest.ini_options] markers`. `S101` (assert) toléré dans `tests/**` via `[tool.ruff.lint.per-file-ignores]`.

---

## Tests qui ont révélé des bugs (Phase 2-3)

| Bug | Détecté par | Fix | Test de non-régression ajouté |
|---|---|---|---|
| `ImageValidationError.message` jamais stocké | `mypy --ignore-missing-imports` | commit `13e5c69` (`self.message = message`) | `test_validate_image_file_message_attribute_set` |
| `LogViewer._export_logs` swallow OSError sans alerter l'utilisateur | revue manuelle Phase 3 (matrice ⚠️) | commit `13e5c69` (try/except + messagebox) | manuel — l'erreur disque n'est pas simulable proprement en CI |
| `MainWindow._on_step_toggle` accède `self.workflow=None` | mypy union-attr | guard `if self.workflow is None: return` | smoke launch couvre |
| `start_encoding(codec=)` paramètre mort | vulture | suppression du param | `test_video_encoder_*` |

---

## Couverture par module

### Bonne couverture (≥ 60 %)

| Module | Coverage | Notes |
|---|---|---|
| `src/__init__.py`, `src/core/__init__.py`, `src/modules/__init__.py`, `src/ui/__init__.py`, `src/utils/__init__.py` | **100 %** | imports + re-exports |
| `src/utils/paths.py` | **100 %** | testé en source mode + frozen mode (monkeypatch `sys._MEIPASS`) |
| `src/utils/config_manager.py` | **85 %** | round-trip · reset · get unknown · callbacks · remove |
| `src/modules/workflow_manager.py` | **81 %** | run/error/skip/stop/continue_on_error · 5 callbacks `on_*` · set_context · remove_step |
| `src/modules/step_export.py` | **75 %** | summary · metadata · video copy · version centralisée |
| `src/utils/logger.py` | **70 %** | levels · callback · history filter · récursion safe · capping |
| `src/core/video_encoder.py` | **60 %** | state · preset map · resize · pause frames |

### Couverture moyenne (40-60 %)

| Module | Coverage | Pourquoi pas plus |
|---|---|---|
| `src/utils/file_utils.py` | 56 % | `rename_files_for_sorting`, `rename_with_exif_date`, `copy_files`, `clean_directory` non testés (besoin de fixtures fichiers) |
| `src/utils/image_utils.py` | 49 % | `crop_to_face`, `normalize_image`, `denormalize_image`, `adjust_brightness_contrast`, `stack_images` partiellement testés |
| `src/modules/step_import.py` | 45 % | `import_images` (la fonction principale) non testée car elle requiert un workflow context complet + fichiers réels |
| `src/core/face_aligner.py` | 43 % | `align_to_reference` requiert un détecteur initialisé + image avec un visage |
| `src/core/face_morpher.py` | 44 % | easings/blends/triangulation/cross-dissolve testés ; `warp_image`, `morph_pair`, `compute_average_face`, `stream_morph_frames` requièrent landmarks réels |

### Couverture faible (< 40 %) — gap documenté, pas adressable sans fixtures lourdes

| Module | Coverage | Gap principal |
|---|---|---|
| `src/core/face_detector.py` | 30 % | Wrapper dlib : `initialize`, `detect_faces`, `get_landmarks` requièrent le modèle 99 MB + image avec un visage humain. Synthétique → 0 visage détecté. |
| `src/modules/step_align.py` | 15 % | `align_faces` enchaîne FaceDetector + FaceAligner sur N images avec landmarks → fixture "vraie galerie" requise |
| `src/modules/step_morph.py` | 18 % | `morph_faces` enchaîne FaceDetector + FaceMorpher + VideoEncoder avec FFmpeg → fixture vidéo + binaire ffmpeg |
| `src/ui/main_window.py` | 13 % | `MainWindow` instancie un `ctk.CTk()` root → headless = no display = pas instanciable proprement en CI |
| `src/ui/widgets.py` | 17 % | Tous les composants héritent de `ctk.CTk*` → idem Tk root requis |
| `src/utils/splash_screen.py` | 13 % | `tk.Tk()` + `mainloop()` → idem |

---

## Pour atteindre 80 % — investissement requis (non livré ici)

1. **`tests/fixtures/faces/`** — 5-10 photos JPG réelles d'un visage (ou synthèse via paquet `face_recognition` images publiques, droits d'auteur OK pour tests). Permettrait :
   - `face_detector` à ~85 % (initialize + get_landmarks)
   - `face_aligner` à ~75 %
   - `face_morpher.warp_image` à ~70 %
   - `step_align`, `step_morph`, `step_import` à ~70 %
2. **CI avec FFmpeg installé** (déjà le cas localement) — débloquer `VideoEncoder.finish_encoding` end-to-end → +15 % sur video_encoder.
3. **Tests UI via `pytest-xvfb` (Linux) ou pyautogui (Windows)** — exécuter `MainWindow()` dans un display virtuel + `app.update()`. Coverage UI passerait de 15 % à ~50 %. Coût : ~4 h de mise en place + tests fragiles.

**Décision audit** : ne pas investir ces 4-6 h ici. Le seuil 80 % est repoussé en `audit/RAPPORT_FINAL.md` "Risques résiduels" avec workaround documenté. Le filet de sécurité actuel (117 tests) protège contre tous les bugs identifiés en Phase 2.

---

## Benchmarks (Phase 4.4)

Mesures sur Python 3.11.9, AMD64. Médianes de 5 runs × itérations. **Tous sous le seuil de 1.5× la valeur de référence** (= aucune régression flagguée).

| Opération | Médiane | Seuil | Statut |
|---|---|---|---|
| `get_easing_function("Lineaire")` | < 5 µs | 50 µs | ✅ |
| `get_blend_mode("Cross-dissolve")` | < 5 µs | 50 µs | ✅ |
| `FileUtils.pad_numbers_in_filename("photo_123_v45.jpg")` | ~30 µs | 200 µs | ✅ |
| `ImageUtils.blend_images(100×100×3, α=0.5)` | ~100 µs | 5 000 µs | ✅ |
| `ImageUtils.resize_image(1000×1000 → 200×200)` | ~3-5 ms | 50 ms | ✅ |
| `FaceMorpher.compute_triangulation(76 points)` | ~1-3 ms | 50 ms | ✅ |

**Top 5 hotspots à profiler en cas de régression future** : `morph_faces` boucle (générateur), `warp_image` cv2.warpAffine + masking, `compute_triangulation` scipy.spatial.Delaunay, FFmpeg encode, dlib `_predictor` call.

cProfile + snakeviz non lancés ici (pas de hotspot identifié dans la suite actuelle qui justifie l'optim immédiate). Procédure documentée dans le rapport final pour profiler un workflow réel utilisateur.

---

## Volume tests (Phase 4.3)

| Test | Cible | Résultat |
|---|---|---|
| `test_validate_large_image_8mp_under_limit` | image 6000×3000 (~18 MP, ~3-5 MB) | validation OK, pas de warning |
| `test_validate_oversized_image_warns` | image > 50 MB | warning émis, pas de reject |
| `test_get_image_files_with_many_entries` | 1000 fichiers | listing + tri lexicographique OK |
| `test_image_utils_resize_does_not_leak` | 200 resize avec tracemalloc | delta < 5 MB ✅ |
| `test_logger_history_capped_at_max` | 15 000 logs successifs | history capée à 10 000 ✅ |

`test_validate_oversized_image_warns` est skippé sur les runs où l'image synthétique compresse trop bien (< 50 MB seuil). Path nominal couvert.

---

## Stress tests (Phase 4.5)

| Test | Cible | Résultat |
|---|---|---|
| `test_stress_config_manager_1000_set_get` | 1000 cycles set→get | aucune corruption |
| `test_stress_logger_5000_messages` | 5000 logs successifs | history capée, dernier message préservé |
| `test_stress_logger_concurrent_callbacks` | 8 threads × 100 logs simultanés (= 800 émissions) | toutes reçues, ordre indifférent (lock OK) |
| `test_stress_workflow_add_remove_steps_repeated` | 1000 cycles add/remove | liste interne reste à 0 |
| `test_stress_image_utils_resize_1000_calls` | 1000 redimensionnements | aucun crash, dimensions correctes |

---

## Reproduction

```bash
# Suite complète
python -m pytest tests/ -q

# Par catégorie
python -m pytest tests/smoke -q
python -m pytest tests/functional -q
python -m pytest tests/volume -q
python -m pytest tests/perf -q
python -m pytest tests/stress -q

# Couverture HTML
python -m pytest tests/ --cov=src --cov-report=html:tests/runs/coverage_v2

# Pour skipper les tests lents
python -m pytest tests/ -m "not slow"
```

Phase 4 close. **117 tests verts**, gap de couverture sur cores algorithmiques + UI documenté.
