# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Questless interactive demo.

    uv run questless demo        (or: uv run streamlit run app/streamlit_app.py)

A thin view over ``questless.Simulation``: every button calls the public API, so the dashboard
can only show what the engine computed. The simulation lives in ``st.session_state``.
"""

from __future__ import annotations

import html
from pathlib import Path

import charts
import pandas as pd
import streamlit as st

from questless import Simulation
from questless.contracts.model import ContractKind, Status
from questless.player import ActionError, Quote, quote_buy, quote_caravan
from questless.sim.ledger import GOODS

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "Iron Shortage": "iron_shortage.toml",
    "Mine Disaster": "mine_disaster.toml",
    "Drought": "drought.toml",
    "Bandits on the Road": "bandits.toml",
    "Baseline (no shocks)": "baseline.toml",
}
SHOCKS = {
    "Mine collapse": dict(effect="site_output", site="mine", factor=0.2, duration=25),
    "Drought": dict(effect="site_output", site="farms", factor=0.4, duration=20),
    "Bandits on the road": dict(effect="transport_capacity", factor=0.3, duration=15),
    "New ore deposit": dict(effect="site_output", site="mine", factor=1.8, duration=30),
}
KIND_LABEL = {
    ContractKind.PROCUREMENT: ("Procurement", ":material/person:"),
    ContractKind.GUILD_SUPPLY: ("Guild supply", ":material/groups:"),
    ContractKind.TOWN_SUPPLY: ("Town supply", ":material/shield:"),
    ContractKind.TRANSPORT: ("Haulage", ":material/local_shipping:"),
}
EVIDENCE_GROUP = {
    "shock": ("root", "Root cause"),
    "production_drop": ("cause", "Effect"),
    "equipment_shortage": ("cause", "Effect"),
    "input_shortage": ("cause", "Effect"),
    "hunger": ("cause", "Effect"),
    "price_spike": ("cause", "Market"),
    "transport_backlog": ("cause", "Bottleneck"),
    "unfilled_demand": ("cause", "Shortage"),
    "need_persisted": ("cause", "Need"),
    "guild_emergency": ("decision", "Guild decision"),
    "town_emergency": ("decision", "Town decision"),
    "partial_funding": ("decision", "Funding"),
    "funding_decision": ("decision", "Funding"),
}

st.set_page_config(page_title="Questless", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    f"<style>{(Path(__file__).parent / 'theme.css').read_text()}</style>", unsafe_allow_html=True
)


# --- state & actions ------------------------------------------------------------------------------


def load(label: str, seed: int) -> None:
    sim = Simulation.from_scenario(ROOT / "scenarios" / SCENARIOS[label], seed=seed)
    first = sim.run_until_contract(max_days=45)  # open on a live quest, not an empty board
    st.session_state.update(sim=sim, selected=first, scenario=label, seed=seed)


def sim() -> Simulation:
    return st.session_state.sim


def act(fn, *args, success: str | None = None) -> None:
    """Run a player action; report the outcome as a toast. ActionError changes nothing."""
    try:
        result = fn(*args)
        if success:
            st.toast(success.format(result=result), icon=":material/check:")
    except ActionError as exc:
        st.toast(str(exc), icon=":material/block:")


def following_own_contract() -> bool:
    cid = st.session_state.get("selected")
    contracts = sim().world.contracts.contracts
    return bool(cid in contracts and contracts[cid].accepted_by == "player")


def advance(days: int) -> None:
    created = sim().step(days)
    if created:
        if not following_own_contract():  # keep the player's own contract (and its outcome) open
            st.session_state.selected = created[-1]
        st.toast(f"{len(created)} new contract(s) posted", icon=":material/assignment:")


def next_quest() -> None:
    cid = sim().run_until_contract(max_days=60)
    if cid:
        st.session_state.selected = cid
    else:
        st.toast("No new contract in 60 days. The world is calm.", icon=":material/bedtime:")


def fire_shock(name: str) -> None:
    act(lambda: sim().shock(name=name, **SHOCKS[name]), success=f"{name} from day {sim().day}")


if "sim" not in st.session_state:
    load("Iron Shortage", 42)


# --- helpers -------------------------------------------------------------------------------------


def names() -> dict[str, str]:
    return {n.id: n.name for n in sim().world.npcs.values()}


def requester_label(c) -> str:
    world = sim().world
    if c.requester.startswith("guild:"):
        return world.guilds[c.requester.removeprefix("guild:")].name
    if c.requester == "town":
        return "Town Watch"
    npc = world.npcs[c.requester]
    return f"{npc.name}, {npc.profession}"


def quest_title(c) -> str:
    good = charts.GOOD_LABELS[str(c.good)]
    if c.kind is ContractKind.TRANSPORT:
        return f"Haul {good.lower()} to market"
    return f"{good} for {requester_label(c).split(',')[0]}"


def kind_label(c) -> tuple[str, str]:
    return KIND_LABEL[c.kind]


def profit_tag(quote: Quote | None) -> str:
    """Estimated profit for a card's meta line, e.g. "≈ +120 profit (market)"."""
    if quote is None:
        return (
            '<span class="ql-loss" title="Neither the market nor a caravan can supply it">'
            "can't source</span>"
        )
    css = "ql-profit" if quote.profit >= 0 else "ql-loss"
    tip = f"Reward minus about {quote.cost} coin to source it ({quote.source}), at today's prices"
    return f'<span class="{css}" title="{tip}">≈ {quote.profit:+d} profit ({quote.source})</span>'


