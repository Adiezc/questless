from questless.api import Simulation
from questless.sim.entities import OUTSIDE, Asset
from questless.sim.smuggling import SMUGGLERS, SmugglingFaction


def test_smuggling_faction_trigger_and_trade():
    sim = Simulation.from_scenario("scenarios/baseline.toml", seed=42)
    world = sim.world

    # Open smugglers account
    if SMUGGLERS not in world.ledger.accounts():
        world.ledger.add_empty_account(SMUGGLERS)

    faction = SmugglingFaction()
    assert not faction.active

    # Force stress: set food price to ceiling for 3 days
    food_cfg = world.config.goods[Asset.FOOD]
    world.prices[Asset.FOOD] = food_cfg.base_price * food_cfg.price_ceiling

    for tick in range(1, 4):
        world.tick = tick
        faction.check_trigger(world)

    # Must be active on day 3
    assert faction.active
    assert faction.active_since_tick == 3
    assert "Price ceiling" in faction.trigger_reason

    # Seed outside stock and mock unmet demand on world.stats
    world.ledger.produce(OUTSIDE, Asset.FOOD, 100, tick=3, reason="restock")
    stat = world.stats[-1] if world.stats else None
    if not stat:
        sim.step(1)
        stat = world.stats[-1]
    stat.unmet[Asset.FOOD] = 10

    initial_outside_food = world.ledger.balance(OUTSIDE, Asset.FOOD)
    initial_total_coin = world.ledger.total("coin")

    trade_result = faction.run_contraband_trade(world)

    # Some contraband traded or confiscated
    total_handled = trade_result["smuggled"] + trade_result["confiscated"]
    assert total_handled > 0
    assert world.ledger.balance(OUTSIDE, Asset.FOOD) == initial_outside_food - total_handled

    # Invariants: total coin strictly conserved across all trades
    assert world.ledger.total("coin") == initial_total_coin
    world.ledger.check_conservation()
