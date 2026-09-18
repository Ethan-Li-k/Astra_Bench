"""Native-MP measured interpolation and coordinated command-rate helpers.

Preserve the existing 0.02 rad/20ms per-joint target-change bound, but
scale the IK displacement from measured joints as one vector. This avoids
independent clipping of a coordinated arm solution. Native IK gates unchanged.
"""
import numpy as np

def measured_ray_step(measured, previous_command, ik_target, max_delta=.02):
    measured,previous,target=[np.asarray(x,dtype=float) for x in (measured,previous_command,ik_target)]
    if measured.shape!=previous.shape or measured.shape!=target.shape or measured.ndim!=1 or not np.isfinite(np.r_[measured,previous,target,max_delta]).all() or max_delta<=0:
        raise ValueError('Finite, equal-width named joint vectors required')
    delta=target-measured;amin,amax=0.,1.
    for q,old,dq in zip(measured,previous,delta):
        if abs(dq)<1e-14:
            if abs(q-old)>max_delta+1e-12:return None
            continue
        low,high=sorted(((old-max_delta-q)/dq,(old+max_delta-q)/dq))
        amin=max(amin,low);amax=min(amax,high)
    if amin>amax or amax<0:return None
    result=measured+amax*delta
    if np.max(abs(result-previous))>max_delta+1e-10:raise AssertionError('Rate contract violation')
    return result

def reanchor_active_components(start_pose, measured_pose, position_indices, orientation_indices):
    """Only for a new idle native-MP command after validation; no in-flight changes.
    Call on backend._start_pose after existing move_four_points validation.
    Inactive components and goal stay untouched. Continuous already uses measured.
    """
    result=start_pose.copy()
    result.positions[position_indices]=measured_pose.positions[position_indices]
    result.quaternions[orientation_indices]=measured_pose.quaternions[orientation_indices]
    return result
