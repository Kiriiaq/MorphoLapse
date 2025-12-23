# MorphoLapse

> **L'evolution de votre visage en video** - Logiciel professionnel de morphing facial

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/Kiriiaq/MorphoLapse/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

---

## Qu'est-ce que MorphoLapse ?

**MorphoLapse** transforme une collection de photos en une **video time-lapse fluide** montrant l'evolution d'un visage au fil du temps.

### Cas d'utilisation

- **Time-lapse de grossesse** : Documentez 9 mois en video
- **Evolution d'un enfant** : De bebe a adulte en quelques secondes
- **Transformation physique** : Perte de poids, musculation
- **Projet artistique** : Morphing entre differentes personnes

---

## Telechargement

### Executables prets a l'emploi

| Version | Description | Telechargement |
|---------|-------------|----------------|
| **Production** | Sans console, utilisation normale | `MorphoLapse-v2.0.0-win64.zip` |
| **Debug** | Avec console, logs detailles | `MorphoLapse_debug-v2.0.0-win64.zip` |

> **Prerequis** : [FFmpeg](https://ffmpeg.org/download.html) doit etre installe sur votre systeme.

### Difference Production vs Debug

| Caracteristique | Production | Debug |
|-----------------|------------|-------|
| Console Windows | Non | Oui |
| Logs detailles | Non | Oui |
| Taille | Optimise | Plus lourd |
| Usage | Utilisateur final | Developpement/diagnostic |

---

## Installation

### Option 1 : Executable (recommande)

1. Telechargez l'archive correspondant a votre systeme
2. Extrayez l'archive
3. Lancez `MorphoLapse.exe`

### Option 2 : Depuis les sources

```bash
# Cloner le projet
git clone https://github.com/Kiriiaq/MorphoLapse.git
cd MorphoLapse

# Installer les dependances
pip install -r requirements.txt

# Telecharger le modele dlib (necessaire)
# http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2

# Lancer l'application
python main_app.py
```

---

## Utilisation

### En 3 etapes

1. **Preparez vos images**
   - Photos en vue frontale du visage
   - Nommees dans l'ordre chronologique (001.jpg, 002.jpg, ...)

2. **Lancez MorphoLapse**
   - Selectionnez le dossier contenant vos images
   - Ajustez les parametres (FPS, transition, qualite)
   - Cliquez sur "Lancer"

3. **Recuperez votre video**
   - La video est generee dans le dossier `runs/`

### Mode ligne de commande

```bash
# Morphing simple
python main_app.py --cli -i photos/ -o resultat/

# Avec options avancees
python main_app.py --cli -i photos/ --fps 30 --transition 2.0
```

---

## Fonctionnalites

### Interface
- Design sombre moderne (CustomTkinter)
- Panneau d'options repliable
- Logs en temps reel
- Raccourcis clavier (F1 pour l'aide)

### Moteur de morphing
- Detection 68 points de repere (dlib)
- Alignement Procrustes
- Triangulation Delaunay
- 6 courbes d'easing : linear, ease_in, ease_out, ease_in_out, cubic, bounce
- 4 modes de blend : alpha, additive, multiply, screen

### Parametres

| Parametre | Description | Defaut |
|-----------|-------------|--------|
| FPS | Images/seconde | 25 |
| Transition | Duree en secondes | 3.0 |
| Pause | Entre images | 0.0 |
| Qualite | Compression | high |
| Format | Container video | MP4 |

---

## Build (developpeurs)

### Generer les executables

```bash
# Installer PyInstaller
pip install pyinstaller

# Build complet (production + debug + archives)
python build.py --all

# Build production uniquement
python build.py --production

# Build debug uniquement
python build.py --debug

# Nettoyer les fichiers de build
python build.py --clean
```

### Structure des fichiers de build

```
MorphoLapse.spec        # Configuration PyInstaller production
MorphoLapse_debug.spec  # Configuration PyInstaller debug
build.py                # Script de build automatise
```

---

## Architecture

```
MorphoLapse/
├── main_app.py              # Point d'entree
├── build.py                 # Script de build
├── MorphoLapse.spec         # Config PyInstaller (prod)
├── MorphoLapse_debug.spec   # Config PyInstaller (debug)
├── src/
│   ├── core/                # Moteurs de traitement
│   │   ├── face_detector.py
│   │   ├── face_aligner.py
│   │   ├── face_morpher.py
│   │   └── video_encoder.py
│   ├── modules/             # Workflow
│   │   ├── workflow_manager.py
│   │   ├── step_import.py
│   │   ├── step_align.py
│   │   ├── step_morph.py
│   │   └── step_export.py
│   ├── ui/                  # Interface
│   │   ├── main_window.py
│   │   ├── widgets.py
│   │   ├── keyboard_manager.py
│   │   └── help_system.py
│   └── utils/               # Utilitaires
│       ├── logger.py
│       ├── config_manager.py
│       ├── export_manager.py
│       └── validators.py
├── config/                  # Configuration
├── ico/                     # Icones
│   └── icone.ico
└── tests/                   # Tests
```

---

## FAQ

**Le morphing ne fonctionne pas correctement**
- Assurez-vous que les visages sont en vue frontale
- Les lunettes de soleil peuvent perturber la detection

**La video n'est pas generee**
- Verifiez que FFmpeg est installe et dans le PATH

**Comment obtenir de meilleurs resultats ?**
- Utilisez des images avec un eclairage similaire
- Gardez une position de tete coherente

---

## Licence

**MIT License** - Utilisation commerciale autorisee sans restriction.

---

## Credits

- Projet original : [face-movie](https://github.com/andrewdcampbell/face-movie) par Andrew Campbell
- Detection faciale : [dlib](http://dlib.net/)
- Interface : [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- Encodage : [FFmpeg](https://ffmpeg.org/)

---

<p align="center">
  <b>MorphoLapse v2.0.0</b><br>
  <a href="https://github.com/Kiriiaq/MorphoLapse/releases">Telecharger</a> |
  <a href="https://github.com/Kiriiaq/MorphoLapse/issues">Signaler un bug</a>
</p>
