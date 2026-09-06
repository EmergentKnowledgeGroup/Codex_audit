"""Offline renderers for Codex token-routing audit documents.

Both public functions accept the JSON-compatible dictionary emitted by the
collector.  They intentionally need no packages, network access, or assets.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any, Mapping, Sequence


TOTAL_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
    "calls",
    "estimated_credits",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _items(value: Any) -> Sequence[Any]:
    return value if isinstance(value, (list, tuple)) else ()


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    return int(round(_number(value)))


def _fmt(value: Any, decimals: int = 0) -> str:
    number = _number(value)
    if decimals:
        return f"{number:,.{decimals}f}"
    return f"{int(round(number)):,}"


def _pct(part: Any, whole: Any) -> float:
    denominator = _number(whole)
    return 0.0 if denominator <= 0 else 100 * _number(part) / denominator


def _text(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def _md(value: Any) -> str:
    """Make user-provided strings safe and readable in a Markdown cell."""
    text = escape(str(value if value is not None else ""), quote=False)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _date(value: Any) -> str:
    raw = str(value or "")
    if not raw:
        return "Not recorded"
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
    except ValueError:
        return raw


def _kind(chat: Mapping[str, Any]) -> str:
    task = str(chat.get("task_ref") or "")
    root = str(chat.get("root_ref") or "")
    parent = str(chat.get("parent_ref") or "")
    return "Root" if not parent or (task and task == root) else "Child"


def _bar(label: str, value: float, maximum: float, detail: str, color: str, title: str = "") -> str:
    width = 0 if maximum <= 0 else min(100, max(0, value / maximum * 100))
    return (
        '<div class="bar-row"><div class="bar-label" title="' + _text(title or label) + '">' + _text(label) + "</div>"
        '<div class="bar-track" aria-label="' + _text(f"{label}: {detail}") + '">'
        '<span class="bar-fill" style="width:' + f"{width:.2f}" + "%;--bar:" + _text(color) + '"></span></div>'
        '<div class="bar-value">' + _text(detail) + "</div></div>"
    )


def _hour_label(value: Any) -> tuple[str, str]:
    """Give a compact UTC hour label while retaining the precise source time."""
    raw = str(value or "Unknown")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%H:00"), raw
    except ValueError:
        return raw, raw


def _short_title(value: Any, limit: int = 108) -> str:
    title = str(value or "Untitled chat").replace("\n", " ").strip()
    return title if len(title) <= limit else title[: limit - 1].rstrip() + "…"


def render_html(doc: Mapping[str, Any]) -> str:
    """Render a self-contained, responsive and printable HTML dashboard."""
    doc = _mapping(doc)
    window, totals, baseline = (_mapping(doc.get(k)) for k in ("window", "totals", "baseline"))
    models, chats, hours, roots = (_items(doc.get(k)) for k in ("models", "chats", "hours", "roots"))
    recommendations, limitations = _items(doc.get("recommendations")), _items(doc.get("limitations"))
    coverage, rate_card = _mapping(doc.get("coverage")), _mapping(doc.get("rate_card"))
    total_tokens, credits, calls = _number(totals.get("total_tokens")), _number(totals.get("estimated_credits")), _number(totals.get("calls"))
    cache_pct = _pct(totals.get("cached_input_tokens"), totals.get("input_tokens"))
    def delta(field: str) -> str:
        old = _number(baseline.get(field))
        return f"{_pct(_number(totals.get(field)) - old, old):+.1f}% vs preceding window" if old else "No baseline recorded"
    model_max = max((_number(_mapping(m).get("total_tokens")) for m in models), default=0)
    hour_max = max((_number(_mapping(h).get("total_tokens")) for h in hours), default=0)

    metric_cards = (
        ("Total tokens", _fmt(total_tokens), delta("total_tokens")),
        ("Calls", _fmt(calls), delta("calls") + (f" · {_fmt(total_tokens / calls) if calls else '0'} tokens/call")),
        ("Cache reuse", f"{cache_pct:.1f}%", f"{_fmt(totals.get('cached_input_tokens'))} cached input tokens"),
        ("Est. standard credits", _fmt(credits, 2), delta("estimated_credits") + " · estimate only"),
    )
    cards = "".join('<article class="card"><p>' + _text(label) + '</p><strong>' + _text(value) + '</strong><small>' + _text(note) + "</small></article>" for label, value, note in metric_cards)
    hours_html = "".join(_bar(label, _number(_mapping(h).get("total_tokens")), hour_max, _fmt(_mapping(h).get("total_tokens")), "#38bdf8", raw) for h in hours for label, raw in (_hour_label(_mapping(h).get("hour")),)) or '<p class="empty">No hourly activity was collected.</p>'
    models_html = "".join(
        _bar(str(_mapping(m).get("model") or "Unknown model"), _number(_mapping(m).get("total_tokens")), model_max,
             f"{_fmt(_mapping(m).get('total_tokens'))} tokens · {_pct(_mapping(m).get('total_tokens'), total_tokens):.1f}% · {_fmt(_mapping(m).get('estimated_credits'), 2)} credits", "#a78bfa")
        for m in models
    ) or '<p class="empty">No model activity was collected.</p>'
    credit_models_html = "".join(
        _bar(str(_mapping(m).get("model") or "Unknown model"), _number(_mapping(m).get("estimated_credits")), credits,
             f"{_fmt(_mapping(m).get('estimated_credits'), 2)} credits · {_pct(_mapping(m).get('estimated_credits'), credits):.1f}%", "#fbbf24")
        for m in models
    ) or '<p class="empty">No model credit estimate was collected.</p>'
    title_by_ref = {str(_mapping(chat).get("task_ref") or ""): str(_mapping(chat).get("title") or "Untitled chat") for chat in chats}
    rows = []
    for raw in chats:
        chat = _mapping(raw)
        task, title = chat.get("task_ref") or "—", str(chat.get("title") or "Untitled chat")
        models_used = ", ".join(str(x) for x in _items(chat.get("models"))) or "—"
        efforts = ", ".join(str(x) for x in _items(chat.get("efforts"))) or "—"
        rows.append("<tr><td><span class=\"badge\">" + _text(_kind(chat)) + "</span><code>" + _text(task) + "</code></td><td title=\"" + _text(title) + "\">" + _text(_short_title(title)) + "</td><td>" + _text(models_used) + "</td><td>" + _text(efforts) + "</td><td class=\"num\">" + _text(_fmt(chat.get("calls"))) + "</td><td class=\"num\">" + _text(_fmt(chat.get("total_tokens"))) + "</td><td class=\"num\">" + _text(_fmt(chat.get("estimated_credits"), 2)) + "</td></tr>")
    table_html = "".join(rows) or '<tr><td colspan="7" class="empty">No chats were collected.</td></tr>'
    root_rows = []
    for raw in roots:
        root = _mapping(raw)
        ref = str(root.get("root_ref") or "—")
        title = title_by_ref.get(ref, "Untitled root")
        root_rows.append("<tr><td><code>" + _text(ref) + "</code></td><td title=\"" + _text(title) + "\">" + _text(_short_title(title)) + "</td><td class=\"num\">" + _text(_fmt(root.get("calls"))) + "</td><td class=\"num\">" + _text(_fmt(root.get("total_tokens"))) + "</td><td class=\"num\">" + _text(_fmt(root.get("estimated_credits"), 2)) + "</td></tr>")
    roots_html = "".join(root_rows) or '<tr><td colspan="5" class="empty">No root rollups were collected.</td></tr>'
    def detail_row(label: str, field: str) -> str:
        return "<tr><th>" + _text(label) + "</th><td class=\"num\">" + _text(_fmt(totals.get(field))) + "</td><td class=\"num\">" + _text(_fmt(baseline.get(field))) + "</td><td class=\"num\">" + _text(delta(field)) + "</td></tr>"
    detail_html = "".join((detail_row("Input", "input_tokens"), detail_row("Cached input", "cached_input_tokens"), detail_row("Uncached input", "uncached_input_tokens"), detail_row("Output", "output_tokens"), detail_row("Reasoning output", "reasoning_output_tokens")))
    coverage_html = "".join('<div><b>' + _text(k) + '</b><span>' + _text(_fmt(v) if isinstance(v, (int, float)) else v) + "</span></div>" for k, v in coverage.items()) or '<p class="empty">No coverage counters were supplied.</p>'
    def bullets(values: Sequence[Any], empty: str) -> str:
        return "<ul>" + "".join("<li>" + _text(x) + "</li>" for x in values) + "</ul>" if values else '<p class="empty">' + _text(empty) + "</p>"
    rates = _mapping(rate_card.get("credits_per_million"))
    rate_lines = "".join('<li><b>' + _text(model) + '</b>: input ' + _text(_fmt(_mapping(rate).get("input"), 2)) + ', cached ' + _text(_fmt(_mapping(rate).get("cached_input"), 2)) + ', output ' + _text(_fmt(_mapping(rate).get("output"), 2)) + " credits / 1M tokens</li>" for model, rate in rates.items())
    title = "Codex usage dashboard"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>{title}</title>
<style>
:root{{--ink:#e6edf7;--muted:#93a4bc;--panel:#111b2d;--line:#283854;--bg:#07111f;--accent:#38bdf8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Arial,sans-serif}}main{{max-width:1440px;margin:auto;padding:34px 24px 56px}}header{{display:flex;gap:24px;justify-content:space-between;align-items:end;border-bottom:1px solid var(--line);padding-bottom:23px}}h1{{font-size:30px;margin:0;letter-spacing:-.04em}}h2{{font-size:17px;margin:0 0 16px}}p{{margin:0}}.muted,small{{color:var(--muted)}}.window{{text-align:right;color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:23px 0}}.card,.panel{{background:var(--panel);border:1px solid var(--line);border-radius:12px}}.card{{padding:18px}}.card p{{color:var(--muted);font-size:13px}}.card strong{{display:block;font-size:27px;letter-spacing:-.04em;margin:5px 0}}.card small{{font-size:12px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}}.panel{{padding:19px}}.bar-row{{display:grid;grid-template-columns:minmax(92px,1fr) 3fr minmax(104px,auto);gap:10px;align-items:center;margin:10px 0;font-size:12px}}.bar-label{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.bar-track{{height:10px;background:#1e2c45;border-radius:99px;overflow:hidden}}.bar-fill{{display:block;height:100%;background:var(--bar);border-radius:inherit}}.bar-value{{color:var(--muted);text-align:right;white-space:nowrap}}.table-wrap{{max-height:430px;overflow:auto;border:1px solid var(--line);border-radius:9px}}table{{border-collapse:collapse;width:100%;min-width:820px;font-size:13px}}th{{position:sticky;top:0;background:#17233a;color:var(--muted);font-weight:600;text-align:left}}td,th{{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}}tr:last-child td{{border:0}}.num{{text-align:right;font-variant-numeric:tabular-nums}}code{{display:block;color:#b8d8ff;font:11px ui-monospace,monospace;margin-top:5px;word-break:break-all}}.badge{{display:inline-block;background:#253858;border:1px solid #3a517a;border-radius:99px;padding:2px 7px;font-size:11px;color:#c7dcff}}.coverage{{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:10px}}.coverage div{{border-left:2px solid var(--accent);padding-left:9px}}.coverage b,.coverage span{{display:block}}.coverage span{{color:var(--muted)}}ul{{padding-left:20px;margin:0}}li+li{{margin-top:8px}}.notice{{color:#c6d1e2;font-size:13px}}.empty{{color:var(--muted);font-style:italic}}footer{{color:var(--muted);font-size:12px;margin-top:15px}}@media(max-width:850px){{main{{padding:22px 14px}}header{{display:block}}.window{{text-align:left;margin-top:10px}}.cards,.grid{{grid-template-columns:1fr 1fr}}.bar-row{{grid-template-columns:84px 1fr}}.bar-value{{grid-column:2;text-align:left}}}}@media(max-width:520px){{.cards,.grid{{grid-template-columns:1fr}}h1{{font-size:25px}}}}@media print{{body{{background:#fff;color:#111;font-size:10pt}}main{{max-width:none;padding:0}}.card,.panel{{background:#fff;border-color:#bbb}}.table-wrap{{max-height:none;overflow:visible}}th{{background:#eee;color:#333}}.bar-track{{background:#ddd}}.muted,small,.window,.bar-value,.empty,footer{{color:#555}}.cards{{break-inside:avoid}}}}
</style><style>.panel{{min-width:0}}.coverage b{{overflow-wrap:anywhere;font-size:12px}}.coverage div{{min-width:0}}@media(max-width:850px){{.bar-value{{white-space:normal;overflow-wrap:anywhere}}}}</style></head><body><main>
<header><div><h1>Codex usage dashboard</h1><p class="muted">Token routing and standard-rate estimate</p></div><div class="window"><b>{_text(_date(window.get('start')))} — {_text(_date(window.get('end')))}</b><br>Baseline begins {_text(_date(window.get('baseline_start')))}</div></header>
<section class="cards">{cards}</section>
<section class="grid"><article class="panel"><h2>Hourly token activity</h2>{hours_html}</article><article class="panel"><h2>Model token share</h2>{models_html}</article></section>
<section class="panel"><h2>Model credit share</h2>{credit_models_html}</section>
<section class="panel"><h2>Token detail and baseline</h2><div class="table-wrap"><table class="detail-table"><thead><tr><th>Metric</th><th class="num">This window</th><th class="num">Preceding window</th><th class="num">Change</th></tr></thead><tbody>{detail_html}</tbody></table></div></section>
<section class="panel"><h2>Chats</h2><div class="table-wrap"><table><thead><tr><th>Thread</th><th>Title</th><th>Models</th><th>Efforts</th><th class="num">Calls</th><th class="num">Tokens</th><th class="num">Credits</th></tr></thead><tbody>{table_html}</tbody></table></div></section>
<section class="panel"><h2>Root and descendant rollups</h2><div class="table-wrap"><table><thead><tr><th>Root task</th><th>Root title</th><th class="num">Calls</th><th class="num">Tokens</th><th class="num">Credits</th></tr></thead><tbody>{roots_html}</tbody></table></div></section>
<section class="grid"><article class="panel"><h2>Recommendations</h2>{bullets(recommendations, 'No recommendations supplied.')}</article><article class="panel"><h2>Limitations</h2>{bullets(limitations, 'No limitations supplied.')}</article></section>
<section class="grid"><article class="panel"><h2>Collection coverage</h2><div class="coverage">{coverage_html}</div></article><article class="panel"><h2>Rate card</h2><p class="notice">Verified {_text(_date(rate_card.get('verified_date')))} · {_text(rate_card.get('source') or 'Source not recorded')}</p><ul>{rate_lines or '<li class="empty">No rate card supplied.</li>'}</ul></article></section>
<footer>All input includes cached input. Output includes reasoning output. Estimated credits use the recorded standard rate card only; they are not a bill, invoice, allowance, or usage-limit measurement.</footer>
</main></body></html>'''


def render_markdown(doc: Mapping[str, Any]) -> str:
    """Render a compact, portable Markdown companion to :func:`render_html`."""
    doc = _mapping(doc)
    window, totals, baseline = (_mapping(doc.get(k)) for k in ("window", "totals", "baseline"))
    total_tokens = _number(totals.get("total_tokens"))
    cache_pct = _pct(totals.get("cached_input_tokens"), totals.get("input_tokens"))
    lines = ["# Codex usage dashboard", "", f"**Window:** {_date(window.get('start'))} — {_date(window.get('end'))}", f"**Baseline start:** {_date(window.get('baseline_start'))}", "", "## Totals", "", "| Tokens | Calls | Cache reuse | Estimated standard credits |", "|---:|---:|---:|---:|", f"| {_fmt(total_tokens)} | {_fmt(totals.get('calls'))} | {cache_pct:.1f}% | {_fmt(totals.get('estimated_credits'), 2)} |", "", "All input includes cached input; output includes reasoning output. Credits are a standard-rate estimate, not a bill or allowance.", "", "## Token detail and baseline", "", "| Metric | This window | Preceding window |", "|---|---:|---:|"]
    for label, field in (("Input", "input_tokens"), ("Cached input", "cached_input_tokens"), ("Uncached input", "uncached_input_tokens"), ("Output", "output_tokens"), ("Reasoning output", "reasoning_output_tokens")):
        lines.append(f"| {label} | {_fmt(totals.get(field))} | {_fmt(baseline.get(field))} |")
    lines += ["", "## Models", "", "| Model | Tokens | Token share | Estimated credits |", "|---|---:|---:|---:|"]
    for raw in _items(doc.get("models")):
        model = _mapping(raw)
        lines.append(f"| {_md(model.get('model') or 'Unknown model')} | {_fmt(model.get('total_tokens'))} | {_pct(model.get('total_tokens'), total_tokens):.1f}% | {_fmt(model.get('estimated_credits'), 2)} |")
    lines += ["", "## Chats", "", "| Type | Task | Title | Calls | Tokens | Credits |", "|---|---|---|---:|---:|---:|"]
    for raw in _items(doc.get("chats")):
        chat = _mapping(raw)
        lines.append(f"| {_kind(chat)} | {_md(chat.get('task_ref') or '—')} | {_md(chat.get('title') or 'Untitled chat')} | {_fmt(chat.get('calls'))} | {_fmt(chat.get('total_tokens'))} | {_fmt(chat.get('estimated_credits'), 2)} |")
    lines += ["", "## Root and descendant rollups", "", "| Root task | Root title | Calls | Tokens | Credits |", "|---|---|---:|---:|---:|"]
    title_by_ref = {str(_mapping(chat).get("task_ref") or ""): _mapping(chat).get("title") or "Untitled root" for chat in _items(doc.get("chats"))}
    for raw in _items(doc.get("roots")):
        root = _mapping(raw)
        ref = str(root.get("root_ref") or "—")
        lines.append(f"| {_md(ref)} | {_md(title_by_ref.get(ref, 'Untitled root'))} | {_fmt(root.get('calls'))} | {_fmt(root.get('total_tokens'))} | {_fmt(root.get('estimated_credits'), 2)} |")
    for heading, key, empty in (("Recommendations", "recommendations", "No recommendations supplied."), ("Limitations", "limitations", "No limitations supplied.")):
        lines += ["", f"## {heading}", ""]
        values = _items(doc.get(key))
        lines += [f"- {_md(value)}" for value in values] if values else [empty]
    lines += ["", "## Collection coverage", ""]
    coverage = _mapping(doc.get("coverage"))
    lines += [f"- **{_md(key)}:** {_md(value)}" for key, value in coverage.items()] or ["No coverage counters supplied."]
    if _number(baseline.get("total_tokens")):
        lines += ["", f"Baseline tokens: {_fmt(baseline.get('total_tokens'))} (preceding equal-duration window)."]
    return "\n".join(lines) + "\n"
