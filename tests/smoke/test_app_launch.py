"""Smoke — `python main.py` boots without crash and stays alive.

Lance l'application en subprocess avec un timeout court, vérifie qu'elle
ne crashe pas immédiatement et capture les logs initiaux.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.slow
def test_app_launches_and_stays_alive_briefly():
    """python main.py démarre le GUI et survit 4 secondes sans crasher.

    On laisse 4 s pour : import customtkinter (~300ms), splash, MainWindow init,
    chargement de la config. Si le process meurt avant, c'est un crash startup.
    """
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
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

    # Initial logs should mention the 4 workflow steps and "MorphoLapse"
    out = stdout.decode("utf-8", errors="replace")
    assert "MorphoLapse" in out or "Étape" in out or "tape" in out  # accents survive cp1252


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
