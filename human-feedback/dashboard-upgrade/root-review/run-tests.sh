#!/usr/bin/env bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/galbot/lizekai/RSI/human-feedback/tools:/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade/root-review
python3 -m unittest -v test_root_review test_ikea_video_labels test_dashboard.BoardTests.test_unknown_not_zero_and_no_model_on_reads test_dashboard.BoardTests.test_queue_failure_saved_and_exact_bound_message_no_user_execution test_dashboard.BoardTests.test_immutable_idempotent_correction_and_binding test_dashboard.BoardTests.test_physical_eligibility_excludes_budget_and_same_reset test_dashboard.HTTPTests 2>&1 | tee human-feedback/dashboard-upgrade/root-review/tests.log
node --check human-feedback/ui/app.js 2>&1 | tee human-feedback/dashboard-upgrade/root-review/javascript-check.log
