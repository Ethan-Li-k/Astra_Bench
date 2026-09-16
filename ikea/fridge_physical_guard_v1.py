"""Frozen copy of verified50Hz/250Hz physical action budget guard."""
import math

def physical_preflight(host, response):
    """Match frozen harness execute() loop ceiling, including final arrival wait.

    Each tick has five 4ms substeps. Use the loop ceiling (duration+2.1s),
    not the earlier controller timeout (elapsed > duration+2s).
    """
    if host.finished or host.backend.active:
        raise ValueError('Physical action unavailable')
    trajectory = response.get('trajectory')
    if not isinstance(trajectory, list) or not 1 <= len(trajectory) <= 5:
        raise ValueError('Invalid physical trajectory')
    durations = [float(row['duration_s']) for row in trajectory]
    if any(not math.isfinite(d) or not .5 <= d <= 3 for d in durations):
        raise ValueError('Invalid physical duration')
    continuous = host.backend.continuous_chunks_enabled and len(durations) > 1
    if continuous:
        duration = math.fsum(durations)
        if duration > 3+1e-9:
            raise ValueError('Continuous duration exceeds contract')
        durations = [min(3., duration)]
    maximum_ticks = sum(int((duration+2.1)/.02) for duration in durations)
    elapsed = (float(host.backend.data.time)-host.episode_start_sim_s)/.02
    used = round(elapsed)
    if used < 0 or abs(elapsed-used) > 1e-4:
        raise ValueError('Physics elapsed time no longer matches 20ms tick contract')
    if (host.max_episode_steps != 12000 or host.backend.physics_substeps != 5
            or not math.isclose(float(host.backend.model.opt.timestep), .004, abs_tol=1e-12)):
        raise ValueError('Frozen physical timing contract mismatch')
    remaining = max(0, host.max_episode_steps-used)
    return dict(accepted=maximum_ticks <= remaining, step_id=used, remaining_steps=remaining,
        maximum_action_steps=maximum_ticks, maximum_action_s=maximum_ticks*.02,
        max_episode_steps=12000, arrival_wait_included=True,
        bound_basis='Frozen execute loop int((duration+2.1)/.02); 5x.004s per tick')
