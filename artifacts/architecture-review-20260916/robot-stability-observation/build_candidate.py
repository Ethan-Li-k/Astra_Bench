from pathlib import Path
root=Path(__file__).resolve().parent
src=(root/'snapshots/rsi/live.py').read_text()
method='''    def _robot_root_observation(self):
        # Named BODY frame, not subtree COM / inertial frame / first freejoint.
        # Tilt uses exactly the xmat element and formula used by tick's gate.
        try:
            body_id = self.model.body('pelvis').id
            if (body_id != self.adapter.body_ids[0]
                    or self.model.body_parentid[body_id] != 0):
                return None
            height = float(self.data.xpos[body_id, 2])
            quaternion = np.asarray(self.data.xquat[body_id], dtype=float)
            rotation = np.asarray(self.data.xmat[body_id], dtype=float).reshape(3, 3)
            if (not np.isfinite(height) or quaternion.shape != (4,)
                    or not np.isfinite(quaternion).all()
                    or not np.isclose(np.linalg.norm(quaternion), 1., atol=1e-6)
                    or not np.isfinite(rotation).all()):
                return None
            tilt = float(np.rad2deg(np.arccos(np.clip(rotation[2, 2], -1, 1))))
            return {'body_name': 'pelvis', 'frame': 'world',
                    'height_world_m': height, 'quaternion_wxyz': quaternion.tolist(),
                    'tilt_deg': tilt}
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            return None  # Missing/nonfinite feedback is not a zero measurement.

'''
assert src.count('    def observe(self):')==1
src=src.replace('    def observe(self):',method+'    def observe(self):')
src=src.replace("'localization_source': 'sim_robot_state_diagnostic',", "'localization_source': 'sim_robot_state_diagnostic',\n                  'robot_root': self._robot_root_observation(),")
(root/'candidate/rsi/live.py').write_text(src)
src=(root/'snapshots/rsi/policy_harness.py').read_text()
helpers='''def _public_robot_root(packet):
    """Copy only finite, named robot BODY feedback; never merge backend extras."""
    value = packet.get('robot_root')
    if (not isinstance(value, dict) or value.get('body_name') != 'pelvis'
            or value.get('frame') != 'world'):
        return None
    height, tilt = value.get('height_world_m'), value.get('tilt_deg')
    quat = value.get('quaternion_wxyz')
    numeric = lambda x: type(x) in (int, float) and np.isfinite(x)
    if (not numeric(height) or not numeric(tilt) or not 0 <= tilt <= 180
            or not isinstance(quat, list) or len(quat) != 4
            or not all(numeric(x) for x in quat)
            or not np.isclose(np.linalg.norm(quat), 1., atol=1e-6)):
        return None
    return {'body_name': 'pelvis', 'frame': 'world', 'height_world_m': float(height),
            'quaternion_wxyz': list(quat), 'tilt_deg': float(tilt)}


def _robot_root_summary(samples):
    # Local to this executed chunk. Never cache a previous episode/sample.
    unavailable = {'status': 'unavailable'}
    if not samples:
        return unavailable
    roots = [_public_robot_root(row) for row in samples]
    times = [row.get('sim_s') for row in samples]
    episode = samples[0].get('episode_id')
    if (not isinstance(episode, str) or not episode or any(r is None for r in roots)
            or any(type(t) not in (int, float) or not np.isfinite(t) for t in times)
            or any(row.get('episode_id') != episode
                   or not isinstance(row.get('observation_id'), str)
                   or not row['observation_id'] for row in samples)
            or any(b <= a for a, b in zip(times, times[1:]))):
        return unavailable
    if len(samples) < 2:
        return {'status': 'insufficient_samples'}
    return {'status': 'sampled', 'episode_id': episode, 'samples': len(samples),
            'start_sim_s': times[0], 'end_sim_s': times[-1],
            'height_change_m': roots[-1]['height_world_m'] - roots[0]['height_world_m'],
            'tilt_change_deg': roots[-1]['tilt_deg'] - roots[0]['tilt_deg'],
            'min_height_world_m': min(r['height_world_m'] for r in roots),
            'max_tilt_deg': max(r['tilt_deg'] for r in roots),
            'limitation': 'Measured samples only; extrema between samples are unknown.'}


'''
assert src.count('class LocalFourPointHarness:')==1
src=src.replace('class LocalFourPointHarness:', helpers+'class LocalFourPointHarness:')
src=src.replace("        observation = self.backend.observe()\n        directory =", "        observation = self.backend.observe()\n        if 'robot_root' in observation:\n            observation['robot_root'] = _public_robot_root(observation)\n            observation['episode_id'] = str(self.output_dir.resolve())\n        directory =",1)
old="""                    'commanded_joint_target_rad':packet.get('commanded_joint_target_rad',[])})
                return packet"""
new="""                    'commanded_joint_target_rad':packet.get('commanded_joint_target_rad',[])})
                if 'robot_root' in packet:
                    motion_samples[-1].update(
                        observation_id=packet.get('observation_id'),
                        episode_id=str(self.output_dir.resolve()),
                        robot_root=_public_robot_root(packet))
                return packet"""
assert old in src;src=src.replace(old,new)
old="""                    'samples':len(motion_samples),'trace_path':str(path.resolve()),"""
assert old in src;src=src.replace(old,old+"\n                    'robot_root_summary':_robot_root_summary(motion_samples),")
(root/'candidate/rsi/policy_harness.py').write_text(src)
