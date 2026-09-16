#!/bin/bash
set -euo pipefail
cd /home/galbot/lizekai/RSI
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/human-feedback/tools:$PWD/human-feedback/dashboard-upgrade/six-task-page:$PWD/human-feedback/dashboard-upgrade/six-task-focus:$PWD/human-feedback/dashboard-upgrade/stability-publication:$PWD/human-feedback/dashboard-upgrade/root-review"
python3 -m unittest -v test_six_page test_six_task_focus test_stability_publication test_root_review.RootReviewTests.test_ground_stale_wait_keeps_last_stage_but_liveness_unknown test_root_review.RootReviewTests.test_framework_newer_result_and_progress_replace_old_status test_dashboard.BoardTests.test_immutable_idempotent_correction_and_binding test_dashboard.BoardTests.test_queue_failure_saved_and_exact_bound_message_no_user_execution test_dashboard.HTTPTests.test_csrf_origin_paths_and_no_get_delivery 2>&1 | tee human-feedback/dashboard-upgrade/six-task-page/affected-tests.log
