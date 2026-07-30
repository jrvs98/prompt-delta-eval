from __future__ import annotations

import argparse
import sys

from .analysis import summarize
from .config import load_experiment
from .report import generate_report
from .runner import run_experiment
from .tasks import load_tasks

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; if absent, rely on real env vars


def cmd_run(args: argparse.Namespace) -> None:
    exp = run_experiment(args.config, verbose=not args.quiet)
    tasks = load_tasks(exp.task_paths)
    summary = summarize(exp.db_path, exp.name, exp.conditions, [m.display_name() for m in exp.models])
    out_path = generate_report(exp, tasks, summary, exp.report_path)
    print(f"\nDone. Report written to: {out_path}")


def cmd_report(args: argparse.Namespace) -> None:
    exp = load_experiment(args.config)
    tasks = load_tasks(exp.task_paths)
    summary = summarize(exp.db_path, exp.name, exp.conditions, [m.display_name() for m in exp.models])
    out_path = generate_report(exp, tasks, summary, exp.report_path)
    print(f"Report regenerated: {out_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="promptdelta", description="Compare bare vs. engineered prompts across LLMs.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run an experiment defined by a YAML config, then generate the report.")
    p_run.add_argument("config", help="Path to an experiment YAML file, e.g. configs/example_experiment.yaml")
    p_run.add_argument("--quiet", action="store_true", help="Suppress per-call progress output.")
    p_run.set_defaults(func=cmd_run)

    p_report = sub.add_parser("report", help="Regenerate the HTML report from an existing results database (no new API calls).")
    p_report.add_argument("config", help="Path to the experiment YAML file whose results.db you want to report on.")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
