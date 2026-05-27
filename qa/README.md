# Dossier de qualification — MorphoLapse v2.0.0

Dossier autonome de validation IHM + fonctionnelle.

## Arborescence

```
qa/
├── README.md                          ← ce fichier
├── matrice_tests.xlsx                 ← 118 tests + feuille Synthèse
├── validation_ihm.html                ← checklist interactive autonome (ouvrir en double-clic)
├── rapport_qualification.md           ← squelette à remplir
├── inputs/
│   ├── input_nominal/                 ← 5 PNG 800×800 visages synthétiques
│   ├── input_vide/                    ← 0 image
│   ├── input_1image/                  ← 1 PNG
│   ├── input_volume/                  ← 100 PNG 300×300 (stress IO/mémoire)
│   ├── input_mauvais_format/          ← 3 .png qui sont du texte
│   ├── input_specchars/               ← 5 PNG noms Unicode (éàç, ω, 中文, ±μ°)
│   ├── input_limite_haute/            ← 5 PNG 2000×2000 (mémoire)
│   ├── input_limite_basse/            ← 2 PNG 64×64
│   ├── input_corrompu/                ← 3 PNG tronqués (50 bytes)
│   ├── input_no_face/                 ← 3 gradients (dlib échoue)
│   └── input_reel/                    ← placeholder pour photos réelles fournies
├── outputs_reference/
│   ├── README.md                      ← conventions de signature
│   └── ref_<id>.<ext>                 ← (vide à l'init, à produire/promouvoir)
├── outputs_reels/                     ← rempli par run_tests.py
└── scripts/
    ├── generate_inputs.py             ← régénère tous les inputs (idempotent)
    ├── generate_matrix.py             ← régénère matrice_tests.xlsx
    ├── run_tests.py                   ← exécute la campagne CLI
    └── compare_outputs.py             ← compare réels vs références
```

## Démarrage rapide

### 1. (Re)générer les inputs

```bash
python qa/scripts/generate_inputs.py
```

### 2. Ouvrir la checklist IHM manuelle

Double-clic sur `qa/validation_ihm.html`. Saisir testeur + date. Cocher OK / NOK / NA
pour chaque ligne et compléter « Valeur observée » + « Commentaire ». Les saisies sont
sauvegardées automatiquement dans `localStorage`. Boutons :

- **📥 Exporter JSON** : sauvegarde l'état complet (à joindre au rapport)
- **📋 Résumé Markdown** : copie un bloc Markdown dans le presse-papier (à coller dans `rapport_qualification.md`)
- **🖨️ Imprimer** : version optimisée papier pour dossier qualité

### 3. Lancer les tests CLI automatisés

```bash
# Lister les tests CLI disponibles
python qa/scripts/run_tests.py --list

# Tout exécuter (peut être long sur input_volume/input_limite_haute)
python qa/scripts/run_tests.py

# Un seul test
python qa/scripts/run_tests.py --only T-074
```

Les sorties vont dans `outputs_reels/<test_id>/` + log dédié `_run.log` par test.
Un rapport JSON global est produit dans `outputs_reels/_run_summary.json`.

### 4. Comparer aux références

Si c'est la première campagne, **promouvoir** les sorties de référence :

```bash
python qa/scripts/compare_outputs.py --promote T-074
```

Puis lors des campagnes suivantes, comparer :

```bash
python qa/scripts/compare_outputs.py
# ou
python qa/scripts/compare_outputs.py --only T-074
```

Le rapport est généré dans `outputs_reels/_comparison_report.md`.

### 5. Remplir le rapport final

Compléter `rapport_qualification.md` en y collant le bloc Markdown généré par le HTML
et en renseignant la décision finale (GO / GO conditionnel / NO-GO).

## Couverture

| Catégorie | Tests | Mode |
|---|---|---|
| IHM | 40 (T-001..T-040) | manuel via `validation_ihm.html` |
| Paramètres | 22 (T-041..T-062) | manuel + scripté |
| Entrées | 12 (T-063..T-074) | scripté via `run_tests.py` |
| Sorties | 8 (T-075..T-082) | scripté + comparaison référence |
| Cas limites | 12 (T-083..T-094) | manuel (renommage dlib/ffmpeg, perms...) |
| Performance | 5 (T-095..T-099) | manuel/instrumenté |
| Robustesse | 8 (T-100..T-107) | manuel (timing annulation) |
| Régression | 11 (T-108..T-118) | manuel ↔ scripté selon test |
| **Total** | **118** | |

## Traçabilité

Chaque test pointe vers une ou plusieurs exigences `REQ-NNN` (colonne `Exigence liée`
de la matrice). Voir la **section 5 du rapport** pour la matrice exigences × tests.

## Limitations connues

- Les inputs synthétiques (`input_nominal`, etc.) **ne contiennent pas de vrais visages**
  détectables par dlib (formes géométriques). Le pipeline atteint `step_morph` qui
  utilise alors le fallback cross-dissolve. Pour valider la **qualité vidéo réelle**, il
  faut déposer des photos dans `input_reel/`.
- Le mode `--cli` actuel n'expose pas toutes les options (résolution, easing) en flags ;
  certains tests de paramétrage sont à exécuter en mode GUI.
- L'interruption FFmpeg pendant `finish_encoding` n'est pas implémentée (cf. pré-rapport audit).
