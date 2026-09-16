# Local web reports

The original full-project page is `http://127.0.0.1:8765/` (including `#ikea` and `#ground`). The separate six-task page is **`http://127.0.0.1:8765/simple-six`**; `/simple-six/` is also supported. Both use the existing Python server, `/api/dashboard`, feedback storage and owner routing. The original browser tab and a separate new tab were preserved by the root's recorded review.

From an RSI data root with the required existing evidence available, the common startup is:

```bash
bash human-feedback/tools/run_server.sh
```

The wrapper invokes `python3 human-feedback/tools/server.py --port 8765` and retains its tee log. The owner runs it in the existing `rsi-human-feedback-h001` tmux session. It binds to loopback `127.0.0.1`; there is no second server for the six-task page. Do not start a duplicate instance when that service is already running.

The source group includes `simple_six.py`, `dashboard.py`, `server.py`, `feedback_board.py`, the UI static sources including `simple-six.html/.css/.js`, and the new-page regression test. Its eight modified implementation files match `human-feedback/dashboard-upgrade/six-task-page/result.json` exactly. That ready result follows a completed engineering turn; `ROOT_UI_REVIEW.json` records the actual-browser resolution of the old-success/current-unfinished label conflict. Nine UI files come from the subsequent `benchmark-alignment/backup` tree, which preserves this verified version. Later alignment edits to the live source are excluded from this fixed version; the snapshot does not imply that a continuously changing server still serves these exact bytes.

Recorded UI validation includes 29 affected regressions, 12 final targeted regressions, 13 initial plus 3 final browser checks, and real video playback/seek with HTTP206 and refresh position preservation. These are the UI owner's recorded checks. The publication increment validates file hashes and source structure without contacting localhost, starting a browser/server or submitting feedback.

The page separates learning/history, autonomous/assisted, initialization/control contract and native/complete audit. Every rate exposes its numerator and denominator; no completed sample means not evaluated. Properly sealed/audited physical-budget exhaustion and safety stops remain valid unsuccessful attempts. Unknown/in-flight/system/pause/replay records are separately visible. Five-stable and preregistered ten-frozen stages are not filled from historical success. Required questions need actual eligibility evidence; unsolicited suggestions remain available through the existing append-only context-bound path.

Service startup verifies retained H001 source/lock records, the legacy video index and media hashes. Those raw frames, observations, recordings and account/session data are deliberately absent from the source snapshot. A clone without the local evidence does not reproduce the complete live service; do not remove checks or fabricate episodes to make it start. The static audit summary is `docs/public-results-index.json`.

Localhost belongs to the machine running the service. A GitHub source commit does not deploy this dynamic site, its feedback API or its auxiliary-account queue. The capture did not change the existing service or user tabs.
