# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Static charts for the experiment (PNG, for the README and case study).

Light surface (GitHub renders README images on light by default). Categorical slots in fixed
order from the validated reference palette; one y-axis per panel; median line with the min-max
band across seeds; the shock window shaded.
"""

from __future__ import annotations

import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SHADE = "#f0efec"
ARM_COLORS = {
    "baseline": MUTED,
    "shock": "#eb6834",
    "shock+importer": "#e87ba4",
    "shock+local": "#2a78d6",
    "shock, no guilds": "#eda100",
    "shock+local, no guilds": "#1baf7a",
}


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def render(rows, scenarios, arms, out: Path) -> None:
    from questless.config import load_scenario

    root = Path(__file__).resolve().parents[1]
    plt.rcParams["font.family"] = ["Helvetica Neue", "Arial", "DejaVu Sans"]

    # 1. Output of the shocked good over time, per arm (median + range across seeds).
    fig, axes = plt.subplots(1, len(scenarios), figsize=(13, 3.8), facecolor=SURFACE)
    for ax, (scenario, good) in zip(axes, scenarios.items(), strict=True):
        _style(ax)
        shock = load_scenario(root / "scenarios" / f"{scenario}.toml").shocks[0]
        ax.axvspan(shock.start, shock.start + shock.duration, color=SHADE, zorder=0)
        ax.text(
            shock.start + 1,
            0.98,
            shock.name,
            transform=ax.get_xaxis_transform(),
            fontsize=8,
            color=INK_2,
            va="top",
        )
        for arm in ("baseline", "shock", "shock+importer", "shock+local"):
            series = [r["series"] for r in rows if r["scenario"] == scenario and r["arm"] == arm]
            days = range(len(series[0]))
            med = [st.median(s[d] for s in series) for d in days]
            lo = [min(s[d] for s in series) for d in days]
            hi = [max(s[d] for s in series) for d in days]
            ax.fill_between(days, lo, hi, color=ARM_COLORS[arm], alpha=0.12, linewidth=0)
            ax.plot(days, med, color=ARM_COLORS[arm], linewidth=2, label=arm)
        ax.set_title(
            f"{scenario.replace('_', ' ').title()}: {str(good).replace('_', ' ')} per day",
            fontsize=10,
            color=INK,
            loc="left",
        )
        ax.set_xlabel("day", fontsize=9, color=MUTED)
        ax.set_ylim(bottom=0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9, loc="lower center", ncol=len(labels))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(out / "output_over_time.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)

    # 2. Shortage days per arm (dots per seed + median tick), for each scenario.
    fig, axes = plt.subplots(1, len(scenarios), figsize=(13, 3.6), facecolor=SURFACE, sharey=True)
    shocked = [a for a in arms if a != "baseline"]
    for ax, scenario in zip(axes, scenarios, strict=True):
        _style(ax)
        for i, arm in enumerate(shocked):
            vals = [
                r["shortage_days"] for r in rows if r["scenario"] == scenario and r["arm"] == arm
            ]
            ax.scatter([i] * len(vals), vals, s=22, color=ARM_COLORS[arm], alpha=0.7, linewidths=0)
            ax.hlines(st.median(vals), i - 0.28, i + 0.28, color=INK, linewidth=2)
        ax.set_xticks(range(len(shocked)))
        ax.set_xticklabels([a.replace(", ", ",\n") for a in shocked], fontsize=8, color=INK_2)
        ax.set_title(scenario.replace("_", " ").title(), fontsize=10, color=INK, loc="left")
    axes[0].set_ylabel("days with >10% of demand unmet", fontsize=9, color=MUTED)
    fig.tight_layout()
    fig.savefig(out / "shortage_days.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
