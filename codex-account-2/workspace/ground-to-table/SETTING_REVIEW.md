# Setting correction for formal task

Parent review of setting_manifest.json found table_and_four_legs_translation_m=[0.55,0,0]. User asked same setting as source thread. Keep this preflight-01 as explicitly shifted-layout diagnostic, but restore the original table position (table_only_offset_x=0) before claiming matched-setting formal trials. Preserve robot reset/dynamics/asset/model/controller; ground cube initial position may be chosen outside the table footprint to make the newly requested ground task physically observable, and must be recorded. Do not count table relocation as the robot's transportation or reduce locomotion requirement.

Do not edit an active physics episode. At next episode boundary, change the isolated scene adapter, save a new manifest/version and repeat initial visibility/contact/standing checks. Retain current manifest and video. Report any remaining task-contract changes clearly. Current preflight is not a successful task or frozen matched-setting result.

Independent reviewer is running under second account in reviewer/, tmux rsi-ground-review-0916; it only writes reviewer/REVIEW.md and review.json. Consume its findings at a safe boundary; no competing code writer.
