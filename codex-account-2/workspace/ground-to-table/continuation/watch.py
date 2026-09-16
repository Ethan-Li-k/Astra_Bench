#!/usr/bin/env python3
"""Reuse the peer's tested natural-exit continuation policy for this task."""
import importlib.util
from pathlib import Path

TASK = Path('/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table')
source = TASK.parents[1] / 'continuation/watch.py'
spec = importlib.util.spec_from_file_location('peer_continuation', source)
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)
watch.OUT = TASK / 'continuation'
watch.THREAD = '01a0a888-a98e-70d0-bd7a-0e268a6668ed'
watch.SESSION = 'rsi-ground-table-0916'
watch.FIRST_LOG = TASK / 'logs/supervisor.jsonl'

if __name__ == '__main__':
    watch.main()
