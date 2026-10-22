# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Plotly figures for the dashboard.

Palette (validated with the dataviz skill's checker against the #1a1a19 surface):
- goods, fixed by entity: food blue, iron ore orange, tools aqua, weapons yellow
- guilds and map states use the first three slots (all-pairs safe); "hungry" is a status colour
  and always comes with its own marker shape and legend label
One y-axis per chart, recessive grid, hover on every mark.
"""

from __future__ import annotations

import math
import random

import plotly.graph_objects as go

from questless.contracts.provenance import _label as subject_label
from questless.sim.ledger import Asset

SURFACE = "#1a1a19"
INK = "#f0efec"
INK_2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"
AXIS = "#383835"
SHADE = "rgba(224, 163, 60, 0.08)"  # shock windows: a wash of the UI accent
ACCENT = "#e0a33c"
CRITICAL = "#d03b3b"

GOOD_COLORS = {"food": "#3987e5", "iron_ore": "#d95926", "tools": "#199e70", "weapons": "#c98500"}
GOOD_LABELS = {"food": "Food", "iron_ore": "Iron ore", "tools": "Tools", "weapons": "Weapons"}
# Guilds have their own distinct palette (purple/violet, teal/cyan, and gold/ochre) to avoid clashing with good colors
GUILD_COLORS = {"miners": "#9c6ade", "merchants": "#0bb8b8", "blacksmiths": "#d49b28"}

STATE_STYLE = {
    "working": ("Working", "#3987e5", "circle"),
    "idle_no_input": ("Idle: no inputs", "#d95926", "square"),
    "idle_no_demand": ("Paused: unsold stock", MUTED, "circle-open"),
    "hungry": ("Hungry", CRITICAL, "x"),
}

SITE_POS = {"market": (5.0, 3.7), "mine": (1.6, 1.2), "farms": (8.4, 1.2)}
SITE_LABEL = {"market": "Market", "mine": "Mine", "farms": "Farms"}


def _layout(
    fig: go.Figure, height: int, title: str | None = None, legend: bool = True
) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=(58 if legend else 34) if title else 8, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family="Geist, system-ui, sans-serif", color=INK_2, size=12),
        title=dict(
            text=title,
            font=dict(size=13, color=INK),
            x=0.01,
            y=0.985,
            yref="container",
            yanchor="top",
        )
        if title
        else None,
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hoverlabel=dict(bgcolor="#222220", bordercolor=GRID, font=dict(color=INK)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    return fig


def _shade_shocks(fig: go.Figure, shocks, day_max: int) -> None:
    for s in shocks:
        if s.start > day_max:
            continue
        fig.add_vrect(
            x0=s.start,
            x1=min(s.end, day_max + 1) - 0.5,
            fillcolor=SHADE,
            line_width=0,
            layer="below",
        )
        fig.add_annotation(
            x=s.start,
            y=1,
            yref="paper",
            text=s.name,
            showarrow=False,
            xanchor="left",
            yanchor="top",
            font=dict(size=10, color=ACCENT),
        )


def settlement_map(sim) -> go.Figure:
    """Three sites, the roads between them, and every NPC as a dot coloured by its state."""
    world = sim.world
    fig = go.Figure()
    for site in ("mine", "farms"):
        (x0, y0), (x1, y1) = SITE_POS["market"], SITE_POS[site]
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                hoverinfo="skip",
                line=dict(color=AXIS, width=2),
                showlegend=False,
            )
        )

    stockpile = {"mine": 0, "farms": 0}
    for n in world.npcs.values():
        if n.site_account != n.account:
            stockpile[str(n.site)] += sum(world.ledger.holdings(n.site_account).values())
    for site, (x, y) in SITE_POS.items():
        extra = f"<br>{stockpile[site]} units waiting" if site in stockpile else ""
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers",
                marker=dict(
                    size=34, symbol="square", color="#222220", line=dict(color=AXIS, width=1)
                ),
                showlegend=False,
                hovertemplate=f"{SITE_LABEL[site]}{extra}<extra></extra>",
            )
        )
        # Label clear of the NPC cluster around the site.
        fig.add_annotation(
            x=x,
            y=y + (1.55 if site == "market" else -1.25),
            text=SITE_LABEL[site],
            showarrow=False,
            font=dict(color=INK, size=12),
        )

    groups: dict[str, list] = {k: [] for k in STATE_STYLE}
    merchants = sorted(n.id for n in world.npcs.values() if str(n.profession) == "merchant")
    for n in world.npcs_in_order():
        rng = random.Random(n.id)  # stable position per NPC
        if str(n.profession) == "merchant":
            dest = "mine" if merchants.index(n.id) % 2 else "farms"
            t = 0.2 + 0.6 * rng.random()
            (x0, y0), (x1, y1) = SITE_POS["market"], SITE_POS[dest]
            x, y = (
                x0 + t * (x1 - x0) + rng.uniform(-0.15, 0.15),
                y0 + t * (y1 - y0) + rng.uniform(-0.15, 0.15),
            )
        else:
            cx, cy = SITE_POS[str(n.site)]
            radius = 0.55 + 0.6 * rng.random() + (0.35 if str(n.profession) == "guard" else 0)
            angle = rng.uniform(0, 2 * math.pi)
            x, y = cx + radius * math.cos(angle) * 1.25, cy + radius * math.sin(angle) * 0.8
        groups[str(n.state) if str(n.state) in groups else "working"].append((x, y, n))

    for state, (label, color, symbol) in STATE_STYLE.items():
        pts = groups[state]
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="markers",
                name=f"{label} ({len(pts)})",
                marker=dict(size=9, color=color, symbol=symbol, line=dict(color=SURFACE, width=1)),
                customdata=[
                    [p[2].name, str(p[2].profession), world.ledger.balance(p[2].id, Asset.COIN)]
                    for p in pts
                ],
                hovertemplate="%{customdata[0]}<br>%{customdata[1]}, "
                + label.lower()
                + "<br>%{customdata[2]} coin<extra></extra>",
            )
        )
    fig.update_xaxes(visible=False, range=[-0.2, 10.2])
    fig.update_yaxes(visible=False, range=[-0.6, 5.6], scaleanchor="x", scaleratio=1)
    return _layout(fig, 340)


def goods_lines(
    series: dict,
    key: str,
    title: str,
    shocks,
    height: int = 260,
    percent: bool = False,
    index: bool = False,
) -> go.Figure:
    """One line per good. ``percent`` pins a 0-100% axis (shares); ``index`` marks 100% = normal
    with a reference line (``*_index`` series)."""
    days = series["day"]
    suffix = "%" if percent or index else ""
    fig = go.Figure()
    for good, values in series[key].items():
        fig.add_trace(
            go.Scatter(
                x=days,
                y=values,
                mode="lines",
                name=GOOD_LABELS[good],
                line=dict(color=GOOD_COLORS[good], width=2),
                hovertemplate=GOOD_LABELS[good] + ": %{y}" + suffix + "<extra></extra>",
            )
        )
    _shade_shocks(fig, shocks, days[-1] if days else 0)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title=dict(text="day", font=dict(size=11, color=MUTED)))
    if percent:  # a share stays within 0-100; the padding keeps lines at the limits visible
        ticks = [0, 25, 50, 75, 100]  # explicit text: Plotly drops ticksuffix with tickvals
        fig.update_yaxes(range=[-3, 103], tickvals=ticks, ticktext=[f"{t}%" for t in ticks])
    if index:
        fig.add_hline(y=100, line=dict(color=MUTED, width=1, dash="dot"))
        fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    return _layout(fig, height, title)


def single_line(days, values, title: str, color: str, shocks, height: int = 220) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=days,
            y=values,
            mode="lines",
            line=dict(color=color, width=2),
            hovertemplate="day %{x}: %{y}<extra></extra>",
        )
    )
    _shade_shocks(fig, shocks, days[-1] if days else 0)
    fig.update_yaxes(rangemode="tozero")
    return _layout(fig, height, title, legend=False)


def evidence_chart(sim, contract, step: int) -> go.Figure:
    """One measured step of the contract's chain, day by day. Values come from
    ``sim.evidence_series``, i.e. the same ``measure()`` that ``verify()`` re-checks, so the line
    passes exactly through the recorded value (the marked point). Baseline and threshold from the
    evidence are drawn as reference lines."""
    ev = contract.provenance.chain[step]
    points = sim.evidence_series(contract.id, step)
    days, values = list(points), list(points.values())
    color = GOOD_COLORS.get(str(contract.good), ACCENT)
    fig = go.Figure(
        go.Scatter(
            x=days,
            y=values,
            mode="lines",
            line=dict(color=color, width=2),
            hovertemplate="day %{x}: %{y}<extra></extra>",
        )
    )
    for value, name, dash in ((ev.baseline, "normal", "dot"), (ev.threshold, "threshold", "dash")):
        if value is not None:
            fig.add_hline(
                y=value,
                line=dict(color=INK_2, width=1, dash=dash),
                annotation_text=f"{name} {value:g}",
                annotation_position="top left",
                annotation_font=dict(size=10, color=INK_2),
            )
    tick = ev.measure[1]
    fig.add_trace(
        go.Scatter(
            x=[tick],
            y=[points[tick]],
            mode="markers",
            marker=dict(color=ACCENT, size=9, line=dict(color=SURFACE, width=2)),
            hovertemplate=f"day {tick}: recorded {ev.value:g}<extra></extra>",
        )
    )
    fig.add_vline(
        x=contract.created_tick,
        line=dict(color=ACCENT, width=1),
        annotation_text=f"{contract.id} posted",
        annotation_position="top right",
        annotation_font=dict(size=10, color=ACCENT),
    )
    _shade_shocks(fig, sim.world.modifiers.shocks, days[-1] if days else 0)
    title = f"{subject_label(ev.subject)}: {ev.metric.replace('_', ' ')}"
    return _layout(fig, 210, title, legend=False)


def default_step(chain, steps: list[int]) -> int | None:
    """The fact charted until the player picks one: the output drop if there is one (the usual
    story), else the first measured effect after the root cause."""
    for kind in ("production_drop", "transport_backlog", "unfilled_demand"):
        for i in steps:
            if chain[i].kind == kind:
                return i
    effects = [i for i in steps if chain[i].kind != "shock"]
    return (effects or steps or [None])[0]


def treasury_chart(series: dict, names: dict[str, str], shocks) -> go.Figure:
    days = series["day"]
    fig = go.Figure()
    for gid, values in series["treasury"].items():
        fig.add_trace(
            go.Scatter(
                x=days,
                y=values,
                mode="lines",
                name=names[gid],
                line=dict(color=GUILD_COLORS.get(gid, INK_2), width=2),
                hovertemplate=names[gid] + ": %{y} coin<extra></extra>",
            )
        )
    _shade_shocks(fig, shocks, days[-1] if days else 0)
    fig.update_layout(hovermode="x unified", yaxis=dict(rangemode="tozero"))
    return _layout(fig, 260, "Guild treasuries (coin)")
