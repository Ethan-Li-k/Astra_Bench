"""Only render archived physics; never start a model or new physics attempt."""
import subprocess
import sys
from pathlib import Path
from ground_task import ROOT

for result in sorted((ROOT/'campaign').glob('episode-*/result.json')):
    Path('/home/galbot/lizekai/RSI/ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md').read_text()
    episode=result.parent.name
    if (ROOT/'artifacts'/(episode+'-feet-render')).exists():continue
    subprocess.run([sys.executable,'-u','-m','tools.render_ground_feet','--episode',episode],check=True)
