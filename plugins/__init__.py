from pathlib import Path

PLUGINS_DIR = Path(__file__).parent
SPEEDTEST_PLUGIN = PLUGINS_DIR / "speedtest"

__all__ = ["PLUGINS_DIR", "SPEEDTEST_PLUGIN"]
