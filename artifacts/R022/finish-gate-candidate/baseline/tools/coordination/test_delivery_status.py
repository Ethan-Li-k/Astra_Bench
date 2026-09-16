"""ACK parsing tests on synthetic public logs, without any session access."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import delivery_status as d
import ikea_gate as g


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="synthetic-ack-", dir=g.OUT/"synthetic-tests"))
        self.log = self.root/"public.jsonl"
        self.log.write_text("")
        self.marker = "SYNTHETIC-ACK-TEST"
        self.event = {"type": "item.completed", "item": {
            "type": "agent_message", "text": self.marker+" ACK — 已读新增要求；合成测试。"}}
        g.atomic_json(self.root/"delivery-state.json", {"message_id": self.marker,
            "log": str(self.log), "log_offset_before_queue": 0,
            "queue_exit_code": 0, "acknowledged": False})

    def refresh(self):
        with patch.object(d, "OUT", self.root):
            return d.refresh()

    def test_queue_receipt_is_not_ack(self):
        self.assertFalse(self.refresh()["acknowledged"])

    def test_tool_echo_is_not_ack(self):
        self.event["item"]["type"] = "command_execution"
        self.log.write_text(json.dumps(self.event)+"\n")
        self.assertFalse(self.refresh()["acknowledged"])

    def test_partial_line_waits_then_ack_persists(self):
        self.log.write_text(json.dumps(self.event))
        self.assertFalse(self.refresh()["acknowledged"])
        with self.log.open("a") as f:
            f.write("\n")
        state = self.refresh()
        self.assertTrue(state["acknowledged"])
        self.assertEqual(state["ack_event_sha256"], g.digest(self.log))
        self.assertTrue(self.refresh()["acknowledged"])

    def test_old_ack_does_not_count(self):
        self.log.write_text(json.dumps(self.event)+"\n")
        state = g.read(self.root/"delivery-state.json")
        state["log_offset_before_queue"] = self.log.stat().st_size
        g.atomic_json(self.root/"delivery-state.json", state)
        self.assertFalse(self.refresh()["acknowledged"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
