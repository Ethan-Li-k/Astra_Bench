# Snapshot exclusions

Credentials and account/session directories are excluded before content reads. Raw model logs, JSONL, recordings/frames, weights/assets, installed environments, caches, nested Git metadata and all symlinks remain local. Protected account directories are not enumerated: recursive counts and bytes are unknown.

The companion `excluded-final.json` contains per-path category/size metadata from the original full inventory plus the bounded final source increment; it is not a continuously refreshed media inventory. No source data was deleted. The damaged historical ground STATUS.md remains excluded.

These eight peripheral sources retain the prior withholding decision and were not reread:

- `GPT-as-Policy/hybrid_rollout/robodojo/test_auth_profiles.py`
- `GPT-as-Policy/hybrid_rollout/robodojo/test_proxy_config.py`
- `GPT-as-Policy/hybrid_rollout/robodojo/test_quota_guard.py`
- `artifacts/architecture-review-20260916/six-task-focus/pause_ikea.py`
- `human-feedback/dashboard-upgrade/explicit-blockers/test_explicit_blockers.py`
- `ikea/budget-coordination/tests/test_parallel.py`
- `ref/RoboRSI/tests/test_litellm_kwargs.py`
- `ref/RoboRSI/tests/test_web_search_tool.py`
