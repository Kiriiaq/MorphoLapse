"""
Morph Step - Étape de morphing facial
Version optimisée avec gestion mémoire efficace et générateurs
"""

import gc
import os
from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Any

import cv2

from ..core.face_detector import FaceDetector
from ..core.face_morpher import BlendMode, EasingFunction, FaceMorpher, MorphConfig
from ..core.video_encoder import VideoEncoder
from ..utils.image_utils import ImageUtils
from .workflow_manager import WorkflowContext


@dataclass
class ImageData:
    """Données d'une image pour le morphing (version légère)"""

    path: str
    landmarks: Any | None = None
    _image: Any | None = None

    def load_image(self):
        """Charge l'image à la demande"""
        if self._image is None:
            self._image = ImageUtils.load_image(self.path)
        return self._image

    def unload_image(self):
        """Libère la mémoire"""
        self._image = None

    @property
    def image(self):
        return self.load_image()


def image_pair_generator(
    image_paths: list, context: WorkflowContext, detector: FaceDetector, logger=None
) -> Generator[tuple[ImageData, ImageData], None, None]:
    """
    Générateur qui charge les paires d'images à la demande.
    Économise la mémoire en ne gardant que 2 images en mémoire maximum.

    Yields:
        Tuple (image1_data, image2_data)
    """
    prev_data: ImageData | None = None
    # Defensive cast against legacy bool values
    _retry_val = context.config.get("retry_detection", 3)
    try:
        max_attempts = int(_retry_val)
    except (TypeError, ValueError):
        max_attempts = 3
    if max_attempts < 1:
        max_attempts = 3

    for idx, image_path in enumerate(image_paths):
        # Charger l'image actuelle
        image = ImageUtils.load_image(image_path)
        if image is None:
            if logger:
                logger.warning(f"Impossible de charger: {image_path}")
            continue

        # Récupérer les landmarks
        if context.landmarks and idx < len(context.landmarks) and context.landmarks[idx] is not None:
            landmarks = context.landmarks[idx]
        else:
            landmarks = detector.get_landmarks(image, add_boundary=True, max_attempts=max_attempts)

        current_data = ImageData(path=image_path, landmarks=landmarks, _image=image)

        # Yield la paire si on a une image précédente
        if prev_data is not None:
            yield (prev_data, current_data)
            # Libérer la mémoire de l'image précédente (sauf la première qui devient 'prev')
            if idx > 1:
                prev_data.unload_image()

        prev_data = current_data

    # Nettoyage final
    if prev_data:
        prev_data.unload_image()

    gc.collect()


def get_easing_function(easing_name: str) -> EasingFunction:
    """Convertit un nom d'easing (clé EN du backend OU libellé UI FR) en enum.

    Accepte les libellés exacts du dropdown OptionsPanel pour que la valeur
    sélectionnée par l'utilisateur arrive bien au moteur de morphing.
    """
    mapping = {
        # EN backend keys
        "linear": EasingFunction.LINEAR,
        "ease_in": EasingFunction.EASE_IN,
        "ease_out": EasingFunction.EASE_OUT,
        "ease_in_out": EasingFunction.EASE_IN_OUT,
        "cubic": EasingFunction.CUBIC,
        "bounce": EasingFunction.BOUNCE,
        # FR UI labels (OptionsPanel dropdown)
        "Lineaire": EasingFunction.LINEAR,
        "Ease In/Out": EasingFunction.EASE_IN_OUT,
        "Ease In": EasingFunction.EASE_IN,
        "Ease Out": EasingFunction.EASE_OUT,
    }
    return mapping.get(easing_name, EasingFunction.LINEAR)


def get_blend_mode(blend_name: str) -> BlendMode:
    """Convertit un nom de blend mode (clé EN OU libellé UI) en enum.

    Cross-dissolve est traité comme un alpha-blend (c'est ce que fait le
    moteur quand `landmarks` est None — fallback `stream_cross_dissolve`).
    """
    mapping = {
        # EN backend keys
        "alpha": BlendMode.ALPHA,
        "additive": BlendMode.ADDITIVE,
        "multiply": BlendMode.MULTIPLY,
        "screen": BlendMode.SCREEN,
        # UI dropdown labels
        "Normal": BlendMode.ALPHA,
        "Cross-dissolve": BlendMode.ALPHA,
        "Additive": BlendMode.ADDITIVE,
        "Multiply": BlendMode.MULTIPLY,
        "Screen": BlendMode.SCREEN,
    }
    return mapping.get(blend_name, BlendMode.ALPHA)


