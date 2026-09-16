# grasp_red_cube task adapter

Status: `DRAFT`.

Actor input is RGB plus named robot state. The task phases are visually locate,
pregrasp, bounded approach, close, lift, and visual/native verification. This
adapter contains no cube coordinates, contact truth, reward, evaluator
thresholds, or privileged waypoints.

The shared action is UMI-4 SE(3) plus two DEX3 closure fractions. Translation
uses an active position mask. Rotation about a fixed point activates both the
selected wrist position and orientation. Every chunk uses a fresh observation
and the common ScaleBFM execution receipt.

This DRAFT is authorized for zero-demonstration Direct evaluation. Start from
fresh RGB and act; no successful demonstration is required. Use observed
tracking receipts to revise a failed approach instead of assuming a geometric
goal was reached. The grasp point/opening is not calibrated; wrist link and
grasp TCP are different. `pi05` and `SIMPLE` are optional unconnected providers.
Do not read developer diagnostics or other episodes. The calibrated horizontal
workspace support plane is world z=0.630 m; this is not an object pose or size.
