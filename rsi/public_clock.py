"""Public execution counters, with native and adapter clocks kept distinct."""
import math


def public_clock(backend, start_sim_s, tracker_ticks, harness_limit, *,
                 native_start=None, declared_native_max=None):
    sim = float(backend.data.time)
    if not math.isfinite(sim) or sim < start_sim_s:
        raise ValueError('Invalid same-episode simulation clock')
    env = getattr(backend, 'env', None)
    observed = getattr(env, 'step_count', None)
    control = getattr(backend, 'control_configuration', {})
    mp = (control.get('adapter') == 'native-mp-checkpoint-force-v1'
          or control.get('controller') == 'native-mp-amo15-arm-ik-stationary-v1')
    sonic = getattr(backend, 'bridge', None) is not None
    # MP calls native task checks, but bypasses native env.step(). Its synthetic
    # step_count is not a count of the original MP control/time-limit unit.
    native = observed if sonic and type(observed) is int else None
    native_used = native-native_start if native is not None and type(native_start) is int and native>=native_start else None
    dt = getattr(getattr(backend, 'model', None), 'opt', None)
    dt = getattr(dt, 'timestep', None)
    return {'physics_clock': 'paused_during_inference', 'rtc': False,
            'sim_s': sim, 'episode_elapsed_sim_s': sim-start_sim_s,
            'physics_dt_s': float(dt) if dt is not None else None,
            'tracker_ticks': tracker_ticks, 'tracker_dt_s': .02,
            'harness_budget_s': None if harness_limit is None else harness_limit*.02,
            'harness_budget_unit': '20ms_tracker_tick',
            'native_max_steps': declared_native_max,
            'native_steps_since_reset': native,
            'native_steps_used': native_used,
            'native_step_unit': 'Sonic env.step call' if sonic else 'unverified MP native env.step unit' if mp else 'not_a_native_SIMPLE_backend',
            'adapter_env_counter': observed if type(observed) is int else None,
            'native_time_limit_enforced': False,
            'native_time_limit_note': 'Learning adapter bypasses gym TimeLimit; formal admission needs original wrapper/unit.'}


def capture_binding(images, *, episode_id, reset_id, observation_id, sim_s):
    """Bind capture requests; only a renderer's matching attestation proves delivery."""
    result=[]
    for image in images:
        expected=dict(episode_id=episode_id,reset_id=reset_id,state_id=observation_id,
                      sim_s=sim_s,camera=image.get('camera'))
        actual=image.get('capture_binding')
        if actual is not None and actual != expected:
            raise ValueError('Renderer capture identity differs from requested state')
        result.append(dict(image,capture_request_binding=expected,
            capture_binding_status='matched_renderer_attestation' if actual is not None else 'source_state_attestation_pending'))
    return result
