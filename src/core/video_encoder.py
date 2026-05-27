"""
Video Encoder - Module d'encodage vidéo via FFmpeg
Version simplifiée et robuste - encode depuis un dossier d'images
"""

import os
import subprocess
import sys
from collections.abc import Callable

import cv2
import numpy as np


def _format_seconds(seconds: float) -> str:
    """Formatte une durée en `XmYYs` ou `YYs` lisible humainement."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, rem = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m{rem:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def _no_console_kwargs() -> dict:
    """Args supplémentaires pour subprocess afin d'éviter une console parasite.

    Sur Windows, quand l'app parent est un EXE PyInstaller en mode
    --windowed (sans console), tout `subprocess.Popen(...)` lance par
    défaut le programme console enfant (FFmpeg) avec sa propre console.
    L'utilisateur peut alors la fermer par mégarde, ce qui tue le sous-
    processus en plein milieu d'un encodage (cf. bug rapporté : encodage
    de 18 min perdu après fermeture accidentelle de la fenêtre FFmpeg).
    `CREATE_NO_WINDOW` empêche cette fenêtre d'apparaître.
    """
    if sys.platform == "win32":
        # 0x08000000 = CREATE_NO_WINDOW (présent depuis Python 3.7)
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}


class VideoEncoder:
    """Encodeur vidéo utilisant FFmpeg - mode fichiers (plus robuste)"""

    # Map ffmpeg preset -> CRF (lower = better quality, larger file)
    _PRESET_TO_CRF = {
        "ultrafast": 28,
        "fast": 25,
        "medium": 23,
        "slow": 20,
        "slower": 18,
    }

    def __init__(self, logger=None):
        self.logger = logger
        self._ffmpeg_available = None
        self._frames_dir = None
        self._frame_count = 0
        self._output_path = None
        self._fps = 25
        self._size = None
        self._preset = "medium"
        self._crf = 23
        # Conserver les frames JPEG après encodage (visible dans le dossier
        # « frames/ » du run, exploitable par le viewer HTML).
        self._keep_frames = True
        # Nombre de threads à passer à FFmpeg via -threads N.
        # 0 = automatique (libx264 décide, ~1.5 × cœurs détectés).
        # N positif = limite stricte au pool d'encodage x264.
        self._ffmpeg_threads = 0

    @property
    def frames_dir(self) -> str | None:
        """Dossier contenant les frames JPEG intermédiaires (None si encodage non démarré)."""
        return self._frames_dir

    def check_ffmpeg(self) -> bool:
        """Vérifie que FFmpeg est disponible."""
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available

        try:
            result = subprocess.run(  # noqa: S603
                ["ffmpeg", "-version"],  # noqa: S607
                capture_output=True, text=True, timeout=5,
                **_no_console_kwargs(),
            )
            self._ffmpeg_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._ffmpeg_available = False

        if not self._ffmpeg_available:
            self._log_error("FFmpeg n'est pas installé ou accessible")

        return self._ffmpeg_available

    def start_encoding(
        self,
        output_path: str,
        fps: int = 25,
        size: tuple[int, int] | None = None,
        quality: str = "medium",
        frames_subdir: str = "frames",
        frames_dir: str | None = None,
        keep_frames: bool = True,
        ffmpeg_threads: int = 0,
    ) -> bool:
        """
        Prépare l'encodage - crée un dossier pour les frames intermédiaires.

        `quality` est un preset FFmpeg ('ultrafast', 'fast', 'medium', 'slow',
        'slower') ; il est conservé pour `finish_encoding` qui l'applique
        avec le CRF correspondant.

        `frames_subdir` : nom du sous-dossier où écrire les frames JPEG si
            `frames_dir` n'est pas fourni (par défaut « frames », adjacent
            au .mp4 final).
        `frames_dir` : chemin absolu (ou relatif) où écrire les frames JPEG.
            S'il est fourni, il prend le pas sur `frames_subdir`. Utilisé
            par MainWindow pour respecter le choix utilisateur d'un dossier
            intermédiaire externe (ex. `D:\\MesFrames\\<timestamp>\\`).
        `keep_frames` : si True (défaut), les frames sont conservées après
            encodage. Mettre False pour libérer l'espace disque.
        """
        if not self.check_ffmpeg():
            return False

        self._output_path = output_path
        self._fps = fps
        self._size = size
        self._frame_count = 0
        self._preset = quality if quality in self._PRESET_TO_CRF else "medium"
        self._crf = self._PRESET_TO_CRF[self._preset]
        self._keep_frames = keep_frames
        # 0 = laisser libx264 choisir ; sinon clamp à [1, 256] (limite x264).
        self._ffmpeg_threads = max(0, min(int(ffmpeg_threads), 256))

        if frames_dir:
            self._frames_dir = frames_dir
        else:
            output_dir = os.path.dirname(output_path)
            self._frames_dir = os.path.join(output_dir, frames_subdir)
        os.makedirs(self._frames_dir, exist_ok=True)

        self._log_info(
            f"Préparation encodage: {output_path} (preset={self._preset}, crf={self._crf})"
        )
        self._log_info(f"Frames intermédiaires : {self._frames_dir}")
        return True

    def write_frame(self, frame: np.ndarray):
        """Sauvegarde une frame en JPEG."""
        if self._frames_dir is None:
            self._log_error("Encodage non démarré")
            return

        try:
            # Redimensionner si nécessaire
            if self._size:
                w, h = self._size
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = cv2.resize(frame, (w, h))

            # Sauvegarder avec numérotation
            frame_path = os.path.join(self._frames_dir, f"frame_{self._frame_count:06d}.jpg")
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            self._frame_count += 1
        except Exception as e:
            self._log_error(f"Erreur écriture frame: {e}")

    def finish_encoding(self, check_cancel=None, progress_callback=None) -> bool:
        """Encode toutes les frames sauvegardées en vidéo avec FFmpeg.

        Args:
            check_cancel: callable optionnel sans argument. Si fourni, on
                interroge le drapeau d'annulation toutes les ~200 ms ; en cas
                d'annulation, on appelle `Popen.terminate()` puis on
                supprime la sortie partielle et on retourne False.
            progress_callback: callable optionnel `(fraction: float, message: str)`.
                Appelé périodiquement avec l'avancement réel FFmpeg (frame
                en cours / total) + ETA. Permet d'afficher une vraie barre
                de progression côté UI plutôt qu'un état figé pendant les
                minutes que dure l'encodage.
        """
        if self._frames_dir is None or self._frame_count == 0:
            self._log_error("Aucune frame à encoder")
            return False

        total_frames = self._frame_count
        self._log_info(f"Encodage de {total_frames} frames...")

        pattern = os.path.join(self._frames_dir, "frame_%06d.jpg")
        command = [
            "ffmpeg",
            "-y",
            # -threads : passe la consigne CPU au pool d'encodage x264.
            # 0 = laisser libx264 choisir (~1.5 × cœurs) ; N > 0 = limite stricte.
            # Ce flag est ce qui détermine RÉELLEMENT l'utilisation CPU pendant
            # l'encodage (la valeur des env OMP/OPENBLAS/MKL n'affecte que
            # NumPy/SciPy, pas le pipeline FFmpeg).
            "-threads", str(self._ffmpeg_threads),
            "-framerate", str(self._fps),
            "-i", pattern,
            "-c:v", "libx264",
            "-preset", self._preset,
            "-crf", str(self._crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",  # Optimisé pour le web
            # `-progress pipe:1` fait écrire à FFmpeg sur stdout des paires
            # key=value (frame, fps, speed, out_time_us, progress=continue/end).
            # On les lit dans un thread pour mettre à jour la barre UI en
            # temps réel — cf. plus bas dans cette méthode.
            "-progress", "pipe:1",
            "-nostats",  # Sinon FFmpeg envoie aussi sur stderr et brouille
            self._output_path,
        ]
        threads_label = "auto" if self._ffmpeg_threads == 0 else f"{self._ffmpeg_threads} threads"
        self._log_info(f"Lancement FFmpeg ({threads_label})...")

        proc = None
        try:
            proc = subprocess.Popen(  # noqa: S603
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                # CREATE_NO_WINDOW : empêche la console FFmpeg parasite qui,
                # si fermée par l'utilisateur, tue le processus en cours
                # d'encodage (bug : 18 min d'encodage perdues).
                **_no_console_kwargs(),
            )

            # Drainage parallèle de stdout ET stderr en threads daemon.
            #
            # Pourquoi les deux : subprocess.Popen() avec stderr=PIPE laisse
            # FFmpeg accumuler ses messages stderr dans un buffer OS de
            # ~64 KB. Quand ce buffer est plein, le prochain write() FFmpeg
            # bloque jusqu'à ce qu'on vide le pipe — sauf qu'on ne le vide
            # qu'à la fin via communicate(). Résultat : FFmpeg gèle à mi-
            # encodage sans aucune nouvelle frame émise, on conclut « bloqué »
            # et on le tue à tort (bug rapporté à 6119/6230 frames = 98 %).
            # En drainant stderr en continu dans un thread, le pipe ne
            # remplit jamais et FFmpeg peut continuer à écrire librement.
            import queue as _queue
            import threading as _threading
            progress_q: _queue.Queue[str] = _queue.Queue()
            stderr_buffer: list[str] = []

            def _stdout_reader():
                try:
                    for line in iter(proc.stdout.readline, ""):
                        if line:
                            progress_q.put(line.strip())
                    proc.stdout.close()
                except Exception:
                    pass

            def _stderr_reader():
                try:
                    for line in iter(proc.stderr.readline, ""):
                        if line:
                            stderr_buffer.append(line)
                    proc.stderr.close()
                except Exception:
                    pass

            reader_thread = _threading.Thread(target=_stdout_reader, daemon=True)
            reader_thread.start()
            stderr_thread = _threading.Thread(target=_stderr_reader, daemon=True)
            stderr_thread.start()

            # Détection « bloqué » par absence de progression plutôt que
            # par un timeout absolu : sur un gros morphing en preset slow,
            # FFmpeg peut légitimement tourner plusieurs heures. On le
            # tue UNIQUEMENT si on n'a vu aucune nouvelle frame depuis
            # NO_PROGRESS_TIMEOUT secondes (= vraiment bloqué).
            import time as _time
            NO_PROGRESS_TIMEOUT = 600.0     # 10 min sans nouvelle frame = bloqué
            LOG_INTERVAL = 30.0             # snapshot dans le log fichier toutes les 30s
            start_time = _time.monotonic()
            last_progress_time = start_time
            last_log_time = start_time
            cancelled = False
            last_reported_frame = 0

            while True:
                now = _time.monotonic()
                elapsed = now - start_time

                # Pas de progression depuis NO_PROGRESS_TIMEOUT : on tue.
                if now - last_progress_time > NO_PROGRESS_TIMEOUT:
                    self._log_error(
                        f"FFmpeg paraît bloqué : aucune nouvelle frame depuis "
                        f"{int(now - last_progress_time)}s "
                        f"(dernière vue : {last_reported_frame}/{total_frames}, "
                        f"écoulé total : {int(elapsed)}s)"
                    )
                    proc.kill()
                    return False
                if check_cancel is not None:
                    try:
                        check_cancel()
                    except Exception as e:
                        # WorkflowCancelled (ou autre) → arrêter ffmpeg proprement
                        cancelled = True
                        self._log_info(f"Annulation FFmpeg en cours ({type(e).__name__})...")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=2)
                        # Nettoyer le mp4 partiel
                        try:
                            if os.path.exists(self._output_path):
                                os.remove(self._output_path)
                                self._log_info(f"Sortie partielle supprimée : {self._output_path}")
                        except OSError as ose:
                            self._log_error(f"Impossible de supprimer la sortie partielle : {ose}")
                        # Re-lever l'exception pour que le step manager
                        # marque l'étape CANCELLED plutôt que ERROR
                        raise

                # Lire les lignes de progression FFmpeg sans bloquer
                try:
                    while True:
                        line = progress_q.get_nowait()
                        if line.startswith("frame="):
                            try:
                                cur_frame = int(line.split("=", 1)[1])
                            except ValueError:
                                continue
                            if cur_frame > last_reported_frame:
                                last_reported_frame = cur_frame
                                last_progress_time = _time.monotonic()  # reset timer "bloqué"
                                if progress_callback is not None:
                                    elapsed_now = last_progress_time - start_time
                                    if cur_frame > 0 and elapsed_now > 0.5:
                                        # Extrapolation linéaire du temps restant
                                        eta = elapsed_now * (total_frames - cur_frame) / cur_frame
                                        eta_str = _format_seconds(eta)
                                        msg = (
                                            f"Encodage : {cur_frame}/{total_frames} "
                                            f"({100 * cur_frame / total_frames:.0f}%) "
                                            f"— reste ~{eta_str}"
                                        )
                                    else:
                                        msg = f"Encodage : {cur_frame}/{total_frames}"
                                    try:
                                        progress_callback(cur_frame / max(1, total_frames), msg)
                                    except Exception:
                                        pass
                        elif line.startswith("progress=end"):
                            # FFmpeg a fini d'envoyer la progression
                            if progress_callback is not None:
                                try:
                                    progress_callback(1.0, f"Encodage : {total_frames}/{total_frames} (100%)")
                                except Exception:
                                    pass
                except _queue.Empty:
                    pass

                # Snapshot périodique dans le log file (toutes les LOG_INTERVAL
                # secondes). Évite le « trou » d'une heure dans le log si
                # l'encodage dure et que l'utilisateur fait planter sa session
                # de validation. Le log fichier reflète au minimum la
                # progression à 30s près même en cas de crash applicatif.
                if now - last_log_time >= LOG_INTERVAL:
                    last_log_time = now
                    if last_reported_frame > 0:
                        pct = 100 * last_reported_frame / max(1, total_frames)
                        fps_est = last_reported_frame / max(0.5, elapsed)
                        eta = elapsed * (total_frames - last_reported_frame) / max(1, last_reported_frame)
                        self._log_info(
                            f"FFmpeg en cours : {last_reported_frame}/{total_frames} "
                            f"({pct:.0f}%) — {fps_est:.1f} fps — reste ~{_format_seconds(eta)} "
                            f"— écoulé {_format_seconds(elapsed)}"
                        )
                    else:
                        # Pas encore de progression remontée : on logue quand
                        # même un battement de cœur pour qu'on sache que
                        # l'app n'est pas figée.
                        self._log_info(
                            f"FFmpeg démarre… (écoulé {_format_seconds(elapsed)}, "
                            f"pas encore de frame émise)"
                        )

                if proc.poll() is not None:
                    break
                _time.sleep(0.2)

            # Les deux pipes sont drainés par les threads — pas besoin
            # d'appeler communicate(). On attend juste que les readers
            # finissent de drainer ce qui reste (EOF rapide après exit).
            reader_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            stderr_text = "".join(stderr_buffer)

            success = proc.returncode == 0
            if success:
                self._log_info("Encodage terminé avec succès")
                # Ne supprimer les frames JPEG QUE si l'utilisateur l'a
                # explicitement demandé (par défaut on les garde dans
                # `frames/` pour le viewer HTML et la récupération manuelle).
                if not self._keep_frames:
                    self._cleanup_frames()
                else:
                    self._log_info(f"Frames préservées dans : {self._frames_dir}")
            else:
                if not cancelled:
                    # Le banner version de FFmpeg occupe les ~400 premiers
                    # caractères de stderr ; l'erreur réelle est à la FIN.
                    # On extrait les dernières lignes utiles.
                    tail = self._extract_ffmpeg_error_tail(stderr_text)
                    self._log_error(f"Erreur FFmpeg (return={proc.returncode}) : {tail}")
                    # Préserver les frames pour récupération manuelle
                    self._log_error(
                        f"Frames intermédiaires conservées dans : {self._frames_dir}\n"
                        f"Pour finir manuellement :\n"
                        f"  ffmpeg -framerate {self._fps} -i \"{os.path.join(self._frames_dir, 'frame_%06d.jpg')}\" "
                        f"-c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p \"{self._output_path}\""
                    )
            return success

        except FileNotFoundError:
            self._log_error("FFmpeg introuvable (vérifier le PATH)")
            return False
        except Exception as e:
            # Laisser WorkflowCancelled remonter ; tout autre s'enregistre puis False
            if e.__class__.__name__ == "WorkflowCancelled":
                raise
            self._log_error(f"Erreur encodage: {e}")
            if proc is not None and proc.poll() is None:
                proc.kill()
            return False

    @staticmethod
    def _extract_ffmpeg_error_tail(stderr: str, max_chars: int = 600) -> str:
        """Extrait la queue utile de stderr FFmpeg (où est la vraie erreur).

        FFmpeg commence par afficher son banner version + configuration
        (~400-600 caractères inutiles). L'erreur effective ("Conversion
        failed", "No such file", etc.) est dans les dernières lignes. On
        prend les `max_chars` derniers caractères, on coupe à la première
        ligne complète et on retourne ça.
        """
        if not stderr:
            return "(stderr vide)"
        tail = stderr[-max_chars:]
        # Si on a tronqué au milieu d'une ligne, sauter la première (incomplète)
        if len(stderr) > max_chars and "\n" in tail:
            tail = tail.split("\n", 1)[1]
        return tail.strip()

    def _cleanup_frames(self):
        """Supprime les frames temporaires."""
        if self._frames_dir and os.path.exists(self._frames_dir):
            try:
                import shutil

                shutil.rmtree(self._frames_dir)
                self._log_info("Frames temporaires supprimées")
            except Exception as e:
                self._log_error(f"Erreur nettoyage: {e}")

    def write_frames(self, frames: list[np.ndarray], progress_callback: Callable[[int, int], None] = None):
        """Écrit plusieurs frames."""
        total = len(frames)
        for idx, frame in enumerate(frames):
            self.write_frame(frame)
            if progress_callback:
                progress_callback(idx + 1, total)

    def write_pause_frames(self, frame: np.ndarray, count: int):
        """Écrit plusieurs copies d'une frame."""
        for _ in range(count):
            self.write_frame(frame)

    def encode_frames_to_video(
        self,
        frames: list[np.ndarray],
        output_path: str,
        fps: int = 25,
        progress_callback: Callable[[int, int], None] = None,
    ) -> bool:
        """Encode une liste de frames en vidéo."""
        if len(frames) == 0:
            self._log_error("Aucune frame à encoder")
            return False

        h, w = frames[0].shape[:2]

        if not self.start_encoding(output_path, fps, (w, h)):
            return False

        self.write_frames(frames, progress_callback)
        return self.finish_encoding()

    @property
    def is_encoding(self) -> bool:
        """Vérifie si un encodage est en préparation."""
        return self._frames_dir is not None

    @property
    def frame_count(self) -> int:
        """Nombre de frames écrites."""
        return self._frame_count

    def _log_info(self, message: str):
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str):
        if self.logger:
            self.logger.error(message)
