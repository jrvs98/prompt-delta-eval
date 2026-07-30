# Architecture

```
configs/example_experiment.yaml
        │
        ▼
  promptdelta.config.load_experiment()      → Experiment (models, tasks, conditions, runs_per_cell, ...)
        │
        ▼
  promptdelta.tasks.load_tasks()            → list[Task]  (items with content + expected/rubric)
  promptdelta.envelopes.EnvelopeBook        → renders bare/minimal/engineered text per task type
        │
        ▼
  promptdelta.runner.run_experiment()       → for each (model × task item × condition × run):
        │                                        1. render the envelope
        │                                        2. call the provider
        │                                        3. score the output (promptdelta.eval)
        │                                        4. persist the row (promptdelta.storage)
        ▼
  results/results.db  (SQLite)
        │
        ▼
  promptdelta.analysis.summarize()          → per-cell means/std, deltas, Cohen's d
        │
        ▼
  promptdelta.report.generate_report()      → results/report.html (self-contained, no external deps)
```

## Module map

| Module | Responsibility |
|---|---|
| `config.py` | Parses experiment YAML into `Experiment` / `ModelSpec` / `JudgeSpec` dataclasses. Validates required fields and that `conditions` are recognized. |
| `tasks.py` | Parses task YAML into `Task` / `TaskItem` / `EvalSpec` / `FormatSpec`. |
| `envelopes.py` | Loads `configs/envelopes.yaml` and renders `{content}` (and any task-specific fields, e.g. `{schema_hint}`) into the bare/minimal/engineered template for a given task type. **This is the entire independent variable of the experiment** — everything else is held constant across conditions. |
| `providers/base.py` | `Provider` ABC — one method, `complete(prompt, temperature, max_tokens) -> ProviderResponse`. Deliberately narrow: no separate system-prompt concept, because using one at all would itself be a form of prompt engineering that the "bare" condition must not get for free. |
| `providers/*_provider.py` | One class per backend (OpenAI, Anthropic, Google, Ollama, Mock). SDK imports are guarded so `import promptdelta` never fails just because you haven't installed every SDK — you only need the one(s) you're actually using. |
| `providers/mock_provider.py` | A scripted stand-in used for offline pipeline testing (see its docstring). Not a simulation of real model behavior — don't draw research conclusions from it. |
| `eval/objective.py` | Deterministic scorers: `exact_match`, `numeric_tolerance`, `regex`, `json_schema`. |
| `eval/format_check.py` | Format compliance, checked independently of correctness (`one_word`, `bullet_count`, `json`, `word_limit`). |
| `eval/llm_judge.py` | Rubric-based scoring for subjective tasks via a configurable judge provider. Falls back to a regex scrape if the judge doesn't return clean JSON. |
| `eval/__init__.py` | `evaluate()` — dispatches to the right scorer based on `task.eval.method`, and always runs the format check alongside it. |
| `storage.py` | Thin SQLite wrapper — one row per (model, task item, condition, run). No ORM, just `sqlite3` + a fixed schema. |
| `runner.py` | Orchestrates the full loop; the only module that calls providers and writes to storage. Skips (rather than crashes on) a model whose SDK isn't installed or whose API key is missing, logging why. |
| `analysis.py` | Reads the SQLite results back out and aggregates: per-cell mean/std/format-rate, per-model-per-task deltas (`compare_mean − baseline_mean`), and pooled Cohen's d. |
| `report.py` | Builds the SVG "gap" chart and renders `templates/report.html.j2` into a single static HTML file — no CDN dependencies, so the report works fully offline. |
| `cli.py` | `promptdelta run <config>` and `promptdelta report <config>` (regenerate the report from existing results without new API calls). |

## Design decisions worth knowing about

- **No system prompt, ever.** Every condition — including `engineered` — puts
  everything into a single user-turn string. This keeps the comparison honest:
  if the harness quietly added a system prompt for every model, "bare" would
  no longer mean "no prompt engineering."
- **Envelope templates are keyed by task *type*, not by item.** This keeps
  task YAML files simple (just content + expected answer) and keeps the
  independent variable centralized in one file (`configs/envelopes.yaml`)
  that's easy to audit and edit.
- **Format compliance is scored separately from correctness.** A model can
  give the right answer in the wrong shape (fails format, "content" score
  might still be partially recoverable depending on the eval method) or the
  wrong answer in a perfectly-formed shape. Conflating the two would hide
  exactly the kind of effect this tool is meant to surface.
- **SQLite, not JSON files.** Once you're running several models × several
  tasks × several conditions × several runs, you end up wanting ad-hoc
  queries (e.g. "just the format-compliance rate for extraction tasks"). A
  real query language is worth the tiny bit of setup.
