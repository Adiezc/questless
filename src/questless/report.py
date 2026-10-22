"""Exportable simulation run report (M21).

Provides:
- ``build_report(world) -> dict``: Complete summary model of economic and quest metrics.
- ``render_markdown(report_data) -> str``: Clean Markdown summary.
- ``render_html(report_data) -> str``: Standalone offline HTML report with pure SVG sparklines.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from questless.sim.world import World


def build_report(world: World) -> dict[str, Any]:
    """Compile a structured report dictionary from a World simulation instance."""
    stats = world.stats
    days = [s.tick for s in stats]
    current_day = world.tick

    # Economy aggregates
    total_produced = sum(sum(s.produced.values()) for s in stats)
    hungry_history = [s.hungry_npcs for s in stats]
    idle_history = [s.idle_npcs for s in stats]

    # Live contracts from contract board
    live_list = world.contracts.live() if callable(world.contracts.live) else []
    live_contracts = [
        {
            "id": c.id,
            "kind": c.kind.name if hasattr(c.kind, "name") else str(c.kind),
            "good": str(c.good),
            "quantity": c.quantity,
            "reward": c.reward,
            "status": c.status.name if hasattr(c.status, "name") else str(c.status),
        }
        for c in live_list
    ]

    # Guild treasuries
    guild_data = {}
    for gid, guild in sorted(world.guilds.items()):
        guild_data[gid] = {
            "name": getattr(guild, "name", gid.title()),
            "treasury_history": [s.guilds[gid].treasury if gid in s.guilds else 0 for s in stats],
            "escrowed_history": [s.guilds[gid].escrowed if gid in s.guilds else 0 for s in stats],
            "current_treasury": guild.treasury if hasattr(guild, "treasury") else 0,
        }

    scenario_name = getattr(world.config, "name", "Simulation")

    return {
        "scenario": scenario_name,
        "total_days": current_day,
        "days": days,
        "npc_count": len(world.npcs),
        "total_produced": total_produced,
        "hungry_history": hungry_history,
        "idle_history": idle_history,
        "live_contracts": live_contracts,
        "guilds": guild_data,
    }


def _svg_sparkline(values: list[float | int], width: int = 140, height: int = 30) -> str:
    """Generate a lightweight SVG polyline with zero external JS."""
    if not values or len(values) < 2:
        return ""
    min_v, max_v = min(values), max(values)
    span = max_v - min_v if max_v != min_v else 1.0

    points = []
    for i, v in enumerate(values):
        x = round((i / (len(values) - 1)) * (width - 4) + 2, 1)
        y = round(height - 2 - ((v - min_v) / span) * (height - 6), 1)
        points.append(f"{x},{y}")

    poly_pts = " ".join(points)
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="overflow:visible">'
        f'<polyline fill="none" stroke="#2563eb" stroke-width="1.8" points="{poly_pts}" />'
        f"</svg>"
    )


def render_markdown(data: dict[str, Any]) -> str:
    """Render report dictionary as clean Markdown."""
    lines = [
        f"# Questless Simulation Report: {data.get('scenario', 'World')}",
        "",
        f"- **Elapsed Days:** {data.get('total_days', 0)}",
        f"- **Population:** {data.get('npc_count', 0)} NPCs",
        f"- **Total Goods Produced:** {data.get('total_produced', 0)}",
        f"- **Active Contracts:** {len(data.get('live_contracts', []))}",
        "",
        "## Guild Treasuries",
        "",
        "| Guild | Current Treasury |",
        "| :--- | :--- |",
    ]
    for gid, ginfo in data.get("guilds", {}).items():
        curr = (
            ginfo["treasury_history"][-1]
            if ginfo.get("treasury_history")
            else ginfo.get("current_treasury", 0)
        )
        lines.append(f"| {html.escape(ginfo.get('name', gid))} | {curr} coin |")

    lines.extend(["", "## Active Contracts", ""])
    if data.get("live_contracts"):
        lines.append("| ID | Kind | Good | Qty | Reward |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in data["live_contracts"]:
            lines.append(
                f"| {c['id']} | {c['kind']} | {c['good']} | {c['quantity']} | {c['reward']} |"
            )
    else:
        lines.append("No active contracts at report time.")

    return "\n".join(lines)


def render_html(data: dict[str, Any]) -> str:
    """Render report dictionary as an offline, single-file HTML document with SVG charts."""
    guild_rows = []
    for gid, ginfo in data.get("guilds", {}).items():
        history = ginfo.get("treasury_history", [])
        curr = history[-1] if history else 0
        spark = _svg_sparkline(history)
        guild_rows.append(
            f"<tr><td><strong>{html.escape(ginfo.get('name', gid))}</strong></td>"
            f"<td>{curr} coin</td><td>{spark}</td></tr>"
        )

    guild_table = (
        "".join(guild_rows)
        if guild_rows
        else "<tr><td colspan='3'>No guild records</td></tr>"
    )

    contract_rows = []
    for c in data.get("live_contracts", []):
        contract_rows.append(
            f"<tr><td>{html.escape(str(c['id']))}</td><td>{html.escape(str(c['kind']))}</td>"
            f"<td>{html.escape(str(c['good']))}</td><td>{c['quantity']}</td>"
            f"<td>{c['reward']} coin</td></tr>"
        )
    contract_table = (
        "".join(contract_rows)
        if contract_rows
        else "<tr><td colspan='5'>No active contracts</td></tr>"
    )

    hungry_spark = _svg_sparkline(data.get("hungry_history", []))
    scen = html.escape(str(data.get("scenario", "World")))
    days = data.get("total_days", 0)
    npcs = data.get("npc_count", 0)
    prod = data.get("total_produced", 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Questless Simulation Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 860px; margin: 40px auto; padding: 0 20px; color: #1e293b; background: #fff; }}
  h1, h2 {{ color: #0f172a; }}
  .metrics {{ display: flex; gap: 24px; margin: 24px 0; }}
  .card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; flex: 1; }}
  .card .val {{ font-size: 1.8rem; font-weight: 700; color: #2563eb; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0 32px 0; }}
  th, td {{ border-bottom: 1px solid #e2e8f0; padding: 10px 12px; text-align: left; }}
  th {{ background: #f8fafc; font-weight: 600; }}
</style>
</head>
<body>
<h1>Questless Simulation Report</h1>
<p>Scenario: <strong>{scen}</strong> | Day: <strong>{days}</strong></p>

<div class="metrics">
  <div class="card"><div>Total Population</div><div class="val">{npcs} NPCs</div></div>
  <div class="card"><div>Total Production</div><div class="val">{prod}</div></div>
  <div class="card"><div>Hungry History</div><div style="margin-top:8px;">{hungry_spark}</div></div>
</div>

<h2>Guild Treasuries</h2>
<table>
  <thead><tr><th>Guild</th><th>Current Treasury</th><th>Treasury Trend</th></tr></thead>
  <tbody>{guild_table}</tbody>
</table>

<h2>Active Contracts</h2>
<table>
  <thead><tr><th>ID</th><th>Kind</th><th>Good</th><th>Qty</th><th>Reward</th></tr></thead>
  <tbody>{contract_table}</tbody>
</table>

<footer style="margin-top:40px; font-size: 0.85rem; color: #64748b;">
  Generated by Questless Simulation Engine. Single-file offline report.
</footer>
</body>
</html>
"""