# --- header --------------------------------------------------------------------------------------

with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
    st.markdown(
        '<div class="ql-brand"><h1>Questless</h1><span>Emergent quests</span></div>',
        unsafe_allow_html=True,
    )
    label = st.selectbox(
        "Scenario",
        list(SCENARIOS),
        index=list(SCENARIOS).index(st.session_state.scenario),
        width=180,
    )
    seed = st.number_input("Seed", value=st.session_state.seed, step=1, min_value=0, width=100)
    st.button("Load", icon=":material/restart_alt:", on_click=load, args=(label, int(seed)))
    st.space("small")
    st.metric("Day", sim().day, width=80)
    st.button("+1", on_click=advance, args=(1,), help="Advance 1 day")
    st.button("+7", on_click=advance, args=(7,), help="Advance 7 days")
    st.button("+30", on_click=advance, args=(30,), help="Advance 30 days")
    st.button("Next quest", icon=":material/skip_next:", type="primary", on_click=next_quest)
    with st.popover("Shock", icon=":material/bolt:"):
        st.caption(
            "Starts today. Shocks only change rates; every effect flows through the economy."
        )
        for name, spec in SHOCKS.items():
            detail = f"x{spec['factor']} for {spec['duration']} days"
            st.button(f"{name} ({detail})", on_click=fire_shock, args=(name,), width="stretch")

st.divider()

# --- main row: world | quest board | provenance --------------------------------------------------

world_col, board_col, why_col = st.columns([1.05, 1.0, 1.25], gap="medium")
s = sim()
series = s.timeseries()
last = s.world.stats[-1] if s.world.stats else None

with world_col:
    st.markdown('<p class="ql-h">Living world</p>', unsafe_allow_html=True)
    st.plotly_chart(charts.settlement_map(s), config={"displayModeBar": False})
    with st.container(horizontal=True):
        st.metric("Hungry NPCs", last.hungry_npcs if last else 0)
        st.metric("Idle for inputs", last.idle_npcs if last else 0)
        st.metric("Live contracts", len(s.world.contracts.live()))
        st.metric("Your coin", s.player()["coin"])
    prices = " ".join(
        f'<span>{charts.GOOD_LABELS[g]} <b class="ql-num">{p:.1f}</b></span>'
        for g, p in s.prices().items()
    )
    st.markdown(f'<div class="ql-card-meta">Prices today: {prices}</div>', unsafe_allow_html=True)