def morph_faces(context: WorkflowContext, progress_callback: Callable, logger=None) -> dict:
    """
    Étape de morphing des visages avec gestion mémoire optimisée.

    Utilise des générateurs pour ne charger que 2 images à la fois,
    évitant les problèmes de mémoire avec de nombreuses images.

    Args:
        context: Contexte du workflow
        progress_callback: Callback(current, total, message)
        logger: Logger instance

    Returns:
        Dictionnaire des résultats
    """
    if logger:
        logger.info("Démarrage du morphing facial (mode optimisé)")

    # Vérifier les prérequis
    images = context.aligned_images if context.aligned_images else context.images
    if not images:
        raise ValueError("Aucune image pour le morphing")

    if len(images) < 2:
        raise ValueError("Au moins 2 images sont nécessaires pour le morphing")

    # Créer le dossier de morphing
    morph_dir = os.path.join(context.run_dir, "03_morph")
    os.makedirs(morph_dir, exist_ok=True)

    # Récupérer les paramètres
    config = context.config
    fps = config.get("fps", 25)
    transition_duration = config.get("transition_duration", 3.0)
    pause_duration = config.get("pause_duration", 0.0)
    easing_name = config.get("easing", "linear")
    blend_mode_name = config.get("blend_mode", "alpha")

    frames_per_transition = int(fps * transition_duration)
    pause_frames = int(fps * pause_duration)

    # Configurer le morphing
    morph_config = MorphConfig(easing=get_easing_function(easing_name), blend_mode=get_blend_mode(blend_mode_name))

    # Initialiser les composants
    model_path = config.get("model_path", "./shape_predictor_68_face_landmarks.dat")
    detector = FaceDetector(logger=logger)
    if not detector.initialize(model_path):
        raise RuntimeError("Impossible d'initialiser le détecteur")

    morpher = FaceMorpher(logger=logger, config=morph_config)
    encoder = VideoEncoder(logger=logger)

    if not encoder.check_ffmpeg():
        raise RuntimeError("FFmpeg n'est pas disponible")

    # Calculer les dimensions à partir de la première image
    first_image = ImageUtils.load_image(images[0])
    if first_image is None:
        raise ValueError("Impossible de charger la première image")

    h, w = first_image.shape[:2]
    original_ratio = w / h

    # Appliquer la résolution configurée (en gardant le ratio d'aspect)
    resolution = str(config.get("resolution", "original")).lower()
    if resolution != "original":
        # Hauteurs cibles pour chaque résolution
        height_map = {"1080p": 1080, "720p": 720, "480p": 480}
        if resolution in height_map:
            target_h = height_map[resolution]
            target_w = int(target_h * original_ratio)
            # Assurer dimensions paires (requis par H.264)
            target_w = target_w + (target_w % 2)
            target_h = target_h + (target_h % 2)
            w, h = target_w, target_h

    output_path = os.path.join(morph_dir, "morph_video.mp4")

    # Qualité vidéo (preset FFmpeg) — accepte clés EN ou libellés UI FR
    quality = config.get("video_quality", "high")
    quality_map = {
        "low": "ultrafast",
        "medium": "medium",
        "high": "slow",
        "ultra": "slower",
        "Basse": "ultrafast",
        "Moyenne": "medium",
        "Haute": "slow",
        "Maximum": "slower",
    }
    preset = quality_map.get(quality, "medium")

    # Si l'utilisateur a renseigné un dossier intermédiaire pour les frames,
    # on y crée un sous-dossier horodaté pour ne pas mélanger les runs.
    # Sinon, on laisse `start_encoding` créer son sous-dossier par défaut
    # (runs/<ts>/03_morph/frames/).
    user_intermediate = (config.get("intermediate_frames_dir") or "").strip()
    if user_intermediate:
        run_label = os.path.basename(context.run_dir) or "run"
        user_frames_dir = os.path.join(user_intermediate, run_label)
        if logger:
            logger.info(f"Frames externes (choisi par l'utilisateur) : {user_frames_dir}")
    else:
        user_frames_dir = None

    # Threads FFmpeg : lus depuis le contexte (renseignés par MainWindow à
    # partir du sélecteur CPU du sidebar). 0 = auto (libx264 décide),
    # N > 0 = limite stricte (= « Max (N) » sélectionné dans l'UI).
    try:
        ffmpeg_threads = int(config.get("ffmpeg_threads", 0) or 0)
    except (TypeError, ValueError):
        ffmpeg_threads = 0

    if not encoder.start_encoding(
        output_path,
        fps=fps,
        size=(w, h),
        quality=preset,
        frames_dir=user_frames_dir,
        ffmpeg_threads=ffmpeg_threads,
    ):
        raise RuntimeError("Impossible de démarrer l'encodage")

    frame_count = 0
    total_pairs = len(images) - 1
    total_frames_estimate = pause_frames + total_pairs * (frames_per_transition + pause_frames)

    if logger:
        logger.info(f"Estimation: {total_frames_estimate} frames pour {total_pairs} transitions")

    # Écrire les frames de pause initiale
    if pause_frames > 0:
        # Redimensionner si nécessaire
        if first_image.shape[1] != w or first_image.shape[0] != h:
            first_image = cv2.resize(first_image, (w, h))

        for _ in range(pause_frames):
            encoder.write_frame(first_image)
            frame_count += 1

    del first_image
    gc.collect()

    # Traiter les paires d'images avec le générateur
    for pair_idx, (data1, data2) in enumerate(image_pair_generator(images, context, detector, logger)):
        context.raise_if_cancelled()
        progress_callback(
            pair_idx + 1, total_pairs, f"Morphing: {os.path.basename(data1.path)} -> {os.path.basename(data2.path)}"
        )

        if logger:
            logger.info(f"Morphing paire {pair_idx + 1}/{total_pairs}")

        im1 = data1.image
        im2 = data2.image

        # Redimensionner si nécessaire
        if im1.shape[1] != w or im1.shape[0] != h:
            im1 = cv2.resize(im1, (w, h))
        if im2.shape[1] != w or im2.shape[0] != h:
            im2 = cv2.resize(im2, (w, h))

        landmarks1 = data1.landmarks
        landmarks2 = data2.landmarks

        # Vérifier si on peut faire un morphing ou une dissolution.
        # On passe `context.raise_if_cancelled` aux générateurs pour permettre
        # une annulation effective sous 1 frame, même au milieu d'une longue
        # transition (cf. Lot E du Phase 2 audit).
        if landmarks1 is None or landmarks2 is None:
            if logger:
                logger.warning("Visage non détecté, utilisation de dissolution croisée")
            for frame in morpher.stream_cross_dissolve(
                im1, im2, frames_per_transition, check_cancel=context.raise_if_cancelled
            ):
                encoder.write_frame(frame)
                frame_count += 1
        else:
            for frame in morpher.stream_morph_frames(
                im1, im2, landmarks1, landmarks2, frames_per_transition,
                check_cancel=context.raise_if_cancelled,
            ):
                encoder.write_frame(frame)
                frame_count += 1

        # Frames de pause entre les transitions
        if pause_frames > 0:
            for _ in range(pause_frames):
                encoder.write_frame(im2)
                frame_count += 1

        # Forcer le garbage collection après chaque paire
        gc.collect()

    # Génération du viewer HTML AVANT l'encodage : ainsi, pendant que FFmpeg
    # tourne (parfois plusieurs minutes pour de gros morphings), l'utilisateur
    # peut déjà ouvrir le viewer et inspecter la séquence frame par frame.
    if encoder.frames_dir:
        viewer_path = _write_frames_viewer(encoder.frames_dir, fps, frame_count, logger)
        if viewer_path and logger:
            logger.success(f"Viewer frames : {viewer_path}")
            logger.info("→ Double-clic pour faire défiler la séquence (slider, play/pause, flèches).")

    # Callback de progression FFmpeg : forwarde la fraction réelle au step
    # progress de l'UI. On considère l'encodage comme une "phase" qui occupe
    # tout l'espace de progression du step (0% → 100%) au moment où il est
    # appelé — c'est plus utile que de figer la barre pendant l'encodage.
    def _ffmpeg_progress(fraction: float, message: str):
        # progress_callback du workflow attend (current, total, message).
        # On exprime la fraction × 100 sur 100 pour cohérence.
        try:
            progress_callback(int(fraction * 100), 100, message)
        except Exception:
            pass

    # Finaliser l'encodage — on transmet check_cancel pour interruption ffmpeg
    if not encoder.finish_encoding(
        check_cancel=context.raise_if_cancelled,
        progress_callback=_ffmpeg_progress,
    ):
        raise RuntimeError("Erreur lors de la finalisation de l'encodage")

    # Copier la vidéo finale à côté des frames (que ce soit dans le dossier
    # utilisateur ou dans le run par défaut). Permet à preview.html d'avoir
    # un <video> qui pointe sur un MP4 local et de tout regrouper en un endroit.
    if encoder.frames_dir:
        try:
            import shutil as _shutil
            mp4_dest = os.path.join(encoder.frames_dir, "morph_video.mp4")
            if os.path.abspath(output_path) != os.path.abspath(mp4_dest):
                _shutil.copy2(output_path, mp4_dest)
                if logger:
                    logger.info(f"Vidéo copiée à côté des frames : {mp4_dest}")
        except Exception as e:
            if logger:
                logger.warning(f"Copie MP4 vers dossier frames échouée : {e}")

    # Mettre à jour le contexte
    context.output_video = output_path

    # Gérer les exports supplémentaires
    extra_exports = {}

    # Export GIF si demandé
    if config.get("create_gif", False):
        gif_path = create_gif_from_video(output_path, morph_dir, fps, logger)
        if gif_path:
            extra_exports["gif"] = gif_path

    # Export thumbnail si demandé
    if config.get("thumbnail", True):
        thumbnail_path = create_thumbnail(output_path, morph_dir, logger)
        if thumbnail_path:
            extra_exports["thumbnail"] = thumbnail_path

    if logger:
        logger.success(f"Vidéo créée: {output_path} ({frame_count} frames)")
        if extra_exports:
            logger.info(f"Exports additionnels: {list(extra_exports.keys())}")

    return {
        "output_video": output_path,
        "total_frames": frame_count,
        "duration": frame_count / fps,
        "resolution": (w, h),
        "extra_exports": extra_exports,
    }


