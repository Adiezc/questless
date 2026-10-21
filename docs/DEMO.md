# Demo guide

```bash
uv sync --extra demo
uv run questless demo          # http://localhost:8501
```

Engine changes need a restart of the demo (Streamlit reloads the app files, not the installed
package).

## The 2-minute script

1. **It opens on Iron Shortage, day 30**, with the Blacksmiths Guild's contract selected. Read the
   chain on the right, root cause first:
   - the mine collapsed on day 15;
   - ore output fell to 5/day;
   - buyers who could pay went unserved;
   - 88% of smiths are short;
   - the guild escrowed 363 coin.

   The green **Verified** line means every measured number was re-checked.
2. **Accept** the contract. Choose **Caravan 31** (310 coin, 3 days). Press **+1 day** three
   times, then **Deliver**. Your coin goes 600 → 290 → 653.
3. Press **+7 days**. The fulfilled contract (Quest board, *History*) shows what changed for the
   smiths you supplied.
4. Switch the scenario to **Mine Disaster**, **Load**, then **+30 days**. Open a farmer's
   *Tools* contract. Its chain runs:

   **mine disaster → miners without tools → ore down → smiths idle → tools down → this farmer.**

   Use the lineage buttons to walk to the contracts it follows.
5. Open **Shock the economy** and fire **Drought**, then **+7 days**. Watch the Town Watch post
   food contracts for its guards.

## Screens

- **Living world:** every NPC as a dot by state (working, idle for inputs, paused with unsold
  stock, hungry ✕), plus the stockpiles waiting at the mine and farms.
- **Quest board:** open, yours and history. Each card shows the reward, the quantity and the
  days left. The caption counts needs that were *not* turned into contracts, and why.
- **Why does this quest exist?:** the causal chain, a verification line, an evidence chart (the
  good's output against its pre-shock normal), lineage, and your actions.
- **Tabs:** economy charts with shock windows shaded, the NPC table, guild treasuries and your
  reputation, the event log, and how it works.

## Recording media

- **Screenshots:** with the demo running, `uv run --extra demo python experiments/capture_screenshots.py`
  (headless Chrome) rewrites `docs/images/dashboard.png` and `docs/images/economy.png`.
- **GIF or video:** record the 2-minute script with macOS **⌘⇧5**, then convert:
  `ffmpeg -i demo.mov -vf "fps=12,scale=1280:-1" docs/images/demo.gif`.
  Suggested 60-90 s cut: shock (10 s), the chain (25 s), fulfil and recovery (25 s), the
  results chart and contact (15 s).
