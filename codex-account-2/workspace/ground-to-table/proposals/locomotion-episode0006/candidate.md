Own-experience locomotion candidate, awaiting shared review.

Original G1/dual DEX3, original model_38000 UMI-4, fixed WristPI,50Hz tracker/250Hz PD, MuJoCo. Actor episode0006 independently generated counter-swing arms and explicit lift/elevated advance/landing phases. Both feet subsequently passed flight/relocation/landing checks; pelvis exceeded20cm and support center12cm. Episodes0006,0007 and0008 now provide three completed independent locomotion phase achievements in this setting. These are not full task successes or a generally validated gait.

The key comparison is public action1 (small bilateral arcs, no flight) versus action2 (different arm pattern and larger arcs, right flight), then action3 (left elevated forward phase before landing) and action4 (another right step). Initial poses and several components differ; do not attribute success to one factor. Use measured anchors, inspect complete public50Hz trajectories and recalibrate each new setting. Final target timeout did not exclude a real step.

A subsequent180mm bilateral wrist descent caused25.052degree tilt stop before object contact. Walking-to-ground-reaching transition remains unresolved. No shared core file was modified; candidate is scoped to this original setting until reviewed and independently reproduced.

Actor-eligible evidence is only campaign/episode-0006/rollout (calibrated RGB, robot state and own references). Host audit/failure_review are supervisor-only and must not be forwarded as hidden feedback to an actor.