def create_gif_from_video(video_path: str, output_dir: str, fps: int, logger=None) -> str | None:
    """
    Crée un GIF animé à partir de la vidéo.

    Args:
        video_path: Chemin vers la vidéo source
        output_dir: Dossier de sortie
        fps: FPS de la vidéo source
        logger: Logger

    Returns:
        Chemin du GIF créé ou None
    """
    try:
        import subprocess
        import sys as _sys

        gif_path = os.path.join(output_dir, "morph_preview.gif")

        # Utiliser FFmpeg pour créer le GIF (plus efficace)
        gif_fps = min(fps, 15)  # Limiter le FPS du GIF

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            f"fps={gif_fps},scale=480:-1:flags=lanczos",
            "-loop",
            "0",
            gif_path,
        ]

        # CREATE_NO_WINDOW : éviter la console parasite FFmpeg sous Windows
        # windowed (cf. video_encoder._no_console_kwargs).
        _extra = {}
        if _sys.platform == "win32":
            _extra["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        result = subprocess.run(cmd, capture_output=True, timeout=120, **_extra)  # noqa: S603

        if result.returncode == 0 and os.path.exists(gif_path):
            if logger:
                logger.info(f"GIF créé: {gif_path}")
            return gif_path
        else:
            if logger:
                logger.warning("Échec de la création du GIF")
            return None

    except Exception as e:
        if logger:
            logger.warning(f"Erreur création GIF: {e}")
        return None


def create_thumbnail(video_path: str, output_dir: str, logger=None) -> str | None:
    """
    Crée une miniature à partir de la vidéo.

    Args:
        video_path: Chemin vers la vidéo source
        output_dir: Dossier de sortie
        logger: Logger

    Returns:
        Chemin de la miniature ou None
    """
    try:
        import subprocess
        import sys as _sys

        thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")

        # Extraire une frame au milieu de la vidéo
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", "thumbnail,scale=640:-1", "-frames:v", "1", thumbnail_path]

        _extra = {}
        if _sys.platform == "win32":
            _extra["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        result = subprocess.run(cmd, capture_output=True, timeout=30, **_extra)  # noqa: S603

        if result.returncode == 0 and os.path.exists(thumbnail_path):
            if logger:
                logger.info(f"Miniature créée: {thumbnail_path}")
            return thumbnail_path
        else:
            return None

    except Exception as e:
        if logger:
            logger.warning(f"Erreur création miniature: {e}")
        return None


def _write_frames_viewer(frames_dir: str, fps: int, frame_count: int, logger=None) -> str | None:
    """Génère un viewer HTML autonome pour scruber dans la séquence de frames.

    Le viewer liste les fichiers JPG du dossier `frames_dir`, embarque le
    tableau des noms en JS, et permet :
      - de naviguer frame par frame avec un slider ou les flèches ← / →
      - de lire la séquence en boucle à la vitesse native ou ×0.25 à ×4
      - de sauter en début / fin avec Home / End
      - d'arrêter/reprendre avec la barre Espace

    Retourne le chemin du HTML créé ou None en cas d'échec.
    """
    import json as _json
    try:
        frame_files = sorted(
            f for f in os.listdir(frames_dir)
            if f.lower().startswith("frame_")
            and f.lower().endswith((".jpg", ".jpeg", ".png"))
        )
        if not frame_files:
            return None

        frames_json = _json.dumps(frame_files)
        html = _FRAMES_VIEWER_HTML.replace("__FRAMES_JSON__", frames_json)
        html = html.replace("__FPS__", str(fps))
        html = html.replace("__TOTAL__", str(frame_count))

        viewer_path = os.path.join(frames_dir, "preview.html")
        with open(viewer_path, "w", encoding="utf-8") as f:
            f.write(html)
        return viewer_path
    except Exception as e:
        if logger:
            logger.warning(f"Génération viewer HTML : {e}")
        return None


_FRAMES_VIEWER_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>MorphoLapse — prévisualisation des frames</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 20px;
    background: #0f172a; color: #e2e8f0;
    font: 14px -apple-system, "Segoe UI", Roboto, sans-serif;
  }
  h1 { margin: 0 0 4px; font-size: 18px; color: #f8fafc; }
  .meta { color: #94a3b8; font-size: 12px; margin-bottom: 16px; }
  .stage {
    display: flex; flex-direction: column; align-items: center;
  }
  .frame-wrap {
    background: #000; padding: 6px; border-radius: 6px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    margin-bottom: 16px;
  }
  #frm {
    display: block;
    max-width: 90vw; max-height: 65vh;
    image-rendering: -webkit-optimize-contrast;
  }
  .controls {
    display: flex; align-items: center; gap: 12px;
    flex-wrap: wrap; justify-content: center;
    width: 100%; max-width: 900px;
  }
  button, select {
    background: #1e293b; color: #e2e8f0;
    border: 1px solid #334155; border-radius: 5px;
    padding: 6px 12px; font-size: 14px; cursor: pointer;
    font-family: inherit;
  }
  button:hover, select:hover { background: #334155; }
  button.primary {
    background: #2563eb; border-color: #2563eb; color: #ffffff;
    min-width: 96px; font-weight: 600;
  }
  button.primary:hover { background: #1d4ed8; }
  input[type=range] {
    flex: 1; min-width: 240px;
    accent-color: #2563eb;
  }
  .counter {
    font-family: ui-monospace, Cascadia, Consolas, monospace;
    font-size: 13px; color: #f1f5f9;
    background: #1e293b; padding: 6px 10px; border-radius: 4px;
    border: 1px solid #334155; min-width: 130px; text-align: center;
  }
  .hint {
    margin-top: 14px; color: #64748b; font-size: 12px;
    text-align: center;
  }
  kbd {
    background: #1e293b; border: 1px solid #475569;
    border-radius: 3px; padding: 1px 6px; font-family: monospace;
    font-size: 11px;
  }
  .final-section {
    margin-top: 32px;
    padding-top: 20px;
    border-top: 1px solid #334155;
    text-align: center;
  }
  .final-section h2 {
    margin: 0 0 12px; font-size: 18px; color: #f8fafc;
  }
  .final-section video {
    max-width: 90vw; max-height: 60vh;
    border-radius: 6px; background: #000;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
  }
  .final-section .not-ready {
    color: #94a3b8; font-size: 13px;
    padding: 30px;
    background: #1e293b; border: 1px dashed #475569;
    border-radius: 6px;
    max-width: 600px; margin: 0 auto;
  }
</style>
</head>
<body>
<h1>🎞️ Frames du morphing — prévisualisation</h1>
<div class="meta" id="meta">Chargement…</div>

<div class="stage">
  <div class="frame-wrap"><img id="frm" alt="frame"></div>
  <div class="controls">
    <button id="first" title="Home">⏮</button>
    <button id="prev" title="←">◀</button>
    <button id="play" class="primary">▶ Play</button>
    <button id="next" title="→">▶</button>
    <button id="last" title="End">⏭</button>
    <input type="range" id="slider" min="0" value="0">
    <span class="counter" id="counter">0 / 0</span>
    <select id="speed" title="Vitesse de lecture">
      <option value="0.25">0.25×</option>
      <option value="0.5">0.5×</option>
      <option value="1" selected>1×</option>
      <option value="2">2×</option>
      <option value="4">4×</option>
    </select>
  </div>
  <div class="hint">
    Navigation : <kbd>←</kbd> / <kbd>→</kbd> frame par frame &nbsp;·&nbsp;
    <kbd>Espace</kbd> play/pause &nbsp;·&nbsp;
    <kbd>Home</kbd> / <kbd>End</kbd> début / fin
  </div>

  <section class="final-section">
    <h2>🎬 Vidéo finale</h2>
    <video id="finalVideo" controls preload="metadata" playsinline>
      <source src="morph_video.mp4" type="video/mp4">
    </video>
    <div class="not-ready" id="notReadyMsg" style="display: none;">
      La vidéo finale n'est pas encore disponible.<br>
      L'encodage FFmpeg est probablement en cours.<br>
      Recharge cette page (<kbd>F5</kbd>) après quelques minutes pour voir le résultat.
    </div>
  </section>
</div>

<script>
"use strict";
const FRAMES = __FRAMES_JSON__;
const NATIVE_FPS = __FPS__;
const TOTAL = __TOTAL__;

const img = document.getElementById('frm');
const slider = document.getElementById('slider');
const counter = document.getElementById('counter');
const playBtn = document.getElementById('play');
const speedSel = document.getElementById('speed');
const meta = document.getElementById('meta');

let cur = 0;
let timer = null;

meta.textContent = FRAMES.length + " frames disponibles · " + NATIVE_FPS + " fps natif · durée " +
                   (FRAMES.length / NATIVE_FPS).toFixed(2) + " s";

slider.max = FRAMES.length - 1;

function show(n) {
  cur = Math.max(0, Math.min(FRAMES.length - 1, n));
  img.src = FRAMES[cur];
  slider.value = cur;
  counter.textContent = (cur + 1) + " / " + FRAMES.length + "  ·  " +
                         (cur / NATIVE_FPS).toFixed(2) + "s";
}

function play() {
  if (timer) return;
  playBtn.textContent = "⏸ Pause";
  const speed = parseFloat(speedSel.value);
  const interval = 1000 / (NATIVE_FPS * speed);
  timer = setInterval(function() {
    show((cur + 1) % FRAMES.length);
  }, interval);
}

function pause() {
  if (!timer) return;
  clearInterval(timer); timer = null;
  playBtn.textContent = "▶ Play";
}

slider.oninput = function() { pause(); show(parseInt(slider.value, 10)); };
document.getElementById('first').onclick = function() { pause(); show(0); };
document.getElementById('prev').onclick = function() { pause(); show(cur - 1); };
document.getElementById('next').onclick = function() { pause(); show(cur + 1); };
document.getElementById('last').onclick = function() { pause(); show(FRAMES.length - 1); };
playBtn.onclick = function() { timer ? pause() : play(); };
speedSel.onchange = function() { if (timer) { pause(); play(); } };

document.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowLeft') { pause(); show(cur - 1); }
  else if (e.key === 'ArrowRight') { pause(); show(cur + 1); }
  else if (e.key === ' ') { e.preventDefault(); timer ? pause() : play(); }
  else if (e.key === 'Home') { pause(); show(0); }
  else if (e.key === 'End') { pause(); show(FRAMES.length - 1); }
});

// Précharger 5 frames en avance pour éviter les saccades en autoplay
function preload() {
  for (let i = 0; i < Math.min(5, FRAMES.length); i++) {
    const im = new Image();
    im.src = FRAMES[i];
  }
}

// Bascule l'affichage selon la disponibilité du MP4 final.
// On laisse le <video> tenter de charger ; s'il échoue (404), on bascule
// vers le message "pas encore disponible".
function setupFinalVideo() {
  const v = document.getElementById('finalVideo');
  const notReady = document.getElementById('notReadyMsg');
  v.addEventListener('error', function() {
    v.style.display = 'none';
    notReady.style.display = 'block';
  });
  v.addEventListener('loadedmetadata', function() {
    v.style.display = 'block';
    notReady.style.display = 'none';
  });
}

show(0);
preload();
setupFinalVideo();
</script>
</body>
</html>
"""


class MorphStep:
    """Classe wrapper pour l'étape de morphing"""

    ID = "03_morph"
    NAME = "Morphing facial"
    DESCRIPTION = "Crée la vidéo de morphing entre les visages (optimisé mémoire)"

    @staticmethod
    def create_step():
        """Crée l'instance WorkflowStep"""
        from .workflow_manager import WorkflowStep

        return WorkflowStep(
            id=MorphStep.ID, name=MorphStep.NAME, description=MorphStep.DESCRIPTION, function=morph_faces
        )
