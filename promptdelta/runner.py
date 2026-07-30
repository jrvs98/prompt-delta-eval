from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from .config import Experiment, load_experiment
from .envelopes import EnvelopeBook
from .eval import evaluate
from .providers import Provider, get_provider
from .storage import init_db, save_result
from .tasks import Task, load_tasks


def run_experiment(config_path: str, verbose: bool = True) -> Experiment:
    exp = load_experiment(config_path)

    envelopes = EnvelopeBook(exp.envelopes_path)
    tasks: List[Task] = load_tasks(exp.task_paths)

    needs_judge = any(t.eval.method == "llm_judge" for t in tasks)
    if needs_judge and exp.judge is None:
        raise ValueError(
            "One or more tasks use eval.method: llm_judge, but no `judge:` "
            "provider is configured in the experiment YAML."
        )

    judge_provider: Provider | None = None
    if exp.judge is not None:
        judge_provider = get_provider(exp.judge.provider, exp.judge.model, **exp.judge.params)

    db_path = Path(exp.db_path)
    init_db(db_path)

    total_calls = len(exp.models) * sum(len(t.items) for t in tasks) * len(exp.conditions) * exp.runs_per_cell
    done = 0

    for model_spec in exp.models:
        try:
            provider = get_provider(model_spec.provider, model_spec.model, **model_spec.params)
        except (ImportError, ValueError) as exc:
            print(f"[skip] {model_spec.display_name()}: {exc}", file=sys.stderr)
            continue

        for task in tasks:
            for item in task.items:
                extra_fields = dict(task.extra_fields)
                for condition in exp.conditions:
                    prompt = envelopes.render(task.type, condition, item.content, extra_fields)
                    for run_idx in range(exp.runs_per_cell):
                        result = provider.complete(prompt, temperature=exp.temperature, max_tokens=exp.max_tokens)
                        done += 1

                        if result.error:
                            save_result(
                                db_path,
                                dict(
                                    experiment=exp.name,
                                    model_label=model_spec.display_name(),
                                    provider=model_spec.provider,
                                    model=model_spec.model,
                                    task_id=task.id,
                                    item_id=item.id,
                                    condition=condition,
                                    run_index=run_idx,
                                    prompt=prompt,
                                    output="",
                                    score=None,
                                    format_ok=None,
                                    latency_ms=result.latency_ms,
                                    error=result.error,
                                ),
                            )
                            if verbose:
                                print(f"[{done}/{total_calls}] ERROR {model_spec.display_name()} "
                                      f"{task.id}/{item.id}/{condition}: {result.error}", file=sys.stderr)
                            continue

                        score, eval_details, format_ok, format_details = evaluate(
                            task, item, result.text, judge_provider
                        )
                        save_result(
                            db_path,
                            dict(
                                experiment=exp.name,
                                model_label=model_spec.display_name(),
                                provider=model_spec.provider,
                                model=model_spec.model,
                                task_id=task.id,
                                item_id=item.id,
                                condition=condition,
                                run_index=run_idx,
                                prompt=prompt,
                                output=result.text,
                                score=score,
                                eval_details=eval_details,
                                format_ok=format_ok,
                                format_details=format_details,
                                latency_ms=result.latency_ms,
                            ),
                        )
                        if verbose:
                            print(f"[{done}/{total_calls}] {model_spec.display_name()} "
                                  f"{task.id}/{item.id}/{condition} run {run_idx}: score={score:.2f}")

    return exp
