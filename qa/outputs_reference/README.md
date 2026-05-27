# outputs_reference/

Vérités terrain pour la non-régression. Pour chaque test ayant une sortie comparable,
un fichier `ref_<test_id>.<ext>` est conservé ici.

## Conventions

Les vidéos `.mp4` ne sont **pas comparées byte-à-byte** (encodeur non déterministe).
On compare des **signatures** :

| Type sortie | Fichier référence | Comparaison |
|---|---|---|
| `.mp4` (vidéo) | `ref_<id>.ffprobe.json` | clés `codec_name`, `pix_fmt`, `width`, `height`, `r_frame_rate`, `nb_frames` (tolérance ±2 frames) |
| `run_summary.json` | `ref_<id>.summary.json` | comparaison structurelle (clés présentes, types corrects) — pas de valeur exacte sur les chemins absolus |
| `metadata.txt` | `ref_<id>.metadata.txt` | match exact des clés ; tolérance sur les valeurs (timestamps, paths) |
| `.gif` | `ref_<id>.gif.info` | dimensions + nombre de frames |
| `.jpg` (thumbnail) | `ref_<id>.thumb.info` | dimensions |

## Comment générer une référence

Première exécution d'un test sur un environnement connu correct :

```bash
# 1. Lancer le test via run_tests.py
python qa/scripts/run_tests.py --only T-074

# 2. Promouvoir la sortie en référence
python qa/scripts/compare_outputs.py --promote T-074
```

## Conventions de nommage

`ref_<test_id>.<format_specific>` — par exemple :
- `ref_T-074.ffprobe.json` (signature ffprobe de la vidéo nominal)
- `ref_T-076.ffprobe.json` (signature 720p)
- `ref_T-081.summary.json` (run_summary attendu)

## État actuel

Le dossier est **vide à l'initialisation**. Les références sont à produire à la
première exécution d'une campagne complète sur un environnement de qualification.
