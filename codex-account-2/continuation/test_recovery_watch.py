import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('watch', Path(__file__).with_name('watch.py'))
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class WaitObserved(Exception):
    pass


class RecoveryWatchTests(unittest.TestCase):
    def test_live_recovery_session_prevents_any_resume(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory); log = root/'current.jsonl'
            log.write_text('{"type":"turn.started"}\n')
            (root/'supervisor-state.json').write_text('{"status":"continue"}')
            (root/'PROMPT.md').write_text('continue')
            (root/'active-supervisor.json').write_text(json.dumps({
                'thread': watch.THREAD, 'session':'rsi-simple-recovery-test',
                'previous_log':str(log),
                'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'pid':0, 'start_ticks':0, 'started_ns':0}))
            commands = []
            def tmux(cmd, **kwargs):
                commands.append(cmd)
                return SimpleNamespace(returncode=0 if cmd[-1]=='rsi-simple-recovery-test' else 1, stderr='')
            with patch.object(watch, 'OUT', root), patch.object(watch, 'record'), \
                 patch.object(watch.subprocess, 'run', side_effect=tmux), \
                 patch.object(watch, 'event_status', return_value=(True, None)), \
                 patch.object(watch.time, 'sleep', side_effect=WaitObserved), \
                 patch.object(watch.subprocess, 'Popen', side_effect=AssertionError('duplicate resume')):
                with self.assertRaises(WaitObserved):
                    watch.main()
            self.assertEqual(commands[0][-1], 'rsi-simple-recovery-test')

    def test_stale_boot_origin_cannot_resume(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            (root/'active-supervisor.json').write_text(json.dumps({
                'thread':watch.THREAD,'boot_id':'previous-boot','session':'old',
                'previous_log':str(root/'old.jsonl')}))
            with patch.object(watch, 'OUT', root):
                with self.assertRaisesRegex(ValueError, 'boot'):
                    watch.supervisor_origin()

    def test_pid_reuse_does_not_match_origin(self):
        pid=os.getpid()
        ticks=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
        self.assertTrue(watch.origin_process_alive({'pid':pid,'start_ticks':ticks}))
        self.assertFalse(watch.origin_process_alive({'pid':pid,'start_ticks':ticks+1}))

    def test_missing_tmux_still_waits_for_same_live_process(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            origin={'session':'gone','previous_log':str(Path(directory)/'log'),'started_ns':0}
            with patch.object(watch,'OUT',Path(directory)), patch.object(watch,'record'), \
                 patch.object(watch,'supervisor_origin',return_value=origin), \
                 patch.object(watch,'origin_process_alive',return_value=True), \
                 patch.object(watch.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='')), \
                 patch.object(watch.time,'sleep',side_effect=WaitObserved), \
                 patch.object(watch.subprocess,'Popen',side_effect=AssertionError('duplicate resume')):
                with self.assertRaises(WaitObserved):watch.main()

    def test_stale_state_cannot_authorize_recovery_continuation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root=Path(directory);state=root/'supervisor-state.json';state.write_text('{"status":"continue"}')
            origin={'session':'gone','previous_log':str(root/'log'),
                    'started_ns':state.stat().st_mtime_ns+1}
            with patch.object(watch,'OUT',root), patch.object(watch,'record') as record, \
                 patch.object(watch,'supervisor_origin',return_value=origin), \
                 patch.object(watch,'origin_process_alive',return_value=False), \
                 patch.object(watch,'event_status',return_value=(True,None)), \
                 patch.object(watch.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='')), \
                 patch.object(watch.subprocess,'Popen',side_effect=AssertionError('duplicate resume')):
                watch.main()
            self.assertEqual(record.call_args.args[0],'blocked_missing_fresh_supervisor_state')


if __name__ == '__main__':
    unittest.main()
