"""Minimal headless Isaac Sim runtime check for the psi_being SIMPLE environment."""

import os

assert os.environ.get("OMNI_KIT_ACCEPT_EULA") == "Y"

from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})
try:
    print("ISAAC_SIMULATION_APP=STARTED", flush=True)
    simulation_app.update()
    print("ISAAC_UPDATE=OK", flush=True)
finally:
    simulation_app.close()
    print("ISAAC_SIMULATION_APP=CLOSED", flush=True)
