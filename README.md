# promptdelta

Does prompt engineering still matter, or have models gotten good enough that a bare
question works almost as well as a carefully engineered prompt?

**promptdelta** runs the *same task content* through multiple LLMs under three
conditions — **bare** (just the raw question), **minimal** (one plain instruction
line), and **engineered** (role framing + explicit instructions + output format
spec) — and reports whether the outputs actually differ, per model and per task
type. The point is to make that comparison measurable instead of anecdotal.

```
configs/example_experiment.yaml  →  promptdelta run  →  results/report.html
```

## Why this exists

"You don't really need to prompt-engineer anymore" is a common claim and a
plausible one — newer models are much better at inferring intent from minimal
input. But it's an empirical question, and it likely depends heavily on *what
kind* of task you're doing (a math problem vs. "give me exactly this JSON
schema" are very different bets). This tool lets you check, for the models and
tasks you actually care about, instead of going on vibes.

## How it works

1. **Task content is fixed.** Each task (math word problems, sentiment
   classification, summarization, structured extraction) has a set of items —
   just the raw content, nothing about how to respond.
2. **Three envelopes wrap that content identically for every model:**
   - `bare` — the raw content, untouched.
   - `minimal` — one plain instruction line, no role/format/examples.
   - `engineered` — role framing, explicit instructions, an output format spec.
3. **Every (model × task item × condition) cell is run `runs_per_cell` times**
   (LLM output is stochastic — one run per cell is noise, not signal).
4. **Each output is scored** — objectively where possible (exact match, numeric
   tolerance, JSON schema compliance), or via an LLM judge against a fixed
   rubric for subjective tasks like summarization — plus a separate,
   independent **format-compliance check** (did it even follow the requested
   shape, regardless of whether the content was right).
5. **Results land in SQLite**, then get aggregated into per-model, per-task
   deltas (`engineered mean − bare mean`, with an effect size) and rendered
   into a self-contained HTML report.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the module-by-module breakdown.

## Quickstart

```bash
git clone <your-fork-url>
cd promptdelta
pip install -r requirements.txt
```

**Try it with zero API keys first** — there's a `mock` provider that exercises
the entire pipeline (config → prompt rendering → scoring → SQLite → HTML
report) without calling any real API. Its "model" is deliberately dumb and
its scores aren't meaningful — it's there so you can sanity-check your own
task definitions and experiment configs before spending real API credits.

```bash
python -m promptdelta run configs/example_experiment.yaml
open results/mock_report.html   # or just open the file in a browser
```

**Run it for real:**

```bash
cp .env.example .env
# fill in the API keys for the providers you're using

cp configs/real_experiment.example.yaml configs/my_experiment.yaml
# edit: pick models, verify their current model IDs with each provider's docs

python -m promptdelta run configs/my_experiment.yaml
```

Re-render the report from existing results without re-running any API calls
(useful after tweaking `report.py` or the HTML template):

```bash
python -m promptdelta report configs/my_experiment.yaml
```

## Providers supported out of the box

| Provider  | Package                  | Auth                          |
|-----------|---------------------------|--------------------------------|
| OpenAI    | `openai`                  | `OPENAI_API_KEY`               |
| Anthropic | `anthropic`                | `ANTHROPIC_API_KEY`            |
| Google    | `google-generativeai`      | `GOOGLE_API_KEY`               |
| Ollama    | `requests` (local server)  | none — run `ollama serve`      |
| Mock      | (built in)                 | none                            |

Install only what you need: `pip install openai anthropic google-generativeai`,
or `pip install -e ".[all]"` for everything (see `pyproject.toml`).

Adding a new provider means implementing one class — see
[`promptdelta/providers/base.py`](promptdelta/providers/base.py) and any
existing provider as a template, then registering it in
[`promptdelta/providers/__init__.py`](promptdelta/providers/__init__.py).

## Writing your own experiment config

```yaml
experiment:
  name: "my-comparison"
  runs_per_cell: 5
  temperature: 0.7
  conditions: [bare, minimal, engineered]   # you can drop "minimal" if you only care about the two extremes

  models:
    - provider: anthropic
      model: claude-sonnet-5       # check current model IDs — these change often
      label: "Claude Sonnet 5"
      generation_rank: 5           # optional — lets the report order models by "how new"

  tasks:
    - configs/tasks/math.yaml
    - configs/tasks/classification.yaml

  judge:                           # required only if a task uses eval.method: llm_judge
    provider: anthropic
    model: claude-sonnet-5

  output:
    db_path: results/results.db
    report_path: results/report.html
```

All paths in the config (`tasks`, `envelopes`, `output.*`) are resolved
relative to wherever you run the `promptdelta` command from — normally the
repo root.

## Adding your own task

Tasks live in `configs/tasks/*.yaml`. Four are included: `math` (numeric,
objective), `classification` (exact-match, format-sensitive), `summarization`
(subjective, LLM-judged), `extraction` (JSON-schema, format-sensitive). To add
a new one:

1. Pick (or add) a `type:` — this selects which envelope templates apply from
   `configs/envelopes.yaml`. If you're inventing a new type, add `bare` /
   `minimal` / `engineered` templates for it there.
2. Write items as `{id, content, expected}` — `content` is the *only* thing
   that gets shown to the model; `expected` is what your `eval.method`
   compares against (skip it for `llm_judge`, which scores against a rubric
   instead).
3. Pick an `eval.method`: `exact_match`, `numeric_tolerance`, `regex`,
   `json_schema`, or `llm_judge`.
4. Optionally set a `format.rule` (`one_word`, `bullet_count`, `json`,
   `word_limit`) — this is checked independently of correctness, and is
   often where the bare-vs-engineered gap shows up most clearly.

## What the report shows

- **Headline number** — average score change (0–1 scale) from the baseline
  condition to the richest condition, averaged across every model and task.
- **The gap, per model** — a slope chart: each model's baseline score
  (hollow dot) connected to its engineered score (filled dot). Long lines
  mean prompting mattered a lot for that model; short or reversed lines mean
  it barely moved the needle.
- **Per-task tables** — mean score and format-compliance rate per condition,
  broken out by task, so you can see *which kind* of task (if any) still
  benefits from careful prompting.

## Known limitations (read before drawing conclusions)

- **Small samples are noisy.** `runs_per_cell: 3-5` gives you a rough signal,
  not a publishable result. Bump it up for anything you're going to rely on.
- **LLM-judge bias.** Judges tend to favor longer, more confident-sounding
  answers regardless of actual quality. Consider using 2-3 different judge
  models and comparing, or spot-checking with a human read.
- **Envelope wording is a design choice.** The specific "engineered" prompt in
  `configs/envelopes.yaml` is one reasonable version of prompt engineering,
  not the only one. If your engineered prompt is weak, you'll underestimate
  how much prompting can help. Edit the templates to match how you'd actually
  write a prompt for a given task.
- **Confounding.** If your "engineered" version sneaks in extra *information*
  (not just structure/instructions), you're measuring something else. Keep
  `{content}` identical across conditions.
- **Cost scales fast.** Total API calls = `models × tasks' items × conditions
  × runs_per_cell`. The default example config (2 models, 4 tasks, ~21 items
  total, 3 conditions, 3 runs) is 378 calls — check that math before pointing
  it at a large model lineup.

## Running tests

```bash
pip install -e ".[dev]"
python -m pytest
```

`tests/test_pipeline_mock.py` runs the full pipeline end-to-end against the
mock provider — no API keys or network access needed, so it's safe to run in
CI.

## License

MIT — see [`LICENSE`](LICENSE).
