"""Tests for M24 Gymnasium AI Agent Environment."""

from questless.gym.env import QuestlessEnv


def test_questless_env_step_lifecycle():
    env = QuestlessEnv("scenarios/baseline.toml", max_days=10)
    obs, info = env.reset(seed=42)

    assert "coin" in obs
    assert "holdings" in obs
    assert "prices" in obs
    assert "contracts" in obs
    assert info["tick"] == 0

    # Step through 5 days with various actions
    for day in range(1, 6):
        # Action: [verb=0 (noop), target=0, good=0, qty=0]
        obs, reward, term, trunc, info = env.step([0, 0, 0, 0])
        assert info["tick"] == day
        assert isinstance(reward, float)
        assert term is False

    # Take a buy action
    obs, reward, term, trunc, info = env.step([3, 0, 0, 0])
    assert info["tick"] == 6


def test_text_rendering_mode():
    env = QuestlessEnv("scenarios/baseline.toml", max_days=5, render_mode="text")
    env.reset(seed=123)
    text = env.render()
    assert text is not None
    assert "Day 0" in text
    assert "Player Coin" in text
