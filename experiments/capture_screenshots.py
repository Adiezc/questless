# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Capture README screenshots of the running dashboard with headless Chrome (DevTools protocol).

    uv run questless demo &                                  # dashboard on :8501
    uv run --extra demo python experiments/capture_screenshots.py

Writes docs/images/dashboard.png (top of the page) and docs/images/economy.png (the economy tab
area). Needs Google Chrome; uses the ``websockets`` package that Streamlit already depends on.
"""

from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
URL = "http://localhost:8501/"
OUT = Path(__file__).resolve().parents[1] / "docs" / "images"
PORT = 9333


async def _capture() -> None:
    targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
    page = next(t for t in targets if t["type"] == "page")
    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=2**26) as ws:
        msg_id = 0

        async def call(method: str, **params) -> dict:
            nonlocal msg_id
            msg_id += 1
            await ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
            while True:
                reply = json.loads(await ws.recv())
                if reply.get("id") == msg_id:
                    return reply.get("result", {})

        await call(
            "Emulation.setDeviceMetricsOverride",
            width=1440,
            height=1000,
            deviceScaleFactor=2,
            mobile=False,
        )
        await call("Page.navigate", url=URL)
        await asyncio.sleep(12)  # Streamlit connects over a websocket, then renders
        shot = await call("Page.captureScreenshot", format="png")
        (OUT / "dashboard.png").write_bytes(base64.b64decode(shot["data"]))
        await call(
            "Runtime.evaluate",
            expression=(
                "document.querySelector('[data-testid=\"stMain\"]').scrollTo(0, 1250);"
                "window.scrollTo(0, 1250);"
            ),
        )
        await asyncio.sleep(2)
        shot = await call("Page.captureScreenshot", format="png")
        (OUT / "economy.png").write_bytes(base64.b64decode(shot["data"]))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        chrome = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--remote-debugging-port={PORT}",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")
                    break
                except OSError:
                    time.sleep(0.2)
            asyncio.run(_capture())
        finally:
            chrome.terminate()
            chrome.wait(timeout=10)
    print(f"wrote {OUT / 'dashboard.png'} and {OUT / 'economy.png'}")


if __name__ == "__main__":
    main()
