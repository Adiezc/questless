# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""World state and its construction from a scenario. The tick loop is added in milestone M2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from questless.config import ScenarioConfig
from questless.sim.entities import (
    ESCROW,
    NPC,
    OUTSIDE,
    PLAYER,
    TOWN,
    Guild,
    Profession,
    Site,
    Traits,
    site_account,
)
from questless.sim.ledger import Asset, Ledger
from questless.sim.names import make_name
from questless.sim.rng import RngStreams

# Sites whose output waits in a stockpile for transport. Market-site producers sell directly.
STOCKPILE_SITES: tuple[Site, ...] = (Site.MINE, Site.FARMS)


@dataclass
class World:
    config: ScenarioConfig
    ledger: Ledger
    rng: RngStreams
    npcs: dict[str, NPC]
    guilds: dict[str, Guild] = field(default_factory=dict)
    prices: dict[Asset, int] = field(default_factory=dict)
    tick: int = 0

    def npcs_in_order(self) -> list[NPC]:
        return [self.npcs[k] for k in sorted(self.npcs)]

    def npcs_by_profession(self, profession: Profession) -> list[NPC]:
        return [n for n in self.npcs_in_order() if n.profession is profession]

    def check_invariants(self) -> None:
        self.ledger.check_conservation()

    def state_dict(self) -> dict:
        """Everything that defines the simulation state, in a deterministic JSON-friendly form."""
        return {
            "tick": self.tick,
            "prices": {str(a): p for a, p in sorted(self.prices.items())},
            "ledger": self.ledger.snapshot(),
            "npcs": {
                n.id: {
                    "guild": n.guild_id,
                    "tool_condition": round(n.tool_condition, 9),
                    "hunger": n.hunger,
                    "state": str(n.state),
                }
                for n in self.npcs_in_order()
            },
            "rng": repr(self.rng.getstate()),
        }

    def state_hash(self) -> str:
        blob = json.dumps(self.state_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()


def build_world(config: ScenarioConfig) -> World:
    """Create the genesis world. Same config (incl. seed) -> identical world, every time."""
    rng = RngStreams(config.seed)
    ledger = Ledger()
    npcs: dict[str, NPC] = {}
    taken_names: set[str] = set()
    trait_rng = rng.stream("genesis.traits")
    name_rng = rng.stream("genesis.names")
    t = config.traits

    index = 0
    for profession in Profession:  # enum order is fixed, so ids are stable
        pc = config.professions[profession]
        for _ in range(pc.count):
            npc_id = f"npc_{index:03d}"
            index += 1
            traits = Traits(
                skill=round(trait_rng.uniform(*t.skill), 3),
                thrift=round(trait_rng.uniform(*t.thrift), 3),
                stock_days=trait_rng.randint(*t.stock_days),
                patience=trait_rng.randint(*t.patience),
            )
            npc = NPC(
                id=npc_id,
                name=make_name(name_rng, str(profession), taken_names),
                profession=profession,
                site=pc.site,
                traits=traits,
                tool_condition=round(trait_rng.uniform(*pc.tool_condition), 3),
            )
            wallet = trait_rng.randint(*pc.wallet)
            ledger.open_account(npc.account, {Asset.COIN: wallet, **pc.inventory})
            npcs[npc_id] = npc

    guilds: dict[str, Guild] = {}
    if config.guilds_enabled:
        for gid, gc in config.guilds.items():
            members = sorted(n.id for n in npcs.values() if n.profession in gc.professions)
            guild = Guild(
                id=gid, name=gc.name, policy=gc.policy, dues_rate=gc.dues_rate, members=members
            )
            for member in members:
                npcs[member].guild_id = gid
            ledger.open_account(guild.account, {Asset.COIN: gc.treasury})
            guilds[gid] = guild

    ledger.open_account(TOWN, {Asset.COIN: config.town.treasury})
    ledger.open_account(PLAYER, {Asset.COIN: config.player_wallet})
    ledger.open_account(ESCROW)
    ledger.open_account(OUTSIDE, dict(config.outside))
    for site in STOCKPILE_SITES:
        ledger.open_account(site_account(site))
    ledger.seal()

    world = World(
        config=config,
        ledger=ledger,
        rng=rng,
        npcs=npcs,
        guilds=guilds,
        prices={asset: gc.base_price for asset, gc in config.goods.items()},
    )
    world.check_invariants()
    return world
