"""Smoke — `python main.py` boots without crash and stays alive.

Lance l'application en subprocess avec un timeout court, vérifie qu'elle
ne crashe pas immédiatement et capture les logs initiaux.
"""

import contextlib
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


def _gather_evidence_of_alive(stdout_text: str, stderr_text: str, log_files_before: set[Path]) -> str:
    """Concatène stdout + stderr + contenu d'un éventuel log fichier créé pendant le run.

    Le subprocess Tkinter ne flushe pas toujours stdout/stderr avant `terminate()`
    sur Windows. Le logger applicatif écrit ÉGALEMENT dans logs/MorphoLapse_*.log
    via un FileHandler — on agrège ces deux sources.
    """
    parts = [stdout_text, stderr_text]
    if LOGS_DIR.exists():
        new_logs = [p for p in LOGS_DIR.glob("MorphoLapse_*.log") if p not in log_files_before]
        for p in new_logs:
            with contextlib.suppress(OSError):
                parts.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


@pytest.mark.slow
def test_app_launches_and_stays_alive_briefly():
    """python main.py démarre le GUI et survit 4 secondes sans crasher.

    On laisse 4 s pour : import customtkinter (~300ms), splash, MainWindow init,
    chargement de la config. Si le process meurt avant, c'est un crash startup.

    On lance avec `-u` (unbuffered) pour maximiser les chances que stdout soit
    visible au moment du terminate ; on agrège ENSUITE les éventuels fichiers
    de log produits, pour rendre l'assertion non-flaky.
    """
    log_files_before = set(LOGS_DIR.glob("MorphoLapse_*.log")) if LOGS_DIR.exists() else set()

    proc = subprocess.Popen(
        [sys.executable, "-u", "main.py"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(4.0)
        assert proc.poll() is None, (
            f"Process exited too early (returncode={proc.returncode}); "
            f"likely a startup crash"
        )
    finally:
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()

    out_full = _gather_evidence_of_alive(
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        log_files_before,
    )
    assert "MorphoLapse" in out_full or "tape" in out_full, (
        "Aucun marqueur de démarrage trouvé dans stdout+stderr+logs/MorphoLapse_*.log. "
        "Soit le process ne loggue rien (regression), soit l'environnement bloque les écritures."
    )


def test_main_module_check_dependencies_returns_true():
    """main.check_dependencies() returns True when all deps importable.

    Deps are installed in the test venv so we should get True.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    import importlib.util

    spec = importlib.util.spec_from_file_location("morpholapse_main", PROJECT_ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.check_dependencies() is True
    assert module.check_model() in (True, False)  # depends on whether the .dat file is local
