#!/usr/bin/env python3
"""Read only new PUBLIC supervisor output; queue acceptance is not an ACK."""
import hashlib
import json
import re
from pathlib import Path

from ikea_gate import OUT, atomic_json, locked, read, utc


def refresh():
    with locked(OUT/"delivery.lock"):
        path = OUT/"delivery-state.json"
        state = read(path)
        if state.get("acknowledged"):
            return state
        log = Path(state["log"])
        cursor = state.get("scan_offset", state["log_offset_before_queue"])
        state["last_checked_at"] = utc()
        if log.stat().st_size < cursor:
            state["scan_error"] = "public log truncated; no ACK inferred"
        else:
            with log.open("rb") as f:
                f.seek(cursor)
                # Bounded incremental scan, not session database/trace access.
                consumed = 0
                while consumed < 2_000_000:
                    start = f.tell()
                    line = f.readline()
                    if not line or not line.endswith(b"\n"):
                        break
                    consumed += len(line)
                    state["scan_offset"] = f.tell()
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    item = event.get("item", {})
                    if event.get("type") != "item.completed" or item.get("type") != "agent_message":
                        continue
                    text = item.get("text", "")
                    pattern = r"(?m)^" + re.escape(state["message_id"]) + r" ACK[^\n]*已读[^\n]*$"
                    match = re.search(pattern, text)
                    if match:
                        state.update(acknowledged=True, acknowledged_at=utc(),
                                     ack_text=match.group(0), ack_log_offset=start,
                                     ack_event_sha256=hashlib.sha256(line).hexdigest())
                        break
        atomic_json(path, state)
    with locked(OUT/"status.lock"):
        status_path = OUT/"coordination-status.json"
        status = read(status_path) if status_path.exists() else {"schema": 1}
        status["supervisor_delivery"] = state
        atomic_json(status_path, status)
    return state


if __name__ == "__main__":
    print(json.dumps(refresh(), ensure_ascii=False, indent=2))
