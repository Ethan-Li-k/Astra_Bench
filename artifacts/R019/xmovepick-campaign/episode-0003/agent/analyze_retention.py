"""Public RGB/proprio analysis only; no simulator or task state access."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.spatial.transform import Rotation

ROOT = Path('/home/galbot/lizekai/RSI/artifacts/R019/xmovepick-campaign/episode-0003/rollout/episode/observations')
records = []
# Manually selected visible apple patches; these include shape/indentation.
# Surface estimates are not object centres or privileged object poses.
for i, u, v in [(26,377,295),(27,373,281),(28,374,285),(29,381,329),(30,387,337),(31,387,316)]:
    p = ROOT / f'{i:04d}'
    o = json.loads((p/'observation.json').read_text())
    left = np.asarray(Image.open(p/'head_stereo_left.png').convert('L'), float)
    right = np.asarray(Image.open(p/'head_stereo_right.png').convert('L'), float)
    yy, xx = np.mgrid[v-10:v+10, u-10:u+7]
    errors = []
    for d in np.arange(17, 26, .025):
        patch = map_coordinates(right, [yy.ravel(), (xx-d).ravel()], order=1).reshape(yy.shape)
        errors.append((float(np.mean((left[yy,xx]-patch)**2)), float(d)))
    error, disparity = min(errors)
    a, b = [im['calibration'] for im in o['images']]
    cam_rot = np.array(a['rotation_camera_to_world_row_major']).reshape(3,3)
    baseline_camera = cam_rot.T @ (np.array(b['position_world_m'])-a['position_world_m'])
    k = a['render_intrinsics']
    depth = k['fx']*baseline_camera[0]/disparity
    surface = np.array(a['position_world_m']) + cam_rot @ np.array([
        (u+.5-k['cx'])*depth/k['fx'], -(v+.5-k['cy'])*depth/k['fy'], -depth])
    w = o['four_point_world']['right_wrist_yaw_link']
    rot = Rotation.from_quat(np.roll(w['quaternion_wxyz'], -1))
    records.append(dict(action=i, observation=str(p/'observation.json'), pixel=[u,v],
        disparity_px=disparity, patch_mse=error, patch_variance=float(np.var(left[yy,xx])),
        baseline_camera_m=baseline_camera.tolist(), visible_surface_world_m=surface.tolist(),
        visible_surface_wrist_m=rot.inv().apply(surface-w['position_world_m']).tolist(),
        wrist_world_m=w['position_world_m'], robot_root=o['robot_root']))
result = dict(method='Manual visible apple patch, rectified stereo photometric correspondence, calibrated pixel centres.',
    limitation='Occlusion, surface normal, changing attitude and contour correspondence cause centimetre uncertainty. This estimates visible surface, not object centre/contact. Native outcome and independent audit are separate.',
    records=records)
Path('retention_analysis.json').write_text(json.dumps(result, indent=2)+'\n')
for r in records:
    print(r['action'], 'surface', np.round(r['visible_surface_world_m'],4),
          'local', np.round(r['visible_surface_wrist_m'],4),
          'disparity',round(r['disparity_px'],3),'variance',round(r['patch_variance'],1))
