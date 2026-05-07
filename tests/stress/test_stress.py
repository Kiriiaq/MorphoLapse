"""Stress tests : opérations répétées + threads."""

import threading

import pytest

from src.utils.config_manager import ConfigManager
from src.utils.logger import Logger


@pytest.mark.stress
def test_stress_config_manager_1000_set_get(temp_config_path):
    """1000 set→get cycles ne doivent ni corrompre la config ni leak."""
    cm = ConfigManager(config_path=temp_config_path)
    for i in range(1000):
        cm.set("morphing.fps", 10 + (i % 50), auto_save=False)
        assert cm.get("morphing.fps") == 10 + (i % 50)


@pytest.mark.stress
def test_stress_logger_5000_messages(tmp_path):
    """5000 logs successifs : pas de crash, history écrête à _max_history."""
    logger = Logger("StressLogger", log_dir=str(tmp_path), file_output=False)
    for i in range(5000):
        logger.info(f"msg-{i}")
    history = logger.get_history()
    assert len(history) <= 10_000
    assert any("msg-4999" in e.message for e in history[-5:])


@pytest.mark.stress
def test_stress_logger_concurrent_callbacks(tmp_path):
    """8 threads loggent en parallèle ; tous les messages doivent atterrir dans
    l'historique sans race fatale.
    """
    logger = Logger("ConcurrentLogger", log_dir=str(tmp_path), file_output=False)
    received = []
    lock = threading.Lock()

    def cb(entry):
        with lock:
            received.append(entry.message)

    logger.add_callback(cb)

    def worker(tid):
        for i in range(100):
            logger.info(f"t{tid}-{i}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(received) == 800  # 8 threads × 100 logs
    # Tous les threads ont émis au moins un message
    seen_tids = {m.split("-")[0] for m in received}
    assert len(seen_tids) == 8


@pytest.mark.stress
def test_stress_workflow_add_remove_steps_repeated():
    """1000 cycles add+remove de steps : pas de leak de la liste interne."""
    from src.modules.workflow_manager import WorkflowManager, WorkflowStep

    mgr = WorkflowManager()
    for i in range(1000):
        s = WorkflowStep(id=f"id{i}", name="N", description="d", function=lambda c, p, _l: {})
        mgr.add_step(s)
        mgr.remove_step(f"id{i}")
    assert len(mgr.steps) == 0


@pytest.mark.stress
def test_stress_image_utils_resize_1000_calls(synthetic_image):
    """1000 resizes consécutifs ne doivent pas crasher."""
    for _ in range(1000):
        out = __import__("src.utils.image_utils", fromlist=["ImageUtils"]).ImageUtils.resize_image(
            synthetic_image, (50, 50), keep_aspect=True
        )
        assert out.shape[:2] == (50, 50)
