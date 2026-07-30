from pathlib import Path

from promptdelta.analysis import summarize
from promptdelta.report import generate_report
from promptdelta.runner import run_experiment
from promptdelta.tasks import load_tasks

REPO_ROOT = Path(__file__).parent.parent
CONFIG = REPO_ROOT / "configs" / "example_experiment.yaml"


def test_full_pipeline_runs_end_to_end(tmp_path, monkeypatch):
    # Run from repo root so relative paths in the config resolve normally.
    monkeypatch.chdir(REPO_ROOT)

    exp = run_experiment(str(CONFIG), verbose=False)

    db_path = Path(exp.db_path)
    assert db_path.exists()

    tasks = load_tasks([Path(p) for p in exp.task_paths])
    summary = summarize(db_path, exp.name, exp.conditions, [m.display_name() for m in exp.models])

    assert len(summary.cells) > 0
    assert set(summary.conditions) == {"bare", "minimal", "engineered"}

    report_path = generate_report(exp, tasks, summary, Path(exp.report_path))
    assert report_path.exists()
    html = report_path.read_text(encoding="utf-8")
    assert "<svg" in html
    assert exp.name in html
