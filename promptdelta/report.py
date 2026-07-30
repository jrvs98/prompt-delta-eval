from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .analysis import Summary
from .config import Experiment
from .tasks import Task

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _fmt(x, decimals=2):
    return f"{x:.{decimals}f}" if isinstance(x, (int, float)) else "—"


def _build_dumbbell_svg(summary: Summary) -> str:
    baseline = summary.deltas[0].baseline_condition if summary.deltas else "bare"
    compare = summary.deltas[0].compare_condition if summary.deltas else "engineered"

    # average baseline/compare score per model across tasks
    per_model: Dict[str, Dict[str, list]] = {}
    for d in summary.deltas:
        if d.baseline_mean is None or d.compare_mean is None:
            continue
        per_model.setdefault(d.model_label, {"base": [], "cmp": []})
        per_model[d.model_label]["base"].append(d.baseline_mean)
        per_model[d.model_label]["cmp"].append(d.compare_mean)

    rows = []
    for label in summary.models_order:
        vals = per_model.get(label)
        if not vals or not vals["base"]:
            continue
        base_mean = sum(vals["base"]) / len(vals["base"])
        cmp_mean = sum(vals["cmp"]) / len(vals["cmp"])
        rows.append((label, base_mean, cmp_mean, cmp_mean - base_mean))

    if not rows:
        return "<p style='font-family:IBM Plex Mono, monospace; color:var(--muted); padding:20px;'>No comparable results yet — run the experiment first.</p>"

    row_h = 44
    margin_left, margin_right = 210, 70
    margin_top, margin_bottom = 30, 34
    width = 900
    plot_w = width - margin_left - margin_right
    height = margin_top + margin_bottom + row_h * len(rows)

    def x_of(score: float) -> float:
        score = max(0.0, min(1.0, score))
        return margin_left + score * plot_w

    svg_parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Mono, monospace">']

    # axis gridlines + ticks
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        tx = x_of(tick)
        svg_parts.append(
            f'<line x1="{tx:.1f}" y1="{margin_top - 6}" x2="{tx:.1f}" y2="{height - margin_bottom + 4}" '
            f'stroke="#C9CCD1" stroke-width="1" />'
        )
        svg_parts.append(
            f'<text x="{tx:.1f}" y="{height - margin_bottom + 20}" font-size="11" fill="#6B7078" text-anchor="middle">{tick:g}</text>'
        )

    for i, (label, base_mean, cmp_mean, delta) in enumerate(rows):
        y = margin_top + i * row_h + row_h / 2
        x1, x2 = x_of(base_mean), x_of(cmp_mean)
        color = "#1F6F6B" if delta > 0.001 else "#B5502D"

        svg_parts.append(
            f'<text x="{margin_left - 16}" y="{y + 4}" font-size="13" fill="#1B1D22" text-anchor="end">{label}</text>'
        )
        svg_parts.append(
            f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="2.5" />'
        )
        svg_parts.append(f'<circle cx="{x1:.1f}" cy="{y:.1f}" r="5.5" fill="#EDEEF0" stroke="#6B7078" stroke-width="1.5" />')
        svg_parts.append(f'<circle cx="{x2:.1f}" cy="{y:.1f}" r="5.5" fill="{color}" />')

        delta_label = f"{delta:+.2f}"
        svg_parts.append(
            f'<text x="{width - margin_right + 14}" y="{y + 4}" font-size="12" fill="{color}" text-anchor="start">{delta_label}</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_report(exp: Experiment, tasks: List[Task], summary: Summary, output_path: str | Path) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
    )
    template = env.get_template("report.html.j2")

    baseline = summary.deltas[0].baseline_condition if summary.deltas else (exp.conditions[0] if exp.conditions else "bare")
    compare = summary.deltas[0].compare_condition if summary.deltas else (exp.conditions[-1] if exp.conditions else "engineered")

    headline_vals = list(summary.model_overall_delta.values())
    headline_delta = f"{(sum(headline_vals) / len(headline_vals)):+.2f}" if headline_vals else "—"

    task_by_id = {t.id: t for t in tasks}
    task_ids = sorted({c.task_id for c in summary.cells})

    task_blocks = []
    for task_id in task_ids:
        task = task_by_id.get(task_id)
        rows_by_model: Dict[str, Dict] = {}
        for cell in summary.cells:
            if cell.task_id != task_id:
                continue
            row = rows_by_model.setdefault(cell.model_label, {"model_label": cell.model_label, "scores": {}, "format_rates": {}, "n": cell.n})
            row["scores"][cell.condition] = _fmt(cell.mean_score)
            row["format_rates"][cell.condition] = _fmt(cell.format_ok_rate) if cell.format_ok_rate is not None else "—"
            row["n"] = max(row["n"], cell.n)

        ordered_rows = [rows_by_model[m] for m in summary.models_order if m in rows_by_model]
        task_blocks.append({
            "id": task_id,
            "description": task.description if task else "",
            "rows": ordered_rows,
        })

    html = template.render(
        experiment_name=exp.name,
        baseline_condition=baseline,
        compare_condition=compare,
        n_models=len({c.model_label for c in summary.cells}),
        n_tasks=len(task_ids),
        headline_delta=headline_delta,
        runs_per_cell=exp.runs_per_cell,
        temperature=exp.temperature,
        conditions=exp.conditions,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        dumbbell_svg=_build_dumbbell_svg(summary),
        task_blocks=task_blocks,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
