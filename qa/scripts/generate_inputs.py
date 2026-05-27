#!/usr/bin/env python3
"""Génère tous les jeux d'inputs synthétiques pour la qualification MorphoLapse.

Usage :
    python qa/scripts/generate_inputs.py

Crée / régénère les dossiers sous qa/inputs/. Idempotent : supprime et recrée.

Note : les "visages" synthétiques sont volontairement des formes géométriques
non détectables par dlib (pas de landmarks 68 points). Ils servent à valider
le pipeline IHM + chemins d'erreur (no-face). Pour les tests fonctionnels
vidéo réels (qualité d'encodage, easing, etc.), fournir des photos réelles
dans qa/inputs/input_reel/.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

TEST_DIR = Path(__file__).resolve().parent.parent
INPUTS_DIR = TEST_DIR / "inputs"


def _draw_synthetic_face(size: int, variant: int) -> Image.Image:
    """Dessine un "visage" géométrique 800×800 (ou size×size).

    Sert pour les tests IHM. Ne contient pas de vrais landmarks dlib.
    Le variant module la position des éléments pour donner de la diversité.
    """
    img = Image.new("RGB", (size, size), color=(230, 215, 195))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    offset = (variant - 2) * (size // 40)  # déplacement de ±5% selon variant

    # Visage (ovale beige clair)
    draw.ellipse(
        [cx - size // 3, cy - size // 2 + offset, cx + size // 3, cy + size // 2 + offset],
        fill=(245, 225, 200),
        outline=(180, 150, 130),
        width=3,
    )
    # Œil gauche
    draw.ellipse(
        [cx - size // 5 - 30, cy - size // 8 + offset, cx - size // 5 + 30, cy - size // 8 + 40 + offset],
        fill=(60, 60, 80),
    )
    # Œil droit
    draw.ellipse(
        [cx + size // 5 - 30, cy - size // 8 + offset, cx + size // 5 + 30, cy - size // 8 + 40 + offset],
        fill=(60, 60, 80),
    )
    # Nez
    draw.polygon(
        [
            (cx, cy - 20 + offset),
            (cx - 25, cy + 80 + offset),
            (cx + 25, cy + 80 + offset),
        ],
        fill=(220, 195, 170),
        outline=(180, 150, 130),
    )
    # Bouche
    draw.arc(
        [cx - 80, cy + 100 + offset, cx + 80, cy + 180 + offset],
        start=10,
        end=170,
        fill=(150, 60, 60),
        width=8,
    )
    return img.filter(ImageFilter.GaussianBlur(radius=0.5))


def _draw_gradient(size: int, variant: int) -> Image.Image:
    """Image gradient pur — aucun visage détectable."""
    img = Image.new("RGB", (size, size))
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            r = (x * 255) // size
            g = (y * 255) // size
            b = (variant * 50) % 256
            pixels[x, y] = (r, g, b)
    return img


def _draw_garbage_text(path: Path) -> None:
    """Crée un fichier .png qui est en réalité du texte (magic bytes invalides)."""
    path.write_text("Ceci n'est pas une image PNG.\nMauvais format intentionnel.\n", encoding="utf-8")


def _draw_truncated_png(path: Path) -> None:
    """Crée un PNG tronqué après ~50 bytes (magic bytes corrects mais corps coupé)."""
    img = Image.new("RGB", (200, 200), color=(100, 100, 100))
    tmp = path.with_suffix(".tmp")
    img.save(tmp, format="PNG")
    raw = tmp.read_bytes()
    tmp.unlink()
    # Garder uniquement les 50 premiers bytes (magic PNG = 8 bytes + IHDR partiel)
    path.write_bytes(raw[:50])


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def generate_nominal() -> None:
    """5 PNG 800×800 visages synthétiques (variation progressive)."""
    out = INPUTS_DIR / "input_nominal"
    _reset_dir(out)
    for i in range(5):
        img = _draw_synthetic_face(800, variant=i)
        img.save(out / f"face_{i:03d}.png", format="PNG", optimize=True)
    print("  input_nominal/ : 5 PNG 800x800")


def generate_vide() -> None:
    out = INPUTS_DIR / "input_vide"
    _reset_dir(out)
    (out / ".gitkeep").touch()
    print("  input_vide/ : 0 image")


def generate_1image() -> None:
    out = INPUTS_DIR / "input_1image"
    _reset_dir(out)
    img = _draw_synthetic_face(800, variant=0)
    img.save(out / "face_unique.png", format="PNG", optimize=True)
    print("  input_1image/ : 1 PNG")


def generate_volume(n: int = 100) -> None:
    """N PNG 300×300 pour stress mémoire/IO sans saturer le repo."""
    out = INPUTS_DIR / "input_volume"
    _reset_dir(out)
    for i in range(n):
        img = _draw_synthetic_face(300, variant=i % 5)
        img.save(out / f"vol_{i:04d}.png", format="PNG", optimize=True)
    print(f"  input_volume/ : {n} PNG 300x300")


def generate_mauvais_format() -> None:
    out = INPUTS_DIR / "input_mauvais_format"
    _reset_dir(out)
    for i in range(3):
        _draw_garbage_text(out / f"fake_{i:03d}.png")
    print("  input_mauvais_format/ : 3 fichiers texte avec extension .png")


def generate_specchars() -> None:
    """Noms de fichiers avec caractères Unicode (UTF-8)."""
    out = INPUTS_DIR / "input_specchars"
    _reset_dir(out)
    names = [
        "éàçù_001.png",
        "ω_002.png",
        "中文_003.png",
        "émoji_face_004.png",
        "deg±μ_005.png",
    ]
    for i, name in enumerate(names):
        img = _draw_synthetic_face(800, variant=i)
        img.save(out / name, format="PNG", optimize=True)
    print("  input_specchars/ : 5 PNG avec noms Unicode")


def generate_limite_haute() -> None:
    """5 PNG 2000×2000 pour stress mémoire."""
    out = INPUTS_DIR / "input_limite_haute"
    _reset_dir(out)
    for i in range(5):
        img = _draw_synthetic_face(2000, variant=i)
        img.save(out / f"big_{i:03d}.png", format="PNG", optimize=True)
    print("  input_limite_haute/ : 5 PNG 2000x2000")


def generate_limite_basse() -> None:
    """2 PNG 64×64 (en dessous des seuils de détection raisonnables)."""
    out = INPUTS_DIR / "input_limite_basse"
    _reset_dir(out)
    for i in range(2):
        img = _draw_synthetic_face(64, variant=i)
        img.save(out / f"tiny_{i:03d}.png", format="PNG", optimize=True)
    print("  input_limite_basse/ : 2 PNG 64x64")


def generate_corrompu() -> None:
    """3 PNG tronqués (50 bytes)."""
    out = INPUTS_DIR / "input_corrompu"
    _reset_dir(out)
    for i in range(3):
        _draw_truncated_png(out / f"corrupt_{i:03d}.png")
    print("  input_corrompu/ : 3 PNG tronqués (50 bytes)")


def generate_no_face() -> None:
    """3 PNG gradients sans aucun visage."""
    out = INPUTS_DIR / "input_no_face"
    _reset_dir(out)
    for i in range(3):
        img = _draw_gradient(800, variant=i)
        img.save(out / f"gradient_{i:03d}.png", format="PNG", optimize=True)
    print("  input_no_face/ : 3 PNG gradients")


def generate_reel_placeholder() -> None:
    """Dossier pour photos réelles fournies par l'utilisateur."""
    out = INPUTS_DIR / "input_reel"
    out.mkdir(parents=True, exist_ok=True)
    readme = out / "README.md"
    readme.write_text(
        "# input_reel\n\n"
        "Déposer ici **3 à 5 photos réelles de visages** (de face, éclairage similaire,\n"
        "nommés `000.jpg`, `001.jpg`, ...) pour les tests fonctionnels vidéo réels :\n"
        "- T-063 nominal vidéo\n"
        "- T-075..T-082 sorties (résolution, easing, etc.)\n\n"
        "**Pas généré automatiquement** (RGPD).\n",
        encoding="utf-8",
    )
    print("  input_reel/ : placeholder (à fournir manuellement)")


def main() -> int:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Génération des inputs dans {INPUTS_DIR} ...")
    generate_nominal()
    generate_vide()
    generate_1image()
    generate_volume(n=100)
    generate_mauvais_format()
    generate_specchars()
    generate_limite_haute()
    generate_limite_basse()
    generate_corrompu()
    generate_no_face()
    generate_reel_placeholder()
    print("OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
