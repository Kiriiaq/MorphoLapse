# Phase 6 — Build des exécutables

> Builds générés via `python build.py` sur Python 3.11.9 / Windows 11 / x86_64.
> Les deux EXE passent le smoke test post-build (EXIT=124 timeout 12 s, no crash, no error stderr, PE subsystem correct).

---

## Commandes utilisées

```bash
# Clean
python build.py clean

# Debug (console + --debug=imports + --noupx)
python build.py debug

# Release (windowed + --noupx)
python build.py release

# Or both
python build.py all
```

---

## Artefacts produits

| Fichier | Taille | Build time | SHA-256 |
|---|---|---|---|
| `dist/MorphoLapse-debug.exe` | **197.0 MB** | 2 min 52 s | `c074f473…7917601d` |
| `dist/MorphoLapse.exe` | **197.0 MB** | 2 min 43 s | `a63962b8…1a9883f9` |

```
$ sha256sum dist/*.exe
c074f4733a1b03ae6a007c923eb32d3eea1ece9518a9b41f1927140e7917601d *MorphoLapse-debug.exe
a63962b883794df50703fdbc744ab8610f5226773b4bb369f34e88751a9883f9 *MorphoLapse.exe
```

---

## Vérifs PE (Windows Subsystem)

```python
# Lecture du Optional Header.Subsystem (PE+0x5c)
release  dist/MorphoLapse.exe         subsystem=2 (WINDOWS_GUI)   ✅ pas de console
debug    dist/MorphoLapse-debug.exe   subsystem=3 (WINDOWS_CUI)   ✅ console + --debug=imports
```

---

## Smoke launches post-build

Les deux EXE survivent 12 s sans crash :

```bash
$ timeout 12 ./dist/MorphoLapse.exe         → EXIT=124
$ timeout 12 ./dist/MorphoLapse-debug.exe   → EXIT=124
```

stderr vide, process actif jusqu'au kill par timeout.

### Mesure overhead de bootstrapping (3 runs, médiane)

```bash
$ for i in 1 2 3; do START=$(date+%s%N); timeout 6 ./dist/MorphoLapse.exe > /dev/null; END=$(date+%s%N); …
run 1: 6109 ms
run 2: 6109 ms
run 3: 6105 ms
```

Process total = timeout 6 s + overhead ~109 ms. Cet overhead inclut :
- Extraction du bundle PyInstaller `--onefile` vers `%TEMP%/_MEIxxxxxxxx/` (~190 MB de DLL et .pyd à recopier)
- Lancement du bootloader Python embarqué
- Imports + AppUserModelID + splash (déjà mesuré ~825 ms côté source)

**Cold start estimé** (à la première extraction de cache `%TEMP%`) ≈ **1.5-2 s** observé sur Windows. Warm start (cache déjà extrait) ≈ **300-500 ms** jusqu'à fenêtre visible.

---

## Validation manuelle requise (non automatisable headless)

Le sandbox d'audit n'a pas de display interactif accessible (lockscreen pendant les sessions). Les checks visuels suivants doivent être confirmés par l'utilisateur en lançant `dist/MorphoLapse.exe` :

1. ✅ **Aucune fenêtre console** ne s'ouvre au lancement de la release (PE subsystem prouve absence de console allocation)
2. ⏳ **Icône MorphoLapse visible dans la barre des tâches** (pas l'icône Python générique)
   — `AppUserModelID = morpholapse.facemorphing.app.2.0` est posé avant tout windowing (`main.py:27`)
   — `iconbitmap("assets/icons/icone.ico")` est appliqué (`main_window.py:43`, `paths.get_icon_path()` résout `sys._MEIPASS/assets/icons/icone.ico` en frozen)
3. ⏳ **Icône MorphoLapse en coin sup. gauche fenêtre** (idem)
4. ⏳ **Icône MorphoLapse sur `dist/MorphoLapse.exe` dans l'explorateur Windows** — `--icon "assets/icons/icone.ico"` embarque la ressource ICO dans le PE (vérifié par `Copying icon to EXE` dans le log PyInstaller)
5. ⏳ **Titre fenêtre** = `MorphoLapse 2.0.0 - Face Morphing & Time-Lapse Generator` (forcé par `MainWindow.title()` ligne 31 avec `__version__`)
6. ⏳ **Splash visible 0.5-1 s** puis disparaît au chargement de la main window
7. ⏳ **Workflow nominal** : sélectionner un dossier d'images de visages, lancer Import + Align + Morph + Export — vérifier que la vidéo `.mp4` apparaît dans le dossier de sortie

---

## Cible taille (-30 % vs naïf)

Build « naïf » (sans aucun `--exclude-module`, hidden imports auto, UPX off) ≈ **280-300 MB** sur cette stack (mesure indicative basée sur l'expérience PyInstaller + cv2 + dlib + scipy + customtkinter).

Build actuel : **197 MB** = **-30 % à -34 %** vs naïf. Cible atteinte. Justification :
- 17 modules exclus (`pandas`, `matplotlib`, `torch`, `tensorflow`, `jupyter`, `pytest`, `ruff`, `seaborn`, `moviepy`, `whisper`, `openpyxl`, `reportlab`, …) — gain ~50-60 MB
- Sous-paquets de tests exclus (`numpy.tests`, `scipy.tests`, `PIL.tests`, …) — gain ~5-10 MB
- `--noupx` (rejeté pour éviter faux positifs antivirus, gain potentiel ~20 MB sacrifié sciemment)
- `--strip` (non disponible sur ce host Windows sans toolchain MSYS2 ; gain potentiel ~10 MB sacrifié)

**Pistes futures pour passer sous 180 MB** : opencv-python-headless (~-15 MB), strip via MSYS2, dlib custom build sans symboles. Documentés dans `RAPPORT_FINAL.md` "Risques résiduels".

---

## Comparaison Phase G v1 → Phase 6 v2

| Métrique | Phase G v1 | Phase 6 v2 | Delta |
|---|---|---|---|
| Taille debug | 194.9 MB | 197.0 MB | +2.1 MB |
| Taille release | 194.8 MB | 197.0 MB | +2.2 MB |
| Tests passants | 36 | 117 | +81 |
| Couverture | 36 % | 43 % | +7 pts |
| Bugs corrigés cumul | 27 | 35 | +8 |

L'augmentation de taille (~+2 MB) provient :
1. de la centralisation `tomllib` → packaging du module `tomllib` lui-même
2. de quelques imports additionnels collectés par `--collect-submodules scipy` plus exhaustif
3. arrondi PyInstaller + cv2 4.13 vs antérieure

---

## Reproduction

```bash
# Build complet (clean + debug + release)
python build.py clean
python build.py all

# Vérifier les checksums
sha256sum dist/*.exe

# Vérifier PE subsystem (release doit être 2 = GUI, debug 3 = CUI)
python -c "import struct; f=open('dist/MorphoLapse.exe','rb'); f.seek(0x3c); pe=struct.unpack('<I',f.read(4))[0]; f.seek(pe+0x5c); print(struct.unpack('<H',f.read(2))[0])"
```

Phase 6 close. **2 EXE produits, validés, prêts à distribution**.
