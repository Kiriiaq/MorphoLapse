# _archive/

Modules retirés de `src/` pendant l'audit (Phase E commit 11) car aucun code n'en dépendait au runtime.

| Fichier | LOC | Raison de l'archivage | Réintégration ? |
|---|---|---|---|
| `export_manager.py` | 666 | Aucun import dans le projet ; dépend de `openpyxl` et `reportlab` qui ne sont pas dans `pyproject.toml`. Le fichier était ré-exporté par `src/utils/__init__.py` mais jamais consommé. | Si un export Excel/PDF/CSV est demandé un jour, déplacer le fichier dans `src/utils/`, déclarer `openpyxl`/`reportlab` dans `pyproject.toml [project] dependencies` et ajouter un appelant. |
| `validators.py` | 612 | `InputValidator`/`WorkflowValidator` jamais importés ; la validation est faite ad-hoc dans `src/modules/step_import.py::validate_image_file`. | Si la validation est centralisée à terme, déplacer dans `src/utils/`, ajouter au moins un test unitaire qui ne soit pas un simple `import`. `read_file_with_encoding_fallback` peut être déplacé séparément si un consommateur émerge. |

`ALLOW_DELETE=NO` lors de l'audit ; ces fichiers sont conservés ici pour traçabilité plutôt que supprimés. Ils ne sont **plus chargés** par l'application (`src/utils/__init__.py` ne les importe plus).