with board_col:
    st.markdown('<p class="ql-h">Quest board</p>', unsafe_allow_html=True)
    view = st.segmented_control(
        "Show", ["Open", "Yours", "History"], default="Open", label_visibility="collapsed"
    )
    contracts = s.contracts()
    if view == "Open":
        shown = [c for c in contracts if c.status is Status.OPEN]
    elif view == "Yours":
        shown = [c for c in contracts if c.accepted_by == "player"]
    else:
        shown = [c for c in contracts if not c.live]
    shown.sort(key=lambda c: (-c.created_tick, c.id))
    if not shown:
        msg = {
            "Open": "No open contracts. Advance time or shock the economy to see quests emerge.",
            "Yours": "You have not taken a contract yet. Open one and accept it.",
            "History": "Nothing has closed yet.",
        }[view or "Open"]
        st.markdown(f'<div class="ql-empty">{msg}</div>', unsafe_allow_html=True)
    with st.container(height=640, border=False):
        for c in shown[:30]:
            selected = c.id == st.session_state.selected
            with st.container(key=f"{'questsel' if selected else 'quest'}-{c.id}"):
                kind, icon = kind_label(c)
                quote = s.quote(c.id) if c.live else None
                st.markdown(
                    f'<div class="ql-card-title">{html.escape(quest_title(c))}</div>'
                    f'<div class="ql-card-reason">{html.escape(c.reason)}</div>'
                    f'<div class="ql-card-meta"><span class="ql-reward">{c.reward} coin</span>'
                    f"<span><b>{c.qty}</b> {charts.GOOD_LABELS[str(c.good)].lower()}</span>"
                    f"<span>{kind}</span>"
                    + (profit_tag(quote) if c.live else "")
                    + (
                        f"<span>{c.deadline_tick - s.day} days left</span>"
                        if c.live
                        else f"<span>{c.status.value}</span>"
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
                with st.container(horizontal=True, gap="small"):
                    st.button(
                        "Why?",
                        key=f"why-{c.id}",
                        icon=":material/account_tree:",
                        on_click=lambda cid=c.id: st.session_state.update(selected=cid),
                    )
                    if c.status is Status.OPEN:
                        st.button(
                            "Accept",
                            key=f"acc-{c.id}",
                            icon=":material/handshake:",
                            on_click=act,
                            args=(s.accept, c.id),
                            kwargs={"success": "Accepted {result}"},
                        )
    suppressed = s.summary()["suppressed"]
    if suppressed:
        parts = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(suppressed.items()))
        st.caption(f"Needs not turned into contracts so far: {parts}.")

with why_col:
    st.markdown('<p class="ql-h">Why does this quest exist?</p>', unsafe_allow_html=True)
    cid = st.session_state.selected
    if not cid or cid not in s.world.contracts.contracts:
        st.markdown(
            '<div class="ql-empty">Select a contract and press <b>Why?</b> to trace it back to '
            "its root cause.</div>",
            unsafe_allow_html=True,
        )
    else:
        c = s.contract(cid)
        kind, icon = kind_label(c)
        st.markdown(
            f"**{icon} {html.escape(quest_title(c))}** &nbsp; `{c.id}` &nbsp; {c.status.value}"
        )
        st.markdown(
            f'<p class="ql-summary">{html.escape(s.summarise(c.id))}</p>', unsafe_allow_html=True
        )
        chain = c.provenance.chain
        steps = [i for i, e in enumerate(chain) if e.measure]  # the ones a chart can show
        picked = st.session_state.get(f"step-{c.id}")
        if picked not in steps:
            picked = charts.default_step(chain, steps)
        lines = c.provenance.render(names())
        items = []
        for i, (ev, line) in enumerate(zip(chain, lines, strict=True)):
            group, tag = EVIDENCE_GROUP.get(ev.kind, ("cause", "Fact"))
            day, _, text = line.partition(": ")
            items.append(
                f'<li class="{group}{" picked" if i == picked else ""}">'
                f'<span class="ql-kind">{tag}</span>'
                f'<span class="ql-day">{html.escape(day)}</span>'
                f'<span class="ql-text">{html.escape(text)}</span></li>'
            )
        st.markdown(f'<ol class="ql-chain">{"".join(items)}</ol>', unsafe_allow_html=True)
        measured = len(steps)
        problems = s.verify(c.id)
        if problems:
            st.error("Provenance check failed: " + "; ".join(problems))
        else:
            st.markdown(
                f'<div class="ql-verified"><b>Verified.</b> All {measured} measured facts '
                "re-check against the simulation record.</div>",
                unsafe_allow_html=True,
            )
        if steps:
            tags = {i: EVIDENCE_GROUP.get(chain[i].kind, ("", "Fact"))[1] for i in steps}
            chips = {  # add the day only where two facts share a tag
                i: tag if list(tags.values()).count(tag) == 1 else f"{tag} · day {chain[i].tick}"
                for i, tag in tags.items()
            }
            st.pills(
                "Chart a measured fact",
                steps,
                default=picked,
                key=f"step-{c.id}",
                format_func=lambda i: chips[i],
            )
            st.plotly_chart(charts.evidence_chart(s, c, picked), config={"displayModeBar": False})

        lineage = s.lineage(c.id)
        if lineage["ancestors"] or lineage["children"]:
            with st.container(horizontal=True, gap="small", vertical_alignment="center"):
                st.caption("Quest lineage")
                for other in reversed(lineage["ancestors"]):
                    st.button(
                        f"follows {other}",
                        key=f"anc-{c.id}-{other}",
                        on_click=lambda o=other: st.session_state.update(selected=o),
                    )
                for other in lineage["children"]:
                    st.button(
                        f"led to {other}",
                        key=f"chi-{c.id}-{other}",
                        on_click=lambda o=other: st.session_state.update(selected=o),
                    )

        # Player panel
        player = s.player()
        good = str(c.good)
        held = player["goods"].get(good, 0)
        if c.status is Status.OPEN:
            st.button(
                "Accept this contract",
                type="primary",
                icon=":material/handshake:",
                on_click=act,
                args=(s.accept, c.id),
                kwargs={"success": "Accepted {result}"},
            )
        elif c.status is Status.ACCEPTED:
            st.markdown(
                f"You hold **{held}/{c.qty}** {charts.GOOD_LABELS[good].lower()}. "
                f"Deadline: day {c.deadline_tick}."
            )
            if c.kind is not ContractKind.TRANSPORT:
                missing = max(c.qty - held, 0)
                market_cost = quote_buy(s.world, c.good, missing)
                caravan_cost = quote_caravan(s.world, c.good, missing)
                with st.container(horizontal=True, gap="small"):
                    st.button(
                        f"Buy {missing} at market ({market_cost} coin)"
                        if market_cost is not None
                        else f"Not enough {charts.GOOD_LABELS[good].lower()} for sale",
                        disabled=not missing or market_cost is None,
                        icon=":material/shopping_cart:",
                        on_click=act,
                        args=(s.buy, good, max(missing, 1)),
                        kwargs={"success": "Bought {result} at market. Prices will feel it."},
                    )
                    st.button(
                        f"Caravan {missing} ({caravan_cost} coin, "
                        f"{s.config.contracts.caravan_days} days)"
                        if caravan_cost is not None
                        else "No caravan carries enough",
                        disabled=not missing or caravan_cost is None,
                        icon=":material/local_shipping:",
                        on_click=act,
                        args=(s.caravan, good, max(missing, 1)),
                        kwargs={"success": "Caravan arrives on day {result}"},
                    )
            with st.container(horizontal=True, gap="small"):
                st.button(
                    "Deliver",
                    type="primary",
                    icon=":material/inventory_2:",
                    on_click=act,
                    args=(s.deliver, c.id),
                    kwargs={"success": "Delivered {result}. Reward paid."},
                )
                st.button(
                    "Abandon",
                    icon=":material/undo:",
                    on_click=act,
                    args=(s.abandon, c.id),
                    kwargs={"success": "Abandoned {result}. Reputation fell."},
                )
            if player["caravans"]:
                arriving = ", ".join(
                    f"{x['qty']} {x['good']} on day {x['arrives']}" for x in player["caravans"]
                )
                st.caption(f"Caravans on the road: {arriving}.")
        elif c.status is Status.FULFILLED:
            before, after = c.outcome.get("before"), c.outcome.get("after")
            if after:
                st.markdown("**What changed for the people you helped (7 days before vs after)**")
                with st.container(horizontal=True):
                    st.metric(
                        "Units produced", after["produced"], after["produced"] - before["produced"]
                    )
                    st.metric(
                        "Idle days",
                        after["idle_days"],
                        after["idle_days"] - before["idle_days"],
                        delta_color="inverse",
                    )
                    st.metric(
                        f"Days short of {good.replace('_', ' ')}",
                        after["days_short"],
                        after["days_short"] - before["days_short"],
                        delta_color="inverse",
                    )
            else:
                st.caption("Delivered. The effect on the beneficiaries is measured 7 days later.")

st.divider()

# --- tabs ----------------------------------------------------------------------------------------

shocks = s.world.modifiers.shocks
econ, npcs_tab, guilds_tab, log_tab, about_tab = st.tabs(
    ["Economy", "NPCs", "Guilds", "Event log", "How it works"]
)

with econ:
    # Index view needs the reference window (days 10-14) to have passed; until then show units.
    indexed = st.toggle(
        "Show as % of normal",
        key="indexed",
        help="Each good relative to its average over days 10-14, after warm-up and before shocks.",
    ) and any(v is not None for values in series["price_index"].values() for v in values)
    a, b = st.columns(2)
    with a:
        st.plotly_chart(
            charts.goods_lines(
                series,
                "produced_index" if indexed else "produced",
                "Production (% of normal)" if indexed else "Production per day",
                shocks,
                index=indexed,
            ),
            config={"displayModeBar": False},
        )
        st.plotly_chart(
            charts.goods_lines(
                series,
                "unfilled_pct",
                "Unmet demand (% of buyers who could pay)",
                shocks,
                percent=True,
            ),
            config={"displayModeBar": False},
        )
    with b:
        st.plotly_chart(
            charts.goods_lines(
                series,
                "price_index" if indexed else "price",
                "Prices (% of normal)" if indexed else "Prices (coin)",
                shocks,
                index=indexed,
            ),
            config={"displayModeBar": False},
        )
        st.plotly_chart(
            charts.single_line(
                series["day"], series["hungry"], "Hungry NPCs", charts.CRITICAL, shocks
            ),
            config={"displayModeBar": False},
        )

with npcs_tab:
    rows = []
    for n in s.world.npcs_in_order():
        info = s.npc(n.id)
        rows.append(
            {
                "Name": info["name"],
                "Profession": info["profession"],
                "Guild": info["guild"] or "",
                "State": info["state"].replace("_", " "),
                "Coin": info["coin"],
                **{charts.GOOD_LABELS[str(g)]: info["goods"].get(str(g), 0) for g in GOODS},
                "Equipment": info["equipment_condition"],
                "Days hungry": info["hunger"],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, height=420)

with guilds_tab:
    cols = st.columns(len(s.world.guilds) or 1)
    for col, gid in zip(cols, sorted(s.world.guilds), strict=False):
        g = s.guild(gid)
        with col:
            st.metric(
                g["name"],
                f"{g['treasury']} coin",
                help=f"Reserve kept for emergencies: {g['reserve']}",
            )
            st.caption(
                f"{g['members']} members. Your reputation: {g['reputation'].get('player', 0)}"
            )
    guild_names = {gid: s.world.guilds[gid].name for gid in s.world.guilds}
    if guild_names:
        st.plotly_chart(
            charts.treasury_chart(series, guild_names, shocks), config={"displayModeBar": False}
        )

with log_tab:
    events = []
    for sh in shocks:
        events.append((sh.start, "Shock", f"{sh.name}: x{sh.factor} until day {sh.end - 1}"))
    for c in s.contracts():
        events.append(
            (c.created_tick, "Contract posted", f"{c.id} {quest_title(c)} ({c.reward} coin)")
        )
        if c.closed_tick is not None:
            events.append((c.closed_tick, f"Contract {c.status.value}", f"{c.id} {quest_title(c)}"))
    for a_ in s.world.actions:
        args = ", ".join(f"{k}={v}" for k, v in a_["args"].items())
        events.append((a_["tick"], "You", f"{a_['action']} {args}"))
    events.sort(key=lambda e: -e[0])
    st.dataframe(
        pd.DataFrame(events, columns=["Day", "Event", "Detail"]), hide_index=True, height=420
    )

with about_tab:
    st.markdown(
        """
100 rule-based NPCs farm, mine, forge, haul and trade. When the economy leaves needs unmet,
guilds and townsfolk post funded contracts. Every quest below was caused by the simulation,
and can show you why.

**The loop.** NPC activity sets economic conditions. Unmet needs become contracts. Player actions
change the world, which creates new activity.

- **NPCs** follow simple rules: eat, keep their tools working, produce, trade. No LLM is involved.
- **A need** becomes a contract only when it is persistent *scarcity* (the NPC could pay, but
  nobody could sell), never mere poverty.
- **Every contract is funded.** The reward is escrowed by the NPC, its guild or the town before
  the contract is posted. A guild that cannot afford it posts less, or nothing.
- **Every contract explains itself.** The chain on the right is assembled from recorded statistics,
  and each number is re-measured to verify it.
- **Everything is reproducible.** Same scenario, same seed and same actions give the same world.

Source, tests and docs: see the repository README.
        """
    )
