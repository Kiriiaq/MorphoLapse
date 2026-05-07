"""Functional tests for WorkflowManager run/stop/error paths."""

from src.modules.workflow_manager import StepStatus, WorkflowManager, WorkflowStep


def _setup_manager_with_runs(tmp_path):
    mgr = WorkflowManager()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    mgr._context.run_dir = str(runs_dir)
    mgr.create_run_directory = lambda: str(runs_dir)
    return mgr


def test_workflow_run_marks_step_completed_on_success(tmp_path):
    mgr = _setup_manager_with_runs(tmp_path)
    step = WorkflowStep(id="ok", name="OK", description="d", function=lambda c, p, _l: {"r": 1})
    mgr.add_step(step)
    success = mgr.run()
    assert success is True
    assert step.status == StepStatus.COMPLETED
    assert step.result == {"r": 1}


def test_workflow_run_marks_step_error_on_exception(tmp_path):
    mgr = _setup_manager_with_runs(tmp_path)

    def explode(c, p, _l):
        raise ValueError("boom")

    step = WorkflowStep(id="kaboom", name="Kaboom", description="d", function=explode)
    mgr.add_step(step)
    success = mgr.run()
    assert success is False
    assert step.status == StepStatus.ERROR
    assert "boom" in step.error_message


def test_workflow_continue_on_error_runs_subsequent_steps(tmp_path):
    mgr = _setup_manager_with_runs(tmp_path)

    invoked = []

    def fail(c, p, _l):
        raise RuntimeError("x")

    def ok(c, p, _l):
        invoked.append("yes")
        return {}

    mgr.add_step(WorkflowStep(id="a", name="A", description="d", function=fail))
    mgr.add_step(WorkflowStep(id="b", name="B", description="d", function=ok))
    mgr.run(continue_on_error=True)
    assert invoked == ["yes"]


def test_workflow_disabled_step_is_skipped(tmp_path):
    mgr = _setup_manager_with_runs(tmp_path)
    invoked = []
    mgr.add_step(
        WorkflowStep(id="skipme", name="Skip", description="d", function=lambda c, p, _l: invoked.append("X"))
    )
    mgr.enable_step("skipme", False)
    mgr.run()
    assert invoked == []
    assert mgr.get_step("skipme").status == StepStatus.SKIPPED


def test_workflow_stop_interrupts_run(tmp_path):
    mgr = _setup_manager_with_runs(tmp_path)

    invoked = []

    def step_a(c, p, _l):
        mgr.stop()  # request stop after first step
        invoked.append("A")
        return {}

    def step_b(c, p, _l):
        invoked.append("B")  # should never run
        return {}

    mgr.add_step(WorkflowStep(id="a", name="A", description="d", function=step_a))
    mgr.add_step(WorkflowStep(id="b", name="B", description="d", function=step_b))
    mgr.run()
    assert invoked == ["A"]


def test_workflow_callback_step_start_fires(tmp_path):
    mgr = _setup_manager_with_runs(tmp_path)
    mgr.add_step(WorkflowStep(id="z", name="Z", description="d", function=lambda c, p, _l: {}))

    started = []
    mgr.on_step_start(started.append)
    mgr.run()
    assert len(started) == 1
    assert started[0].id == "z"


def test_workflow_progress_callback(tmp_path):
    mgr = _setup_manager_with_runs(tmp_path)

    def emits(c, progress_cb, _l):
        progress_cb(1, 2, "half")
        progress_cb(2, 2, "full")
        return {}

    mgr.add_step(WorkflowStep(id="p", name="P", description="d", function=emits))
    progresses = []
    mgr.on_progress(lambda step, pct, msg: progresses.append(pct))
    mgr.run()
    assert any(p > 0 for p in progresses)
