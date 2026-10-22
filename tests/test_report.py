from pathlib import Path

from questless.api import Simulation
from questless.report import build_report, render_html, render_markdown


def test_build_report_and_renderers():
    sim = Simulation.from_scenario(Path("scenarios/baseline.toml"), seed=42)
    sim.step(12)
    report = build_report(sim.world)

    assert report["total_days"] == 12
    assert report["npc_count"] > 0
    assert "guilds" in report
    assert len(report["guilds"]) > 0

    md = render_markdown(report)
    assert "# Questless Simulation Report" in md
    assert "Guild Treasuries" in md

    html_out = render_html(report)
    assert "<!DOCTYPE html>" in html_out
    assert "Questless Simulation Report" in html_out
    assert "<svg" in html_out
