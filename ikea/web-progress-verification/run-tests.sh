#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
{
  python3 ikea/web-progress-verification/test_ikea_progress.py
  python3 -m unittest discover -s human-feedback/tools -p test_video_home.py -v
  python3 - <<'PY'
import sys,unittest
from pathlib import Path
sys.path.insert(0,'human-feedback/tools')
import test_api_progress
test_api_progress.EVIDENCE=Path('ikea/web-progress-verification').resolve()
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_api_progress))
raise SystemExit(not result.wasSuccessful())
PY
} 2>&1 | tee -a ikea/web-progress-verification/tests.log
