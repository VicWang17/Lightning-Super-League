#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("PYTHONPATH", ".")
os.environ.setdefault("MATCH_ENGINE_TRANSPORT", "process")
os.environ.setdefault("MATCH_ENGINE_MODE", "instant")
os.environ.setdefault("MATCH_ENGINE_FALLBACK_RANDOM", "false")
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1,::1")
sys.path.insert(0, str(BACKEND_DIR))

from app.console.main import main


if __name__ == "__main__":
    asyncio.run(main())
